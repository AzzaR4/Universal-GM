import { Badge, PanelTitle } from '../lib/ui'
import type { Character } from '../types'

export default function CharacterPanel({ character }: { character?: Character }) {
  if (!character) {
    return (
      <div className="p-4 text-sm text-ink-600">
        No player character yet. Add one from the World panel.
      </div>
    )
  }
  const resources = character.ruleset_data?.resources || {}
  const attributes = character.ruleset_data?.attributes || {}

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto p-4">
      <div>
        <PanelTitle>Character</PanelTitle>
        <h2 className="text-lg font-bold text-ink-100">{character.name}</h2>
        <p className="mt-1 text-xs text-ink-600">{character.description}</p>
        <div className="mt-2">
          <Badge color={character.status === 'alive' ? 'green' : 'red'}>{character.status}</Badge>
        </div>
      </div>

      {Object.keys(resources).length > 0 && (
        <div>
          <PanelTitle>Resources</PanelTitle>
          <div className="space-y-3">
            {Object.entries(resources).map(([name, r]) => {
              const pct = r.max > 0 ? Math.round((r.current / r.max) * 100) : 0
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
                      className="h-full rounded-full bg-gradient-to-r from-ember-600 to-ember-400 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {Object.keys(attributes).length > 0 && (
        <div>
          <PanelTitle>Attributes</PanelTitle>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(attributes).map(([name, val]) => (
              <div key={name} className="rounded-lg border border-ink-700 bg-ink-900 p-2 text-center">
                <div className="text-lg font-bold text-ember-400">{val}</div>
                <div className="text-[10px] uppercase tracking-wide text-ink-600">{name}</div>
              </div>
            ))}
          </div>
        </div>
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
