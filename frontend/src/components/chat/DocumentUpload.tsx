import { useRef, type ChangeEvent } from 'react'
import { DOCUMENT_ACCEPT } from '../../api/documents'
import type { ProjectDocument } from '../../types/document'
import { PaperclipIcon, TrashIcon } from '../icons/NavIcons'

interface DocumentChipListProps {
  documents: ProjectDocument[]
  deletingId?: string | null
  onDelete: (documentId: string) => void
}

interface DocumentUploadButtonProps {
  uploading: boolean
  onUpload: (files: FileList | File[]) => void
  disabled?: boolean
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function statusLabel(doc: ProjectDocument): string {
  if (doc.status === 'ready') return 'Ready'
  if (doc.status === 'failed') return doc.error_message ?? 'Failed'
  return 'Processing…'
}

function statusClass(doc: ProjectDocument): string {
  if (doc.status === 'ready') return 'text-emerald-600 dark:text-emerald-400'
  if (doc.status === 'failed') return 'text-red-600 dark:text-red-400'
  return 'text-amber-600 dark:text-amber-400'
}

export function DocumentChipList({ documents, deletingId, onDelete }: DocumentChipListProps) {
  if (documents.length === 0) return null

  return (
    <div className="mb-2 flex flex-wrap gap-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="group flex max-w-full items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-2.5 py-1.5 text-[12px] dark:border-zinc-700 dark:bg-zinc-800/80"
          title={doc.status === 'failed' ? doc.error_message ?? undefined : doc.filename}
        >
          <span className="max-w-[140px] truncate font-medium text-zinc-700 dark:text-zinc-200">
            {doc.filename}
          </span>
          <span className="text-zinc-400">·</span>
          <span className={`truncate ${statusClass(doc)}`}>{statusLabel(doc)}</span>
          {doc.status === 'ready' && doc.chunk_count > 0 && (
            <>
              <span className="text-zinc-400">·</span>
              <span className="text-zinc-500">{doc.chunk_count} chunks</span>
            </>
          )}
          <span className="hidden text-zinc-400 sm:inline">{formatFileSize(doc.file_size)}</span>
          <button
            type="button"
            onClick={() => onDelete(doc.id)}
            disabled={deletingId === doc.id}
            aria-label={`Remove ${doc.filename}`}
            className="ml-0.5 rounded-md p-1 text-zinc-400 transition hover:bg-zinc-200 hover:text-red-600 disabled:opacity-50 dark:hover:bg-zinc-700 dark:hover:text-red-400"
          >
            {deletingId === doc.id ? (
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-zinc-300 border-t-red-500" />
            ) : (
              <TrashIcon className="h-3 w-3" />
            )}
          </button>
        </div>
      ))}
    </div>
  )
}

export function DocumentUploadButton({ uploading, onUpload, disabled }: DocumentUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handlePickClick() {
    inputRef.current?.click()
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (files && files.length > 0) {
      void onUpload(files)
    }
    e.target.value = ''
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={DOCUMENT_ACCEPT}
        onChange={handleFileChange}
        className="hidden"
        aria-hidden
      />
      <button
        type="button"
        onClick={handlePickClick}
        disabled={disabled || uploading}
        aria-label="Upload documents"
        title="Upload PDF, Word (.docx), TXT, or Markdown"
        className="mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl text-zinc-500 transition hover:bg-zinc-100 hover:text-violet-600 disabled:cursor-not-allowed disabled:opacity-40 dark:text-zinc-400 dark:hover:bg-zinc-700 dark:hover:text-violet-400"
      >
        {uploading ? (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-violet-600 dark:border-zinc-600 dark:border-t-violet-400" />
        ) : (
          <PaperclipIcon className="h-4 w-4" />
        )}
      </button>
    </>
  )
}
