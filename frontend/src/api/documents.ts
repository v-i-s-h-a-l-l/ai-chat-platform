import { api } from "./client";
import type {
  DocumentUploadResponse,
  ProjectDocument,
} from "../types/document";

const EXTENSION_MIME: Record<string, string> = {
  pdf: "application/pdf",
  txt: "text/plain",
  md: "text/markdown",
  markdown: "text/markdown",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

const SUPPORTED_MIMES = new Set(Object.values(EXTENSION_MIME));

const IMAGE_EXTENSIONS = new Set([
  "jpg",
  "jpeg",
  "png",
  "webp",
  "gif",
  "bmp",
  "heic",
  "heif",
]);

export const MAX_UPLOAD_MB = 25;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

export const DOCUMENT_ACCEPT =
  ".pdf,.docx,.txt,.md,.markdown,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export function validateFileSize(
  file: File,
): { ok: true } | { ok: false; error: string } {
  if (file.size > MAX_UPLOAD_BYTES) {
    return {
      ok: false,
      error: `"${file.name}" exceeds the ${MAX_UPLOAD_MB} MB limit (${formatBytes(file.size)}).`,
    };
  }
  return { ok: true };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function inferMimeType(file: File): string {
  if (file.type && file.type !== "application/octet-stream") {
    return file.type;
  }
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (ext && EXTENSION_MIME[ext]) {
    return EXTENSION_MIME[ext];
  }
  return file.type || "application/octet-stream";
}

export function validateDocumentFile(
  file: File,
): { ok: true; mime: string } | { ok: false; error: string } {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";

  if (IMAGE_EXTENSIONS.has(ext) || file.type.startsWith("image/")) {
    return {
      ok: false,
      error: `"${file.name}" is an image. Photo upload isn't supported yet — use PDF, Word (.docx), TXT, or Markdown.`,
    };
  }

  const mime = inferMimeType(file);
  if (!SUPPORTED_MIMES.has(mime)) {
    return {
      ok: false,
      error: `"${file.name}" isn't supported. Allowed: PDF, Word (.docx), TXT, Markdown (.md).`,
    };
  }

  const sizeCheck = validateFileSize(file);
  if (!sizeCheck.ok) {
    return sizeCheck;
  }

  return { ok: true, mime };
}

export const documentApi = {
  list(projectId: string): Promise<ProjectDocument[]> {
    return api
      .get<ProjectDocument[]>(`/projects/${projectId}/documents`)
      .then((res) => res.data);
  },

  upload(
    projectId: string,
    file: File,
    options?: { confirmed?: boolean; onProgress?: (percent: number) => void },
  ): Promise<DocumentUploadResponse> {
    const form = new FormData();
    form.append("file", file);
    const headers: Record<string, string> = {
      "Content-Type": "multipart/form-data",
    };
    if (options?.confirmed) {
      headers["X-Upload-Confirm"] = "true";
    }
    return api
      .post<DocumentUploadResponse>(`/projects/${projectId}/documents`, form, {
        headers,
        timeout: 120_000,
        onUploadProgress: (event) => {
          if (!options?.onProgress || !event.total) return;
          options.onProgress(
            Math.min(100, Math.round((event.loaded / event.total) * 100)),
          );
        },
      })
      .then((res) => res.data);
  },

  delete(projectId: string, documentId: string): Promise<void> {
    return api
      .delete(`/projects/${projectId}/documents/${documentId}`)
      .then(() => undefined);
  },

  reprocess(projectId: string, documentId: string): Promise<ProjectDocument> {
    return api
      .post<ProjectDocument>(
        `/projects/${projectId}/documents/${documentId}/reprocess`,
      )
      .then((res) => res.data);
  },
};
