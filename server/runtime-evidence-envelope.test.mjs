import assert from "node:assert/strict";
import test from "node:test";

import { assessRuntimeEvidenceEnvelope } from "./runtime-evidence-envelope.mjs";

const expected = Object.freeze({
  authority: "privacy_shield",
  resourceId: "attachment:file-123",
  operation: "goreecloud-ai.knowledge.index",
  assessmentTimeMs: Date.parse("2026-09-06T15:00:00Z"),
});

const currentEnvelope = () => ({
  authority: "privacy_shield",
  resourceId: "attachment:file-123",
  operation: "goreecloud-ai.knowledge.index",
  observedAt: "2026-09-06T14:55:00Z",
  expiresAt: "2026-09-06T15:05:00Z",
});

test("matching current envelope remains structurally non-authorizing", () => {
  const result = assessRuntimeEvidenceEnvelope(currentEnvelope(), expected);
  assert.equal(result.structurallyBoundAndCurrent, true);
  assert.deepEqual(result.issues, []);
  assert.equal(result.productionTrustedInput, false);
  assert.equal(result.persistentAuthorizationCreated, false);
  assert.equal(result.executionAuthorized, false);
  assert.equal(result.indexingEligible, false);
  assert.equal(result.retrievalEligible, false);
  assert.equal(result.modelContextEligible, false);
});

test("authority resource and operation mismatches fail closed", () => {
  const envelope = currentEnvelope();
  envelope.authority = "identity";
  envelope.resourceId = "attachment:other";
  envelope.operation = "goreecloud-ai.knowledge.retrieve";
  const result = assessRuntimeEvidenceEnvelope(envelope, expected);
  assert.equal(result.structurallyBoundAndCurrent, false);
  assert.ok(result.issues.includes("authority_mismatch"));
  assert.ok(result.issues.includes("resource_mismatch"));
  assert.ok(result.issues.includes("operation_mismatch"));
});

test("expired future and impossible temporal evidence fail closed", () => {
  const expired = currentEnvelope();
  expired.observedAt = "2026-09-06T14:00:00Z";
  expired.expiresAt = "2026-09-06T14:30:00Z";
  assert.ok(assessRuntimeEvidenceEnvelope(expired, expected).issues.includes("evidence_expired"));

  const future = currentEnvelope();
  future.observedAt = "2026-09-06T15:01:00Z";
  future.expiresAt = "2026-09-06T15:10:00Z";
  assert.ok(assessRuntimeEvidenceEnvelope(future, expected).issues.includes("observed_in_future"));

  const impossible = currentEnvelope();
  impossible.observedAt = "2026-09-06T14:55:00Z";
  impossible.expiresAt = "2026-09-06T14:54:59Z";
  assert.ok(
    assessRuntimeEvidenceEnvelope(impossible, expected).issues.includes("invalid_validity_interval"),
  );
});

test("unknown fields and malformed bindings are rejected or blocked", () => {
  const unknown = { ...currentEnvelope(), trusted: true };
  assert.throws(() => assessRuntimeEvidenceEnvelope(unknown, expected), /unknown runtime evidence fields/);

  const malformed = currentEnvelope();
  malformed.resourceId = "bad\u0000id";
  malformed.observedAt = "yesterday";
  const result = assessRuntimeEvidenceEnvelope(malformed, expected);
  assert.ok(result.issues.includes("invalid_resource_id"));
  assert.ok(result.issues.includes("invalid_observed_at"));
  assert.equal(result.executionAuthorized, false);
});
