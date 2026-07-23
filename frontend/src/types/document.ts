export type DocumentStatus = 'processing' | 'ready' | 'failed'

export interface ProjectDocument {
  id: string
  project_id: string
  filename: string
  mime_type: string
  file_size: number
  status: DocumentStatus
  error_message: string | null
  chunk_count: number
  created_at: string
}

export interface DocumentUploadResponse {
  document: ProjectDocument
  message: string
}
