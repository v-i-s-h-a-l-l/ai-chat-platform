import type { ReactNode } from 'react'

interface AuthCardProps {
  title: string
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}

export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-8 shadow-xl shadow-slate-200/50 dark:border-zinc-700 dark:bg-zinc-900 dark:shadow-none">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-zinc-100">{title}</h1>
            <p className="mt-2 text-sm text-slate-500 dark:text-zinc-400">{subtitle}</p>
          </div>
          {children}
          {footer && <div className="mt-6 text-center text-sm text-slate-500 dark:text-zinc-400">{footer}</div>}
        </div>
      </div>
    </div>
  )
}
