import { FormEvent, useEffect, useState } from 'react'
import { Button } from '../ui/Button'

interface RenameProjectModalProps {
  open: boolean
  initialName: string
  loading?: boolean
  onClose: () => void
  onSubmit: (name: string) => Promise<void>
}

export function RenameProjectModal({
  open,
  initialName,
  loading,
  onClose,
  onSubmit,
}: RenameProjectModalProps) {
  const [name, setName] = useState(initialName)

  useEffect(() => {
    if (open) setName(initialName)
  }, [open, initialName])

  if (!open) return null

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    await onSubmit(trimmed)
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4">
      <div
        className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-700 dark:bg-zinc-900"
        role="dialog"
        aria-labelledby="rename-project-title"
      >
        <h2 id="rename-project-title" className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          Rename project
        </h2>
        <form onSubmit={(e) => void handleSubmit(e)} className="mt-4 space-y-4">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2.5 text-sm text-zinc-900 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
            maxLength={255}
          />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} disabled={!name.trim()}>
              Save
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
