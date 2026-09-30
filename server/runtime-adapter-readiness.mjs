export const RUNTIME_ADAPTER_READINESS_VERSION = 1;

const REQUIRED_EVIDENCE = Object.freeze([
  "identity_authenticated_transport",
  "identity_authoritative_source",
  "identity_actor_binding",
  "application_resource_authorization",
  "privacy_shield_authenticated_transport",
  "privacy_shield_authoritative_decision",
  "privacy_shield_request_decision_binding",
  "privacy_shield_resource_binding",
  "privacy_shield_operation_binding",
  "privacy_shield_unexpired_decision",
  "wardveil_authenticated_evidence",
  "wardveil_resource_binding",
  "wardveil_operation_binding",
]);

/**
 * Evaluate whether future authenticated runtime adapters have supplied every
 * explicitly required evidence class for the knowledge boundary.
 *
 * This Development helper cannot create trust or authorization by itself. It
 * intentionally keeps productionTrustedInput, persistentAuthorizationCreated,
 * and executionAuthorized false even when every readiness flag is present.
 * Actual trusted values must come from separately implemented and accepted
 * runtime adapters rather than caller-supplied JSON.
 */
export function assessRuntimeAdapterReadiness(evidence) {
  if (evidence === null || typeof evidence !== "object" || Array.isArray(evidence)) {
    throw new TypeError("runtime adapter evidence must be an object");
  }

  const unknown = Object.keys(evidence).filter((key) => !REQUIRED_EVIDENCE.includes(key));
  if (unknown.length > 0) {
    throw new TypeError(`unknown runtime adapter evidence fields: ${unknown.sort().join(", ")}`);
  }

  const missingEvidence = [];
  for (const key of REQUIRED_EVIDENCE) {
    if (evidence[key] !== true) {
      missingEvidence.push(key);
    }
  }

  return Object.freeze({
    contractVersion: RUNTIME_ADAPTER_READINESS_VERSION,
    adapterEvidenceReady: missingEvidence.length === 0,
    missingEvidence: Object.freeze(missingEvidence),
    productionTrustedInput: false,
    persistentAuthorizationCreated: false,
    executionAuthorized: false,
    indexingEligible: false,
    retrievalEligible: false,
    modelContextEligible: false,
  });
}

export const runtimeAdapterEvidenceRequirements = REQUIRED_EVIDENCE;
