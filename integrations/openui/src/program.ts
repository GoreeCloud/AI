import { createParser } from "@openuidev/react-lang";
import { glazeOpenUILibrary } from "./glaze-library";
import { validateOpenUIResponse } from "./boundary.mjs";

const parser = createParser(glazeOpenUILibrary.toJSONSchema());

export type ProgramCheck = { ok: true } | { ok: false; reason: string };

/** Single-root, data-only Development subset. This is NOT an authorization boundary. */
export function validateOpenUIProgram(input: unknown): ProgramCheck {
  const initial = validateOpenUIResponse(input);
  if (!initial.ok) return initial;
  let result: ReturnType<typeof parser.parse>;
  try {
    result = parser.parse(input as string);
  } catch {
    return { ok: false, reason: "Malformed interface syntax." };
  }
  if (!result.root || result.root.partial || result.meta.incomplete ||
      result.meta.errors.length !== 0 ||
      result.meta.unresolved.length !== 0 ||
      result.meta.orphaned.length !== 0 ||
      result.meta.statementCount !== 1) {
    return { ok: false, reason: "A single complete, supported interface component is required." };
  }
  if (result.queryStatements.length > 0 || result.mutationStatements.length > 0 ||
      Object.keys(result.stateDeclarations).length > 0) {
    return { ok: false, reason: "Model-controlled tools and state are not allowed." };
  }
  const component = glazeOpenUILibrary.components[result.root.typeName];
  if (!component || !component.props.safeParse(result.root.props).success) {
    return { ok: false, reason: "Invalid component properties." };
  }
  return { ok: true };
}
