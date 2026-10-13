import { test } from "node:test";
import { strict as assert } from "node:assert";
import { MAX_OPENUI_RESPONSE_CHARS, validateOpenUIResponse } from "../src/boundary.mjs";
test("reject absent, oversized and binary-like output", () => {
  for (const x of [null, {}, "", "  ", "x".repeat(MAX_OPENUI_RESPONSE_CHARS + 1), "hello\u0000world"])
    assert.equal(validateOpenUIResponse(x).ok, false);
});
test("refuse executable/model-driven tool and state instructions", () => {
  for (const x of ["@Run tool()", "@Set state.value=1", "@Reset", "Query({})", "Mutation({})"])
    assert.equal(validateOpenUIResponse(x).ok, false, x);
});
test("accept syntactically valid, bounded inert OpenUI text", () => {
  assert.deepEqual(validateOpenUIResponse('root = GlzText("Hello", "World")'), { ok: true });
});
