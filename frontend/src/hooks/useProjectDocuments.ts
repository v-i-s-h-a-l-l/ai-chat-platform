import { useCallback, useEffect, useRef, useState } from "react";
import { documentApi, validateDocumentFile } from "../api/documents";
import { getErrorMessage } from "../api/client";
import {
  parseUploadConfirmationError,
  type UploadConfirmationDetail,
} from "../api/uploadValidation";
import { useToastOptional } from "../contexts/ToastContext";
import type { ProjectDocument } from "../types/document";
import type { UploadQueueItem } from "../types/upload";

const PROCESSING_POLL_MS = 3_000;
const SUCCESS_DISMISS_MS = 2_500;

function hasActiveUploads(queue: UploadQueueItem[]): boolean {
  return queue.some(
    (item) => item.status === "uploading" || item.status === "pending",
  );
}

function createQueueItem(file: File): UploadQueueItem {
  const validation = validateDocumentFile(file);
  if (!validation.ok) {
    return {
      id: crypto.randomUUID(),
      file,
      status: "invalid",
      progress: 0,
      error: validation.error,
    };
  }
  return {
    id: crypto.randomUUID(),
    file,
    status: "pending",
    progress: 0,
  };
}

export function useProjectDocuments(projectId: string | undefined) {
  const toast = useToastOptional();
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingUpload, setPendingUpload] = useState<{
    file: File;
    detail: UploadConfirmationDetail;
    queueId: string;
  } | null>(null);
  const reprocessingRef = useRef(false);
  const queueRef = useRef<UploadQueueItem[]>([]);
  const processingRef = useRef(false);

  const syncQueue = useCallback(
    (updater: (prev: UploadQueueItem[]) => UploadQueueItem[]) => {
      const next = updater(queueRef.current);
      queueRef.current = next;
      setUploadQueue(next);
    },
    [],
  );

  const listDocuments = useCallback(async () => {
    if (!projectId) return [];
    return documentApi.list(projectId);
  }, [projectId]);

  const refresh = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      setError(null);

      const failed = docs.filter((d) => d.status === "failed");
      if (failed.length > 0 && !reprocessingRef.current) {
        reprocessingRef.current = true;
        try {
          const updated = await Promise.all(
            failed.map((doc) =>
              documentApi.reprocess(projectId, doc.id).catch(() => doc),
            ),
          );
          setDocuments((prev) => {
            const byId = new Map(prev.map((d) => [d.id, d]));
            for (const doc of updated) {
              byId.set(doc.id, doc);
            }
            return Array.from(byId.values()).sort(
              (a, b) =>
                new Date(b.created_at).getTime() -
                new Date(a.created_at).getTime(),
            );
          });
        } finally {
          reprocessingRef.current = false;
        }
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [projectId, listDocuments]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!projectId) return;
    const hasProcessing = documents.some((doc) => doc.status === "processing");
    if (!hasProcessing) return;

    const intervalId = window.setInterval(async () => {
      try {
        const docs = await listDocuments();
        setDocuments(docs);
      } catch {
        // Keep polling silently; user can refresh manually if needed.
      }
    }, PROCESSING_POLL_MS);

    return () => window.clearInterval(intervalId);
  }, [projectId, documents, listDocuments]);

  const updateQueueItem = useCallback(
    (id: string, patch: Partial<UploadQueueItem>) => {
      syncQueue((prev) =>
        prev.map((item) => (item.id === id ? { ...item, ...patch } : item)),
      );
    },
    [syncQueue],
  );

  const dismissQueueItem = useCallback(
    (id: string, delayMs = 0) => {
      window.setTimeout(() => {
        syncQueue((prev) => prev.filter((item) => item.id !== id));
      }, delayMs);
    },
    [syncQueue],
  );

  const uploadSingleFile = useCallback(
    async (
      item: UploadQueueItem,
      confirmed = false,
    ): Promise<"success" | "confirmation_required" | "failed"> => {
      if (!projectId) return "failed";

      const userConfirmed = confirmed || item.confirmed === true;

      updateQueueItem(item.id, {
        status: "uploading",
        progress: 0,
        error: undefined,
      });

      try {
        const { document } = await documentApi.upload(projectId, item.file, {
          confirmed: userConfirmed,
          onProgress: (percent) =>
            updateQueueItem(item.id, { progress: percent }),
        });
        setDocuments((prev) => [
          document,
          ...prev.filter((d) => d.id !== document.id),
        ]);

        if (document.status === "failed") {
          const message =
            document.error_message ?? `Failed to process "${item.file.name}"`;
          updateQueueItem(item.id, {
            status: "error",
            progress: 100,
            error: message,
          });
          setError(message);
          return "failed";
        }

        updateQueueItem(item.id, { status: "success", progress: 100 });
        toast?.showToast(`Uploaded ${item.file.name}`);
        dismissQueueItem(item.id, SUCCESS_DISMISS_MS);
        return "success";
      } catch (err) {
        const confirmation = parseUploadConfirmationError(err);
        if (confirmation && !confirmed) {
          setPendingUpload({
            file: item.file,
            detail: confirmation,
            queueId: item.id,
          });
          updateQueueItem(item.id, { status: "confirmation", progress: 0 });
          return "confirmation_required";
        }
        const message = getErrorMessage(err);
        updateQueueItem(item.id, {
          status: "error",
          progress: 100,
          error: message,
        });
        setError(message);
        return "failed";
      }
    },
    [projectId, updateQueueItem, dismissQueueItem, toast],
  );

  const processQueue = useCallback(async () => {
    if (!projectId || processingRef.current) return;

    processingRef.current = true;
    setError(null);

    try {
      while (true) {
        const next = queueRef.current.find((item) => item.status === "pending");
        if (!next) break;

        const outcome = await uploadSingleFile(next);
        if (outcome === "confirmation_required") break;
      }
    } finally {
      processingRef.current = false;
      if (queueRef.current.some((item) => item.status === "pending")) {
        queueMicrotask(() => {
          void processQueue();
        });
      }
    }
  }, [projectId, uploadSingleFile]);

  useEffect(() => {
    if (!projectId) return;
    if (!uploadQueue.some((item) => item.status === "pending")) return;
    queueMicrotask(() => {
      void processQueue();
    });
  }, [projectId, uploadQueue, processQueue]);

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      if (!projectId) return;

      const fileArray = Array.from(files);
      if (fileArray.length === 0) return;

      const newItems = fileArray.map(createQueueItem);
      syncQueue((prev) => [...prev, ...newItems]);

      const invalidCount = newItems.filter(
        (item) => item.status === "invalid",
      ).length;
      if (invalidCount > 0) {
        setError(
          invalidCount === 1
            ? (newItems.find((item) => item.status === "invalid")?.error ??
                "Invalid file")
            : `${invalidCount} files could not be added. Check type and size (max 25 MB).`,
        );
      }

      if (newItems.some((item) => item.status === "pending")) {
        queueMicrotask(() => {
          void processQueue();
        });
      }
    },
    [projectId, syncQueue, processQueue],
  );

  const removeQueuedFile = useCallback(
    (id: string) => {
      syncQueue((prev) => {
        const item = prev.find((entry) => entry.id === id);
        if (!item || item.status === "uploading") return prev;
        return prev.filter((entry) => entry.id !== id);
      });
    },
    [syncQueue],
  );

  const confirmPendingUpload = useCallback(() => {
    if (!pendingUpload || !projectId) return;
    const { queueId } = pendingUpload;
    const otherActive = queueRef.current.some(
      (item) =>
        item.id !== queueId &&
        (item.status === "uploading" || item.status === "pending"),
    );
    if (otherActive) return;

    setError(null);
    setPendingUpload(null);
    updateQueueItem(queueId, { status: "pending", confirmed: true });
    void processQueue();
  }, [pendingUpload, projectId, updateQueueItem, processQueue]);

  const cancelPendingUpload = useCallback(() => {
    if (pendingUpload) {
      dismissQueueItem(pendingUpload.queueId);
    }
    setPendingUpload(null);
  }, [pendingUpload, dismissQueueItem]);

  const deleteDocument = useCallback(
    async (documentId: string) => {
      if (!projectId || deletingId) return;
      setDeletingId(documentId);
      setError(null);
      try {
        await documentApi.delete(projectId, documentId);
        setDocuments((prev) => prev.filter((d) => d.id !== documentId));
        toast?.showToast("Document removed");
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setDeletingId(null);
      }
    },
    [projectId, deletingId, toast],
  );

  return {
    documents,
    loading,
    uploading: hasActiveUploads(uploadQueue),
    uploadQueue,
    deletingId,
    error,
    setError,
    pendingUpload,
    addFiles,
    removeQueuedFile,
    confirmPendingUpload,
    cancelPendingUpload,
    deleteDocument,
    refresh,
  };
}
