import { memo, useEffect, useRef, useState } from 'react'
import { getErrorMessage } from '../../api/client'
import {
  detectExportIntent,
  downloadExport,
  exportFormatLabel,
  getExportFormats,
  isStructuredAssistantContent,
  type ExportFormat,
} from '../../api/export'

interface MessageActionsProps {
  projectId: string
  messageId: string
  content: string
  disabled?: boolean
}

const BASE_FORMATS: ExportFormat[] = ['pdf', 'docx', 'md', 'txt']

export const MessageActions = memo(function MessageActions({
  projectId,
  messageId,
  content,
  disabled,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false)
  const [open, setOpen] = useState(false)
  const [formats, setFormats] = useState<ExportFormat[]>(BASE_FORMATS)
  const [exporting, setExporting] = useState<ExportFormat | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const showExport = isStructuredAssistantContent(content)

  useEffect(() => {
    if (!showExport || disabled) return
    getExportFormats(projectId, messageId)
      .then((res) => setFormats(res.formats as ExportFormat[]))
      .catch(() => setFormats(BASE_FORMATS))
  }, [projectId, messageId, showExport, disabled])

  useEffect(() => {
    if (!open) return
    function handleClick(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  async function handleCopy() {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  async function handleExport(format: ExportFormat) {
    setExporting(format)
    setExportError(null)
    setOpen(false)
    try {
      await downloadExport(projectId, messageId, format)
    } catch (err) {
      setExportError(getErrorMessage(err))
    } finally {
      setExporting(null)
    }
  }

  if (disabled) return null

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={handleCopy}
        className="rounded-lg px-2.5 py-1 text-[11px] font-medium text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
      >
        {copied ? 'Copied' : 'Copy'}
      </button>

      {showExport && (
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => {
              setExportError(null)
              setOpen((value) => !value)
            }}
            disabled={exporting !== null}
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-[11px] font-medium text-violet-600 transition hover:bg-violet-50 disabled:opacity-60 dark:text-violet-400 dark:hover:bg-violet-950/40"
          >
            {exporting ? `Exporting ${exportFormatLabel(exporting)}…` : 'Export ▼'}
          </button>

          {exportError && (
            <span
              className="ml-1 max-w-[220px] truncate text-[11px] text-red-600 dark:text-red-400"
              title={exportError}
            >
              {exportError}
            </span>
          )}

          {open && (
            <div className="absolute left-0 top-full z-20 mt-1 min-w-[140px] overflow-hidden rounded-xl border border-zinc-200 bg-white py-1 shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
              {formats.map((format) => (
                <button
                  key={format}
                  type="button"
                  onClick={() => handleExport(format)}
                  className="block w-full px-3 py-2 text-left text-[12px] text-zinc-700 transition hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-zinc-800"
                >
                  {exportFormatLabel(format)}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
})

export { detectExportIntent }
