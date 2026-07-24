export type UploadQueueStatus =
  "pending" | "invalid" | "uploading" | "success" | "error" | "confirmation";

export interface ActivityLogEntry {
  id: string;
  at: string;
  message: string;
}

export interface UploadQueueItem {
  id: string;
  file: File;
  status: UploadQueueStatus;
  progress: number;
  error?: string;
  /** Set after the user accepts an upload confirmation modal. */
  confirmed?: boolean;
  logs?: ActivityLogEntry[];
  documentId?: string;
  lastLoggedProgress?: number;
}

export function createActivityLog(message: string): ActivityLogEntry {
  return {
    id: crypto.randomUUID(),
    at: new Date().toISOString(),
    message,
  };
}

export function appendActivityLog(
  logs: ActivityLogEntry[] | undefined,
  message: string,
): ActivityLogEntry[] {
  const prev = logs ?? [];
  if (prev.length > 0 && prev[prev.length - 1]?.message === message) {
    return prev;
  }
  return [...prev, createActivityLog(message)];
}

export const UPLOAD_PROGRESS_MILESTONES = [10, 25, 50, 75, 100] as const;

export const INDEXING_ACTIVITY_STEPS = [
  "Extracting text from document…",
  "Splitting into searchable chunks…",
  "Generating embeddings…",
  "Indexing for chat…",
] as const;

export const INDEXING_STEP_INTERVAL_MS = 7_000;
