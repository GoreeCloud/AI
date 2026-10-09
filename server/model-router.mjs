/**
 * GoreeCloud AI's development-only, side-effect-free model-role selector.
 *
 * An administrator supplies explicit role approvals for discovered local model
 * names. Family preferences are only a deterministic tie-breaker; model names
 * never grant capabilities, tools, network access, or authorization.
 *
 * This module does not call Ollama, load model files, enable an inference
 * endpoint, or authorize external processing. Integration requires separate
 * runtime validation and GoreeCloud platform acceptance.
 */

export const MODEL_ROLES = Object.freeze([
  'reasoning', 'fast', 'general', 'coding', 'research', 'writing',
  'vision', 'multimodal', 'embedding', 'agent', 'creative', 'image',
  'experimental',
])

const ROLE_SET = new Set(MODEL_ROLES)
const FAMILY_SET = new Set(['gemma', 'qwen', 'other'])
const MODEL_NAME = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/

// Preferences are not declarations that a given installed model has a
// capability. A model must be individually approved for each requested role.
const ROLE_FAMILY_PREFERENCE = Object.freeze({
  reasoning: ['gemma', 'qwen', 'other'],
  fast: ['gemma', 'qwen', 'other'],
  general: ['gemma', 'qwen', 'other'],
  coding: ['qwen', 'gemma', 'other'],
  research: ['qwen', 'gemma', 'other'],
  writing: ['gemma', 'qwen', 'other'],
  vision: ['gemma', 'qwen', 'other'],
  multimodal: ['gemma', 'qwen', 'other'],
  embedding: ['qwen', 'gemma', 'other'],
  agent: ['qwen', 'gemma', 'other'],
  creative: ['gemma', 'qwen', 'other'],
  image: ['gemma', 'qwen', 'other'],
  experimental: ['gemma', 'qwen', 'other'],
})

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function validName(value) {
  return typeof value === 'string' && MODEL_NAME.test(value)
}

function invalid(reason) {
  return { status: 'invalid', reason }
}

function unavailable(reason) {
  return { status: 'unavailable', reason }
}

/**
 * @param {{ role: string, discoveredModels: Array<{name: string}>,
 *   approvedModels: Array<{name: string, family: 'gemma'|'qwen'|'other',
 *     roles: string[], priority?: number}>, preferredModel?: string }} request
 * @returns {{status:'selected', role:string, model:string, family:string,
 *   selection:'automatic'|'manual'}|{status:'invalid'|'unavailable',reason:string}}
 */
export function selectApprovedModel(request) {
  if (!isRecord(request)) return invalid('invalid_request')
  const { role, discoveredModels, approvedModels, preferredModel } = request
  if (!ROLE_SET.has(role)) return invalid('unsupported_role')
  if (!Array.isArray(discoveredModels) || !Array.isArray(approvedModels)) {
    return invalid('invalid_model_catalog')
  }
  if (preferredModel !== undefined && !validName(preferredModel)) {
    return invalid('invalid_preferred_model')
  }

  const installed = new Set()
  for (const model of discoveredModels) {
    if (!isRecord(model) || !validName(model.name) || installed.has(model.name)) {
      return invalid('invalid_discovered_model')
    }
    installed.add(model.name)
  }

  const approvedNames = new Set()
  const eligible = []
  for (const approval of approvedModels) {
    if (!isRecord(approval) || !validName(approval.name) ||
        !FAMILY_SET.has(approval.family) ||
        !Array.isArray(approval.roles) || approval.roles.length === 0 ||
        !approval.roles.every((entry) => ROLE_SET.has(entry)) ||
        new Set(approval.roles).size !== approval.roles.length ||
        (approval.priority !== undefined &&
          (!Number.isSafeInteger(approval.priority) || approval.priority < 0 || approval.priority > 1000)) ||
        approvedNames.has(approval.name)) {
      return invalid('invalid_model_approval')
    }
    approvedNames.add(approval.name)
    if (installed.has(approval.name) && approval.roles.includes(role)) eligible.push(approval)
  }

  if (preferredModel !== undefined) {
    const requested = eligible.find((entry) => entry.name === preferredModel)
    if (!requested) return unavailable('preferred_model_not_approved_and_installed_for_role')
    return { status: 'selected', role, model: requested.name, family: requested.family, selection: 'manual' }
  }

  if (eligible.length === 0) return unavailable('no_approved_installed_model_for_role')
  const families = ROLE_FAMILY_PREFERENCE[role]
  eligible.sort((left, right) =>
    (left.priority ?? 100) - (right.priority ?? 100) ||
    families.indexOf(left.family) - families.indexOf(right.family) ||
    left.name.localeCompare(right.name, 'en'),
  )
  const selected = eligible[0]
  return { status: 'selected', role, model: selected.name, family: selected.family, selection: 'automatic' }
}
