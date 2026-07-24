import { api } from './client'
import type { DocumentUploadResponse, ProjectDocument } from '../types/document'

const EXTENSION_MIME: Record<string, string> = {
  pdf: 'application/pdf',
  txt: 'text/plain',
  md: 'text/markdown',
  markdown: 'text/markdown',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

const SUPPORTED_MIMES = new Set(Object.values(EXTENSION_MIME))

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'heif'])

export const DOCUMENT_ACCEPT =
  '.pdf,.docx,.txt,.md,.markdown,image/*,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document'

export function inferMimeType(file: File): string {
  if (file.type && file.type !== 'application/octet-stream') {
    return file.type
  }
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext && EXTENSION_MIME[ext]) {
    return EXTENSION_MIME[ext]
  }
  return file.type || 'application/octet-stream'
}

export function validateDocumentFile(file: File): { ok: true; mime: string } | { ok: false; error: string } {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''

  if (IMAGE_EXTENSIONS.has(ext) || file.type.startsWith('image/')) {
    return {
      ok: false,
      error: `"${file.name}" is an image. Photo upload isn't supported yet — use PDF, Word (.docx), TXT, or Markdown.`,
    }
  }

  const mime = inferMimeType(file)
  if (!SUPPORTED_MIMES.has(mime)) {
    return {
      ok: false,
      error: `"${file.name}" isn't supported. Allowed: PDF, Word (.docx), TXT, Markdown (.md).`,
    }
  }

  return { ok: true, mime }
}

export const documentApi = {
  list(projectId: string): Promise<ProjectDocument[]> {
    return api.get<ProjectDocument[]>(`/projects/${projectId}/documents`).then((res) => res.data)
  },

  upload(projectId: string, file: File, options?: { confirmed?: boolean }): Promise<DocumentUploadResponse> {
    const form = new FormData()
    form.append('file', file)
    const headers: Record<string, string> = { 'Content-Type': 'multipart/form-data' }
    if (options?.confirmed) {
      headers['X-Upload-Confirm'] = 'true'
    }
    return api
      .post<DocumentUploadResponse>(`/projects/${projectId}/documents`, form, {
        headers,
        timeout: 60_000,
      })
      .then((res) => res.data)
  },

  delete(projectId: string, documentId: string): Promise<void> {
    return api.delete(`/projects/${projectId}/documents/${documentId}`).then(() => undefined)
  },

  reprocess(projectId: string, documentId: string): Promise<ProjectDocument> {
    return api
      .post<ProjectDocument>(`/projects/${projectId}/documents/${documentId}/reprocess`)
      .then((res) => res.data)
  },
}
