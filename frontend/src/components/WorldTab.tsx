import { useState } from 'react'
import {
  useCreateFaction,
  useDeleteFaction,
  useFactions,
  useTickWorld,
  useWorldEvents,
} from '../hooks/queries'
import { Badge, Button, Input, Label, PanelTitle, Textarea } from '../lib/ui'
import type { Faction } from '../types'
import Modal from './Modal'

const DISPOSITIONS = ['friendly', 'neutral', 'hostile']
const AUTONOMY = ['passive', 'active', 'aggressive']

function dispositionColor(d: string): 'green' | 'ink' | 'red' {
  if (d === 'friendly') return 'green'
  if (d === 'hostile') return 'red'
  return 'ink'
}

function StatBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-0.5 flex justify-between text-[10px]">
        <span className="text-ink-600">{label}</span>
        <span className="font-mono text-ink-100">{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
        <div
          className="h-full rounded-full bg-gradient-to-r from-arcane-600 to-arcane-400"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  )
}

function FactionCard({ faction, onDelete }: { faction: Faction; onDelete: () => void }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 p-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-semibold text-ink-100">{faction.name}</div>
          <div className="mt-0.5 flex flex-wrap gap-1">
            <Badge color={dispositionColor(faction.disposition)}>{faction.disposition}</Badge>
            <Badge color="arcane">{faction.autonomy_level}</Badge>
          </div>
        </div>
        <button onClick={onDelete} className="text-ink-600 hover:text-red-400" title="Delete">
          ✕
        </button>
      </div>
      {faction.description && <p className="mt-1.5 text-xs text-ink-600">{faction.description}</p>}
      <div className="mt-2 grid grid-cols-2 gap-2">
        <StatBar label="Influence" value={faction.influence} />
        <StatBar label="Resources" value={faction.resources} />
      </div>
      {Array.isArray(faction.goals) && faction.goals.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-[11px] text-ink-100">
          {faction.goals.map((g, i) => (
            <li key={i}>◆ {typeof g === 'string' ? g : JSON.stringify(g)}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function WorldTab({ campaignId }: { campaignId: string }) {
  const { data: factions } = useFactions(campaignId)
  const { data: events } = useWorldEvents(campaignId)
  const createFaction = useCreateFaction(campaignId)
  const deleteFaction = useDeleteFaction(campaignId)
  const tickWorld = useTickWorld(campaignId)

  const [modalOpen, setModalOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [goals, setGoals] = useState('')
  const [disposition, setDisposition] = useState('neutral')
  const [autonomy, setAutonomy] = useState('active')

  function resetForm() {
    setName('')
    setDescription('')
    setGoals('')
    setDisposition('neutral')
    setAutonomy('active')
  }

  function createSubmit() {
    createFaction.mutate({
      name: name.trim(),
      description: description.trim(),
      goals: goals
        .split('\n')
        .map((g) => g.trim())
        .filter(Boolean),
      disposition,
      autonomy_level: autonomy,
    })
    resetForm()
    setModalOpen(false)
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <PanelTitle>Factions ({factions?.length || 0})</PanelTitle>
        <div className="flex gap-1.5">
          <Button variant="secondary" onClick={() => setModalOpen(true)}>
            + Faction
          </Button>
          <Button
            onClick={() => tickWorld.mutate(true)}
            disabled={tickWorld.isPending}
            title="Advance the world one turn"
          >
            {tickWorld.isPending ? '…' : '⟳ Tick World'}
          </Button>
        </div>
      </div>

      {(!factions || factions.length === 0) && (
        <p className="text-sm text-ink-600">
          No factions yet. Create one, then tick the world to see it act autonomously.
        </p>
      )}
      <div className="space-y-2">
        {(factions || []).map((f) => (
          <FactionCard key={f.id} faction={f} onDelete={() => deleteFaction.mutate(f.id)} />
        ))}
      </div>

      <div>
        <PanelTitle>World Events</PanelTitle>
        {(!events || events.length === 0) && (
          <p className="text-sm text-ink-600">No world events yet.</p>
        )}
        <div className="space-y-2">
          {(events || []).map((ev) => (
            <div key={ev.id} className="rounded-lg border border-ink-700 bg-ink-900/60 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-ink-100">{ev.title}</span>
                <Badge color={ev.is_revealed ? 'ember' : 'ink'}>
                  {ev.is_revealed ? 'revealed' : 'hidden'}
                </Badge>
              </div>
              {ev.description && <p className="mt-1 text-xs text-ink-600">{ev.description}</p>}
              <div className="mt-1 text-[10px] uppercase tracking-wide text-ink-600">
                {ev.event_type}
              </div>
            </div>
          ))}
        </div>
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Faction">
        <div className="space-y-3">
          <div>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. The Iron Syndicate" />
          </div>
          <div>
            <Label>Description</Label>
            <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <Label>Goals (one per line)</Label>
            <Textarea
              rows={2}
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
              placeholder={'Control the docks\nEliminate rivals'}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Disposition</Label>
              <select
                className="w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-ink-100"
                value={disposition}
                onChange={(e) => setDisposition(e.target.value)}
              >
                {DISPOSITIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Autonomy</Label>
              <select
                className="w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-ink-100"
                value={autonomy}
                onChange={(e) => setAutonomy(e.target.value)}
              >
                {AUTONOMY.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Button className="w-full" disabled={!name.trim()} onClick={createSubmit}>
            Create Faction
          </Button>
        </div>
      </Modal>
    </div>
  )
}
