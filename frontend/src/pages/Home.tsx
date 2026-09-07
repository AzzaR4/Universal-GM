import { useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useCampaigns } from '../hooks/queries'
import { Badge, Button, Card } from '../lib/ui'

export default function Home() {
  const { data: campaigns, isLoading } = useCampaigns()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleImport(file: File) {
    const text = await file.text()
    try {
      const data = JSON.parse(text)
      const res = await api.importCampaign(data)
      await qc.invalidateQueries({ queryKey: ['campaigns'] })
      navigate(`/campaigns/${res.campaign_id}/play`)
    } catch (e: any) {
      alert(`Import failed: ${e.message}`)
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete campaign "${name}"? This cannot be undone.`)) return
    await api.deleteCampaign(id)
    qc.invalidateQueries({ queryKey: ['campaigns'] })
  }

  return (
    <div className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-4xl font-bold text-ink-100">
            <span className="text-ember-500">🎲</span> Universal GM
          </h1>
          <p className="mt-2 text-ink-600">
            An AI-powered Game Master for any tabletop RPG. Your worlds, your rules.
          </p>
        </div>
        <Link to="/settings">
          <Button variant="secondary">⚙ Settings</Button>
        </Link>
      </header>

      <div className="mb-6 flex gap-3">
        <Button onClick={() => navigate('/campaigns/new')}>+ New Campaign</Button>
        <Button variant="secondary" onClick={() => fileRef.current?.click()}>
          ⬆ Import Campaign
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleImport(e.target.files[0])}
        />
      </div>

      {isLoading && <p className="text-ink-600">Loading campaigns…</p>}

      {!isLoading && campaigns && campaigns.length === 0 && (
        <Card className="text-center py-16">
          <p className="text-lg text-ink-100">No campaigns yet.</p>
          <p className="mt-2 text-ink-600">
            Create your first campaign to begin your adventure.
          </p>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {campaigns?.map((c) => (
          <Card key={c.id} className="group relative">
            <div className="flex items-start justify-between">
              <h2 className="text-xl font-semibold text-ink-100">{c.name}</h2>
              <Badge color="ember">{c.ruleset_id}</Badge>
            </div>
            <p className="mt-1 text-sm text-ink-600 line-clamp-2 min-h-[2.5rem]">
              {c.description || 'No description.'}
            </p>
            {c.campaign_style && (
              <p className="mt-2 text-xs text-arcane-400">Style: {c.campaign_style}</p>
            )}
            <div className="mt-4 flex gap-2">
              <Link to={`/campaigns/${c.id}/play`} className="flex-1">
                <Button className="w-full">▶ Play</Button>
              </Link>
              <Button
                variant="secondary"
                onClick={() => api.exportCampaign(c.id).then(downloadJSON(c.name))}
              >
                ⬇
              </Button>
              <Button variant="danger" onClick={() => handleDelete(c.id, c.name)}>
                🗑
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

function downloadJSON(name: string) {
  return (data: any) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name.replace(/\s+/g, '_')}_export.json`
    a.click()
    URL.revokeObjectURL(url)
  }
}
