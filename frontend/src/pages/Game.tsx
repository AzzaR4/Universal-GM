import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api, streamAction } from '../api/client'
import {
  useCampaign,
  useCharacters,
  useCombat,
  useCombatAction,
  useCreateLocation,
  useCreateNPC,
  useEndCombat,
  useEvents,
  useLocations,
  useNPCs,
  useStartCombat,
} from '../hooks/queries'
import { useSessionStore } from '../stores/sessionStore'
import { Button, Input, Textarea } from '../lib/ui'
import CharacterPanel from '../components/CharacterPanel'
import CombatTracker from '../components/CombatTracker'
import WorldPanel from '../components/WorldPanel'
import DiceDisplay from '../components/DiceDisplay'
import Modal from '../components/Modal'
import PartyPanel from '../components/PartyPanel'
import WorldTab from '../components/WorldTab'
import MemoryBrowser from '../components/MemoryBrowser'
import SessionLog from '../components/SessionLog'

export default function Game() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: campaign } = useCampaign(id)
  const { data: characters } = useCharacters(id)
  const { data: npcs } = useNPCs(id)
  const { data: locations } = useLocations(id)
  const { data: events } = useEvents(id)

  const createNPC = useCreateNPC(id)
  const createLocation = useCreateLocation(id)

  const { data: combatData } = useCombat(id)
  const startCombat = useStartCombat(id)
  const combatAction = useCombatAction(id)
  const endCombat = useEndCombat(id)
  const combat = combatData?.combat && combatData.active ? combatData.combat : null

  const {
    messages,
    currentDice,
    isStreaming,
    error,
    addMessage,
    appendToMessage,
    finalizeMessage,
    setDice,
    setStreaming,
    setError,
  } = useSessionStore()

  const [input, setInput] = useState('')
  const [modal, setModal] = useState<ModalKind>(null)
  const [rightTab, setRightTab] = useState<RightTab>('scene')
  const scrollRef = useRef<HTMLDivElement>(null)

  const pc = characters?.find((c) => c.is_player_character)
  const currentLocation = locations?.find((l) => l.id === campaign?.current_location_id)
  const npcsHere = (npcs || []).filter(
    (n) => !currentLocation || n.location_id === currentLocation.id || !n.location_id,
  )

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    setError(null)
    setDice(null)
    addMessage({ id: `p-${Date.now()}`, role: 'player', text })
    const gmId = `gm-${Date.now()}`
    addMessage({ id: gmId, role: 'gm', text: '', streaming: true })
    setStreaming(true)

    try {
      await streamAction(id, text, (ev) => {
        if (ev.type === 'dice') {
          setDice(ev.data)
        } else if (ev.type === 'narrative') {
          appendToMessage(gmId, typeof ev.data === 'string' ? ev.data : '')
        } else if (ev.type === 'error') {
          setError(typeof ev.data === 'string' ? ev.data : JSON.stringify(ev.data))
        } else if (ev.type === 'complete') {
          finalizeMessage(gmId)
        }
      })
    } catch (e: any) {
      setError(e.message)
    } finally {
      finalizeMessage(gmId)
      setStreaming(false)
      qc.invalidateQueries({ queryKey: ['characters', id] })
      qc.invalidateQueries({ queryKey: ['events', id] })
      qc.invalidateQueries({ queryKey: ['npcs', id] })
      qc.invalidateQueries({ queryKey: ['campaign', id] })
    }
  }

  async function exportCampaign() {
    const data = await api.exportCampaign(id)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${campaign?.name.replace(/\s+/g, '_') || 'campaign'}_export.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex h-screen flex-col bg-ink-950">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-ink-700 bg-ink-900/80 px-4 py-2.5 backdrop-blur">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-ink-600 hover:text-ink-100">
            ←
          </Link>
          <span className="text-lg">🎲</span>
          <span className="font-bold text-ink-100">Universal GM</span>
          <span className="text-ink-600">|</span>
          <span className="text-sm text-ember-400">{campaign?.name}</span>
        </div>
        <div className="flex gap-2">
          {!combat && (
            <Button
              variant="danger"
              onClick={() => startCombat.mutate({})}
              disabled={startCombat.isPending}
            >
              ⚔ Start Combat
            </Button>
          )}
          <Button variant="secondary" onClick={exportCampaign}>
            ⬇ Export
          </Button>
          <Link to="/rulesets/builder">
            <Button variant="secondary">🛠️ Rulesets</Button>
          </Link>
          <Link to="/settings">
            <Button variant="secondary">⚙ Settings</Button>
          </Link>
        </div>
      </header>

      {/* Three panels */}
      <div className="grid flex-1 grid-cols-1 overflow-hidden md:grid-cols-[280px_1fr_300px]">
        {/* Left */}
        <aside className="hidden border-r border-ink-700 bg-ink-900/40 md:block">
          <CharacterPanel character={pc} rulesetId={campaign?.ruleset_id} />
        </aside>

        {/* Center */}
        <main className="flex flex-col overflow-hidden">
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-6">
            {messages.length === 0 && (
              <div className="mx-auto max-w-lg pt-12 text-center">
                <p className="text-2xl">📖</p>
                <p className="mt-3 narrative-prose text-ink-600">
                  {currentLocation
                    ? `You find yourself in ${currentLocation.name}. ${currentLocation.description} What do you do?`
                    : 'Your adventure awaits. Describe your first action to begin.'}
                </p>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className="animate-fade-in">
                {m.role === 'player' ? (
                  <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-arcane-600/20 px-4 py-2 text-sm text-arcane-400 border border-arcane-600/30 w-fit">
                    <span className="mr-1 font-semibold">You:</span> {m.text}
                  </div>
                ) : (
                  <div className="narrative-prose text-ink-100">
                    <span className={m.streaming && !m.text ? 'cursor-blink' : ''}>{m.text}</span>
                    {m.streaming && m.text && <span className="cursor-blink" />}
                  </div>
                )}
              </div>
            ))}

            {isStreaming && (
              <div className="flex items-center gap-2 text-sm text-ink-600">
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-ember-500 border-t-transparent" />
                The GM is weaving your tale…
              </div>
            )}
          </div>

          {/* Dice + error + input */}
          <div className="space-y-3 border-t border-ink-700 bg-ink-900/60 p-4">
            {currentDice && <DiceDisplay dice={currentDice} />}
            {error && (
              <div className="rounded-lg border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-300">
                ⚠ {error}{' '}
                <Link to="/settings" className="underline hover:text-red-100">
                  Open Settings
                </Link>
              </div>
            )}
            <div className="flex items-end gap-2">
              <Textarea
                rows={2}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    send()
                  }
                }}
                placeholder="Describe your action…  (Enter to send, Shift+Enter for newline)"
                disabled={isStreaming}
              />
              <Button onClick={send} disabled={isStreaming || !input.trim()}>
                Send
              </Button>
            </div>
          </div>
        </main>

        {/* Right */}
        <aside className="hidden flex-col border-l border-ink-700 bg-ink-900/40 md:flex">
          {combat ? (
            <CombatTracker
              combat={combat}
              busy={combatAction.isPending}
              onAction={(d) => combatAction.mutate(d)}
              onEnd={() => endCombat.mutate()}
            />
          ) : (
            <>
              <div className="flex flex-shrink-0 border-b border-ink-700 text-xs">
                {RIGHT_TABS.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setRightTab(t.key)}
                    className={`flex-1 py-2 font-medium transition-colors ${
                      rightTab === t.key
                        ? 'bg-ink-800 text-ember-400'
                        : 'text-ink-600 hover:text-ink-100'
                    }`}
                    title={t.label}
                  >
                    {t.icon}
                  </button>
                ))}
              </div>
              <div className="flex-1 overflow-hidden">
                {rightTab === 'scene' && (
                  <WorldPanel
                    location={currentLocation}
                    npcs={npcsHere}
                    events={events || []}
                    onAddNPC={() => setModal('npc')}
                    onAddLocation={() => setModal('location')}
                  />
                )}
                {rightTab === 'party' && (
                  <PartyPanel campaignId={id} rulesetId={campaign?.ruleset_id} />
                )}
                {rightTab === 'world' && <WorldTab campaignId={id} />}
                {rightTab === 'memory' && <MemoryBrowser campaignId={id} />}
                {rightTab === 'sessions' && <SessionLog campaignId={id} />}
              </div>
            </>
          )}
        </aside>
      </div>

      <EntityModals
        campaignId={id}
        onCreateNPC={(d) => createNPC.mutate({ ...d, location_id: currentLocation?.id })}
        onCreateLocation={(d) => createLocation.mutate(d)}
        modal={modal}
        setModal={setModal}
      />
    </div>
  )
}

