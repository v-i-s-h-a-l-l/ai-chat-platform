import { useCallback, useEffect, useRef, useState } from "react";
import { documentApi, validateDocumentFile } from "../api/documents";
import { getErrorMessage } from "../api/client";
import {
  parseUploadConfirmationError,
  type UploadConfirmationDetail,
} from "../api/uploadValidation";
import { useToastOptional } from "../contexts/ToastContext";
import type { ProjectDocument } from "../types/document";
import {
  appendActivityLog,
  INDEXING_ACTIVITY_STEPS,
  INDEXING_STEP_INTERVAL_MS,
  UPLOAD_PROGRESS_MILESTONES,
  type ActivityLogEntry,
  type UploadQueueItem,
} from "../types/upload";

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
      logs: appendActivityLog(undefined, validation.error),
    };
  }
  return {
    id: crypto.randomUUID(),
    file,
    status: "pending",
    progress: 0,
    logs: appendActivityLog(undefined, "Queued for upload"),
  };
}

function nextProgressMilestone(
  percent: number,
  lastLogged?: number,
): number | null {
  for (const milestone of UPLOAD_PROGRESS_MILESTONES) {
    if (percent >= milestone && (lastLogged ?? 0) < milestone) {
      return milestone;
    }
  }
  return null;
}

export function useProjectDocuments(projectId: string | undefined) {
  const toast = useToastOptional();
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([]);
  const [documentLogs, setDocumentLogs] = useState<
    Record<string, ActivityLogEntry[]>
  >({});
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
  const documentStatusRef = useRef<Map<string, string>>(new Map());

  const syncQueue = useCallback(
    (updater: (prev: UploadQueueItem[]) => UploadQueueItem[]) => {
      const next = updater(queueRef.current);
      queueRef.current = next;
      setUploadQueue(next);
    },
    [],
  );

  const appendQueueLog = useCallback(
    (id: string, message: string, patch?: Partial<UploadQueueItem>) => {
      syncQueue((prev) =>
        prev.map((item) => {
          if (item.id !== id) return item;
          return {
            ...item,
            ...patch,
            logs: appendActivityLog(item.logs, message),
          };
        }),
      );
    },
    [syncQueue],
  );

  const appendDocumentLog = useCallback(
    (documentId: string, message: string) => {
      setDocumentLogs((prev) => ({
        ...prev,
        [documentId]: appendActivityLog(prev[documentId], message),
      }));
    },
    [],
  );

  const seedDocumentIndexingLogs = useCallback(
    (documentId: string, queueLogs?: ActivityLogEntry[]) => {
      setDocumentLogs((prev) => {
        const merged = [...(queueLogs ?? []), ...(prev[documentId] ?? [])];
        const withUploadComplete = appendActivityLog(
          merged,
          "Upload complete — indexing started",
        );
        const withFirstStep = appendActivityLog(
          withUploadComplete,
          INDEXING_ACTIVITY_STEPS[0],
        );
        return { ...prev, [documentId]: withFirstStep };
      });
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

  useEffect(() => {
    for (const doc of documents) {
      const prevStatus = documentStatusRef.current.get(doc.id);
      if (prevStatus === "processing" && doc.status === "ready") {
        appendDocumentLog(
          doc.id,
          `Ready — ${doc.chunk_count} chunk${doc.chunk_count === 1 ? "" : "s"} indexed`,
        );
      } else if (
        prevStatus === "processing" &&
        doc.status === "failed" &&
        doc.error_message
      ) {
        appendDocumentLog(doc.id, doc.error_message);
      }
      documentStatusRef.current.set(doc.id, doc.status);
    }
  }, [documents, appendDocumentLog]);

  useEffect(() => {
    const processingDocs = documents.filter(
      (doc) => doc.status === "processing" && !doc.error_message,
    );
    if (processingDocs.length === 0) return;

    const intervalId = window.setInterval(() => {
      for (const doc of processingDocs) {
        setDocumentLogs((prev) => {
          const logs = prev[doc.id] ?? [];
          const currentStepIndex = INDEXING_ACTIVITY_STEPS.findIndex((step) =>
            logs.some((entry) => entry.message === step),
          );
          const nextIndex = currentStepIndex + 1;
          if (nextIndex >= INDEXING_ACTIVITY_STEPS.length) return prev;

          const nextStep = INDEXING_ACTIVITY_STEPS[nextIndex];
          if (logs.some((entry) => entry.message === nextStep)) return prev;

          return {
            ...prev,
            [doc.id]: appendActivityLog(logs, nextStep),
          };
        });
      }
    }, INDEXING_STEP_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [documents]);

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
        lastLoggedProgress: 0,
      });
      appendQueueLog(item.id, "Starting upload…");

      try {
        const { document } = await documentApi.upload(projectId, item.file, {
          confirmed: userConfirmed,
          onProgress: (percent) => {
            const current = queueRef.current.find((entry) => entry.id === item.id);
            const milestone = nextProgressMilestone(
              percent,
              current?.lastLoggedProgress,
            );
            if (milestone !== null) {
              appendQueueLog(item.id, `Uploaded ${milestone}%…`, {
                progress: percent,
                lastLoggedProgress: milestone,
              });
            } else {
              updateQueueItem(item.id, { progress: percent });
            }
          },
        });
        setDocuments((prev) => [
          document,
          ...prev.filter((d) => d.id !== document.id),
        ]);

        if (document.status === "failed") {
          const message =
            document.error_message ?? `Failed to process "${item.file.name}"`;
          appendQueueLog(item.id, message, {
            status: "error",
            progress: 100,
            error: message,
          });
          setError(message);
          return "failed";
        }

        const currentItem = queueRef.current.find((entry) => entry.id === item.id);
        seedDocumentIndexingLogs(document.id, currentItem?.logs);
        updateQueueItem(item.id, {
          status: "success",
          progress: 100,
          documentId: document.id,
          lastLoggedProgress: 100,
        });
        appendQueueLog(item.id, "Upload complete — indexing started");
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
          appendQueueLog(item.id, "Confirmation required before upload", {
            status: "confirmation",
            progress: 0,
          });
          return "confirmation_required";
        }
        const message = getErrorMessage(err);
        appendQueueLog(item.id, message, {
          status: "error",
          progress: 100,
          error: message,
        });
        setError(message);
        return "failed";
      }
    },
    [
      projectId,
      updateQueueItem,
      appendQueueLog,
      seedDocumentIndexingLogs,
      dismissQueueItem,
      toast,
    ],
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
    appendQueueLog(queueId, "Confirmation accepted — queued for upload");
    void processQueue();
  }, [pendingUpload, projectId, updateQueueItem, appendQueueLog, processQueue]);

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
        setDocumentLogs((prev) => {
          const next = { ...prev };
          delete next[documentId];
          return next;
        });
        documentStatusRef.current.delete(documentId);
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
    documentLogs,
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
