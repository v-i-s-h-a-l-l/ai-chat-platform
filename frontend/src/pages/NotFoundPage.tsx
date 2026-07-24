import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-50 px-6 text-center dark:bg-zinc-950">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">Page not found</h1>
      <p className="max-w-md text-sm text-zinc-600 dark:text-zinc-400">
        The page you requested does not exist or may have moved.
      </p>
      <Link
        to="/home"
        className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-brand-hover"
      >
        Back to home
      </Link>
    </div>
  )
}
