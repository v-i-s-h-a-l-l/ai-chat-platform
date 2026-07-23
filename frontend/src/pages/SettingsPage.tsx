import { useAuth } from '../contexts/AuthContext'

export function SettingsPage() {
  const { user } = useAuth()

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-6 py-8">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">Settings</h1>
        <p className="mt-1 text-[13px] text-zinc-500">Manage your account preferences</p>

        <div className="mt-8 space-y-4">
          <section className="rounded-2xl border border-zinc-200/80 bg-white p-6 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
            <h2 className="text-[13px] font-semibold uppercase tracking-wider text-zinc-400">
              Profile
            </h2>
            <dl className="mt-4 space-y-4">
              <div>
                <dt className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">Name</dt>
                <dd className="mt-1 text-sm font-medium text-zinc-900">{user?.name}</dd>
              </div>
              <div>
                <dt className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">Email</dt>
                <dd className="mt-1 text-sm font-medium text-zinc-900">{user?.email}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-2xl border border-zinc-200/80 bg-white p-6 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
            <h2 className="text-[13px] font-semibold uppercase tracking-wider text-zinc-400">
              AI Model
            </h2>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-50">
                <span className="text-sm">⚡</span>
              </div>
              <div>
                <p className="text-sm font-medium text-zinc-900">openai/gpt-oss-120b</p>
                <p className="text-[12px] text-zinc-500">Powered by Groq · Ultra-fast inference</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
