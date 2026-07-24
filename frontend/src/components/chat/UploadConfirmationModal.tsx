import type { UploadConfirmationDetail } from '../../api/uploadValidation'

interface UploadConfirmationModalProps {
  detail: UploadConfirmationDetail
  filename: string
  uploading?: boolean
  onContinue: () => void
  onCancel: () => void
}

export function UploadConfirmationModal({
  detail,
  filename,
  uploading,
  onContinue,
  onCancel,
}: UploadConfirmationModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-700 dark:bg-zinc-900"
        role="dialog"
        aria-labelledby="upload-confirm-title"
      >
        <h2
          id="upload-confirm-title"
          className="text-base font-semibold text-zinc-900 dark:text-zinc-100"
        >
          Sensitive information detected
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-zinc-600 dark:text-zinc-300">
          {detail.message}
        </p>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
          File: <span className="font-medium text-zinc-700 dark:text-zinc-200">{filename}</span>
          {detail.document_type ? (
            <>
              {' '}
              · Detected as <span className="font-medium">{detail.document_type}</span>
            </>
          ) : null}
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={uploading}
            className="rounded-lg px-4 py-2 text-sm font-medium text-zinc-600 transition hover:bg-zinc-100 disabled:opacity-60 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onContinue}
            disabled={uploading}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-zinc-900 transition hover:bg-brand-hover disabled:opacity-60"
          >
            {uploading ? 'Uploading…' : 'Continue'}
          </button>
        </div>
      </div>
    </div>
  )
}
