import { memo } from 'react'

export const TypingIndicator = memo(function TypingIndicator() {
  return (
    <div className="typing-indicator flex items-center gap-1.5 py-1" aria-label="Assistant is typing">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </div>
  )
})
