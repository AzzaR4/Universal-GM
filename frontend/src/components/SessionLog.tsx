import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { streamSessionEnd } from '../api/client'
import { useCampaign, useSessions, useStartSession } from '../hooks/queries'
import { Badge, Button, PanelTitle } from '../lib/ui'
import type { GameSession } from '../types'

function fmt(ts: string | null): string {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
}

function SessionCard({ session }: { session: GameSession }) {
  const [open, setOpen] = useState(false)
  const active = !session.ended_at
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 p-3">
      <button className="flex w-full items-center justify-between text-left" onClick={() => setOpen(!open)}>
        <div>
          <div className="text-sm font-medium text-ink-100">
            {fmt(session.started_at)}
            {active && <span className="ml-2 text-ember-400">● live</span>}
          </div>
          <div className="text-[11px] text-ink-600">
            {session.player_actions_count} actions
            {session.xp_awarded != null && ` · ${session.xp_awarded} XP`}
          </div>
        </div>
        <span className="text-ink-600">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {session.xp_awarded != null && <Badge color="ember">+{session.xp_awarded} XP</Badge>}
          {session.summary ? (
            <p className="whitespace-pre-line text-xs text-ink-100">{session.summary}</p>
          ) : (
            <p className="text-xs text-ink-600">No recap yet.</p>
          )}
          {Array.isArray(session.key_events) && session.key_events.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wide text-ink-600">Key events</div>
              <ul className="mt-1 space-y-0.5 text-xs text-ink-100">
                {session.key_events.map((e, i) => (
                  <li key={i}>◆ {typeof e === 'string' ? e : (e as any).title || JSON.stringify(e)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function SessionLog({ campaignId }: { campaignId: string }) {
  const qc = useQueryClient()
  const { data: campaign } = useCampaign(campaignId)
  const { data: sessions } = useSessions(campaignId)
  const startSession = useStartSession(campaignId)

  const [ending, setEnding] = useState(false)
  const [recap, setRecap] = useState('')
  const [error, setError] = useState<string | null>(null)

  const activeSession = (sessions || []).find((s) => !s.ended_at)

  async function endSession() {
    if (!activeSession) return
    setEnding(true)
    setRecap('')
    setError(null)
    try {
      await streamSessionEnd(campaignId, activeSession.id, (ev) => {
        if (ev.type === 'recap') {
          setRecap((prev) => prev + (typeof ev.data === 'string' ? ev.data : ev.data?.text || ''))
        } else if (ev.type === 'error') {
          setError(typeof ev.data === 'string' ? ev.data : ev.data?.detail || 'Error')
        }
      })
    } catch (e: any) {
      setError(e?.message || 'Failed to end session')
    } finally {
      setEnding(false)
      qc.invalidateQueries({ queryKey: ['sessions', campaignId] })
      qc.invalidateQueries({ queryKey: ['campaign', campaignId] })
    }
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <div className="flex items-center justify-between">
        <PanelTitle>Sessions ({sessions?.length || 0})</PanelTitle>
        {activeSession ? (
          <Button variant="danger" onClick={endSession} disabled={ending}>
            {ending ? 'Ending…' : 'End Session'}
          </Button>
        ) : (
          <Button onClick={() => startSession.mutate()} disabled={startSession.isPending}>
            ▶ Start Session
          </Button>
        )}
      </div>

      {!campaign?.current_session_id && !activeSession && (
        <p className="text-sm text-ink-600">
          No active session. Start one to track actions and generate an AI recap when you end it.
        </p>
      )}

      {ending && recap && (
        <div className="rounded-lg border border-ember-600/40 bg-ember-600/10 p-3">
          <div className="mb-1 text-[10px] uppercase tracking-wide text-ember-400">Generating recap…</div>
          <p className="whitespace-pre-line text-xs text-ink-100">{recap}</p>
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-300">
          ⚠ {error}
        </div>
      )}

      <div className="space-y-2">
        {(sessions || []).map((s) => (
          <SessionCard key={s.id} session={s} />
        ))}
      </div>
    </div>
  )
}
