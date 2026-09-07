import { useState } from 'react'
import { Badge, Button, PanelTitle } from '../lib/ui'
import type { Combatant, CombatState } from '../types'

interface Props {
  combat: CombatState
  onAction: (data: {
    actor_id?: string | null
    target_id?: string | null
    action_type?: string
    description?: string
    end_turn?: boolean
  }) => void
  onEnd: () => void
  busy?: boolean
}

function HpBar({ c }: { c: Combatant }) {
  const pct = c.hp_max > 0 ? Math.round((c.hp_current / c.hp_max) * 100) : 0
  const color =
    pct > 50 ? 'from-green-600 to-green-400' : pct > 20 ? 'from-ember-600 to-ember-400' : 'from-red-700 to-red-500'
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px]">
        <span className="text-ink-100">{c.resource}</span>
        <span className="font-mono text-ink-600">
          {c.hp_current}/{c.hp_max}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
        <div className={`h-full rounded-full bg-gradient-to-r ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function CombatTracker({ combat, onAction, onEnd, busy }: Props) {
  const ordered = [...combat.combatants].sort((a, b) => b.initiative - a.initiative)
  const current = combat.combatants.find((c) => c.id === combat.current_id) || null
  const livingEnemies = combat.combatants.filter((c) => !c.is_player && c.status === 'alive')

  const [targetId, setTargetId] = useState<string>('')
  const effectiveTarget = targetId || livingEnemies[0]?.id || ''

  const actorIsPlayer = current?.is_player ?? false

  function attack() {
    if (!current) return
    onAction({
      actor_id: current.id,
      target_id: effectiveTarget || null,
      action_type: 'attack',
      description: `${current.name} attacks`,
      end_turn: true,
    })
  }

  function skipTurn() {
    if (!current) return
    onAction({
      actor_id: current.id,
      target_id: null,
      action_type: 'wait',
      description: `${current.name} holds their action`,
      end_turn: true,
    })
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <PanelTitle>
          <span className="text-red-400">⚔ Combat</span>
        </PanelTitle>
        <Badge color="ember">Round {combat.round}</Badge>
      </div>

      {combat.is_over && (
        <div className="rounded-lg border border-green-800 bg-green-900/30 px-3 py-2 text-sm text-green-300">
          The encounter is decided. End combat to continue the story.
        </div>
      )}

      {/* Turn order */}
      <div className="space-y-2">
        {ordered.map((c) => {
          const isCurrent = c.id === combat.current_id
          const defeated = c.status !== 'alive'
          return (
            <div
              key={c.id}
              className={`rounded-lg border p-2.5 transition-all ${
                isCurrent
                  ? 'border-ember-500 bg-ember-600/10 shadow-lg shadow-ember-600/10'
                  : 'border-ink-700 bg-ink-900/40'
              } ${defeated ? 'opacity-40' : ''}`}
            >
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded font-mono text-[11px] ${
                      c.is_player ? 'bg-arcane-600/30 text-arcane-300' : 'bg-red-900/40 text-red-300'
                    }`}
                    title="Initiative"
                  >
                    {c.initiative}
                  </span>
                  <span className={`text-sm font-semibold ${defeated ? 'line-through text-ink-600' : 'text-ink-100'}`}>
                    {c.name}
                  </span>
                  {isCurrent && !defeated && <Badge color="ember">Turn</Badge>}
                </div>
                {defeated ? (
                  <Badge color="red">Defeated</Badge>
                ) : (
                  <Badge color={c.is_player ? 'arcane' : 'red'}>{c.is_player ? 'PC' : 'Enemy'}</Badge>
                )}
              </div>
              <HpBar c={c} />
            </div>
          )
        })}
      </div>

      {/* Action controls */}
      {!combat.is_over && current && (
        <div className="space-y-2 rounded-lg border border-ink-700 bg-ink-900/60 p-3">
          <div className="text-xs text-ink-600">
            Current turn: <span className="text-ink-100">{current.name}</span>
          </div>
          {actorIsPlayer && livingEnemies.length > 0 && (
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-wide text-ink-600">Target</label>
              <select
                value={effectiveTarget}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full rounded-lg border border-ink-600 bg-ink-900 px-2 py-1.5 text-sm text-ink-100 outline-none focus:border-ember-500"
              >
                {livingEnemies.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} ({e.hp_current}/{e.hp_max})
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="flex gap-2">
            <Button className="flex-1" onClick={attack} disabled={busy || (actorIsPlayer && !effectiveTarget)}>
              ⚔ Attack
            </Button>
            <Button variant="secondary" onClick={skipTurn} disabled={busy}>
              Skip
            </Button>
          </div>
        </div>
      )}

      {/* Log */}
      {combat.log.length > 0 && (
        <div>
          <PanelTitle>Combat Log</PanelTitle>
          <ul className="space-y-1 text-xs text-ink-600">
            {combat.log.slice(-8).map((line, i) => (
              <li key={i} className="border-l-2 border-ink-700 pl-2">
                {line}
              </li>
            ))}
          </ul>
        </div>
      )}

      <Button variant="danger" className="mt-auto" onClick={onEnd} disabled={busy}>
        End Combat
      </Button>
    </div>
  )
}
