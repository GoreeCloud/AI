import { validateOpenUIProgram } from "./program";

export type AcceptedLocalUI =
  | { ok: true; response: string; model: string }
  | { ok: false; reason: string };

/**
 * Accepts only the internal, source-normalized local Python bridge envelope.
 * A syntactically valid UI is presentation only, not permission for any action.
 */
export function acceptLocalOpenUICandidate(input: unknown): AcceptedLocalUI {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return { ok: false, reason: "Local model result unavailable." };
  }
  const value = input as Record<string, unknown>;
  const permitted = ["provider", "model", "processing", "response", "validation"];
  if (Object.keys(value).some(key => !permitted.includes(key))) {
    return { ok: false, reason: "Unexpected fields in local model result." };
  }
  if (value.provider !== "ollama" || value.processing !== "local" ||
      value.validation !== "not_validated" ||
      typeof value.model !== "string" ||
      !/^[A-Za-z0-9][A-Za-z0-9._/+:@-]{0,159}$/.test(value.model)) {
    return { ok: false, reason: "Unrecognized local model identity." };
  }
  const parsed = validateOpenUIProgram(value.response);
  if (!parsed.ok) {
    return { ok: false, reason: "Model response is not an approved interface." };
  }
  return { ok: true, response: value.response as string, model: value.model };
}
