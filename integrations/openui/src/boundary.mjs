// GoreeCloud AI Development: UI data boundary, not a security sandbox.
export const MAX_OPENUI_RESPONSE_CHARS = 48000;
const ACTIVE_SYNTAX = /(?:@Run\b|@Set\b|@Reset\b|\bQuery\s*\(|\bMutation\s*\()/i;
export function validateOpenUIResponse(response) {
  if (typeof response !== "string") return { ok: false, reason: "Response must be text." };
  if (!response.trim()) return { ok: false, reason: "No interface response available." };
  if (response.length > MAX_OPENUI_RESPONSE_CHARS) return { ok: false, reason: "Interface response exceeds size limit." };
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(response)) return { ok: false, reason: "Interface response contains disallowed control characters." };
  if (ACTIVE_SYNTAX.test(response)) return { ok: false, reason: "Tool calls and state mutations are disabled for this renderer." };
  return { ok: true };
}
