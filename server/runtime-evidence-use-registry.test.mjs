import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { RuntimeEvidenceUseRegistry } from "./runtime-evidence-use-registry.mjs";

function temporaryRegistry() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "goreecloud-ai-evidence-registry-"));
  return { directory, file: path.join(directory, "runtime-evidence.jsonl") };
}

test("reservation survives restart and blocks exact replay without authorizing execution", () => {
  const temp = temporaryRegistry();
  try {
    const first = new RuntimeEvidenceUseRegistry(temp.file);
    const reserved = first.reserve(
      { evidenceId: "evidence-001", requestId: "request-001" },
      new Date("2026-09-07T20:00:00Z"),
    );
    assert.equal(reserved.reserved, true);
    assert.equal(reserved.executionAuthorized, false);

    const reopened = new RuntimeEvidenceUseRegistry(temp.file);
    const replay = reopened.reserve(
      { evidenceId: "evidence-001", requestId: "request-001" },
      new Date("2026-09-07T20:00:01Z"),
    );
    assert.equal(replay.reserved, false);
    assert.equal(replay.replayDetected, true);
    assert.equal(replay.requestMatchesPriorReservation, true);
    assert.equal(replay.productionTrustedInput, false);
    assert.equal(replay.executionAuthorized, false);
  } finally {
    fs.rmSync(temp.directory, { recursive: true, force: true });
  }
});

test("cross-request evidence reuse is detected and raw identifiers are never persisted", () => {
  const temp = temporaryRegistry();
  try {
    const registry = new RuntimeEvidenceUseRegistry(temp.file);
    registry.reserve(
      { evidenceId: "evidence-sensitive-id", requestId: "request-original" },
      new Date("2026-09-07T20:00:00Z"),
    );
    const replay = registry.reserve(
      { evidenceId: "evidence-sensitive-id", requestId: "request-other" },
      new Date("2026-09-07T20:00:02Z"),
    );
    assert.equal(replay.replayDetected, true);
    assert.equal(replay.requestMatchesPriorReservation, false);

    const persisted = fs.readFileSync(temp.file, "utf8");
    assert.equal(persisted.includes("evidence-sensitive-id"), false);
    assert.equal(persisted.includes("request-original"), false);
    assert.match(persisted, /sha256:[0-9a-f]{64}/);
    assert.equal(fs.statSync(temp.file).mode & 0o077, 0);
  } finally {
    fs.rmSync(temp.directory, { recursive: true, force: true });
  }
});

test("revocation persists and prevents later reservation", () => {
  const temp = temporaryRegistry();
  try {
    const registry = new RuntimeEvidenceUseRegistry(temp.file);
    registry.reserve(
      { evidenceId: "evidence-002", requestId: "request-002" },
      new Date("2026-09-07T20:00:00Z"),
    );
    const revoked = registry.revoke(
      { evidenceId: "evidence-002", requestId: "request-002" },
      new Date("2026-09-07T20:00:03Z"),
    );
    assert.equal(revoked.revoked, true);
    assert.equal(revoked.executionAuthorized, false);

    const reopened = new RuntimeEvidenceUseRegistry(temp.file);
    const result = reopened.reserve(
      { evidenceId: "evidence-002", requestId: "request-002" },
      new Date("2026-09-07T20:00:04Z"),
    );
    assert.equal(result.reserved, false);
    assert.equal(result.revoked, true);
    assert.equal(result.executionAuthorized, false);
  } finally {
    fs.rmSync(temp.directory, { recursive: true, force: true });
  }
});

test("malformed durable registry fails closed", () => {
  const temp = temporaryRegistry();
  try {
    fs.mkdirSync(temp.directory, { recursive: true });
    fs.writeFileSync(temp.file, "not-json\n", { mode: 0o600 });
    assert.throws(() => new RuntimeEvidenceUseRegistry(temp.file), /invalid JSON/);
  } finally {
    fs.rmSync(temp.directory, { recursive: true, force: true });
  }
});
