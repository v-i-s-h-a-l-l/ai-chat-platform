import { useCallback, useEffect, useRef, useState } from 'react'
import { documentApi, validateDocumentFile } from '../api/documents'
import { getErrorMessage } from '../api/client'
import { parseUploadConfirmationError, type UploadConfirmationDetail } from '../api/uploadValidation'
import type { ProjectDocument } from '../types/document'

const PROCESSING_POLL_MS = 3_000

export function useProjectDocuments(projectId: string | undefined) {
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pendingUpload, setPendingUpload] = useState<{
    file: File
    detail: UploadConfirmationDetail
  } | null>(null)
  const reprocessingRef = useRef(false)

  const listDocuments = useCallback(async () => {
    if (!projectId) return []
    return documentApi.list(projectId)
  }, [projectId])

  const refresh = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const docs = await listDocuments()
      setDocuments(docs)
      setError(null)

      const failed = docs.filter((d) => d.status === 'failed')
      if (failed.length > 0 && !reprocessingRef.current) {
        reprocessingRef.current = true
        try {
          const updated = await Promise.all(
            failed.map((doc) => documentApi.reprocess(projectId, doc.id).catch(() => doc)),
          )
          setDocuments((prev) => {
            const byId = new Map(prev.map((d) => [d.id, d]))
            for (const doc of updated) {
              byId.set(doc.id, doc)
            }
            return Array.from(byId.values()).sort(
              (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
            )
          })
        } finally {
          reprocessingRef.current = false
        }
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [projectId, listDocuments])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!projectId) return
    const hasProcessing = documents.some((doc) => doc.status === 'processing')
    if (!hasProcessing) return

    const intervalId = window.setInterval(async () => {
      try {
        const docs = await listDocuments()
        setDocuments(docs)
      } catch {
        // Keep polling silently; user can refresh manually if needed.
      }
    }, PROCESSING_POLL_MS)

    return () => window.clearInterval(intervalId)
  }, [projectId, documents, listDocuments])

  const uploadSingleFile = useCallback(
    async (file: File, confirmed = false): Promise<'success' | 'confirmation_required' | 'failed'> => {
      if (!projectId) return 'failed'

      try {
        const { document } = await documentApi.upload(projectId, file, { confirmed })
        setDocuments((prev) => [document, ...prev.filter((d) => d.id !== document.id)])
        if (document.status === 'failed') {
          setError(document.error_message ?? `Failed to process "${file.name}"`)
        }
        return 'success'
      } catch (err) {
        const confirmation = parseUploadConfirmationError(err)
        if (confirmation && !confirmed) {
          setPendingUpload({ file, detail: confirmation })
          return 'confirmation_required'
        }
        setError(getErrorMessage(err))
        return 'failed'
      }
    },
    [projectId],
  )

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      if (!projectId || uploading) return

      const fileArray = Array.from(files)
      if (fileArray.length === 0) return

      setUploading(true)
      setError(null)
      setPendingUpload(null)

      for (const file of fileArray) {
        const validation = validateDocumentFile(file)
        if (!validation.ok) {
          setError(validation.error)
          continue
        }

        const outcome = await uploadSingleFile(file)
        if (outcome === 'confirmation_required') {
          break
        }
      }

      setUploading(false)
    },
    [projectId, uploading, uploadSingleFile],
  )

  const confirmPendingUpload = useCallback(async () => {
    if (!pendingUpload || !projectId || uploading) return
    setUploading(true)
    setError(null)
    const { file } = pendingUpload
    setPendingUpload(null)
    await uploadSingleFile(file, true)
    setUploading(false)
  }, [pendingUpload, projectId, uploading, uploadSingleFile])

  const cancelPendingUpload = useCallback(() => {
    setPendingUpload(null)
  }, [])

  const deleteDocument = useCallback(
    async (documentId: string) => {
      if (!projectId || deletingId) return
      setDeletingId(documentId)
      setError(null)
      try {
        await documentApi.delete(projectId, documentId)
        setDocuments((prev) => prev.filter((d) => d.id !== documentId))
      } catch (err) {
        setError(getErrorMessage(err))
      } finally {
        setDeletingId(null)
      }
    },
    [projectId, deletingId],
  )

  return {
    documents,
    loading,
    uploading,
    deletingId,
    error,
    setError,
    pendingUpload,
    uploadFiles,
    confirmPendingUpload,
    cancelPendingUpload,
    deleteDocument,
    refresh,
  }
}
