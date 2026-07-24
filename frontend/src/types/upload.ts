export type UploadQueueStatus =
  "pending" | "invalid" | "uploading" | "success" | "error" | "confirmation";

export interface UploadQueueItem {
  id: string;
  file: File;
  status: UploadQueueStatus;
  progress: number;
  error?: string;
  /** Set after the user accepts an upload confirmation modal. */
  confirmed?: boolean;
}
