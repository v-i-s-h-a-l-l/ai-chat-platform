interface InlineErrorProps {
  message: string
}

/** Inline alert for form/API errors — wraps long strings and JSON safely. */
export function InlineError({ message }: InlineErrorProps) {
  return (
    <div
      role="alert"
      className="min-w-0 overflow-hidden rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] leading-relaxed text-red-700 break-words [overflow-wrap:anywhere] dark:border-red-900 dark:bg-red-950 dark:text-red-300"
    >
      {message}
    </div>
  )
}
