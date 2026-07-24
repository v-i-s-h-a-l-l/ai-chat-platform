import { useState, type ComponentType } from 'react'

interface VoiceInputLazyProps {
  disabled?: boolean
  onTranscript: (text: string) => void | Promise<void>
}

function MicIcon({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.75}
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 18.75a4.5 4.5 0 004.5-4.5V7.5a4.5 4.5 0 10-9 0v6.75a4.5 4.5 0 004.5 4.5z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 10.5c0 4.142-3.358 7.5-7.5 7.5S4.5 14.642 4.5 10.5M12 18.75V21"
      />
    </svg>
  )
}

/** Loads voice recorder code only after the user clicks the microphone. */
export function VoiceInputLazy({ disabled, onTranscript }: VoiceInputLazyProps) {
  const [Recorder, setRecorder] = useState<
    ComponentType<VoiceInputLazyProps> | null
  >(null)

  if (!Recorder) {
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          void import('./VoiceRecorder').then((module) => {
            setRecorder(() => module.VoiceRecorder)
          })
        }}
        aria-label="Start voice input"
        className="mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-white text-zinc-500 transition hover:border-amber-300 hover:text-amber-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/40 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:border-amber-500 dark:hover:text-amber-300"
      >
        <MicIcon />
      </button>
    )
  }

  return <Recorder disabled={disabled} onTranscript={onTranscript} />
}
