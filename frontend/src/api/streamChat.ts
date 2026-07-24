import { refreshAccessToken } from './client'
import type { ChatMessage } from '../types/project'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface StreamChatHandlers {
  onMeta: (data: {
    user_message: ChatMessage
    web_search_used: boolean
    documents_used: boolean
  }) => void
  onToken: (content: string) => void
  onDone: (data: {
    assistant_message: ChatMessage
    web_search_used: boolean
    documents_used: boolean
  }) => void
  onStopped?: (data: {
    assistant_message: ChatMessage
    web_search_used: boolean
    documents_used: boolean
  }) => void
  onError: (detail: string) => void
}

function parseSseBlock(block: string): { event: string; data: string } | null {
  let event = 'message'
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7).trim()
    if (line.startsWith('data: ')) data = line.slice(6)
  }
  return data ? { event, data } : null
}

function postStream(projectId: string, message: string, signal?: AbortSignal): Promise<Response> {
  return fetch(`${API_URL}/projects/${projectId}/chat/stream`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
    signal,
  })
}

export async function streamChatMessage(
  projectId: string,
  message: string,
  handlers: StreamChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await postStream(projectId, message, signal)
  } catch (err) {
    if (signal?.aborted) return
    throw err
  }

  // fetch() bypasses the axios interceptor, so a 401 mid-stream (expired
  // access token) would otherwise never trigger a refresh. Retry once,
  // sharing the same single-flight refresh as the rest of the app.
  if (response.status === 401) {
    try {
      await refreshAccessToken()
      response = await postStream(projectId, message, signal)
    } catch {
      if (signal?.aborted) return
      // Refresh failed — fall through to normal error handling below using
      // the original 401 response.
    }
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : detail
    } catch {
      /* ignore */
    }
    handlers.onError(detail)
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    handlers.onError('Streaming not supported')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel()
        return
      }

      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''

      for (const block of blocks) {
        const parsed = parseSseBlock(block)
        if (!parsed) continue

        try {
          const payload = JSON.parse(parsed.data)
          switch (parsed.event) {
            case 'meta':
              handlers.onMeta(payload)
              break
            case 'token':
              handlers.onToken(payload.content)
              break
            case 'done':
              handlers.onDone(payload)
              break
            case 'stopped':
              handlers.onStopped?.(payload)
              break
            case 'error':
              handlers.onError(payload.detail ?? 'Unknown error')
              break
          }
        } catch {
          /* skip malformed events */
        }
      }
    }
  } catch (err) {
    if (signal?.aborted) return
    throw err
  }
}
