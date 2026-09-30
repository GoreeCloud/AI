import assert from "node:assert/strict";
import test from "node:test";

import { assessRuntimeEvidenceReplayPrecondition } from "./runtime-evidence-replay.mjs";

const REQUEST_ID = "knowledge-request-20260907-001";

test("exact request binding remains explicitly non-authorizing without durable replay state", () => {
  const result = assessRuntimeEvidenceReplayPrecondition(
    { evidenceId: "identity-evidence-001", requestId: REQUEST_ID },
    REQUEST_ID,
  );

  assert.equal(result.requestBindingSatisfied, true);
  assert.deepEqual(result.issues, []);
  assert.equal(result.durableSingleUseRegistryPresent, false);
  assert.equal(result.replayProtectionSatisfied, false);
  assert.equal(result.productionTrustedInput, false);
  assert.equal(result.persistentAuthorizationCreated, false);
  assert.equal(result.executionAuthorized, false);
  assert.equal(result.indexingEligible, false);
  assert.equal(result.retrievalEligible, false);
  assert.equal(result.modelContextEligible, false);
});

test("evidence cannot be structurally rebound to another request", () => {
  const result = assessRuntimeEvidenceReplayPrecondition(
    { evidenceId: "identity-evidence-001", requestId: "knowledge-request-previous" },
    REQUEST_ID,
  );

  assert.equal(result.requestBindingSatisfied, false);
  assert.deepEqual(result.issues, ["request_id_mismatch"]);
  assert.equal(result.replayProtectionSatisfied, false);
});

test("malformed identifiers fail closed", () => {
  const result = assessRuntimeEvidenceReplayPrecondition(
    { evidenceId: " ../evidence ", requestId: "request with spaces" },
    REQUEST_ID,
  );

  assert.equal(result.requestBindingSatisfied, false);
  assert.deepEqual(result.issues, ["invalid_evidence_id", "invalid_request_id"]);
});

test("unknown replay fields are rejected", () => {
  assert.throws(
    () => assessRuntimeEvidenceReplayPrecondition(
      { evidenceId: "identity-evidence-001", requestId: REQUEST_ID, used: false },
      REQUEST_ID,
    ),
    /unknown runtime evidence replay fields/,
  );
});
