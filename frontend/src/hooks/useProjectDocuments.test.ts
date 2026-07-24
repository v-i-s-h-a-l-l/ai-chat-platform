import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { documentApi } from '../api/documents'
import { useProjectDocuments } from './useProjectDocuments'

vi.mock('../api/documents', () => ({
  documentApi: {
    list: vi.fn(),
    upload: vi.fn(),
    delete: vi.fn(),
    reprocess: vi.fn(),
  },
  validateDocumentFile: vi.fn(() => ({ ok: true as const, mime: 'application/pdf' })),
}))

vi.mock('../contexts/ToastContext', () => ({
  useToastOptional: () => ({ showToast: vi.fn() }),
}))

describe('useProjectDocuments', () => {
  beforeEach(() => {
    vi.mocked(documentApi.list).mockResolvedValue([])
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads documents for a project', async () => {
    vi.mocked(documentApi.list).mockResolvedValue([
      {
        id: 'doc-1',
        project_id: 'proj-1',
        filename: 'notes.pdf',
        mime_type: 'application/pdf',
        file_size: 100,
        status: 'ready',
        error_message: null,
        chunk_count: 3,
        created_at: '2026-01-01T00:00:00Z',
      },
    ])

    const { result } = renderHook(() => useProjectDocuments('proj-1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.documents).toHaveLength(1)
    expect(result.current.documents[0]?.filename).toBe('notes.pdf')
  })

  it('processes pending uploads after addFiles', async () => {
    vi.mocked(documentApi.upload).mockResolvedValue({
      message: 'Uploaded',
      document: {
        id: 'doc-2',
        project_id: 'proj-1',
        filename: 'report.pdf',
        mime_type: 'application/pdf',
        file_size: 200,
        status: 'processing',
        error_message: null,
        chunk_count: 0,
        created_at: '2026-01-01T00:00:00Z',
      },
    })

    const { result } = renderHook(() => useProjectDocuments('proj-1'))
    const file = new File(['%PDF-1.4'], 'report.pdf', { type: 'application/pdf' })

    await act(async () => {
      result.current.addFiles([file])
    })

    await waitFor(() => {
      expect(documentApi.upload).toHaveBeenCalledWith(
        'proj-1',
        file,
        expect.objectContaining({ confirmed: false }),
      )
    })

    await waitFor(() => {
      expect(result.current.uploadQueue.some((item) => item.status === 'uploading')).toBe(false)
    })
  })

  it('does not upload when projectId is missing', async () => {
    const { result } = renderHook(() => useProjectDocuments(undefined))
    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' })

    await act(async () => {
      result.current.addFiles([file])
    })

    expect(documentApi.upload).not.toHaveBeenCalled()
    expect(result.current.uploadQueue).toHaveLength(0)
  })
})
