import axios from 'axios'
import { api } from './client'

export type ExportFormat = 'pdf' | 'docx' | 'xlsx' | 'md' | 'txt'

export interface ExportFormatsResponse {
  formats: ExportFormat[]
  excel_supported: boolean
}

const FORMAT_LABELS: Record<ExportFormat, string> = {
  pdf: 'PDF',
  docx: 'Word',
  xlsx: 'Excel',
  md: 'Markdown',
  txt: 'Text',
}

export function exportFormatLabel(format: ExportFormat): string {
  return FORMAT_LABELS[format]
}

export async function getExportFormats(
  projectId: string,
  messageId: string,
): Promise<ExportFormatsResponse> {
  const res = await api.get<ExportFormatsResponse>(
    `/projects/${projectId}/messages/${messageId}/export/formats`,
  )
  return res.data
}

async function readBlobErrorDetail(data: unknown): Promise<string | null> {
  if (!(data instanceof Blob)) return null
  try {
    const text = await data.text()
    const parsed = JSON.parse(text) as { detail?: unknown }
    if (typeof parsed.detail === 'string') return parsed.detail
    if (Array.isArray(parsed.detail)) {
      return parsed.detail.map((item) => String(item)).join(', ')
    }
  } catch {
    return null
  }
  return null
}

export async function downloadExport(
  projectId: string,
  messageId: string,
  format: ExportFormat,
): Promise<void> {
  try {
    const res = await api.get(`/projects/${projectId}/messages/${messageId}/export`, {
      params: { format },
      responseType: 'blob',
    })

    const disposition = res.headers['content-disposition'] as string | undefined
    const filenameMatch = disposition?.match(/filename="?([^"]+)"?/)
    const filename = filenameMatch?.[1] ?? `export.${format}`

    const url = window.URL.createObjectURL(res.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
      const detail = await readBlobErrorDetail(error.response.data)
      if (detail) {
        throw new Error(detail)
      }
    }
    throw error
  }
}

const EXPORT_INTENT_PATTERNS: Array<{ pattern: RegExp; format: ExportFormat }> = [
  { pattern: /\b(?:download|save|export).{0,20}\b(?:as|to)\s+pdf\b/i, format: 'pdf' },
  { pattern: /\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:word|docx?)\b/i, format: 'docx' },
  { pattern: /\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:excel|xlsx?)\b/i, format: 'xlsx' },
  { pattern: /\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:markdown|md)\b/i, format: 'md' },
  { pattern: /\b(?:download|save|export).{0,20}\b(?:as|to)\s+(?:text|txt)\b/i, format: 'txt' },
]

export function detectExportIntent(message: string): ExportFormat | null {
  const text = message.trim()
  if (!text) return null
  for (const { pattern, format } of EXPORT_INTENT_PATTERNS) {
    if (pattern.test(text)) return format
  }
  return null
}

export function isStructuredAssistantContent(content: string): boolean {
  const trimmed = content.trim()
  if (trimmed.length < 80) return false
  return (
    /^#{1,3}\s/m.test(trimmed) ||
    /^\s*[-*+]\s/m.test(trimmed) ||
    /^\s*\d+\.\s/m.test(trimmed) ||
    /\|.+\|/.test(trimmed) ||
    /^```/m.test(trimmed)
  )
}
