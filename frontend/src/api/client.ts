import type {
  AIProvider,
  Campaign,
  Character,
  EventLogEntry,
  Location,
  NPC,
  ProviderPreset,
  Quest,
  Ruleset,
  CombatResponse,
} from '../types'

const BASE = '/api'

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  // Meta
  rulesets: () => req<Ruleset[]>('/rulesets'),
  rulesetSchema: (id: string) => req<any>(`/rulesets/${id}/schema`),

  // Campaigns
  listCampaigns: () => req<Campaign[]>('/campaigns'),
  getCampaign: (id: string) => req<Campaign>(`/campaigns/${id}`),
  createCampaign: (data: Partial<Campaign>) =>
    req<Campaign>('/campaigns', { method: 'POST', body: JSON.stringify(data) }),
  updateCampaign: (id: string, data: Partial<Campaign>) =>
    req<Campaign>(`/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCampaign: (id: string) => req<any>(`/campaigns/${id}`, { method: 'DELETE' }),
  events: (id: string) => req<EventLogEntry[]>(`/campaigns/${id}/events`),

  // Characters
  listCharacters: (cid: string) => req<Character[]>(`/campaigns/${cid}/characters`),
  createCharacter: (cid: string, data: Partial<Character>) =>
    req<Character>(`/campaigns/${cid}/characters`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateCharacter: (cid: string, id: string, data: Partial<Character>) =>
    req<Character>(`/campaigns/${cid}/characters/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteCharacter: (cid: string, id: string) =>
    req<any>(`/campaigns/${cid}/characters/${id}`, { method: 'DELETE' }),

  // NPCs
  listNPCs: (cid: string) => req<NPC[]>(`/campaigns/${cid}/npcs`),
  createNPC: (cid: string, data: Partial<NPC>) =>
    req<NPC>(`/campaigns/${cid}/npcs`, { method: 'POST', body: JSON.stringify(data) }),
  updateNPC: (cid: string, id: string, data: Partial<NPC>) =>
    req<NPC>(`/campaigns/${cid}/npcs/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteNPC: (cid: string, id: string) =>
    req<any>(`/campaigns/${cid}/npcs/${id}`, { method: 'DELETE' }),

  // Locations
  listLocations: (cid: string) => req<Location[]>(`/campaigns/${cid}/locations`),
  createLocation: (cid: string, data: Partial<Location>) =>
    req<Location>(`/campaigns/${cid}/locations`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateLocation: (cid: string, id: string, data: Partial<Location>) =>
    req<Location>(`/campaigns/${cid}/locations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteLocation: (cid: string, id: string) =>
    req<any>(`/campaigns/${cid}/locations/${id}`, { method: 'DELETE' }),

  // Quests
  listQuests: (cid: string) => req<Quest[]>(`/campaigns/${cid}/quests`).catch(() => []),

  // Combat
  getCombat: (cid: string) => req<CombatResponse>(`/campaigns/${cid}/combat`),
  startCombat: (cid: string, data: { enemy_ids?: string[]; default_enemy_hp?: number } = {}) =>
    req<CombatResponse>(`/campaigns/${cid}/combat/start`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  combatAction: (
    cid: string,
    data: {
      actor_id?: string | null
      target_id?: string | null
      action_type?: string
      skill_used?: string | null
      description?: string
      metadata?: Record<string, any>
      end_turn?: boolean
    },
  ) =>
    req<CombatResponse>(`/campaigns/${cid}/combat/action`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  endCombat: (cid: string) =>
    req<CombatResponse>(`/campaigns/${cid}/combat/end`, { method: 'POST' }),

  // AI providers
  listProviders: () => req<AIProvider[]>('/settings/providers'),
  providerPresets: () => req<ProviderPreset[]>('/settings/providers/presets'),
  createProvider: (data: any) =>
    req<AIProvider>('/settings/providers', { method: 'POST', body: JSON.stringify(data) }),
  updateProvider: (id: string, data: any) =>
    req<AIProvider>(`/settings/providers/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  activateProvider: (id: string) =>
    req<AIProvider>(`/settings/providers/${id}/activate`, { method: 'POST' }),
  deleteProvider: (id: string) =>
    req<any>(`/settings/providers/${id}`, { method: 'DELETE' }),
  testProvider: (id: string) =>
    req<{ ok: boolean; latency_ms: number | null; detail: string; model: string }>(
      `/settings/providers/${id}/test`,
      { method: 'POST' },
    ),

  // Export / import
  exportCampaign: (id: string) => req<any>(`/campaigns/${id}/export`),
  importCampaign: (data: any) =>
    req<{ imported: boolean; campaign_id: string }>('/campaigns/import', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

// SSE action streaming via fetch + ReadableStream (POST body support).
export interface StreamEvent {
  type: string
  data: any
}

export async function streamAction(
  campaignId: string,
  text: string,
  onEvent: (ev: StreamEvent) => void,
): Promise<void> {
  const res = await fetch(`${BASE}/campaigns/${campaignId}/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok || !res.body) {
    throw new Error(`Action request failed: ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      const lines = chunk.split('\n')
      let eventType = 'message'
      let dataStr = ''
      for (const line of lines) {
        if (line.startsWith('event:')) eventType = line.slice(6).trim()
        else if (line.startsWith('data:')) dataStr += line.slice(5).trim()
      }
      if (dataStr) {
        try {
          onEvent({ type: eventType, data: JSON.parse(dataStr) })
        } catch {
          onEvent({ type: eventType, data: dataStr })
        }
      }
    }
  }
}
