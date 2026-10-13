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

test("GlzChoice renders accessible radio inputs but no submit action", () => {
  const source = 'root = GlzChoice("Preferred mode?", [{label: "Local", description: "Private processing"}, {label: "Offline", description: "No internet"}])';
  assert.equal(validateOpenUIProgram(source).ok, true);
  const markup = renderToStaticMarkup(createElement(Renderer, {
    response: source,
    library: glazeOpenUILibrary,
  }));
  assert.ok(markup.includes('type="radio"'));
  assert.ok(markup.includes("<fieldset"));
  assert.ok(markup.includes("No selection."));
  assert.ok(!markup.includes('type="submit"'));
});

test("GlzChoice bounds option counts, text and unknown object keys", () => {
  const cases = [
    'root = GlzChoice("Too few", [{label: "One", description: "Only option"}])',
    'root = GlzChoice("Unexpected key", [{label: "One", description: "First", action: "delete"}, {label: "Two", description: "Second"}])',
  ];
  for (const source of cases) assert.equal(validateOpenUIProgram(source).ok, false, source);
});
