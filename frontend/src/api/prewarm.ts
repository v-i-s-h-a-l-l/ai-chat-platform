import { API_URL } from '../config/api'

const PREWARM_COOLDOWN_MS = 60_000
const PREWARM_TIMEOUT_MS = 45_000

let lastPrewarmAt = 0

/**
 * Best-effort wake-up for a cold Render API. Fire-and-forget; failures are ignored.
 */
export function prewarmApi(): void {
  const now = Date.now()
  if (now - lastPrewarmAt < PREWARM_COOLDOWN_MS) {
    return
  }
  lastPrewarmAt = now

  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), PREWARM_TIMEOUT_MS)

  fetch(`${API_URL}/health`, {
    method: 'GET',
    credentials: 'omit',
    signal: controller.signal,
  })
    .catch(() => {
      // Silent — pre-warm is opportunistic only.
    })
    .finally(() => {
      window.clearTimeout(timeoutId)
    })
}
