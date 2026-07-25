import { Link } from 'react-router-dom'
import { YelloBotLogo } from '../components/brand/YelloBotLogo'
import { Navbar } from '../components/layout/Navbar'
import { Button } from '../components/ui/Button'
import { useApiPrewarm } from '../hooks/useApiPrewarm'

export function LandingPage() {
  useApiPrewarm()

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-amber-50/40 dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-950">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <section className="flex flex-col items-center py-24 text-center sm:py-32">
          <span className="mb-6 inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-4 py-1.5 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
            AI-Powered Conversations
          </span>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-slate-900 sm:text-6xl dark:text-zinc-50">
            Your AI assistant, powered by{' '}
            <YelloBotLogo size="inherit" className="inline" />
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-600 dark:text-zinc-300">
            Create, manage, and chat with custom AI projects on YelloBot. Get started
            in minutes with a secure, scalable foundation built for production.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link to="/register">
              <Button className="px-8 py-3 text-base">Get Started</Button>
            </Link>
            <Link to="/login">
              <Button variant="secondary" className="px-8 py-3 text-base">
                Sign in
              </Button>
            </Link>
          </div>

          <div className="mt-20 grid w-full max-w-4xl gap-6 sm:grid-cols-3">
            {[
              {
                title: 'Custom AI Projects',
                desc: 'Create assistants with their own instructions, tone, and persistent chat history.',
              },
              {
                title: 'Chat With Your Documents',
                desc: 'Upload PDFs, Word files, and notes — YelloBot answers using your uploaded content.',
              },
              {
                title: 'Live Web Search',
                desc: 'When your files are not enough, pull in fresh answers from the web in real time.',
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-zinc-700 dark:bg-zinc-900 dark:shadow-none"
              >
                <h3 className="font-semibold text-slate-900 dark:text-zinc-100">{feature.title}</h3>
                <p className="mt-2 text-sm text-slate-500 dark:text-zinc-400">{feature.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
