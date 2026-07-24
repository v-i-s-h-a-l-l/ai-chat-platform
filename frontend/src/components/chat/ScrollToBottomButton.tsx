interface ScrollToBottomButtonProps {
  visible: boolean
  newMessageCount?: number
  onClick: () => void
}

function ChevronDownIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}

export function ScrollToBottomButton({
  visible,
  newMessageCount = 0,
  onClick,
}: ScrollToBottomButtonProps) {
  const showBadge = newMessageCount > 0
  const label = showBadge
    ? `${newMessageCount} new message${newMessageCount === 1 ? '' : 's'}`
    : 'Scroll to bottom'

  if (!visible) return null

  return (
    <div
      className="pointer-events-none absolute inset-x-0 bottom-full z-50 mb-3 flex justify-center"
      data-scroll-to-bottom-visible="true"
    >
      <button
        type="button"
        onClick={onClick}
        aria-label={label}
        title={label}
        className="pointer-events-auto relative flex h-11 w-11 select-none items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-700 shadow-[0_2px_12px_rgba(0,0,0,0.12)] transition duration-200 ease-out hover:scale-105 hover:bg-zinc-50 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200 dark:shadow-[0_2px_12px_rgba(0,0,0,0.45)] dark:hover:bg-zinc-700 dark:focus-visible:ring-offset-zinc-900"
      >
        <ChevronDownIcon className="h-5 w-5" />
        {showBadge && (
          <span className="absolute -top-2 left-1/2 flex -translate-x-1/2 whitespace-nowrap rounded-full bg-zinc-900 px-2 py-0.5 text-[10px] font-medium leading-none text-white shadow-sm dark:bg-zinc-100 dark:text-zinc-900">
            {newMessageCount > 99 ? '99+' : newMessageCount} new
          </span>
        )}
      </button>
    </div>
  )
}
