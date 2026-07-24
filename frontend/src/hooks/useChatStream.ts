import { useCallback, useEffect, useRef, useState } from 'react'
import { getErrorMessage } from '../api/client'
import { detectExportIntent, downloadExport } from '../api/export'
import { projectApi } from '../api/projects'
import type { ChatMessage, Project } from '../types/project'

interface UseChatStreamResult {
  project: Project | null
  messages: ChatMessage[]
  loading: boolean
  sending: boolean
  streamingId: string | null
  error: string
  sendMessage: (message: string) => Promise<void>
  stopGeneration: () => void
}

/**
 * Owns everything about a project's chat session: initial load, optimistic
 * messages, SSE streaming (with rAF-batched token flushing), and abort/stop.
 * ProjectChatPage only renders — all state lives here so it's reusable/testable
 * independent of the page's markup.
 */
export function useChatStream(projectId: string | undefined): UseChatStreamResult {
  const [project, setProject] = useState<Project | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [streamingId, setStreamingId] = useState<string | null>(null)
  const [error, setError] = useState('')

  const abortRef = useRef<AbortController | null>(null)
  const metaReceivedRef = useRef(false)
  const tokenBufferRef = useRef('')
  const tokenFlushRafRef = useRef<number | null>(null)

  const fetchData = useCallback(async () => {
    if (!projectId) return
    try {
      const [projectData, messageData] = await Promise.all([
        projectApi.get(projectId),
        projectApi.getMessages(projectId),
      ])
      setProject(projectData)
      setMessages(messageData)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchData()
    return () => abortRef.current?.abort()
  }, [fetchData])

  function flushBufferedTokens(streamMsgId: string) {
    if (tokenFlushRafRef.current !== null) return

    tokenFlushRafRef.current = requestAnimationFrame(() => {
      const chunk = tokenBufferRef.current
      tokenBufferRef.current = ''
      tokenFlushRafRef.current = null

      if (!chunk) return

      setMessages((prev) => {
        const index = prev.findIndex((m) => m.id === streamMsgId)
        if (index === -1) return prev
        const current = prev[index]
        const next = [...prev]
        next[index] = { ...current, content: current.content + chunk }
        return next
      })
    })
  }

  function appendStreamToken(streamMsgId: string, token: string) {
    tokenBufferRef.current += token
    flushBufferedTokens(streamMsgId)
  }

  function flushPendingTokens(): string | null {
    if (tokenFlushRafRef.current !== null) {
      cancelAnimationFrame(tokenFlushRafRef.current)
      tokenFlushRafRef.current = null
    }

    const chunk = tokenBufferRef.current
    tokenBufferRef.current = ''
    return chunk || null
  }

  function stopGeneration() {
    abortRef.current?.abort()
  }

  function finalizeStoppedStream(streamMsgId: string) {
    // The partial content already streamed in is correct as-is — no need to
    // refetch from the server; the backend persists the partial message
    // independently on disconnect.
    setMessages((prev) => {
      const streaming = prev.find((m) => m.id === streamMsgId)
      if (streaming && !streaming.content.trim()) {
        return prev.filter((m) => m.id !== streamMsgId)
      }
      return prev
    })
    setStreamingId(null)
  }

  const sendMessage = useCallback(
    async (message: string) => {
      if (!projectId || sending) return

      const exportFormat = detectExportIntent(message)
      if (exportFormat) {
        const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant' && m.content.trim())
        if (lastAssistant && !lastAssistant.id.startsWith('stream-')) {
          setError('')
          try {
            await downloadExport(projectId, lastAssistant.id, exportFormat)
          } catch (err) {
            setError(getErrorMessage(err))
          }
          return
        }
      }

      const streamMsgId = `stream-${Date.now()}`
      metaReceivedRef.current = false
      const optimisticUser: ChatMessage = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      }
      const optimisticAssistant: ChatMessage = {
        id: streamMsgId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, optimisticUser, optimisticAssistant])
      setSending(true)
      setStreamingId(streamMsgId)
      setError('')

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      try {
        await projectApi.streamMessage(
          projectId,
          message,
          {
            onMeta: ({ user_message, web_search_used, documents_used }) => {
              metaReceivedRef.current = true
              setMessages((prev) => {
                const assistantContent = prev.find((m) => m.id === streamMsgId)?.content ?? ''
                return [
                  ...prev.filter((m) => m.id !== optimisticUser.id && m.id !== streamMsgId),
                  user_message,
                  {
                    id: streamMsgId,
                    role: 'assistant',
                    content: assistantContent,
                    created_at: new Date().toISOString(),
                    web_search_used,
                    documents_used,
                  },
                ]
              })
            },
            onToken: (token) => {
              appendStreamToken(streamMsgId, token)
            },
            onDone: ({ assistant_message, web_search_used, documents_used }) => {
              const pending = flushPendingTokens()
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== streamMsgId) return m
                  if (pending) {
                    return {
                      ...assistant_message,
                      content: m.content + pending,
                      web_search_used,
                      documents_used,
                    }
                  }
                  return { ...assistant_message, web_search_used, documents_used }
                }),
              )
              setStreamingId(null)
            },
            onStopped: ({ assistant_message, web_search_used, documents_used }) => {
              const pending = flushPendingTokens()
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== streamMsgId) return m
                  if (pending) {
                    return {
                      ...assistant_message,
                      content: m.content + pending,
                      web_search_used,
                      documents_used,
                    }
                  }
                  return { ...assistant_message, web_search_used, documents_used }
                }),
              )
              setStreamingId(null)
            },
            onError: (detail) => {
              setMessages((prev) =>
                prev.filter((m) => m.id !== streamMsgId && m.id !== optimisticUser.id),
              )
              setError(detail)
              setStreamingId(null)
            },
          },
          controller.signal,
        )
      } catch (err) {
        if (controller.signal.aborted) {
          if (!metaReceivedRef.current) {
            setMessages((prev) =>
              prev.filter((m) => m.id !== streamMsgId && m.id !== optimisticUser.id),
            )
            setStreamingId(null)
          } else {
            finalizeStoppedStream(streamMsgId)
          }
          return
        }
        setMessages((prev) =>
          prev.filter((m) => m.id !== streamMsgId && m.id !== optimisticUser.id),
        )
        setError(getErrorMessage(err))
        setStreamingId(null)
      } finally {
        setSending(false)
      }
    },
    [projectId, sending, messages],
  )

  return { project, messages, loading, sending, streamingId, error, sendMessage, stopGeneration }
}
