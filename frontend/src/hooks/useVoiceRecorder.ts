import { useCallback, useEffect, useRef, useState } from 'react'

import { getSpeechErrorMessage, speechApi } from '../api/speech'

export type VoiceRecorderState = 'idle' | 'listening' | 'processing' | 'completed' | 'error'

const MAX_RECORDING_MS = 30_000

function pickRecorderMimeType(): string | undefined {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
  ]
  if (typeof MediaRecorder === 'undefined') return undefined
  return candidates.find((type) => MediaRecorder.isTypeSupported(type))
}

function formatTimer(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

interface UseVoiceRecorderOptions {
  disabled?: boolean
  onTranscript: (text: string) => void | Promise<void>
  onError?: (message: string) => void
}

export function useVoiceRecorder({
  disabled = false,
  onTranscript,
  onError,
}: UseVoiceRecorderOptions) {
  const [state, setState] = useState<VoiceRecorderState>('idle')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)
  const maxDurationRef = useRef<number | null>(null)
  const mimeTypeRef = useRef<string | undefined>(undefined)

  const cleanupStream = useCallback(() => {
    mediaRecorderRef.current = null
    if (mediaStreamRef.current) {
      for (const track of mediaStreamRef.current.getTracks()) {
        track.stop()
      }
      mediaStreamRef.current = null
    }
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (maxDurationRef.current !== null) {
      window.clearTimeout(maxDurationRef.current)
      maxDurationRef.current = null
    }
  }, [])

  const resetToIdle = useCallback(() => {
    cleanupStream()
    chunksRef.current = []
    setElapsedSeconds(0)
    setErrorMessage(null)
    setState('idle')
  }, [cleanupStream])

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state === 'inactive') return
    recorder.stop()
  }, [])

  const cancelRecording = useCallback(() => {
    cleanupStream()
    chunksRef.current = []
    setElapsedSeconds(0)
    setErrorMessage(null)
    setState('idle')
  }, [cleanupStream])

  const startRecording = useCallback(async () => {
    if (disabled || state === 'listening' || state === 'processing') return

    setErrorMessage(null)
    setElapsedSeconds(0)
    chunksRef.current = []

    if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      const message = 'Voice input is not supported in this browser.'
      setErrorMessage(message)
      setState('error')
      onError?.(message)
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStreamRef.current = stream
      const mimeType = pickRecorderMimeType()
      mimeTypeRef.current = mimeType
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)

      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onerror = () => {
        cleanupStream()
        const message = 'Recording failed. Please try again.'
        setErrorMessage(message)
        setState('error')
        onError?.(message)
      }

      recorder.onstop = () => {
        cleanupStream()
        void (async () => {
          const blob = new Blob(chunksRef.current, {
            type: mimeTypeRef.current ?? 'audio/webm',
          })
          chunksRef.current = []

          if (blob.size === 0) {
            const message = 'No audio captured. Please try again.'
            setErrorMessage(message)
            setState('error')
            onError?.(message)
            return
          }

          setState('processing')
          try {
            const { text } = await speechApi.transcribe(blob)
            setState('completed')
            await onTranscript(text)
            resetToIdle()
          } catch (err) {
            const message = getSpeechErrorMessage(err)
            setErrorMessage(message)
            setState('error')
            onError?.(message)
          }
        })()
      }

      recorder.start()
      setState('listening')

      timerRef.current = window.setInterval(() => {
        setElapsedSeconds((prev) => prev + 1)
      }, 1000)

      maxDurationRef.current = window.setTimeout(() => {
        void stopRecording()
      }, MAX_RECORDING_MS)
    } catch (err) {
      cleanupStream()
      const message =
        err instanceof DOMException && err.name === 'NotAllowedError'
          ? 'Microphone permission denied.'
          : err instanceof DOMException && err.name === 'NotFoundError'
            ? 'No microphone found.'
            : 'Could not access the microphone.'
      setErrorMessage(message)
      setState('error')
      onError?.(message)
    }
  }, [
    cleanupStream,
    disabled,
    onError,
    onTranscript,
    resetToIdle,
    state,
    stopRecording,
  ])

  const toggleRecording = useCallback(() => {
    if (state === 'listening') {
      void stopRecording()
      return
    }
    if (state === 'idle' || state === 'error' || state === 'completed') {
      void startRecording()
    }
  }, [startRecording, state, stopRecording])

  useEffect(() => {
    if (state !== 'listening') return

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        cancelRecording()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [cancelRecording, state])

  useEffect(() => () => cleanupStream(), [cleanupStream])

  return {
    state,
    elapsedSeconds,
    timerLabel: formatTimer(elapsedSeconds),
    errorMessage,
    toggleRecording,
    cancelRecording,
    isBusy: state === 'listening' || state === 'processing',
  }
}
