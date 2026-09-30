import assert from "node:assert/strict";
import test from "node:test";

import {
  assessRuntimeAdapterReadiness,
  runtimeAdapterEvidenceRequirements,
} from "./runtime-adapter-readiness.mjs";

const allReady = Object.fromEntries(
  runtimeAdapterEvidenceRequirements.map((name) => [name, true]),
);

test("missing runtime evidence is explicit and fail closed", () => {
  const assessment = assessRuntimeAdapterReadiness({
    ...allReady,
    identity_authoritative_source: false,
    privacy_shield_request_decision_binding: false,
    wardveil_authenticated_evidence: false,
  });

  assert.equal(assessment.adapterEvidenceReady, false);
  assert.deepEqual(assessment.missingEvidence, [
    "identity_authoritative_source",
    "privacy_shield_request_decision_binding",
    "wardveil_authenticated_evidence",
  ]);
  assert.equal(assessment.productionTrustedInput, false);
  assert.equal(assessment.executionAuthorized, false);
  assert.equal(assessment.indexingEligible, false);
});

test("complete readiness evidence still cannot manufacture production trust", () => {
  const assessment = assessRuntimeAdapterReadiness(allReady);

  assert.equal(assessment.adapterEvidenceReady, true);
  assert.deepEqual(assessment.missingEvidence, []);
  assert.equal(assessment.productionTrustedInput, false);
  assert.equal(assessment.persistentAuthorizationCreated, false);
  assert.equal(assessment.executionAuthorized, false);
  assert.equal(assessment.indexingEligible, false);
  assert.equal(assessment.retrievalEligible, false);
  assert.equal(assessment.modelContextEligible, false);
});

test("unknown evidence fields fail closed instead of silently drifting", () => {
  assert.throws(
    () => assessRuntimeAdapterReadiness({ ...allReady, trust_me: true }),
    /unknown runtime adapter evidence fields: trust_me/,
  );
});

test("non-object evidence is rejected", () => {
  assert.throws(() => assessRuntimeAdapterReadiness(null), /must be an object/);
  assert.throws(() => assessRuntimeAdapterReadiness([]), /must be an object/);
});
