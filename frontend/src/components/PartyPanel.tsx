import { useState } from 'react'
import { useCharacters, useParty, useAddToParty, useRemoveFromParty } from '../hooks/queries'
import { Badge, Button, PanelTitle } from '../lib/ui'
import type { Character } from '../types'
import CharacterWizard from './CharacterWizard'

function primaryResource(c: Character): { name: string; current: number; max: number } | null {
  const res = (c.ruleset_data?.resources || {}) as Record<string, { current: number; max: number }>
  const entries = Object.entries(res)
  if (entries.length === 0) return null
  // Prefer a health-like resource, else the first.
  const health = entries.find(([n]) => /hp|health|endurance/i.test(n))
  const [name, r] = health || entries[0]
  return { name, current: r.current, max: r.max }
}

function MemberCard({
  character,
  onRemove,
}: {
  character: Character
  onRemove: () => void
}) {
  const res = primaryResource(character)
  const pct = res && res.max > 0 ? Math.round((res.current / res.max) * 100) : 0
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 p-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-semibold text-ink-100">{character.name}</div>
          {character.player_name && (
            <div className="text-[11px] text-ember-400/80">{character.player_name}</div>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <Badge color={character.status === 'alive' ? 'green' : 'red'}>{character.status}</Badge>
          <button
            onClick={onRemove}
            className="text-ink-600 hover:text-red-400"
            title="Remove from party"
          >
            ✕
          </button>
        </div>
      </div>
      {res && (
        <div className="mt-2">
          <div className="mb-1 flex justify-between text-[11px]">
            <span className="text-ink-100">{res.name}</span>
            <span className="font-mono text-ink-600">
              {res.current}/{res.max}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
            <div
              className="h-full rounded-full bg-gradient-to-r from-ember-600 to-ember-400"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}
      {character.conditions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {character.conditions.map((c) => (
            <Badge key={c} color="red">
              {c}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

export default function PartyPanel({
  campaignId,
  rulesetId,
}: {
  campaignId: string
  rulesetId?: string
}) {
  const { data: party } = useParty(campaignId)
  const { data: characters } = useCharacters(campaignId)
  const addToParty = useAddToParty(campaignId)
  const removeFromParty = useRemoveFromParty(campaignId)
  const [wizardOpen, setWizardOpen] = useState(false)

  const partyIds = new Set((party || []).map((c) => c.id))
  // PCs that exist but are not currently in the party.
  const available = (characters || []).filter(
    (c) => c.is_player_character && !partyIds.has(c.id),
  )

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <PanelTitle>Party ({party?.length || 0})</PanelTitle>
        <Button variant="secondary" onClick={() => setWizardOpen(true)}>
          + New
        </Button>
      </div>

      {(!party || party.length === 0) && (
        <p className="text-sm text-ink-600">No party members yet. Create a character to begin.</p>
      )}

      <div className="space-y-2">
        {(party || []).map((c) => (
          <MemberCard
            key={c.id}
            character={c}
            onRemove={() => removeFromParty.mutate(c.id)}
          />
        ))}
      </div>

      {available.length > 0 && (
        <div>
          <PanelTitle>Available Characters</PanelTitle>
          <div className="space-y-2">
            {available.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between rounded-lg border border-ink-700 bg-ink-900/60 p-2"
              >
                <span className="text-sm text-ink-100">{c.name}</span>
                <Button variant="secondary" onClick={() => addToParty.mutate(c.id)}>
                  Add
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <CharacterWizard
        campaignId={campaignId}
        rulesetId={rulesetId}
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
      />
    </div>
  )
}
