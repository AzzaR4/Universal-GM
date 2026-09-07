import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import {
  useCreateCustomRuleset,
  useCustomRulesets,
  useDeleteCustomRuleset,
  useImportCustomRuleset,
  useUpdateCustomRuleset,
} from '../hooks/queries'
import { Badge, Button, Card, Input, Label, PanelTitle, Textarea } from '../lib/ui'
import type { CustomRuleset } from '../types'

const ROLL_MODES: Array<{ value: string; label: string }> = [
  { value: 'single', label: 'Single die vs threshold' },
  { value: 'pool_count_successes', label: 'Dice pool — count successes' },
  { value: 'pool_sum', label: 'Dice pool — sum total' },
]

interface AttrRow {
  name: string
  default: number
  min?: number
  max?: number
}
interface ResRow {
  name: string
  max: number
  default: number
}
interface SkillRow {
  name: string
}

interface Draft {
  name: string
  display_name: string
  description: string
  dice_formula: string
  roll_mode: string
  success_threshold: number
  attributes: AttrRow[]
  resources: ResRow[]
  skills: SkillRow[]
  prompt_instructions: string
}

const EMPTY: Draft = {
  name: '',
  display_name: '',
  description: '',
  dice_formula: '1d20',
  roll_mode: 'single',
  success_threshold: 6,
  attributes: [{ name: 'Might', default: 5, min: 1, max: 10 }],
  resources: [{ name: 'Health', max: 10, default: 10 }],
  skills: [],
  prompt_instructions: '',
}

const TABS = ['Identity', 'Dice', 'Attributes', 'Resources', 'Skills', 'GM Instructions'] as const
type Tab = (typeof TABS)[number]

function fromModel(r: CustomRuleset): Draft {
  return {
    name: r.name,
    display_name: r.display_name,
    description: r.description,
    dice_formula: r.dice_formula,
    roll_mode: r.roll_mode,
    success_threshold: r.success_threshold,
    attributes: (r.attributes as AttrRow[]) || [],
    resources: (r.resources as ResRow[]) || [],
    skills: (r.skills as SkillRow[]) || [],
    prompt_instructions: r.prompt_instructions,
  }
}

