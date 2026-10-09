const OPAQUE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const EXPECTED_FIELDS = new Set(["evidenceId", "requestId"]);

export const RUNTIME_EVIDENCE_REPLAY_CONTRACT_VERSION = 1;

/**
 * Assess request binding for future authenticated runtime evidence.
 *
 * This deliberately does not claim anti-replay completion. Exact evidence and
 * request IDs are necessary structural preconditions, but GoreeCloud AI still
 * needs an authenticated durable single-use/revocation registry before runtime
 * evidence can be considered replay-protected or production trusted.
 */
export function assessRuntimeEvidenceReplayPrecondition(input, expectedRequestId) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("runtime evidence replay precondition must be an object");
  }
  const unknown = Object.keys(input).filter((field) => !EXPECTED_FIELDS.has(field));
  if (unknown.length > 0) {
    throw new TypeError(`unknown runtime evidence replay fields: ${unknown.sort().join(", ")}`);
  }
  if (typeof expectedRequestId !== "string" || !OPAQUE_ID.test(expectedRequestId)) {
    throw new TypeError("expected runtime evidence request id is invalid");
  }

  const issues = [];
  if (typeof input.evidenceId !== "string" || !OPAQUE_ID.test(input.evidenceId)) {
    issues.push("invalid_evidence_id");
  }
  if (typeof input.requestId !== "string" || !OPAQUE_ID.test(input.requestId)) {
    issues.push("invalid_request_id");
  } else if (input.requestId !== expectedRequestId) {
    issues.push("request_id_mismatch");
  }

  return Object.freeze({
    contractVersion: RUNTIME_EVIDENCE_REPLAY_CONTRACT_VERSION,
    requestBindingSatisfied: issues.length === 0,
    issues: Object.freeze([...issues]),
    durableSingleUseRegistryPresent: false,
    replayProtectionSatisfied: false,
    productionTrustedInput: false,
    persistentAuthorizationCreated: false,
    executionAuthorized: false,
    indexingEligible: false,
    retrievalEligible: false,
    modelContextEligible: false,
  });
}
