import { FormEvent, KeyboardEvent, useRef, useState, type ChangeEvent } from 'react'
import type { ChatMessage } from '../../types/project'
import type { ProjectDocument } from '../../types/document'
import { useChatAutoScroll } from '../../hooks/useChatAutoScroll'
import { SendIcon, SparklesIcon, StopIcon } from '../icons/NavIcons'
import { DocumentChipList, DocumentUploadButton } from './DocumentUpload'
import { MessageBubble } from './MessageBubble'

interface ChatWindowProps {
  messages: ChatMessage[]
  projectId?: string
  onSend: (message: string) => Promise<void>
  onStop?: () => void
  loading: boolean
  streamingId?: string | null
  projectName?: string
  documents?: ProjectDocument[]
  documentsUploading?: boolean
  deletingDocumentId?: string | null
  onDocumentUpload?: (files: FileList | File[]) => void
  onDocumentDelete?: (documentId: string) => void
}

export function ChatWindow({
  messages,
  projectId,
  onSend,
  onStop,
  loading,
  streamingId,
  projectName,
  documents = [],
  documentsUploading = false,
  deletingDocumentId = null,
  onDocumentUpload,
  onDocumentDelete,
}: ChatWindowProps) {
  const [input, setInput] = useState('')
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useChatAutoScroll({
    containerRef: scrollContainerRef,
    observeTargetRef: messagesContainerRef,
    messageCount: messages.length,
    streamingId: streamingId ?? null,
  })

  async function handleSubmit(e?: FormEvent) {
    e?.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    await onSend(trimmed)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  function handleInput(e: ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-100 to-indigo-100">
                <SparklesIcon className="h-6 w-6 text-violet-600" />
              </div>
              <h3 className="text-base font-semibold text-zinc-900">
                Start a conversation
              </h3>
              <p className="mt-1.5 max-w-xs text-sm text-zinc-500">
                {projectName
                  ? `Ask ${projectName} anything. Your messages are saved automatically.`
                  : 'Send a message to begin chatting with your AI assistant.'}
              </p>
            </div>
          )}

          <div ref={messagesContainerRef} className="space-y-6">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                role={msg.role as 'user' | 'assistant'}
                content={msg.content}
                messageId={msg.id}
                projectId={projectId}
                webSearchUsed={msg.web_search_used}
                documentsUsed={msg.documents_used}
                isStreaming={msg.id === streamingId}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-zinc-200/80 bg-white/80 px-4 py-4 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/80">
        <form onSubmit={handleSubmit} className="mx-auto max-w-[1280px]">
          {onDocumentDelete && (
            <DocumentChipList
              documents={documents}
              deletingId={deletingDocumentId}
              onDelete={onDocumentDelete}
            />
          )}
          <div className="flex items-end gap-2 rounded-2xl border border-zinc-200 bg-white p-2 shadow-sm transition focus-within:border-violet-300 focus-within:shadow-md focus-within:shadow-violet-500/5 dark:border-zinc-700 dark:bg-zinc-800 dark:focus-within:border-violet-500">
            {onDocumentUpload && (
              <DocumentUploadButton
                uploading={documentsUploading}
                onUpload={onDocumentUpload}
                disabled={loading}
              />
            )}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Message your assistant…"
              disabled={loading}
              rows={1}
              className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-[0.9375rem] text-zinc-900 outline-none placeholder:text-zinc-400 disabled:opacity-60 dark:text-zinc-100 dark:placeholder:text-zinc-500"
            />
            {loading ? (
              <button
                type="button"
                onClick={onStop}
                aria-label="Stop generating"
                className="mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border border-zinc-300 bg-zinc-100 text-zinc-700 shadow-sm transition hover:bg-zinc-200 active:scale-95 dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-600"
              >
                <StopIcon className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-b from-violet-600 to-violet-700 text-white shadow-sm transition hover:from-violet-500 hover:to-violet-600 disabled:cursor-not-allowed disabled:opacity-40 active:scale-95"
              >
                <SendIcon className="h-4 w-4" />
              </button>
            )}
          </div>
          <p className="mt-2 text-center text-[11px] text-zinc-400">
            Enter to send · Shift+Enter for new line
            {onDocumentUpload && ' · Attach PDF, Word, TXT, or Markdown (indexed on upload)'}
          </p>
        </form>
      </div>
    </div>
  )
}
