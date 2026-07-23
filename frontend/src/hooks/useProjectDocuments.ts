import { useCallback, useEffect, useRef, useState } from 'react'
import { documentApi, validateDocumentFile } from '../api/documents'
import { getErrorMessage } from '../api/client'
import type { ProjectDocument } from '../types/document'

export function useProjectDocuments(projectId: string | undefined) {
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const reprocessingRef = useRef(false)

  const refresh = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const docs = await documentApi.list(projectId)
      setDocuments(docs)
      setError(null)

      const stuck = docs.filter((d) => d.status === 'processing' || d.status === 'failed')
      if (stuck.length > 0 && !reprocessingRef.current) {
        reprocessingRef.current = true
        try {
          const updated = await Promise.all(
            stuck.map((doc) => documentApi.reprocess(projectId, doc.id).catch(() => doc)),
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
  }, [projectId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      if (!projectId || uploading) return

      const fileArray = Array.from(files)
      if (fileArray.length === 0) return

      setUploading(true)
      setError(null)

      for (const file of fileArray) {
        const validation = validateDocumentFile(file)
        if (!validation.ok) {
          setError(validation.error)
          continue
        }

        try {
          const { document } = await documentApi.upload(projectId, file)
          setDocuments((prev) => [document, ...prev.filter((d) => d.id !== document.id)])
          if (document.status === 'failed') {
            setError(document.error_message ?? `Failed to process "${file.name}"`)
          }
        } catch (err) {
          setError(getErrorMessage(err))
        }
      }

      setUploading(false)
    },
    [projectId, uploading],
  )

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
    uploadFiles,
    deleteDocument,
    refresh,
  }
}
