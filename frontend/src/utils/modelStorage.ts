import { DEFAULT_MODEL_ID } from '../config/availableModels'

const USER_MODEL_KEY = 'yellobot:preferredModel'

export function readUserPreferredModel(): string | null {
  try {
    return localStorage.getItem(USER_MODEL_KEY)
  } catch {
    return null
  }
}

export function writeUserPreferredModel(modelId: string): void {
  try {
    localStorage.setItem(USER_MODEL_KEY, modelId)
  } catch {
    /* ignore quota / private mode */
  }
}

export function clearUserPreferredModel(): void {
  try {
    localStorage.removeItem(USER_MODEL_KEY)
  } catch {
    /* ignore */
  }
}

export function readUserPreferredModelOrDefault(): string {
  const stored = readUserPreferredModel()
  return stored ?? DEFAULT_MODEL_ID
}
