import { test } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { acceptLocalOpenUICandidate } from "../src/local-candidate";
import { GoreeCloudLocalOpenUI } from "../src/GoreeCloudLocalOpenUI";

const candidate = () => ({
  provider: "ollama",
  model: "local:latest",
  processing: "local",
  validation: "not_validated",
  response: 'root = GlzText("Local AI", "Synthetic fixture")',
});

test("the approved local gateway envelope renders a Glaze component", () => {
  const result = acceptLocalOpenUICandidate(candidate());
  assert.equal(result.ok, true);
  const html = renderToStaticMarkup(createElement(GoreeCloudLocalOpenUI, { candidate: candidate() }));
  assert.match(html, /Synthetic fixture/);
  assert.doesNotMatch(html, /role="alert"/);
});

test("refuse external identities and unknown envelope properties", () => {
  for (const change of [
    { provider: "openai" }, { processing: "external" },
    { model: "bad model!" }, { validation: "validated" },
    { response: 'root = ArbitraryCode("hidden")' },
    { response: 'root = GlzMetric("Missing")' },
    { extra: "not authorized" },
  ]) {
    const attempted = { ...candidate(), ...change };
    assert.equal(acceptLocalOpenUICandidate(attempted).ok, false);
    const html = renderToStaticMarkup(createElement(GoreeCloudLocalOpenUI, {candidate:attempted}));
    assert.match(html, /role="alert"/);
    assert.doesNotMatch(html, /Synthetic fixture/);
  }
});

test("fail closed for missing response and unsupported envelope shapes", () => {
  for (const value of [null, undefined, {}, [], "", 9, { ...candidate(), response: "" }]) {
    assert.equal(acceptLocalOpenUICandidate(value).ok, false);
  }
});
