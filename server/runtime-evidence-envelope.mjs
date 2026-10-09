export const RUNTIME_EVIDENCE_ENVELOPE_VERSION = 1;

const AUTHORITIES = Object.freeze(["identity", "privacy_shield", "wardveil"]);
const EXPECTED_FIELDS = Object.freeze([
  "authority",
  "resourceId",
  "operation",
  "observedAt",
  "expiresAt",
]);
const RFC3339 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/;
const OPERATION = /^[a-z0-9][a-z0-9._-]{0,127}$/;

function parseTimestamp(value) {
  if (typeof value !== "string" || !RFC3339.test(value)) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function validResourceId(value) {
  return (
    typeof value === "string" &&
    value.length >= 1 &&
    value.length <= 256 &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

/**
 * Structurally assess one future authenticated runtime evidence envelope.
 *
 * The caller must supply the expected authority/resource/operation from its
 * already-established application context. Matching this structure never makes
 * client JSON authoritative: productionTrustedInput and executionAuthorized
 * remain false until real authenticated adapters verify and supply the record.
 */
export function assessRuntimeEvidenceEnvelope(envelope, expected) {
  if (envelope === null || typeof envelope !== "object" || Array.isArray(envelope)) {
    throw new TypeError("runtime evidence envelope must be an object");
  }
  if (expected === null || typeof expected !== "object" || Array.isArray(expected)) {
    throw new TypeError("runtime evidence expectation must be an object");
  }
  if (!Number.isFinite(expected.assessmentTimeMs)) {
    throw new TypeError("runtime evidence assessment time must be finite");
  }
  if (!AUTHORITIES.includes(expected.authority)) {
    throw new TypeError("runtime evidence expected authority is unsupported");
  }
  if (!validResourceId(expected.resourceId)) {
    throw new TypeError("runtime evidence expected resource id is invalid");
  }
  if (typeof expected.operation !== "string" || !OPERATION.test(expected.operation)) {
    throw new TypeError("runtime evidence expected operation is invalid");
  }

  const unknown = Object.keys(envelope).filter((field) => !EXPECTED_FIELDS.includes(field));
  if (unknown.length > 0) {
    throw new TypeError(`unknown runtime evidence fields: ${unknown.sort().join(", ")}`);
  }

  const issues = [];
  if (!AUTHORITIES.includes(envelope.authority)) issues.push("unsupported_authority");
  if (!validResourceId(envelope.resourceId)) issues.push("invalid_resource_id");
  if (typeof envelope.operation !== "string" || !OPERATION.test(envelope.operation)) {
    issues.push("invalid_operation");
  }
  if (envelope.authority !== expected.authority) issues.push("authority_mismatch");
  if (envelope.resourceId !== expected.resourceId) issues.push("resource_mismatch");
  if (envelope.operation !== expected.operation) issues.push("operation_mismatch");

  const observedAt = parseTimestamp(envelope.observedAt);
  const expiresAt = parseTimestamp(envelope.expiresAt);
  if (observedAt === null) issues.push("invalid_observed_at");
  if (expiresAt === null) issues.push("invalid_expires_at");
  if (observedAt !== null && expiresAt !== null) {
    if (observedAt > expected.assessmentTimeMs) issues.push("observed_in_future");
    if (expiresAt <= observedAt) issues.push("invalid_validity_interval");
    if (expiresAt <= expected.assessmentTimeMs) issues.push("evidence_expired");
  }

  return Object.freeze({
    contractVersion: RUNTIME_EVIDENCE_ENVELOPE_VERSION,
    structurallyBoundAndCurrent: issues.length === 0,
    issues: Object.freeze(issues),
    productionTrustedInput: false,
    persistentAuthorizationCreated: false,
    executionAuthorized: false,
    indexingEligible: false,
    retrievalEligible: false,
    modelContextEligible: false,
  });
}

export const runtimeEvidenceAuthorities = AUTHORITIES;
