export interface AvailableModel {
  id: string
  name: string
  description: string
  icon: string
  recommended?: boolean
}

export const DEFAULT_MODEL_ID = 'openai/gpt-oss-120b'

export const AVAILABLE_MODELS: AvailableModel[] = [
  {
    id: 'openai/gpt-oss-120b',
    name: 'GPT-OSS 120B',
    description: 'Best for reasoning, document analysis, RAG, planning, coding and complex tasks.',
    icon: '⭐',
    recommended: true,
  },
  {
    id: 'llama-3.3-70b-versatile',
    name: 'Llama 3.3 70B',
    description: 'Balanced model for conversations, creativity and everyday assistance.',
    icon: '🦙',
  },
  {
    id: 'qwen/qwen3.6-27b',
    name: 'Qwen 3.6 27B',
    description: 'Optimized for coding, debugging and technical problem solving.',
    icon: '💻',
  },
]

const MODEL_MAP = new Map(AVAILABLE_MODELS.map((model) => [model.id, model]))

export function getModelById(modelId: string | null | undefined): AvailableModel | undefined {
  if (!modelId) return undefined
  return MODEL_MAP.get(modelId)
}

export function resolveActiveModelId(
  projectModel: string | null | undefined,
  userModel: string | null | undefined,
): string {
  const candidates = [projectModel, userModel, DEFAULT_MODEL_ID]
  for (const candidate of candidates) {
    if (candidate && MODEL_MAP.has(candidate)) return candidate
  }
  return DEFAULT_MODEL_ID
}

export function filterModels(query: string): AvailableModel[] {
  const trimmed = query.trim().toLowerCase()
  if (!trimmed) return AVAILABLE_MODELS
  return AVAILABLE_MODELS.filter(
    (model) =>
      model.name.toLowerCase().includes(trimmed) ||
      model.description.toLowerCase().includes(trimmed) ||
      model.id.toLowerCase().includes(trimmed),
  )
}
