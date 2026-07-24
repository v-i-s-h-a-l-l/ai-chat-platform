import { memo, useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { ChevronDownIcon } from '../icons/NavIcons'
import {
  AVAILABLE_MODELS,
  filterModels,
  getModelById,
  type AvailableModel,
} from '../../config/availableModels'

interface ModelSelectorProps {
  selectedModelId: string
  onSelect: (modelId: string) => void
  disabled?: boolean
}

function ModelOptionCard({
  model,
  selected,
  highlighted,
  onSelect,
}: {
  model: AvailableModel
  selected: boolean
  highlighted: boolean
  onSelect: (modelId: string) => void
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={selected}
      onClick={() => onSelect(model.id)}
      className={`w-full rounded-xl border px-3.5 py-3 text-left transition duration-150 ${
        selected
          ? 'border-amber-300 bg-amber-50/80 shadow-sm dark:border-amber-700 dark:bg-amber-950/40'
          : highlighted
            ? 'border-amber-200 bg-amber-50/50 dark:border-amber-800/70 dark:bg-amber-950/20'
            : 'border-transparent hover:border-zinc-200 hover:bg-zinc-50 dark:hover:border-zinc-700 dark:hover:bg-zinc-800/80'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-lg leading-none" aria-hidden>
          {model.icon}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{model.name}</span>
            {model.recommended && (
              <span className="rounded-full bg-brand px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-900">
                Recommended
              </span>
            )}
          </div>
          <p className="mt-1 text-[12px] leading-relaxed text-zinc-500 dark:text-zinc-400">
            {model.description}
          </p>
        </div>
        {selected && (
          <span className="mt-1 text-xs font-semibold text-amber-700 dark:text-amber-400" aria-hidden>
            ✓
          </span>
        )}
      </div>
    </button>
  )
}

export const ModelSelector = memo(function ModelSelector({
  selectedModelId,
  onSelect,
  disabled = false,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [highlightIndex, setHighlightIndex] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const listboxId = useId()
  const selected = getModelById(selectedModelId) ?? AVAILABLE_MODELS[0]

  const filteredModels = useMemo(() => filterModels(query), [query])

  useEffect(() => {
    setHighlightIndex(0)
  }, [query, open])

  useEffect(() => {
    if (!open) return

    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
        setQuery('')
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        setQuery('')
      }
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const chooseModel = useCallback(
    (modelId: string) => {
      onSelect(modelId)
      setOpen(false)
      setQuery('')
    },
    [onSelect],
  )

  function onTriggerKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    if (disabled) return
    if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
    }
  }

  function onSearchKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlightIndex((prev) => Math.min(prev + 1, filteredModels.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlightIndex((prev) => Math.max(prev - 1, 0))
    } else if (event.key === 'Enter' && filteredModels[highlightIndex]) {
      event.preventDefault()
      chooseModel(filteredModels[highlightIndex].id)
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => {
          if (disabled) return
          setOpen((prev) => !prev)
        }}
        onKeyDown={onTriggerKeyDown}
        className="group flex min-w-[220px] max-w-[280px] items-center gap-2 rounded-xl border border-zinc-200/80 bg-white px-3 py-2 text-left shadow-sm transition hover:border-amber-200 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-amber-700/60"
      >
        <span className="text-base leading-none" aria-hidden>
          {selected.icon}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-semibold text-zinc-900 dark:text-zinc-100">
            {selected.name}
          </span>
          {selected.recommended && (
            <span className="block text-[10px] font-medium text-amber-700 dark:text-amber-400">
              Recommended
            </span>
          )}
        </span>
        <ChevronDownIcon
          className={`h-4 w-4 flex-shrink-0 text-zinc-400 transition-transform duration-200 group-hover:text-zinc-600 dark:group-hover:text-zinc-300 ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-[calc(100%+8px)] z-50 w-[min(360px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-xl shadow-black/10 dark:border-zinc-700 dark:bg-zinc-900 dark:shadow-black/40">
          <div className="border-b border-zinc-100 p-3 dark:border-zinc-800">
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={onSearchKeyDown}
              placeholder="Search models…"
              aria-label="Search models"
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-amber-400 focus:ring-2 focus:ring-amber-500/15 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
              autoFocus
            />
          </div>

          <ul
            id={listboxId}
            role="listbox"
            aria-label="AI models"
            className="max-h-[min(420px,60vh)] space-y-1 overflow-y-auto p-2"
          >
            {filteredModels.length === 0 ? (
              <li className="px-3 py-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
                No models match your search.
              </li>
            ) : (
              filteredModels.map((model, index) => (
                <li key={model.id} role="presentation">
                  <ModelOptionCard
                    model={model}
                    selected={model.id === selectedModelId}
                    highlighted={index === highlightIndex}
                    onSelect={chooseModel}
                  />
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  )
})
