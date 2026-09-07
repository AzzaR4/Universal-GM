import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { useCharacterSchema } from '../hooks/queries'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Input, Label, Textarea } from '../lib/ui'
import Modal from './Modal'
import type { CharacterSchema } from '../types'

interface AttrDef {
  key: string
  name: string
  min?: number
  max?: number
  default?: number
}

/** Normalise the ruleset's attribute definitions into a common shape.
 * dnd5e uses `abilities` keyed by `key`; other rulesets use `attributes` keyed by `name`. */
function readAttrs(schema?: CharacterSchema): { container: 'abilities' | 'attributes'; defs: AttrDef[] } {
  if (!schema) return { container: 'attributes', defs: [] }
  if (Array.isArray(schema.abilities) && schema.abilities.length > 0) {
    return {
      container: 'abilities',
      defs: schema.abilities.map((a: any) => ({
        key: a.key ?? a.name,
        name: a.name ?? a.key,
        min: a.min,
        max: a.max,
        default: a.default,
      })),
    }
  }
  const attrs = Array.isArray(schema.attributes) ? schema.attributes : []
  return {
    container: 'attributes',
    defs: attrs.map((a: any) => ({
      key: a.name,
      name: a.name,
      min: a.min,
      max: a.max,
      default: a.default,
    })),
  }
}

export default function CharacterWizard({
  campaignId,
  rulesetId,
  open,
  onClose,
}: {
  campaignId: string
  rulesetId?: string
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const { data: schema } = useCharacterSchema(rulesetId)
  const { container, defs } = useMemo(() => readAttrs(schema), [schema])

  const [step, setStep] = useState(0)
  const [name, setName] = useState('')
  const [playerName, setPlayerName] = useState('')
  const [description, setDescription] = useState('')
  const [isPC, setIsPC] = useState(true)
  const [addToParty, setAddToParty] = useState(true)
  const [attrs, setAttrs] = useState<Record<string, number>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function attrValue(d: AttrDef): number {
    return attrs[d.key] ?? d.default ?? d.min ?? 0
  }

  function reset() {
    setStep(0)
    setName('')
    setPlayerName('')
    setDescription('')
    setIsPC(true)
    setAddToParty(true)
    setAttrs({})
    setError(null)
    setSaving(false)
  }

  async function submit() {
    setSaving(true)
    setError(null)
    try {
      // Create with backend defaults (full, correct ruleset_data shape).
      const created = await api.createCharacter(campaignId, {
        name: name.trim(),
        description: description.trim(),
        is_player_character: isPC,
        player_name: playerName.trim() || undefined,
        add_to_party: isPC && addToParty,
      } as any)

      // Overlay any customised attribute values onto the created defaults.
      const changed = defs.some((d) => attrs[d.key] != null && attrs[d.key] !== d.default)
      if (changed) {
        const data: Record<string, any> = { ...(created.ruleset_data || {}) }
        const bucket: Record<string, number> = { ...((data as any)[container] || {}) }
        for (const d of defs) bucket[d.key] = attrValue(d)
        ;(data as any)[container] = bucket
        await api.updateCharacter(campaignId, created.id, { ruleset_data: data } as any)
      }

      qc.invalidateQueries({ queryKey: ['characters', campaignId] })
      qc.invalidateQueries({ queryKey: ['party', campaignId] })
      reset()
      onClose()
    } catch (e: any) {
      setError(e?.message || 'Failed to create character')
      setSaving(false)
    }
  }

  const canNext0 = name.trim().length > 0
  const title = ['New Character — Identity', 'New Character — Attributes', 'New Character — Confirm'][step]

  return (
    <Modal open={open} onClose={onClose} title={title}>
      {/* Step indicator */}
      <div className="mb-4 flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full ${i <= step ? 'bg-ember-500' : 'bg-ink-700'}`}
          />
        ))}
      </div>

      {step === 0 && (
        <div className="space-y-3">
          <div>
            <Label>Character Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Thorin" />
          </div>
          <div>
            <Label>Player Name (optional)</Label>
            <Input
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="Who plays this character?"
            />
          </div>
          <div>
            <Label>Background / Description</Label>
            <Textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A short background…"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-ink-100">
            <input type="checkbox" checked={isPC} onChange={(e) => setIsPC(e.target.checked)} />
            Player character
          </label>
          {isPC && (
            <label className="flex items-center gap-2 text-sm text-ink-100">
              <input
                type="checkbox"
                checked={addToParty}
                onChange={(e) => setAddToParty(e.target.checked)}
              />
              Add to active party
            </label>
          )}
          <div className="flex justify-end pt-2">
            <Button disabled={!canNext0} onClick={() => setStep(1)}>
              Next →
            </Button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3">
          {defs.length === 0 ? (
            <p className="text-sm text-ink-600">
              This ruleset has no editable attributes — defaults will be used.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {defs.map((d) => (
                <div key={d.key}>
                  <Label>{d.name}</Label>
                  <Input
                    type="number"
                    min={d.min}
                    max={d.max}
                    value={attrValue(d)}
                    onChange={(e) =>
                      setAttrs((prev) => ({ ...prev, [d.key]: Number(e.target.value) }))
                    }
                  />
                </div>
              ))}
            </div>
          )}
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(0)}>
              ← Back
            </Button>
            <Button onClick={() => setStep(2)}>Next →</Button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3">
          <div className="rounded-lg border border-ink-700 bg-ink-900 p-3 text-sm">
            <div className="text-lg font-bold text-ink-100">{name}</div>
            {playerName && <div className="text-xs text-ember-400/80">Played by {playerName}</div>}
            {description && <p className="mt-1 text-xs text-ink-600">{description}</p>}
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {defs.map((d) => (
                <span key={d.key} className="rounded bg-ink-700 px-2 py-0.5 text-ink-100">
                  {d.name}: <span className="font-mono text-ember-400">{attrValue(d)}</span>
                </span>
              ))}
            </div>
            <div className="mt-2 text-xs text-ink-600">
              {isPC ? 'Player character' : 'NPC'}
              {isPC && addToParty ? ' · joins the party' : ''}
            </div>
          </div>
          {error && (
            <div className="rounded-lg border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-300">
              ⚠ {error}
            </div>
          )}
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep(1)} disabled={saving}>
              ← Back
            </Button>
            <Button onClick={submit} disabled={saving}>
              {saving ? 'Creating…' : 'Create Character'}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}
