import { Link } from 'react-router-dom'
import { Navbar } from '../components/layout/Navbar'
import { Button } from '../components/ui/Button'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-violet-50/30 dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-950">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <section className="flex flex-col items-center py-24 text-center sm:py-32">
          <span className="mb-6 inline-flex items-center rounded-full border border-primary-200 bg-primary-50 px-4 py-1.5 text-xs font-medium text-primary-700">
            AI-Powered Conversations
          </span>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-slate-900 sm:text-6xl">
            Build intelligent chatbots for your business
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
            A modern platform to create, manage, and deploy AI chatbots. Get started
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
              { title: 'Secure Auth', desc: 'JWT-based authentication out of the box' },
              { title: 'Modern Stack', desc: 'React 19, FastAPI, and PostgreSQL' },
              { title: 'Production Ready', desc: 'Clean architecture built to scale' },
            ].map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm"
              >
                <h3 className="font-semibold text-slate-900">{feature.title}</h3>
                <p className="mt-2 text-sm text-slate-500">{feature.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