export default function RulesetBuilder() {
  const { data: rulesets } = useCustomRulesets()
  const createRuleset = useCreateCustomRuleset()
  const updateRuleset = useUpdateCustomRuleset()
  const deleteRuleset = useDeleteCustomRuleset()
  const importRuleset = useImportCustomRuleset()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft>(EMPTY)
  const [tab, setTab] = useState<Tab>('Identity')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  function newRuleset() {
    setEditingId(null)
    setDraft(EMPTY)
    setTab('Identity')
    setError(null)
    setNotice(null)
  }

  function editRuleset(r: CustomRuleset) {
    setEditingId(r.id)
    setDraft(fromModel(r))
    setTab('Identity')
    setError(null)
    setNotice(null)
  }

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((d) => ({ ...d, [key]: value }))
  }

  async function save() {
    setError(null)
    setNotice(null)
    const payload = {
      ...draft,
      display_name: draft.display_name || draft.name,
    }
    try {
      if (editingId) {
        const updated = await updateRuleset.mutateAsync({ id: editingId, data: payload })
        setEditingId(updated.id)
        setNotice('Ruleset saved.')
      } else {
        const created = await createRuleset.mutateAsync(payload)
        setEditingId(created.id)
        setNotice('Ruleset created.')
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to save ruleset')
    }
  }

  async function remove(r: CustomRuleset) {
    await deleteRuleset.mutateAsync(r.id)
    if (editingId === r.id) newRuleset()
  }

  async function exportOne(r: CustomRuleset) {
    const data = await api.exportRuleset(r.id)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${r.name}_ruleset.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const json = JSON.parse(text)
      const imported = await importRuleset.mutateAsync(json)
      setNotice(`Imported "${imported.name}".`)
    } catch (err: any) {
      setError(err?.message || 'Failed to import ruleset')
    } finally {
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="min-h-screen bg-ink-950 text-ink-100">
      <header className="flex items-center justify-between border-b border-ink-700 bg-ink-900/80 px-6 py-3">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-ink-600 hover:text-ink-100">
            ←
          </Link>
          <span className="text-lg">🛠️</span>
          <span className="font-bold">Ruleset Builder</span>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={onImportFile}
          />
          <Button variant="secondary" onClick={() => fileRef.current?.click()}>
            ⬆ Import
          </Button>
          <Button onClick={newRuleset}>+ New Ruleset</Button>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-[260px_1fr_300px]">
        {/* Left: list */}
        <aside className="space-y-2">
          <PanelTitle>Your Rulesets</PanelTitle>
          {(!rulesets || rulesets.length === 0) && (
            <p className="text-sm text-ink-600">No custom rulesets yet.</p>
          )}
          {(rulesets || []).map((r) => (
            <div
              key={r.id}
              className={`rounded-lg border p-2.5 ${
                editingId === r.id ? 'border-ember-500 bg-ink-800' : 'border-ink-700 bg-ink-900'
              }`}
            >
              <button className="block w-full text-left" onClick={() => editRuleset(r)}>
                <div className="font-medium text-ink-100">{r.display_name || r.name}</div>
                <div className="text-[11px] text-ink-600">{r.name}</div>
              </button>
              <div className="mt-1.5 flex gap-1.5">
                <button className="text-[11px] text-ink-600 hover:text-ember-400" onClick={() => exportOne(r)}>
                  export
                </button>
                <button className="text-[11px] text-ink-600 hover:text-red-400" onClick={() => remove(r)}>
                  delete
                </button>
              </div>
            </div>
          ))}
        </aside>

        {/* Center: editor */}
        <main>
          <Card>
            <div className="mb-4 flex flex-wrap gap-1.5">
              {TABS.map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`rounded-lg px-3 py-1.5 text-sm ${
                    tab === t ? 'bg-ember-600 text-ink-950' : 'bg-ink-800 text-ink-100 hover:bg-ink-700'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {tab === 'Identity' && (
              <div className="space-y-3">
                <div>
                  <Label>Internal Name (lowercase, no spaces)</Label>
                  <Input
                    value={draft.name}
                    onChange={(e) => set('name', e.target.value)}
                    placeholder="my_custom_system"
                    disabled={!!editingId}
                  />
                  {editingId && (
                    <p className="mt-1 text-[11px] text-ink-600">
                      Internal name can be changed via the API only after creation.
                    </p>
                  )}
                </div>
                <div>
                  <Label>Display Name</Label>
                  <Input
                    value={draft.display_name}
                    onChange={(e) => set('display_name', e.target.value)}
                    placeholder="My Custom System"
                  />
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea
                    rows={3}
                    value={draft.description}
                    onChange={(e) => set('description', e.target.value)}
                  />
                </div>
              </div>
            )}

            {tab === 'Dice' && (
              <div className="space-y-3">
                <div>
                  <Label>Dice Formula</Label>
                  <Input
                    value={draft.dice_formula}
                    onChange={(e) => set('dice_formula', e.target.value)}
                    placeholder="1d20 or 6d6"
                  />
                </div>
                <div>
                  <Label>Roll Mode</Label>
                  <select
                    className="w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-ink-100"
                    value={draft.roll_mode}
                    onChange={(e) => set('roll_mode', e.target.value)}
                  >
                    {ROLL_MODES.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label>Success Threshold</Label>
                  <Input
                    type="number"
                    value={draft.success_threshold}
                    onChange={(e) => set('success_threshold', Number(e.target.value))}
                  />
                  <p className="mt-1 text-[11px] text-ink-600">
                    {draft.roll_mode === 'single'
                      ? 'Roll meets or beats this number to succeed.'
                      : 'Each die at or above this value counts as one success.'}
                  </p>
                </div>
              </div>
            )}

            {tab === 'Attributes' && (
              <RowEditor
                title="Attributes"
                rows={draft.attributes}
                onChange={(rows) => set('attributes', rows)}
                empty={{ name: '', default: 5, min: 1, max: 10 }}
                columns={[
                  { key: 'name', label: 'Name', type: 'text' },
                  { key: 'default', label: 'Default', type: 'number' },
                  { key: 'min', label: 'Min', type: 'number' },
                  { key: 'max', label: 'Max', type: 'number' },
                ]}
              />
            )}

            {tab === 'Resources' && (
              <RowEditor
                title="Resources"
                rows={draft.resources}
                onChange={(rows) => set('resources', rows)}
                empty={{ name: '', max: 10, default: 10 }}
                columns={[
                  { key: 'name', label: 'Name', type: 'text' },
                  { key: 'max', label: 'Max', type: 'number' },
                  { key: 'default', label: 'Start', type: 'number' },
                ]}
              />
            )}

            {tab === 'Skills' && (
              <RowEditor
                title="Skills"
                rows={draft.skills}
                onChange={(rows) => set('skills', rows)}
                empty={{ name: '' }}
                columns={[{ key: 'name', label: 'Name', type: 'text' }]}
              />
            )}

            {tab === 'GM Instructions' && (
              <div>
                <Label>GM Instructions (added to the AI system prompt)</Label>
                <Textarea
                  rows={8}
                  value={draft.prompt_instructions}
                  onChange={(e) => set('prompt_instructions', e.target.value)}
                  placeholder="Describe tone, mechanics emphasis, and how the GM should adjudicate this system…"
                />
              </div>
            )}

            {error && (
              <div className="mt-4 rounded-lg border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-300">
                ⚠ {error}
              </div>
            )}
            {notice && (
              <div className="mt-4 rounded-lg border border-green-800 bg-green-900/30 px-3 py-2 text-sm text-green-300">
                ✓ {notice}
              </div>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <Button onClick={save} disabled={!draft.name.trim() || createRuleset.isPending || updateRuleset.isPending}>
                {editingId ? 'Save Changes' : 'Create Ruleset'}
              </Button>
            </div>
          </Card>
        </main>

        {/* Right: live preview */}
        <aside>
          <PanelTitle>Live Preview</PanelTitle>
          <Card>
            <div className="text-lg font-bold text-ink-100">{draft.display_name || draft.name || 'Untitled'}</div>
            {draft.description && <p className="mt-1 text-xs text-ink-600">{draft.description}</p>}
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge color="ember">{draft.dice_formula}</Badge>
              <Badge color="arcane">{draft.roll_mode}</Badge>
              <Badge color="ink">≥ {draft.success_threshold}</Badge>
            </div>
            <PreviewList title="Attributes" items={draft.attributes.map((a) => `${a.name} (${a.default})`)} />
            <PreviewList
              title="Resources"
              items={draft.resources.map((r) => `${r.name} ${r.default}/${r.max}`)}
            />
            <PreviewList title="Skills" items={draft.skills.map((s) => s.name)} />
          </Card>
        </aside>
      </div>
    </div>
  )
}

function PreviewList({ title, items }: { title: string; items: string[] }) {
  const filtered = items.filter(Boolean)
  if (filtered.length === 0) return null
  return (
    <div className="mt-3">
      <div className="text-[10px] uppercase tracking-wide text-ink-600">{title}</div>
      <div className="mt-1 flex flex-wrap gap-1">
        {filtered.map((it, i) => (
          <span key={i} className="rounded bg-ink-700 px-2 py-0.5 text-[11px] text-ink-100">
            {it}
          </span>
        ))}
      </div>
    </div>
  )
}

interface Column {
  key: string
  label: string
  type: 'text' | 'number'
}

function RowEditor<T extends Record<string, any>>({
  title,
  rows,
  onChange,
  empty,
  columns,
}: {
  title: string
  rows: T[]
  onChange: (rows: T[]) => void
  empty: T
  columns: Column[]
}) {
  function update(idx: number, key: string, value: string, type: 'text' | 'number') {
    const next = rows.slice()
    next[idx] = { ...next[idx], [key]: type === 'number' ? Number(value) : value }
    onChange(next)
  }
  function add() {
    onChange([...rows, { ...empty }])
  }
  function remove(idx: number) {
    onChange(rows.filter((_, i) => i !== idx))
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-ink-100">{title}</span>
        <Button variant="secondary" onClick={add}>
          + Add
        </Button>
      </div>
      {rows.length === 0 && <p className="text-sm text-ink-600">None yet.</p>}
      {rows.map((row, idx) => (
        <div key={idx} className="flex items-end gap-2">
          {columns.map((col) => (
            <div key={col.key} className="flex-1">
              <Label>{col.label}</Label>
              <Input
                type={col.type === 'number' ? 'number' : 'text'}
                value={row[col.key] ?? ''}
                onChange={(e) => update(idx, col.key, e.target.value, col.type)}
              />
            </div>
          ))}
          <button
            onClick={() => remove(idx)}
            className="mb-2 text-ink-600 hover:text-red-400"
            title="Remove"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
