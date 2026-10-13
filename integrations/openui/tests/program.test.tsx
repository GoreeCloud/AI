import { test } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Renderer } from "@openuidev/react-lang";
import { glazeOpenUILibrary } from "../src/glaze-library";
import { validateOpenUIProgram } from "../src/program";

test("valid positional OpenUI Lang renders the three approved Glaze components", () => {
  const cases = [
    ['root = GlzText("Hello", "Local mode")', "Local mode"],
    ['root = GlzNotice("Local", "No paid provider", "information")', "No paid provider"],
    ['root = GlzMetric("Requests", "7", "count", "Synthetic fixture", "2026-10-13T06:00:00Z", "measured")', "Synthetic fixture"],
  ] as const;
  for (const [source, expected] of cases) {
    assert.equal(validateOpenUIProgram(source).ok, true, source);
    const markup = renderToStaticMarkup(createElement(Renderer, {
      response: source,
      library: glazeOpenUILibrary,
    }));
    assert.ok(markup.includes(expected), source);
  }
});

test("reject unknown components, malformed syntax and invalid properties", () => {
  for (const source of [
    'root = Unknown("not-allowed")',
    'GlzText({heading:"Hello",text:"World"})',
    '<GlzText heading="Hello" text="World" />',
    'root = GlzMetric("Requests")',
    'root = GlzNotice("Notice", "Body", "dangerous")',
    'unused = "orphan"\nroot = GlzText("Hello", "World")',
    'root = GlzText("First", "One")\nextra = GlzText("Second", "Two")',
  ]) assert.equal(validateOpenUIProgram(source).ok, false, source);
});
