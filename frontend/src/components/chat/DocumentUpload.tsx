import {
  useCallback,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type ReactNode,
} from "react";

import type { ProjectDocument } from "../../types/document";

import type { UploadQueueItem } from "../../types/upload";

import { DOCUMENT_ACCEPT, MAX_UPLOAD_MB } from "../../api/documents";

import { PaperclipIcon, TrashIcon } from "../icons/NavIcons";

interface DocumentChipListProps {
  documents: ProjectDocument[];

  deletingId?: string | null;

  onDelete: (documentId: string) => void;
}

interface DocumentDropZoneProps {
  children: (openPicker: () => void) => ReactNode;

  disabled?: boolean;

  onAddFiles: (files: FileList | File[]) => void;
}

interface DocumentStatusBannerProps {
  uploading: boolean;

  documents: ProjectDocument[];

  uploadQueue?: UploadQueueItem[];
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;

  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(doc: ProjectDocument): string {
  if (doc.status === "ready") return "Ready";

  if (doc.status === "failed") return doc.error_message ?? "Failed";

  if (doc.error_message) return doc.error_message;

  return "Uploaded · Indexing…";
}

function showProcessingSpinner(doc: ProjectDocument): boolean {
  return doc.status === "processing" && !doc.error_message;
}

function statusClass(doc: ProjectDocument): string {
  if (doc.status === "ready") return "text-emerald-600 dark:text-emerald-400";

  if (doc.status === "failed" || doc.error_message) {
    return "text-red-600 dark:text-red-400";
  }

  return "text-amber-600 dark:text-amber-400";
}

function StatusSpinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-3 w-3 flex-shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent opacity-80 ${className}`}

      aria-hidden
    />
  );
}

function FileTypeIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"

        strokeLinejoin="round"

        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 18H15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0015 4.5h-4.086a1.125 1.125 0 00-.794.329l-2.829 2.828A1.125 1.125 0 006.75 7.5H5.25a2.25 2.25 0 00-2.25 2.25v9A2.25 2.25 0 005.25 21h3.75"
      />
    </svg>
  );
}

function queueStatusLabel(item: UploadQueueItem): string {
  switch (item.status) {
    case "pending":
      return "Ready to upload";

    case "uploading":
      return `Uploading… ${item.progress}%`;

    case "success":
      return "Uploaded";

    case "error":
      return item.error ?? "Upload failed";

    case "invalid":
      return item.error ?? "Invalid file";

    case "confirmation":
      return "Confirmation required";

    default:
      return "";
  }
}

function queueStatusClass(item: UploadQueueItem): string {
  switch (item.status) {
    case "success":
      return "text-emerald-600 dark:text-emerald-400";

    case "error":
    case "invalid":
      return "text-red-600 dark:text-red-400";

    case "uploading":
    case "confirmation":
      return "text-amber-600 dark:text-amber-400";

    default:
      return "text-zinc-500 dark:text-zinc-400";
  }
}

export function DocumentStatusBanner({
  uploading,
  documents,
  uploadQueue = [],
}: DocumentStatusBannerProps) {
  const indexing = documents.filter(
    (d) => d.status === "processing" && !d.error_message,
  );
  const uploadInFlight = uploadQueue.some((item) => item.status === "uploading");
  const showUploadBanner = uploading && uploadInFlight;

  if (!showUploadBanner && indexing.length === 0) return null;

  if (showUploadBanner) {
    return (
      <div
        role="status"

        className="mb-2 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] text-amber-900 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-200"
      >
        <StatusSpinner className="text-amber-700 dark:text-amber-300" />

        <span>
          <span className="font-semibold">Uploading…</span>

          <span className="text-amber-800/85 dark:text-amber-300/85">
            {" "}
            Sending file to the server. Indexing starts right after.
          </span>
        </span>
      </div>
    );
  }

  const names = indexing.map((d) => d.filename);

  const label =
    names.length === 1 ? `"${names[0]}"` : `${names.length} documents`;

  return (
    <div
      role="status"

      className="mb-2 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] text-amber-900 dark:border-amber-800/80 dark:bg-amber-950/50 dark:text-amber-100"
    >
      <StatusSpinner className="mt-0.5 text-amber-600 dark:text-amber-300" />

      <div className="min-w-0">
        <p>
          <span className="font-semibold">Uploaded · Indexing…</span>

          <span className="text-amber-800/85 dark:text-amber-200/85">
            {" "}
            {label} {names.length === 1 ? "is" : "are"} being prepared for chat.
          </span>
        </p>

        <p className="mt-0.5 text-amber-700/75 dark:text-amber-300/70">
          You can keep chatting. Answers can use{" "}
          {names.length === 1 ? "this file" : "these files"} once status shows
          Ready.
        </p>
      </div>
    </div>
  );
}

export function UploadQueueList({
  items,

  onRemove,
}: {
  items: UploadQueueItem[];

  onRemove: (id: string) => void;
}) {
  if (items.length === 0) return null;

  return (
    <div className="mb-2 space-y-1.5">
      {items.map((item) => {
        const canRemove =
          item.status === "pending" ||
          item.status === "invalid" ||
          item.status === "error";

        return (
          <div
            key={item.id}

            className={`group relative overflow-hidden rounded-xl border px-3 py-2.5 transition-all duration-200 ${
              item.status === "invalid" || item.status === "error"
                ? "border-red-200/80 bg-red-50/80 dark:border-red-900/60 dark:bg-red-950/30"
                : item.status === "success"
                  ? "border-emerald-200/80 bg-emerald-50/60 dark:border-emerald-900/50 dark:bg-emerald-950/20"
                  : "border-zinc-200/90 bg-zinc-50/90 dark:border-zinc-700/80 dark:bg-zinc-800/50"
            }`}
          >
            {(item.status === "uploading" || item.status === "success") && (
              <div
                className={`absolute inset-y-0 left-0 transition-all duration-300 ${
                  item.status === "success"
                    ? "w-full bg-emerald-400/15 dark:bg-emerald-500/10"
                    : "bg-amber-400/20 dark:bg-amber-500/15"
                }`}

                style={{ width: `${item.progress}%` }}

                aria-hidden
              />
            )}

            <div className="relative flex items-center gap-2.5">
              <div
                className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${
                  item.status === "invalid" || item.status === "error"
                    ? "bg-red-100 text-red-600 dark:bg-red-950/50 dark:text-red-400"
                    : item.status === "success"
                      ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
                      : "bg-white text-zinc-500 shadow-sm dark:bg-zinc-900 dark:text-zinc-400"
                }`}
              >
                {item.status === "uploading" ? (
                  <StatusSpinner />
                ) : item.status === "success" ? (
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : (
                  <FileTypeIcon className="h-4 w-4" />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium text-zinc-800 dark:text-zinc-100">
                  {item.file.name}
                </p>

                <p className={`truncate text-[11px] ${queueStatusClass(item)}`}>
                  {queueStatusLabel(item)}
                </p>
              </div>

              <span className="hidden text-[11px] text-zinc-400 sm:inline">
                {formatFileSize(item.file.size)}
              </span>

              {canRemove && (
                <button
                  type="button"

                  onClick={() => onRemove(item.id)}

                  aria-label={`Remove ${item.file.name}`}

                  className="rounded-lg p-1.5 text-zinc-400 opacity-70 transition hover:bg-zinc-200/80 hover:text-red-600 hover:opacity-100 dark:hover:bg-zinc-700 dark:hover:text-red-400"
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function DocumentChipList({
  documents,
  deletingId,
  onDelete,
}: DocumentChipListProps) {
  if (documents.length === 0) return null;

  return (
    <div className="mb-2 flex flex-wrap gap-2">
      {documents.map((doc) => (
        <div
          key={doc.id}

          className="group flex max-w-full items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-2.5 py-1.5 text-[12px] dark:border-zinc-700 dark:bg-zinc-800/80"

          title={
            doc.error_message
              ? doc.error_message
              : doc.status === "processing"
                ? "File uploaded — indexing embeddings in the background"
                : doc.filename
          }
        >
          <span className="max-w-[140px] truncate font-medium text-zinc-700 dark:text-zinc-200">
            {doc.filename}
          </span>

          <span className="text-zinc-400">·</span>

          <span
            className={`inline-flex items-center gap-1.5 truncate ${statusClass(doc)}`}
          >
            {showProcessingSpinner(doc) && <StatusSpinner />}

            {statusLabel(doc)}
          </span>

          {doc.status === "ready" && doc.chunk_count > 0 && (
            <>
              <span className="text-zinc-400">·</span>

              <span className="text-zinc-500">{doc.chunk_count} chunks</span>
            </>
          )}

          <span className="hidden text-zinc-400 sm:inline">
            {formatFileSize(doc.file_size)}
          </span>

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
  );
}

export function DocumentDropZone({
  children,

  disabled = false,

  onAddFiles,
}: DocumentDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const dragDepthRef = useRef(0);

  const [isDragging, setIsDragging] = useState(false);

  const hasFilePayload = useCallback((event: DragEvent) => {
    return Array.from(event.dataTransfer.types).includes("Files");
  }, []);

  const handleDragEnter = useCallback(
    (event: DragEvent) => {
      if (disabled || !hasFilePayload(event)) return;

      event.preventDefault();

      dragDepthRef.current += 1;

      setIsDragging(true);
    },

    [disabled, hasFilePayload],
  );

  const handleDragLeave = useCallback(
    (event: DragEvent) => {
      if (disabled || !hasFilePayload(event)) return;

      event.preventDefault();

      dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);

      if (dragDepthRef.current === 0) setIsDragging(false);
    },

    [disabled, hasFilePayload],
  );

  const handleDragOver = useCallback(
    (event: DragEvent) => {
      if (disabled || !hasFilePayload(event)) return;

      event.preventDefault();

      event.dataTransfer.dropEffect = "copy";
    },

    [disabled, hasFilePayload],
  );

  const handleDrop = useCallback(
    (event: DragEvent) => {
      if (disabled) return;

      event.preventDefault();

      dragDepthRef.current = 0;

      setIsDragging(false);

      const files = event.dataTransfer.files;

      if (files.length > 0) {
        onAddFiles(files);
      }
    },

    [disabled, onAddFiles],
  );

  function handleBrowseClick() {
    if (!disabled) inputRef.current?.click();
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;

    if (files && files.length > 0) {
      onAddFiles(files);
    }

    event.target.value = "";
  }

  return (
    <div
      className="relative flex h-full min-h-0 flex-col"

      onDragEnter={handleDragEnter}

      onDragLeave={handleDragLeave}

      onDragOver={handleDragOver}

      onDrop={handleDrop}
    >
      <input
        ref={inputRef}

        type="file"

        multiple

        accept={DOCUMENT_ACCEPT}

        onChange={handleFileChange}

        className="hidden"

        aria-hidden
      />

      {isDragging && (
        <div
          className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center bg-amber-500/8 backdrop-blur-[2px] transition-opacity duration-200 dark:bg-amber-400/10"

          aria-hidden
        >
          <div className="mx-4 flex max-w-md flex-col items-center rounded-2xl border-2 border-dashed border-amber-400/70 bg-white/95 px-8 py-10 text-center shadow-xl shadow-amber-500/10 dark:border-amber-500/50 dark:bg-zinc-900/95">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400">
              <PaperclipIcon className="h-7 w-7" />
            </div>

            <p className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Drop files to upload
            </p>

            <p className="mt-1.5 text-sm text-zinc-500 dark:text-zinc-400">
              PDF, Word, TXT, or Markdown · up to {MAX_UPLOAD_MB} MB each
            </p>
          </div>
        </div>
      )}

      {children(handleBrowseClick)}
    </div>
  );
}

interface AttachButtonProps {
  disabled?: boolean;

  onClick: () => void;
}

export function DocumentAttachButton({ disabled, onClick }: AttachButtonProps) {
  return (
    <button
      type="button"

      onClick={onClick}

      disabled={disabled}

      aria-label="Attach documents"

      title={`Attach files — PDF, Word (.docx), TXT, Markdown · max ${MAX_UPLOAD_MB} MB`}

      className="mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl text-zinc-500 transition hover:bg-zinc-100 hover:text-amber-700 disabled:cursor-not-allowed disabled:opacity-40 dark:text-zinc-400 dark:hover:bg-zinc-700 dark:hover:text-amber-400"
    >
      <PaperclipIcon className="h-4 w-4" />
    </button>
  );
}
