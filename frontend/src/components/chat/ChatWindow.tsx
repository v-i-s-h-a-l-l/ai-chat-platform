import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import type { ChatMessage } from "../../types/project";

import type { ProjectDocument } from "../../types/document";

import type { UploadQueueItem, ActivityLogEntry } from "../../types/upload";

import { MAX_UPLOAD_MB } from "../../api/documents";

import { useChatAutoScroll } from "../../hooks/useChatAutoScroll";

import { SendIcon, StopIcon } from "../icons/NavIcons";

import { YelloBotLogo } from "../brand/YelloBotLogo";

import {
  DocumentAttachButton,
  DocumentChipList,
  DocumentDropZone,
  DocumentStatusBanner,
  UploadQueueList,
} from "./DocumentUpload";

import { MessageBubble } from "./MessageBubble";

import { VoiceInputLazy } from "./VoiceInputLazy";

import { ScrollToBottomButton } from "./ScrollToBottomButton";

const VIRTUAL_MESSAGE_THRESHOLD = 50;

interface ChatWindowProps {
  messages: ChatMessage[];

  projectId?: string;

  onSend: (message: string) => Promise<void>;

  onStop?: () => void;

  loading: boolean;

  streamingId?: string | null;

  projectName?: string;

  documents?: ProjectDocument[];

  documentsUploading?: boolean;

  uploadQueue?: UploadQueueItem[];

  documentLogs?: Record<string, ActivityLogEntry[]>;

  deletingDocumentId?: string | null;

  onDocumentUpload?: (files: FileList | File[]) => void;

  onRemoveQueuedFile?: (id: string) => void;

  onDocumentDelete?: (documentId: string) => void;
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

  uploadQueue = [],

  documentLogs = {},

  deletingDocumentId = null,

  onDocumentUpload,

  onRemoveQueuedFile,

