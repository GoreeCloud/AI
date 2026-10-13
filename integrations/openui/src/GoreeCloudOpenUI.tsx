"use client";
import { useState } from "react";
import { Renderer } from "@openuidev/react-lang";
import { glazeOpenUILibrary } from "./glaze-library";
import { validateOpenUIResponse } from "./boundary.mjs";
import { validateOpenUIProgram } from "./program";

export interface GoreeCloudOpenUIProps {
  /** A validated, provider-normalized OpenUI Lang text response from a trusted GoreeCloud AI backend. */
  response: string | null;
  isStreaming?: boolean;
}
export function GoreeCloudOpenUI({ response, isStreaming = false }: GoreeCloudOpenUIProps) {
  const [renderError, setRenderError] = useState(false);
  if (response === null) return <p role="status">Waiting for interface output.</p>;
  const checked = validateOpenUIResponse(response);
  if (!checked.ok) return <p role="alert">Interface unavailable: {checked.reason}</p>;
  // Streaming fragments are incomplete; validate the full OpenUI parse once complete.
  const program = isStreaming ? { ok: true as const } : validateOpenUIProgram(response);
  if (!program.ok) return <p role="alert">Interface unavailable: {program.reason}</p>;
  return <section data-glz-openui="renderer" aria-label="AI-generated interactive presentation">
    <p><small>AI-generated interface · values require source verification</small></p>
    {renderError && <p role="alert">The interface could not be fully rendered.</p>}
    <Renderer
      response={response}
      library={glazeOpenUILibrary}
      isStreaming={isStreaming}
      onError={(errors) => setRenderError(errors.length > 0)}
    />
  </section>;
}
// Intentionally no toolProvider, onAction handler, or arbitrary component registration.
// Actions, mutations, data access, and authorization remain with GoreeCloud's backend capability broker.
