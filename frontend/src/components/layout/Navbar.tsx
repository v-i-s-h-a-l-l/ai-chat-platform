import { Link } from 'react-router-dom'
import { ThemeToggle } from '../ui/ThemeToggle'

interface NavbarProps {
  variant?: 'landing' | 'auth'
}

export function Navbar({ variant = 'landing' }: NavbarProps) {
  return (
    <nav className="border-b border-slate-200/80 bg-white/80 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-900/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-sm font-bold text-white shadow-sm">
            AI
          </div>
          <span className="text-lg font-semibold text-slate-900 dark:text-zinc-100">Chatbot Platform</span>
        </Link>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          {variant === 'landing' && (
            <>
              <Link
                to="/login"
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-100"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