  onDocumentDelete,
}: ChatWindowProps) {
  const [input, setInput] = useState("");

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const bottomSentinelRef = useRef<HTMLDivElement>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const useVirtualList = messages.length > VIRTUAL_MESSAGE_THRESHOLD;

  const rowVirtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () => 128,
    overscan: 8,
  });

  const { showScrollToBottom, newMessageCount, scrollToBottom } =
    useChatAutoScroll({
      containerRef: scrollContainerRef,

      observeTargetRef: messagesContainerRef,

      bottomSentinelRef,

      messageCount: messages.length,

      streamingId: streamingId ?? null,
    });

  const submitMessage = useCallback(
    async (message: string) => {
      const trimmed = message.trim();
      if (!trimmed || loading) return;

      setInput("");

      if (textareaRef.current) textareaRef.current.style.height = "auto";

      await onSend(trimmed);
    },
    [loading, onSend],
  );

  async function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    await submitMessage(input);
  }

  const handleVoiceTranscript = useCallback(
    async (transcript: string) => {
      const trimmed = transcript.trim();
      if (!trimmed || loading) return;
      setInput(trimmed);
      await submitMessage(trimmed);
    },
    [loading, submitMessage],
  );

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();

      handleSubmit();
    }
  }

  function handleInput(e: ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);

    e.target.style.height = "auto";

    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  const uploadEnabled = Boolean(onDocumentUpload && onRemoveQueuedFile);

  function renderMessage(msg: ChatMessage) {
    return (
      <MessageBubble
        key={msg.id}
        role={msg.role as "user" | "assistant"}
        content={msg.content}
        messageId={msg.id}
        projectId={projectId}
        webSearchUsed={msg.web_search_used}
        documentsUsed={msg.documents_used}
        isStreaming={msg.id === streamingId}
        createdAt={msg.created_at}
      />
    );
  }

  const chatBody = (openPicker?: () => void) => (
    <>
      <div
        ref={scrollContainerRef}

        className="min-h-0 flex-1 overflow-y-auto [overflow-anchor:none]"

        data-chat-scroll-container
      >
        <div className="mx-auto max-w-[1280px] px-4 py-8 sm:px-6">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="mb-6 flex items-center justify-center">
                <YelloBotLogo size="xl" />
              </div>

              <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                Start a conversation
              </h3>

              <p className="mt-1.5 max-w-xs text-sm text-zinc-500 dark:text-zinc-400">
                {projectName
                  ? `Ask ${projectName} anything. Your messages are saved automatically.`
                  : "Send a message to begin chatting with YelloBot."}
              </p>

              {uploadEnabled && (
                <p className="mt-4 max-w-sm text-xs text-zinc-400 dark:text-zinc-500">
                  Drag and drop files anywhere in this chat, or use the attach
                  button below.
                </p>
              )}
            </div>
          )}

          <div
            ref={messagesContainerRef}
            className={useVirtualList ? "relative w-full" : "space-y-6"}
            style={
              useVirtualList
                ? { height: `${rowVirtualizer.getTotalSize()}px` }
                : undefined
            }
          >
            {useVirtualList
              ? rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const msg = messages[virtualRow.index];
                  return (
                    <div
                      key={msg.id}
                      data-index={virtualRow.index}
                      ref={rowVirtualizer.measureElement}
                      className="absolute left-0 top-0 w-full pb-6"
                      style={{ transform: `translateY(${virtualRow.start}px)` }}
                    >
                      {renderMessage(msg)}
                    </div>
                  );
                })
              : messages.map((msg) => renderMessage(msg))}

            <div
              ref={bottomSentinelRef}
              className="h-px w-full shrink-0"
              style={
                useVirtualList
                  ? {
                      position: "absolute",
                      top: rowVirtualizer.getTotalSize(),
                      left: 0,
                    }
                  : undefined
              }
              aria-hidden
            />
          </div>
        </div>
      </div>

      <div className="relative flex-shrink-0 border-t border-zinc-200/80 bg-white/80 px-4 py-4 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/80">
        <ScrollToBottomButton
          visible={showScrollToBottom}

          newMessageCount={newMessageCount}

          onClick={scrollToBottom}
        />

        <form onSubmit={handleSubmit} className="mx-auto max-w-[1280px]">
          {(uploadEnabled || onDocumentDelete) && (
            <DocumentStatusBanner
              uploading={documentsUploading}
              documents={documents}
              uploadQueue={uploadQueue}
              documentLogs={documentLogs}
            />
          )}

          {uploadEnabled && onRemoveQueuedFile && (
            <UploadQueueList
              items={uploadQueue}
              onRemove={onRemoveQueuedFile}
            />
          )}

          {onDocumentDelete && (
            <DocumentChipList
              documents={documents}

              deletingId={deletingDocumentId}

              documentLogs={documentLogs}

              onDelete={onDocumentDelete}
            />
          )}

          <div
            className={`flex items-end gap-2 rounded-2xl border bg-white p-2 shadow-sm transition focus-within:shadow-md dark:bg-zinc-800 ${
              uploadEnabled
                ? "border-zinc-200 focus-within:border-amber-300 focus-within:shadow-amber-500/10 dark:border-zinc-700 dark:focus-within:border-amber-500"
                : "border-zinc-200 focus-within:border-amber-300 dark:border-zinc-700"
            }`}
          >
            {uploadEnabled && openPicker && (
              <DocumentAttachButton onClick={openPicker} disabled={loading} />
            )}

            <VoiceInputLazy
              disabled={loading}
              onTranscript={handleVoiceTranscript}
            />

            <textarea
              ref={textareaRef}

              value={input}

              onChange={handleInput}

              onKeyDown={handleKeyDown}

              placeholder="Message YelloBot…"

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

                className="mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-brand text-zinc-900 shadow-sm transition hover:bg-brand-hover active:scale-95 enabled:hover:shadow-md enabled:hover:shadow-amber-500/20 disabled:cursor-not-allowed disabled:bg-zinc-100 disabled:text-zinc-400 disabled:shadow-none dark:disabled:bg-zinc-700 dark:disabled:text-zinc-500"
              >
                <SendIcon className="h-4 w-4" />
              </button>
            )}
          </div>

          <p className="mt-2 text-center text-[11px] text-zinc-400">
            Enter to send · Shift+Enter for new line
            {uploadEnabled &&
              ` · Drop files here or attach · PDF, DOCX, TXT, MD · max ${MAX_UPLOAD_MB} MB`}
          </p>
        </form>
      </div>
    </>
  );

  if (uploadEnabled && onDocumentUpload && onRemoveQueuedFile) {
    return (
      <DocumentDropZone
        disabled={loading}

        onAddFiles={onDocumentUpload}
      >
        {(openPicker) => (
          <div className="flex h-full min-h-0 flex-col">
            {chatBody(openPicker)}
          </div>
        )}
      </DocumentDropZone>
    );
  }

  return <div className="flex h-full min-h-0 flex-col">{chatBody()}</div>;
}
