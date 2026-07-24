import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-50 px-6 text-center dark:bg-zinc-950">
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Something went wrong
          </h1>
          <p className="max-w-md text-sm text-zinc-600 dark:text-zinc-400">
            An unexpected error occurred. Refresh the page or return home to continue.
          </p>
          <a
            href="/home"
            className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-brand-hover"
          >
            Go to home
          </a>
        </div>
      )
    }

    return this.props.children
  }
}
