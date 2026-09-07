import { Badge, Button, PanelTitle } from '../lib/ui'
import type { EventLogEntry, Location, NPC } from '../types'

const EVENT_ICON: Record<string, string> = {
  action_attempted: '⚔',
  check_resolved: '🎲',
  narration_generated: '📜',
  character_damaged: '💥',
  character_moved: '🚶',
}

export default function WorldPanel({
  location,
  npcs,
  events,
  onAddNPC,
  onAddLocation,
}: {
  location?: Location
  npcs: NPC[]
  events: EventLogEntry[]
  onAddNPC: () => void
  onAddLocation: () => void
}) {
  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto p-4">
      <div>
        <div className="flex items-center justify-between">
          <PanelTitle>Location</PanelTitle>
          <button onClick={onAddLocation} className="text-xs text-ember-400 hover:text-ember-500">
            + Add
          </button>
        </div>
        {location ? (
          <div>
            <h3 className="font-semibold text-ink-100">{location.name}</h3>
            <p className="mt-1 text-xs text-ink-600">{location.description}</p>
            {location.atmosphere && (
              <p className="mt-2 text-xs italic text-arcane-400">“{location.atmosphere}”</p>
            )}
          </div>
        ) : (
          <p className="text-xs text-ink-600">No location set. Add one to begin.</p>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between">
          <PanelTitle>NPCs Present</PanelTitle>
          <button onClick={onAddNPC} className="text-xs text-ember-400 hover:text-ember-500">
            + Add
          </button>
        </div>
        {npcs.length === 0 ? (
          <p className="text-xs text-ink-600">No one is here.</p>
        ) : (
          <ul className="space-y-2">
            {npcs.map((n) => (
              <li key={n.id} className="rounded-lg border border-ink-700 bg-ink-900 p-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink-100">{n.name}</span>
                  <Badge color={n.status === 'alive' ? 'ink' : 'red'}>{n.status}</Badge>
                </div>
                {n.current_activity && (
                  <p className="mt-0.5 text-[11px] text-ink-600">{n.current_activity}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <PanelTitle>Event Log</PanelTitle>
        {events.length === 0 ? (
          <p className="text-xs text-ink-600">No events yet.</p>
        ) : (
          <ul className="space-y-1.5">
            {events.slice(0, 20).map((e) => (
              <li key={e.id} className="flex gap-2 text-[11px] text-ink-600">
                <span>{EVENT_ICON[e.event_type] || '•'}</span>
                <span className="flex-1">
                  {e.data?.summary || e.event_type.replace(/_/g, ' ')}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
