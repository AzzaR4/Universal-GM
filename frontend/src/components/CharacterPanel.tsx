import { Badge, PanelTitle } from '../lib/ui'
import type { Character } from '../types'

const DND_ABILITIES: Array<[string, string]> = [
  ['str', 'STR'],
  ['dex', 'DEX'],
  ['con', 'CON'],
  ['int', 'INT'],
  ['wis', 'WIS'],
  ['cha', 'CHA'],
]

function abilityMod(score: number): string {
  const m = Math.floor((score - 10) / 2)
  return m >= 0 ? `+${m}` : `${m}`
}

function ResourceBars({ resources }: { resources: Record<string, { current: number; max: number }> }) {
  if (Object.keys(resources).length === 0) return null
  return (
    <div>
      <PanelTitle>Resources</PanelTitle>
      <div className="space-y-3">
        {Object.entries(resources).map(([name, r]) => {
          const pct = r.max > 0 ? Math.round((r.current / r.max) * 100) : 0
          // Shadow / Stress are "bad" resources — fill in a warning color.
          const bad = /shadow|stress/i.test(name)
          const bar = bad ? 'from-arcane-600 to-red-500' : 'from-ember-600 to-ember-400'
          return (
            <div key={name}>
              <div className="mb-1 flex justify-between text-xs">
                <span className="text-ink-100">{name}</span>
                <span className="font-mono text-ink-600">
                  {r.current}/{r.max}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-ink-700">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${bar} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AttributeGrid({
  attributes,
  cols = 2,
}: {
  attributes: Record<string, number>
  cols?: number
}) {
  const entries = Object.entries(attributes)
  if (entries.length === 0) return null
  return (
    <div>
      <PanelTitle>Attributes</PanelTitle>
      <div className={`grid gap-2 ${cols === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
        {entries.map(([name, val]) => (
          <div key={name} className="rounded-lg border border-ink-700 bg-ink-900 p-2 text-center">
            <div className="text-lg font-bold text-ember-400">{val}</div>
            <div className="text-[10px] uppercase tracking-wide text-ink-600">{name}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/** D&D 5e — ability scores with modifiers, class/level, AC, proficiency. */
function DnD5eStats({ data }: { data: Character['ruleset_data'] & Record<string, any> }) {
  const abilities: Record<string, number> = data?.abilities || {}
  return (
    <>
      <div className="flex flex-wrap gap-1.5">
        {data?.char_class && <Badge color="ember">{data.char_class}</Badge>}
        {data?.level != null && <Badge color="arcane">Level {data.level}</Badge>}
      </div>
      <div className="grid grid-cols-3 gap-2">
        {(data?.armor_class != null || true) && (
          <Stat label="AC" value={data?.armor_class ?? '—'} />
        )}
        <Stat label="Prof" value={data?.proficiency_bonus != null ? `+${data.proficiency_bonus}` : '—'} />
        {data?.hit_dice && <Stat label="Hit Dice" value={data.hit_dice} />}
      </div>
      {Object.keys(abilities).length > 0 && (
        <div>
          <PanelTitle>Ability Scores</PanelTitle>
          <div className="grid grid-cols-3 gap-2">
            {DND_ABILITIES.filter(([k]) => abilities[k] != null).map(([k, label]) => (
              <div key={k} className="rounded-lg border border-ink-700 bg-ink-900 p-2 text-center">
                <div className="text-[10px] uppercase tracking-wide text-ink-600">{label}</div>
                <div className="text-lg font-bold text-ink-100">{abilities[k]}</div>
                <div className="text-xs font-mono text-ember-400">{abilityMod(abilities[k])}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 p-2 text-center">
      <div className="text-lg font-bold text-ember-400">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-ink-600">{label}</div>
    </div>
  )
}

export default function CharacterPanel({
  character,
  rulesetId,
}: {
  character?: Character
  rulesetId?: string
}) {
  if (!character) {
    return (
      <div className="p-4 text-sm text-ink-600">
        No player character yet. Add one from the World panel.
      </div>
    )
  }
  const data = (character.ruleset_data || {}) as Character['ruleset_data'] & Record<string, any>
  const resources = data.resources || {}
  const attributes = data.attributes || {}

  // Ruleset-specific condition flags surfaced as badges.
  const flags: string[] = []
  if (rulesetId === 'one_ring') {
    const shadow = resources['Shadow']
    if (shadow && shadow.current >= shadow.max) flags.push('Miserable')
    const end = resources['Endurance']
    if (end && end.max > 0 && end.current <= end.max * 0.25) flags.push('Weary')
  }
  if (rulesetId === 'alien_rpg') {
    if ((data.panic_level ?? 0) > 0) flags.push(`Panic ${data.panic_level}`)
    const stress = resources['Stress']
    if (stress && stress.current > 0) flags.push(`Stress ${stress.current}`)
  }

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto p-4">
      <div>
        <PanelTitle>Character</PanelTitle>
        <h2 className="text-lg font-bold text-ink-100">{character.name}</h2>
        {(data.culture || data.calling || data.career) && (
          <p className="mt-0.5 text-xs text-ember-400/80">
            {[data.culture, data.calling, data.career].filter(Boolean).join(' · ')}
          </p>
        )}
        <p className="mt-1 text-xs text-ink-600">{character.description}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge color={character.status === 'alive' ? 'green' : 'red'}>{character.status}</Badge>
          {flags.map((f) => (
            <Badge key={f} color="red">
              {f}
            </Badge>
          ))}
        </div>
      </div>

      <ResourceBars resources={resources} />

      {rulesetId === 'dnd5e' ? (
        <DnD5eStats data={data} />
      ) : rulesetId === 'one_ring' ? (
        <AttributeGrid attributes={attributes} cols={3} />
      ) : rulesetId === 'alien_rpg' ? (
        <AttributeGrid attributes={attributes} cols={2} />
      ) : (
        <AttributeGrid attributes={attributes} cols={2} />
      )}

      <div>
        <PanelTitle>Conditions</PanelTitle>
        {character.conditions.length === 0 ? (
          <p className="text-xs text-ink-600">None</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {character.conditions.map((c) => (
              <Badge key={c} color="red">
                {c}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <div>
        <PanelTitle>Inventory</PanelTitle>
        {character.inventory.length === 0 ? (
          <p className="text-xs text-ink-600">Empty</p>
        ) : (
          <ul className="space-y-1 text-sm text-ink-100">
            {character.inventory.map((item, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="text-ember-400">◆</span> {String(item)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
