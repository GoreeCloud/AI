export const MAX_OPENUI_RESPONSE_CHARS: number;
export type ResponseCheck = { ok: true; reason?: never } | { ok: false; reason: string };
export function validateOpenUIResponse(response: unknown): ResponseCheck;
