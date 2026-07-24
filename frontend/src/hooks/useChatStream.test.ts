import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { projectApi } from '../api/projects'
import { useChatStream } from './useChatStream'

vi.mock('../api/projects', () => ({
  projectApi: {
    get: vi.fn(),
    getMessages: vi.fn(),
    update: vi.fn(),
    streamMessage: vi.fn(),
  },
}))

vi.mock('../api/auth', () => ({
  userApi: { updateMe: vi.fn() },
}))

vi.mock('../api/export', () => ({
  detectExportIntent: vi.fn(() => null),
  downloadExport: vi.fn(),
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      email: 'user@example.com',
      name: 'User',
      preferred_llm_model: null,
    },
    setUser: vi.fn(),
    refreshSession: vi.fn(),
    clearSession: vi.fn(),
  }),
}))

vi.mock('../contexts/ProjectsContext', () => ({
  useProjectsOptional: () => null,
}))

vi.mock('../contexts/ToastContext', () => ({
  useToastOptional: () => null,
}))

describe('useChatStream', () => {
  beforeEach(() => {
    vi.mocked(projectApi.get).mockResolvedValue({
      id: 'proj-1',
      name: 'Test Project',
      description: '',
      system_prompt: '',
      llm_model: null,
      is_pinned: false,
      last_accessed_at: null,
      created_at: '2026-01-01T00:00:00Z',
    })
    vi.mocked(projectApi.getMessages).mockResolvedValue([])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads project and messages on mount', async () => {
    const { result } = renderHook(() => useChatStream('proj-1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.project?.name).toBe('Test Project')
    expect(result.current.messages).toEqual([])
  })

  it('adds optimistic messages when sending', async () => {
    vi.mocked(projectApi.streamMessage).mockImplementation(
      async (_projectId, _message, _model, handlers) => {
        await handlers.onMeta?.({
          user_message: {
            id: 'user-1',
            role: 'user',
            content: 'Hello',
            created_at: '2026-01-01T00:00:00Z',
          },
          web_search_used: false,
          documents_used: false,
        })
        await handlers.onDone?.({
          assistant_message: {
            id: 'assistant-1',
            role: 'assistant',
            content: 'Hi',
            created_at: '2026-01-01T00:00:00Z',
          },
          web_search_used: false,
          documents_used: false,
        })
      },
    )

    const { result } = renderHook(() => useChatStream('proj-1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.sendMessage('Hello')
    })

    expect(projectApi.streamMessage).toHaveBeenCalled()
    expect(result.current.messages.some((m) => m.role === 'user')).toBe(true)
    expect(result.current.messages.some((m) => m.role === 'assistant')).toBe(true)
    expect(result.current.sending).toBe(false)
  })

  it('aborts in-flight stream when stopGeneration is called', async () => {
    let capturedSignal: AbortSignal | undefined

    vi.mocked(projectApi.streamMessage).mockImplementation(
      async (_projectId, _message, _model, _handlers, signal) => {
        capturedSignal = signal
        await new Promise(() => {
          /* hang until aborted */
        })
      },
    )

    const { result } = renderHook(() => useChatStream('proj-1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      void result.current.sendMessage('Hello')
    })

    await waitFor(() => {
      expect(result.current.sending).toBe(true)
    })

    act(() => {
      result.current.stopGeneration()
    })

    await waitFor(() => {
      expect(capturedSignal?.aborted).toBe(true)
    })
  })
})
