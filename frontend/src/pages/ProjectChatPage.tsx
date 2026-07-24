import { Link, useParams } from 'react-router-dom'
import { ChatWindow } from '../components/chat/ChatWindow'
import { UploadConfirmationModal } from '../components/chat/UploadConfirmationModal'
import { ArrowLeftIcon, SparklesIcon } from '../components/icons/NavIcons'
import { useChatStream } from '../hooks/useChatStream'
import { useProjectDocuments } from '../hooks/useProjectDocuments'

export function ProjectChatPage() {
  const { id } = useParams<{ id: string }>()
  const { project, messages, loading, sending, streamingId, error, sendMessage, stopGeneration } =
    useChatStream(id)
  const {
    documents,
    uploading: documentsUploading,
    deletingId: deletingDocumentId,
    error: documentsError,
    setError: setDocumentsError,
    pendingUpload,
    uploadFiles,
    confirmPendingUpload,
    cancelPendingUpload,
    deleteDocument,
  } = useProjectDocuments(id)

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-violet-200 border-t-violet-600" />
      </div>
    )
  }

  if (error && !project) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-6">
        <p className="text-sm text-red-600">{error}</p>
        <Link to="/home" className="text-sm font-medium text-violet-600 hover:text-violet-700">
          ← Back to projects
        </Link>
      </div>
    )
  }

  if (!project) return null

  return (
    <div className="flex h-full flex-col bg-zinc-50/50 dark:bg-zinc-950">
      <div className="flex h-[60px] flex-shrink-0 items-center gap-4 border-b border-zinc-200/80 bg-white px-5 dark:border-zinc-800 dark:bg-zinc-900">
        <Link
          to="/home"
          className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <ArrowLeftIcon className="h-3.5 w-3.5" />
          Projects
        </Link>

        <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-700" />

        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600">
            <SparklesIcon className="h-3.5 w-3.5 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">{project.name}</h1>
            {project.system_prompt && (
              <p className="truncate text-[11px] text-zinc-400">{project.system_prompt}</p>
            )}
          </div>
        </div>

        <div className="hidden items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 sm:flex dark:border-violet-800 dark:bg-violet-950">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span className="text-[11px] font-medium text-violet-700 dark:text-violet-300">gpt-oss-120b</span>
        </div>
      </div>

      {(error || documentsError) && (
        <div className="mx-auto mt-3 w-full max-w-3xl px-4">
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-[13px] text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {documentsError ?? error}
            {documentsError && (
              <button
                type="button"
                onClick={() => setDocumentsError(null)}
                className="ml-2 underline hover:no-underline"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <ChatWindow
          messages={messages}
          projectId={project.id}
          onSend={sendMessage}
          onStop={stopGeneration}
          loading={sending}
          streamingId={streamingId}
          projectName={project.name}
          documents={documents}
          documentsUploading={documentsUploading}
          deletingDocumentId={deletingDocumentId}
          onDocumentUpload={uploadFiles}
          onDocumentDelete={deleteDocument}
        />
      </div>

      {pendingUpload && (
        <UploadConfirmationModal
          detail={pendingUpload.detail}
          filename={pendingUpload.file.name}
          uploading={documentsUploading}
          onContinue={() => void confirmPendingUpload()}
          onCancel={cancelPendingUpload}
        />
      )}
    </div>
  )
}
