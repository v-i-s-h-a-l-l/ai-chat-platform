import { FormEvent, useEffect, useState } from 'react'
import { getErrorMessage } from '../../api/client'
import { projectApi } from '../../api/projects'
import type { PromptOptimizationResponse } from '../../types/project'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'

interface CreateProjectModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: { name: string; description: string; system_prompt: string }) => Promise<void>
}

type Step = 'form' | 'review'

export function CreateProjectModal({ open, onClose, onSubmit }: CreateProjectModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [step, setStep] = useState<Step>('form')
  const [optimization, setOptimization] = useState<PromptOptimizationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) {
      setStep('form')
      setOptimization(null)
      setError('')
    }
  }, [open])

  function resetForm() {
    setName('')
    setDescription('')
    setSystemPrompt('')
    setStep('form')
    setOptimization(null)
    setError('')
  }

  async function handleFormSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('Project name is required')
      return
    }

    setLoading(true)
    setError('')

    try {
      const trimmedPrompt = systemPrompt.trim()

      // Empty prompt — skip optimization, create directly.
      if (!trimmedPrompt) {
        await onSubmit({ name: name.trim(), description, system_prompt: '' })
        resetForm()
        onClose()
        return
      }

      const result = await projectApi.optimizePrompt({
        project_name: name.trim(),
        description,
        system_prompt: trimmedPrompt,
      })

      if (!result.safe) {
        setError(result.reason ?? 'This system prompt was flagged as unsafe and cannot be used.')
        return
      }

      setOptimization(result)
      setStep('review')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function finalizePrompt(useImproved: boolean) {
    if (!optimization) return

    const chosenPrompt = useImproved
      ? (optimization.improved_prompt ?? optimization.original_prompt)
      : optimization.original_prompt

    setLoading(true)
    setError('')
    try {
      await onSubmit({
        name: name.trim(),
        description,
        system_prompt: chosenPrompt,
      })
      resetForm()
      onClose()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-zinc-900/60 backdrop-blur-sm" onClick={onClose} />
      <div
        className={`relative w-full animate-fade-in rounded-2xl border border-zinc-200 bg-white shadow-2xl ${
          step === 'review' ? 'max-w-3xl' : 'max-w-lg'
        }`}
      >
        <div className="border-b border-zinc-100 px-6 py-5">
          <h2 className="text-base font-semibold text-zinc-900">
            {step === 'form' ? 'New Project' : 'Review System Prompt'}
          </h2>
          <p className="mt-0.5 text-[13px] text-zinc-500">
            {step === 'form'
              ? "Configure your chatbot's name, description, and behavior."
              : 'We proofread your prompt for clarity. Choose which version to use.'}
          </p>
        </div>

        {step === 'form' ? (
          <form onSubmit={handleFormSubmit} className="space-y-4 p-6">
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
                {error}
              </div>
            )}

            <Input
              label="Project Name"
              placeholder="e.g. Code Assistant"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />

            <div className="space-y-1.5">
              <label className="block text-[13px] font-medium text-zinc-700">Description</label>
              <textarea
                className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-[13px] text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-violet-400 focus:ring-2 focus:ring-violet-500/15"
                rows={2}
                placeholder="Brief description of this project"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-[13px] font-medium text-zinc-700">
                System Prompt
                <span className="ml-1.5 font-normal text-zinc-400">(defines AI behavior)</span>
              </label>
              <textarea
                className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-[13px] text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-violet-400 focus:ring-2 focus:ring-violet-500/15"
                rows={4}
                placeholder="You are a helpful coding assistant. Provide clear, concise answers with examples..."
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-3 border-t border-zinc-100 pt-4">
              <Button type="button" variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={loading}>
                Create Project
              </Button>
            </div>
          </form>
        ) : (
          optimization && (
            <div className="space-y-4 p-6">
              {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700">
                  {error}
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <h3 className="text-[13px] font-semibold text-zinc-800">Original Prompt</h3>
                  <div className="max-h-48 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-[13px] leading-relaxed whitespace-pre-wrap text-zinc-700">
                    {optimization.original_prompt}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <h3 className="text-[13px] font-semibold text-zinc-800">Improved Prompt</h3>
                  <div className="max-h-48 overflow-y-auto rounded-xl border border-violet-200 bg-violet-50/50 px-4 py-3 text-[13px] leading-relaxed whitespace-pre-wrap text-zinc-700">
                    {optimization.improved_prompt}
                  </div>
                </div>
              </div>

              {optimization.changes.length > 0 && (
                <div className="space-y-1.5">
                  <h3 className="text-[13px] font-semibold text-zinc-800">Changes</h3>
                  <ul className="list-inside list-disc space-y-0.5 rounded-xl border border-zinc-200 bg-white px-4 py-3 text-[13px] text-zinc-600">
                    {optimization.changes.map((change) => (
                      <li key={change}>{change}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex flex-wrap justify-end gap-3 border-t border-zinc-100 pt-4">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void finalizePrompt(false)}
                  loading={loading}
                >
                  Keep Original
                </Button>
                <Button type="button" onClick={() => void finalizePrompt(true)} loading={loading}>
                  Use AI Version
                </Button>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  )
}
