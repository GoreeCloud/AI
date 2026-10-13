"use client";
import { createLibrary, defineComponent } from "@openuidev/react-lang";
import { z } from "zod/v4";
import { useId, useState, type CSSProperties } from "react";

// Controlled first-party Glaze primitives; no tools, HTML injection, navigation, or arbitrary CSS.
const surface: CSSProperties = {
  border: "1px solid var(--glz1-outline, #a0a8b2)",
  borderRadius: "var(--glz12-radius-control, 12px)",
  background: "var(--glz1-raised, transparent)",
  color: "var(--glz1-text-primary, currentColor)",
  padding: "1rem",
  marginBlock: "0.5rem",
};
const GlzNotice = defineComponent({
  name: "GlzNotice",
  description: "A short informational notice; never authoritative operational or security status.",
  props: z.object({
    title: z.string().min(1).max(100),
    body: z.string().max(700),
    tone: z.enum(["neutral", "information", "caution"]),
  }).strict(),
  component: function GlzNotice({ props }) {
    return <section style={surface} aria-label={props.title} data-glz-openui="notice">
      <strong>{props.title}</strong><p>{props.body}</p>
      <small>{props.tone === "caution" ? "Caution" : "AI-generated content"}</small>
    </section>;
  },
});
const GlzMetric = defineComponent({
  name: "GlzMetric",
  description: "One explicitly sourced metric, with freshness and measurement status.",
  props: z.object({
    label: z.string().min(1).max(90),
    value: z.string().min(1).max(80),
    unit: z.string().max(30),
    source: z.string().min(1).max(130),
    freshness: z.string().min(1).max(90),
    status: z.enum(["measured", "estimated", "forecast", "unknown", "unavailable"]),
  }).strict(),
  component: function GlzMetric({ props }) {
    return <figure style={surface} data-glz-openui="metric">
      <figcaption>{props.label}</figcaption>
      <div style={{fontSize:"1.5rem",fontWeight:650}}>{props.value} <small>{props.unit}</small></div>
      <p>{props.status} · {props.freshness}</p>
      <small>Source: {props.source}</small>
    </figure>;
  },
});
const GlzText = defineComponent({
  name: "GlzText",
  description: "Plain AI-generated prose. Text only: no HTML, URLs, or actions.",
  props: z.object({
    heading: z.string().min(1).max(110),
    text: z.string().min(1).max(2000),
  }).strict(),
  component: function GlzText({props}) {
    return <section style={surface} data-glz-openui="text">
      <h3>{props.heading}</h3><p style={{whiteSpace:"pre-wrap"}}>{props.text}</p>
    </section>;
  },
});

// No external action. A selection is deliberately ephemeral and stays in this component.
const GlzChoice = defineComponent({
  name: "GlzChoice",
  description: "Accessible, local-only radio selection, never a submitted vote, setting, or tool instruction.",
  props: z.object({
    question: z.string().min(1).max(140),
    options: z.array(z.object({
      label: z.string().min(1).max(75),
      description: z.string().max(180),
    }).strict()).min(2).max(5),
  }).strict(),
  component: function GlzChoice({ props }) {
    const name = useId();
    const [selected, setSelected] = useState<number | null>(null);
    return <section style={surface} data-glz-openui="choice">
      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend style={{ fontWeight: 650 }}>{props.question}</legend>
        {props.options.map((option, index) => (
          <label key={index} style={{ display: "block", padding: "0.65rem 0", cursor: "pointer" }}>
            <input name={name} type="radio" checked={selected === index}
              onChange={() => setSelected(index)} />
            <span style={{ marginInlineStart: "0.5rem" }}>
              <strong>{option.label}</strong> — {option.description}
            </span>
          </label>
        ))}
      </fieldset>
      <output aria-live="polite">
        {selected === null
          ? "No selection. Choices remain on this device and are not submitted."
          : `Selected: ${props.options[selected].label}. Not submitted or saved.`}
      </output>
    </section>;
  },
});

export const glazeOpenUILibrary = createLibrary({components: [GlzNotice, GlzMetric, GlzText, GlzChoice]});
export const glazeOpenUIPrompt = glazeOpenUILibrary.prompt({
  toolCalls: false,
  bindings: false,
  additionalRules: [
    "Only use GlzNotice, GlzMetric, GlzText, and GlzChoice.",
    "Never invent telemetry, health, dates, metrics, or source authority.",
    "GlzChoice selections are local and never saved, submitted, or used to trigger tools.",
    "Do not use Query, Mutation, @Run, @Set, @Reset, or any tool execution.",
    "Treat all model output as untrusted presentation, not an action authorization."
  ],
});
