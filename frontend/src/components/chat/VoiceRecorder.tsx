import { useVoiceRecorder } from '../../hooks/useVoiceRecorder'
import { useToastOptional } from '../../contexts/ToastContext'

export interface VoiceRecorderProps {
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

export function VoiceRecorder({ disabled, onTranscript }: VoiceRecorderProps) {
  const toast = useToastOptional()

  const { state, timerLabel, toggleRecording } = useVoiceRecorder({
    disabled,
    onTranscript,
    onError: (message) => toast?.showToast(message),
  })

  const isListening = state === 'listening'
  const isProcessing = state === 'processing'

  return (
    <div className="relative flex flex-col items-center">
      <button
        type="button"
        onClick={toggleRecording}
        disabled={disabled || isProcessing}
        aria-label={
          isListening
            ? 'Stop recording'
            : isProcessing
              ? 'Transcribing speech'
              : 'Start voice input'
        }
        aria-pressed={isListening}
        className={`relative mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border transition focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/40 disabled:cursor-not-allowed disabled:opacity-50 ${
          isListening
            ? 'border-amber-400 bg-amber-50 text-amber-700 shadow-sm shadow-amber-500/20 dark:border-amber-500 dark:bg-amber-950/40 dark:text-amber-300'
            : 'border-zinc-200 bg-white text-zinc-500 hover:border-amber-300 hover:text-amber-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:border-amber-500 dark:hover:text-amber-300'
        }`}
      >
        {isListening && (
          <span
            className="absolute inset-0 animate-ping rounded-xl bg-amber-400/20"
            aria-hidden
          />
        )}
        {isProcessing ? (
          <span
            className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
            aria-hidden
          />
        ) : (
          <MicIcon />
        )}
      </button>

      {(isListening || isProcessing) && (
        <span className="pointer-events-none absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-medium text-zinc-500 dark:text-zinc-400">
          {isProcessing ? 'Transcribing…' : timerLabel}
        </span>
      )}
    </div>
  )
}
