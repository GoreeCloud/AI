import { test } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Renderer } from "@openuidev/react-lang";
import { GoreeCloudOpenUI } from "../src/GoreeCloudOpenUI";
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

test("local choice interactions update the visible selection without a network action", async () => {
  const { JSDOM } = await import("jsdom");
  const dom = new JSDOM("<div id=\"root\"></div>", { url: "http://localhost/" });
  const previous = {
    window: globalThis.window,
    document: globalThis.document,
  };
  Object.assign(globalThis, {
    window: dom.window,
    document: dom.window.document,
    IS_REACT_ACT_ENVIRONMENT: true,
  });
  try {
    const { act } = await import("react");
    const { createRoot } = await import("react-dom/client");
    const container = dom.window.document.getElementById("root")!;
    const root = createRoot(container);
    const source = 'root = GlzChoice("Mode?", [{label: "Local", description: "Private"}, {label: "Offline", description: "No network"}])';
    await act(async () => {
      root.render(createElement("main", null,
        createElement(GoreeCloudOpenUI, { response: source }),
        createElement(GoreeCloudOpenUI, { response: 'root = Unknown("not-authorized")' }),
      ));
    });
    const alerts = [...container.querySelectorAll('[role="alert"]')].map(node => node.textContent ?? "");
    assert.equal(alerts.length, 1, "No false error message for the valid interface");
    assert.match(alerts[0], /Interface unavailable/);
    const radios = [...container.querySelectorAll<HTMLInputElement>('input[type="radio"]')];
    assert.equal(radios.length, 2);
    assert.equal(radios[0].checked, false);
    assert.equal(radios[1].checked, false);
    await act(async () => radios[1].click());
    assert.equal(radios[1].checked, true);
    assert.match(container.querySelector("output")?.textContent ?? "", /Selected: Offline. Not submitted or saved/);
    assert.equal(container.querySelector('button[type="submit"]'), null);
    // Model replaces the question in the same mounted renderer: never apply an old index.
    const changed = 'root = GlzChoice("New question?", [{label: "Fresh", description: "A new option"}, {label: "Other", description: "Different meaning"}])';
    await act(async () => {
      root.render(createElement("main", null,
        createElement(GoreeCloudOpenUI, { response: changed }),
        createElement(GoreeCloudOpenUI, { response: 'root = Unknown("not-authorized")' }),
      ));
    });
    const resetRadios = [...container.querySelectorAll<HTMLInputElement>('input[type="radio"]')];
    assert.equal(resetRadios.length, 2);
    assert.equal(resetRadios.every(radio => !radio.checked), true, "Selection resets on changed AI question");
    assert.match(container.querySelector("output")?.textContent ?? "", /No selection/);
    await act(async () => root.unmount());
  } finally {
    Object.assign(globalThis, previous);
    delete (globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT;
    dom.window.close();
  }
});
