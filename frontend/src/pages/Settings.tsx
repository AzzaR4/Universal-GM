import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useProviderPresets, useProviders } from '../hooks/queries'
import { Badge, Button, Card, Input, Label } from '../lib/ui'
import type { AIProvider } from '../types'

const empty = {
  name: '',
  provider_type: 'openai_compatible',
  endpoint_url: 'https://api.openai.com/v1',
  model_name: 'gpt-4o-mini',
  api_key: '',
  temperature: 0.8,
  max_tokens: 1024,
  context_window: 8192,
  is_active: true,
}

export default function Settings() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: providers } = useProviders()
  const { data: presets } = useProviderPresets()
  const [form, setForm] = useState({ ...empty })
  const [editingId, setEditingId] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  function applyPreset(name: string) {
    const p = presets?.find((x) => x.name === name)
    if (!p) return
    setForm((f) => ({
      ...f,
      name: f.name || p.name,
      endpoint_url: p.endpoint_url,
      model_name: p.model_name,
    }))
  }

  async function save() {
    setBusy(true)
    try {
      if (editingId) {
        const payload: any = { ...form }
        if (!payload.api_key) delete payload.api_key
        await api.updateProvider(editingId, payload)
      } else {
        await api.createProvider(form)
      }
      await qc.invalidateQueries({ queryKey: ['providers'] })
      setForm({ ...empty })
      setEditingId(null)
    } catch (e: any) {
      alert(`Save failed: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  function edit(p: AIProvider) {
    setEditingId(p.id)
    setForm({
      name: p.name,
      provider_type: p.provider_type,
      endpoint_url: p.endpoint_url,
      model_name: p.model_name,
      api_key: '',
      temperature: p.temperature,
      max_tokens: p.max_tokens,
      context_window: p.context_window,
      is_active: p.is_active,
    })
  }

  async function test(id: string) {
    setTestResults((r) => ({ ...r, [id]: '⏳ Testing…' }))
    try {
      const res = await api.testProvider(id)
      setTestResults((r) => ({
        ...r,
        [id]: res.ok
          ? `✓ OK (${res.latency_ms}ms) — ${res.detail}`
          : `✗ Failed: ${res.detail}`,
      }))
    } catch (e: any) {
      setTestResults((r) => ({ ...r, [id]: `✗ ${e.message}` }))
    }
  }

  async function activate(id: string) {
    await api.activateProvider(id)
    qc.invalidateQueries({ queryKey: ['providers'] })
  }

  async function remove(id: string) {
    if (!confirm('Delete this provider?')) return
    await api.deleteProvider(id)
    qc.invalidateQueries({ queryKey: ['providers'] })
  }

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-6 py-10">
      <button onClick={() => navigate(-1)} className="mb-4 text-sm text-ink-600 hover:text-ink-100">
        ← Back
      </button>
      <h1 className="mb-1 text-3xl font-bold text-ink-100">AI Provider Settings</h1>
      <p className="mb-8 text-ink-600">
        Configure the AI that powers your Game Master. Works with OpenAI, Ollama, LM Studio, Groq,
        and any OpenAI-compatible endpoint. Switch providers anytime.
      </p>

      {/* Existing providers */}
      <div className="mb-8 space-y-3">
        {providers?.length === 0 && (
          <Card className="text-ink-600">No providers configured yet. Add one below.</Card>
        )}
        {providers?.map((p) => (
          <Card key={p.id}>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-ink-100">{p.name}</span>
                  {p.is_active ? <Badge color="green">Active</Badge> : <Badge>Inactive</Badge>}
                  {p.has_api_key && <Badge color="arcane">Key set</Badge>}
                </div>
                <p className="mt-1 text-xs text-ink-600">
                  {p.model_name} · {p.endpoint_url}
                </p>
                {testResults[p.id] && (
                  <p className="mt-2 text-xs text-ember-400">{testResults[p.id]}</p>
                )}
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <Button variant="secondary" onClick={() => test(p.id)}>
                  Test
                </Button>
                {!p.is_active && (
                  <Button variant="secondary" onClick={() => activate(p.id)}>
                    Set Active
                  </Button>
                )}
                <Button variant="ghost" onClick={() => edit(p)}>
                  Edit
                </Button>
                <Button variant="danger" onClick={() => remove(p.id)}>
                  Delete
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Add / edit form */}
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-ink-100">
          {editingId ? 'Edit Provider' : 'Add Provider'}
        </h2>

        <div className="mb-4">
          <Label>Preset</Label>
          <select
            className="w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-ink-100"
            onChange={(e) => applyPreset(e.target.value)}
            defaultValue=""
          >
            <option value="" disabled>
              Choose a preset…
            </option>
            {presets?.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label>Name</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My OpenAI" />
          </div>
          <div>
            <Label>Model Name</Label>
            <Input value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label>Endpoint URL</Label>
            <Input value={form.endpoint_url} onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <Label>API Key {editingId && '(leave blank to keep existing)'}</Label>
            <Input
              type="password"
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              placeholder="sk-… (not required for local providers)"
            />
          </div>
          <div>
            <Label>Temperature: {form.temperature}</Label>
            <input
              type="range"
              min={0}
              max={2}
              step={0.1}
              value={form.temperature}
              onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
              className="w-full accent-ember-500"
            />
          </div>
          <div>
            <Label>Max Tokens</Label>
            <Input
              type="number"
              value={form.max_tokens}
              onChange={(e) => setForm({ ...form, max_tokens: parseInt(e.target.value) || 256 })}
            />
          </div>
        </div>

        <label className="mt-4 flex items-center gap-2 text-sm text-ink-100">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            className="accent-ember-500"
          />
          Set as active provider
        </label>

        <div className="mt-6 flex gap-2">
          <Button disabled={busy || !form.name} onClick={save}>
            {busy ? 'Saving…' : editingId ? 'Update Provider' : 'Add Provider'}
          </Button>
          {editingId && (
            <Button
              variant="secondary"
              onClick={() => {
                setEditingId(null)
                setForm({ ...empty })
              }}
            >
              Cancel
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}
