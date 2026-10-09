import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export const RUNTIME_EVIDENCE_USE_REGISTRY_VERSION = 1;

const MAX_REGISTRY_BYTES = 8 * 1024 * 1024;
const MAX_RECORDS = 10_000;
const OPAQUE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const HASH = /^sha256:[0-9a-f]{64}$/;
const STATES = new Set(["reserved", "revoked"]);
const RECORD_FIELDS = new Set(["schemaVersion", "evidenceHash", "requestHash", "state", "recordedAt"]);
const RFC3339 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/;

function hashOpaqueId(value) {
  return `sha256:${crypto.createHash("sha256").update(value, "utf8").digest("hex")}`;
}

function requireOpaqueId(value, name) {
  if (typeof value !== "string" || !OPAQUE_ID.test(value)) {
    throw new TypeError(`${name} must be a bounded opaque identifier`);
  }
}

function requireNow(now) {
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) {
    throw new TypeError("runtime evidence registry time must be a valid Date");
  }
  return now.toISOString();
}

function validateRecord(record, lineNumber) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) {
    throw new Error(`runtime evidence registry line ${lineNumber} must be an object`);
  }
  const unknown = Object.keys(record).filter((field) => !RECORD_FIELDS.has(field));
  if (unknown.length > 0) {
    throw new Error(`runtime evidence registry line ${lineNumber} has unknown fields: ${unknown.sort().join(", ")}`);
  }
  if (record.schemaVersion !== RUNTIME_EVIDENCE_USE_REGISTRY_VERSION) {
    throw new Error(`runtime evidence registry line ${lineNumber} has unsupported schema version`);
  }
  if (!HASH.test(record.evidenceHash) || !HASH.test(record.requestHash)) {
    throw new Error(`runtime evidence registry line ${lineNumber} has invalid hashed identifiers`);
  }
  if (!STATES.has(record.state)) {
    throw new Error(`runtime evidence registry line ${lineNumber} has invalid state`);
  }
  if (typeof record.recordedAt !== "string" || !RFC3339.test(record.recordedAt) || !Number.isFinite(Date.parse(record.recordedAt))) {
    throw new Error(`runtime evidence registry line ${lineNumber} has invalid recordedAt`);
  }
  return record;
}

/**
 * Development-only durable single-use/revocation registry for future authenticated
 * runtime evidence. Raw evidence/request identifiers are never persisted; only
 * SHA-256 digests are recorded in a restrictive JSONL file.
 *
 * This registry is necessary replay state, not proof of authenticated provenance.
 * Its results therefore never authorize execution, indexing, retrieval, or model
 * context by themselves.
 */
export class RuntimeEvidenceUseRegistry {
  constructor(filePath) {
    if (typeof filePath !== "string" || filePath.length === 0) {
      throw new TypeError("runtime evidence registry path is required");
    }
    this.filePath = path.resolve(filePath);
    fs.mkdirSync(path.dirname(this.filePath), { recursive: true, mode: 0o700 });
    const fd = fs.openSync(this.filePath, "a", 0o600);
    fs.closeSync(fd);
    fs.chmodSync(this.filePath, 0o600);
    this.#load();
  }

  reserve({ evidenceId, requestId }, now = new Date()) {
    requireOpaqueId(evidenceId, "evidenceId");
    requireOpaqueId(requestId, "requestId");
    const recordedAt = requireNow(now);
    const evidenceHash = hashOpaqueId(evidenceId);
    const requestHash = hashOpaqueId(requestId);
    const records = this.#load();
    const prior = records.filter((record) => record.evidenceHash === evidenceHash);
    const revoked = prior.some((record) => record.state === "revoked");
    const reserved = prior.some((record) => record.state === "reserved");
    if (revoked || reserved) {
      return Object.freeze({
        registryVersion: RUNTIME_EVIDENCE_USE_REGISTRY_VERSION,
        reserved: false,
        replayDetected: reserved,
        revoked,
        requestMatchesPriorReservation: prior.some(
          (record) => record.state === "reserved" && record.requestHash === requestHash,
        ),
        productionTrustedInput: false,
        executionAuthorized: false,
        indexingEligible: false,
        retrievalEligible: false,
        modelContextEligible: false,
      });
    }
    this.#append({
      schemaVersion: RUNTIME_EVIDENCE_USE_REGISTRY_VERSION,
      evidenceHash,
      requestHash,
      state: "reserved",
      recordedAt,
    });
    return Object.freeze({
      registryVersion: RUNTIME_EVIDENCE_USE_REGISTRY_VERSION,
      reserved: true,
      replayDetected: false,
      revoked: false,
      requestMatchesPriorReservation: false,
      productionTrustedInput: false,
      executionAuthorized: false,
      indexingEligible: false,
      retrievalEligible: false,
      modelContextEligible: false,
    });
  }

  revoke({ evidenceId, requestId }, now = new Date()) {
    requireOpaqueId(evidenceId, "evidenceId");
    requireOpaqueId(requestId, "requestId");
    const recordedAt = requireNow(now);
    const evidenceHash = hashOpaqueId(evidenceId);
    const requestHash = hashOpaqueId(requestId);
    const records = this.#load();
    const matchingReservation = records.some(
      (record) =>
        record.evidenceHash === evidenceHash &&
        record.requestHash === requestHash &&
        record.state === "reserved",
    );
    if (!matchingReservation) {
      return Object.freeze({ revoked: false, reason: "reservation_not_found", executionAuthorized: false });
    }
    if (records.some((record) => record.evidenceHash === evidenceHash && record.state === "revoked")) {
      return Object.freeze({ revoked: false, reason: "already_revoked", executionAuthorized: false });
    }
    this.#append({
      schemaVersion: RUNTIME_EVIDENCE_USE_REGISTRY_VERSION,
      evidenceHash,
      requestHash,
      state: "revoked",
      recordedAt,
    });
    return Object.freeze({ revoked: true, reason: null, executionAuthorized: false });
  }

  #load() {
    const stat = fs.statSync(this.filePath);
    if (stat.size > MAX_REGISTRY_BYTES) {
      throw new Error("runtime evidence registry exceeds bounded Development size");
    }
    const text = fs.readFileSync(this.filePath, "utf8");
    if (text.length === 0) return [];
    if (!text.endsWith("\n")) {
      throw new Error("runtime evidence registry has an incomplete final record");
    }
    const lines = text.slice(0, -1).split("\n");
    if (lines.length > MAX_RECORDS) {
      throw new Error("runtime evidence registry exceeds bounded Development record count");
    }
    return lines.map((line, index) => {
      let record;
      try {
        record = JSON.parse(line);
      } catch (error) {
        throw new Error(`runtime evidence registry line ${index + 1} is invalid JSON`, { cause: error });
      }
      return validateRecord(record, index + 1);
    });
  }

  #append(record) {
    validateRecord(record, 0);
    const payload = `${JSON.stringify(record)}\n`;
    const fd = fs.openSync(this.filePath, "a", 0o600);
    try {
      fs.writeFileSync(fd, payload, "utf8");
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
  }
}