type ModalKind = null | 'npc' | 'location'

type RightTab = 'scene' | 'party' | 'world' | 'memory' | 'sessions'

const RIGHT_TABS: Array<{ key: RightTab; label: string; icon: string }> = [
  { key: 'scene', label: 'Scene', icon: '🗺️' },
  { key: 'party', label: 'Party', icon: '👥' },
  { key: 'world', label: 'World', icon: '🌐' },
  { key: 'memory', label: 'Memory', icon: '🧠' },
  { key: 'sessions', label: 'Sessions', icon: '📜' },
]

// Small wrapper managing modal state via closure-free hook usage.
function EntityModals({
  onCreateNPC,
  onCreateLocation,
  modal,
  setModal,
}: {
  campaignId: string
  onCreateNPC: (d: any) => void
  onCreateLocation: (d: any) => void
  modal: ModalKind
  setModal: (m: ModalKind) => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [atmosphere, setAtmosphere] = useState('')
  const [activity, setActivity] = useState('')

  function reset() {
    setName('')
    setDescription('')
    setAtmosphere('')
    setActivity('')
  }

  return (
    <>
      <Modal open={modal === 'npc'} onClose={() => setModal(null)} title="Add NPC">
        <div className="space-y-3">
          <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Textarea rows={2} placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          <Input placeholder="Current activity" value={activity} onChange={(e) => setActivity(e.target.value)} />
          <Button
            className="w-full"
            disabled={!name.trim()}
            onClick={() => {
              onCreateNPC({ name, description, current_activity: activity })
              reset()
              setModal(null)
            }}
          >
            Create NPC
          </Button>
        </div>
      </Modal>

      <Modal open={modal === 'location'} onClose={() => setModal(null)} title="Add Location">
        <div className="space-y-3">
          <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Textarea rows={2} placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          <Input placeholder="Atmosphere" value={atmosphere} onChange={(e) => setAtmosphere(e.target.value)} />
          <Button
            className="w-full"
            disabled={!name.trim()}
            onClick={() => {
              onCreateLocation({ name, description, atmosphere })
              reset()
              setModal(null)
            }}
          >
            Create Location
          </Button>
        </div>
      </Modal>
    </>
  )
}
