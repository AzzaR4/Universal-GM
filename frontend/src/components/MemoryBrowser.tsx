import { useMemo, useState } from 'react'
import { useCreateMemory, useDeleteMemory, useMemories } from '../hooks/queries'
import { Badge, Button, Input, Label, PanelTitle, Textarea } from '../lib/ui'
import Modal from './Modal'

const MEMORY_TYPES = ['lore', 'event', 'character', 'location', 'quest']

function importanceColor(v: number): 'red' | 'ember' | 'ink' {
  if (v >= 0.75) return 'red'
  if (v >= 0.5) return 'ember'
  return 'ink'
}

export default function MemoryBrowser({ campaignId }: { campaignId: string }) {
  const [q, setQ] = useState('')
  const [minImportance, setMinImportance] = useState(0)
  const [activeTag, setActiveTag] = useState<string | null>(null)

  const params = useMemo(
    () => ({
      q: q.trim() || undefined,
      min_importance: minImportance > 0 ? minImportance : undefined,
      tag: activeTag || undefined,
    }),
    [q, minImportance, activeTag],
  )

  const { data: memories } = useMemories(campaignId, params)
  const createMemory = useCreateMemory(campaignId)
  const deleteMemory = useDeleteMemory(campaignId)

  const [modalOpen, setModalOpen] = useState(false)
  const [content, setContent] = useState('')
  const [memType, setMemType] = useState('lore')
  const [importance, setImportance] = useState(0.5)
  const [tags, setTags] = useState('')

  // Collect all tags present for quick-filter chips.
  const allTags = useMemo(() => {
    const set = new Set<string>()
    for (const m of memories || []) for (const t of m.tags || []) set.add(t)
    return Array.from(set).sort()
  }, [memories])

  function submit() {
    createMemory.mutate({
      content: content.trim(),
      memory_type: memType,
      importance,
      tags: tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    })
    setContent('')
    setTags('')
    setImportance(0.5)
    setMemType('lore')
    setModalOpen(false)
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <PanelTitle>Memory ({memories?.length || 0})</PanelTitle>
        <Button variant="secondary" onClick={() => setModalOpen(true)}>
          + Add
        </Button>
      </div>

      <Input placeholder="Search memories…" value={q} onChange={(e) => setQ(e.target.value)} />

      <div>
        <div className="mb-1 flex justify-between text-[11px] text-ink-600">
          <span>Min importance</span>
          <span className="font-mono">{minImportance.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={minImportance}
          onChange={(e) => setMinImportance(Number(e.target.value))}
          className="w-full accent-ember-500"
        />
      </div>

      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setActiveTag(null)}
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              activeTag === null ? 'bg-ember-600/30 text-ember-300' : 'bg-ink-700 text-ink-100'
            }`}
          >
            all
          </button>
          {allTags.map((t) => (
            <button
              key={t}
              onClick={() => setActiveTag(t === activeTag ? null : t)}
              className={`rounded-full px-2 py-0.5 text-[10px] ${
                activeTag === t ? 'bg-ember-600/30 text-ember-300' : 'bg-ink-700 text-ink-100'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-2">
        {(!memories || memories.length === 0) && (
          <p className="text-sm text-ink-600">No memories match.</p>
        )}
        {(memories || []).map((m) => (
          <div key={m.id} className="rounded-lg border border-ink-700 bg-ink-900 p-2.5">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm text-ink-100">{m.content}</p>
              <button
                onClick={() => deleteMemory.mutate(m.id)}
                className="text-ink-600 hover:text-red-400"
                title="Delete"
              >
                ✕
              </button>
            </div>
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <Badge color="arcane">{m.memory_type}</Badge>
              <Badge color={importanceColor(m.importance)}>★ {m.importance.toFixed(2)}</Badge>
              {m.has_embedding && <Badge color="green">embedded</Badge>}
              {(m.tags || []).map((t) => (
                <span key={t} className="rounded-full bg-ink-700 px-2 py-0.5 text-[10px] text-ink-100">
                  #{t}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add Memory">
        <div className="space-y-3">
          <div>
            <Label>Content</Label>
            <Textarea rows={3} value={content} onChange={(e) => setContent(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Type</Label>
              <select
                className="w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-ink-100"
                value={memType}
                onChange={(e) => setMemType(e.target.value)}
              >
                {MEMORY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Importance ({importance.toFixed(2)})</Label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={importance}
                onChange={(e) => setImportance(Number(e.target.value))}
                className="mt-3 w-full accent-ember-500"
              />
            </div>
          </div>
          <div>
            <Label>Tags (comma-separated)</Label>
            <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="villain, betrayal" />
          </div>
          <Button className="w-full" disabled={!content.trim()} onClick={submit}>
            Save Memory
          </Button>
        </div>
      </Modal>
    </div>
  )
}
