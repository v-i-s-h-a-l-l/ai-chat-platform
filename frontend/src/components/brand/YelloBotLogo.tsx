interface YelloBotLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'inherit'
  className?: string
  /** `dark` keeps “Bot” white on always-dark surfaces (sidebar). */
  tone?: 'auto' | 'dark'
  /** Collapsed sidebar / small avatars — show “Y” only. */
  compact?: boolean
}

const SIZE_CLASSES = {
  sm: 'text-base',
  md: 'text-xl',
  lg: 'text-2xl sm:text-3xl',
  xl: 'text-4xl sm:text-5xl',
  inherit: 'text-[length:inherit] leading-[inherit]',
} as const

const YELLO_COLOR = 'text-[#F5B800]'

export function YelloBotLogo({
  size = 'md',
  className = '',
  tone = 'auto',
  compact = false,
}: YelloBotLogoProps) {
  const botColor = tone === 'dark' ? 'text-white' : 'text-black dark:text-white'

  if (compact) {
    return (
      <span
        aria-label="Yello Bot"
        className={`font-bold leading-none ${YELLO_COLOR} ${SIZE_CLASSES[size]} ${className}`}
      >
        Y
      </span>
    )
  }

  return (
    <span
      aria-label="Yello Bot"
      className={`whitespace-nowrap font-bold tracking-tight ${SIZE_CLASSES[size]} ${className}`}
    >
      <span className={YELLO_COLOR}>Yello</span>{' '}
      <span className={botColor}>Bot</span>
    </span>
  )
}
