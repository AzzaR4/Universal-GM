import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type {
  Character,
  CustomRuleset,
  Faction,
  Location,
  Memory,
  NPC,
  WorldEvent,
} from '../types'

export const useCampaigns = () =>
  useQuery({ queryKey: ['campaigns'], queryFn: api.listCampaigns })

export const useCampaign = (id: string) =>
  useQuery({ queryKey: ['campaign', id], queryFn: () => api.getCampaign(id), enabled: !!id })

export const useCharacters = (cid: string) =>
  useQuery({ queryKey: ['characters', cid], queryFn: () => api.listCharacters(cid), enabled: !!cid })

export const useNPCs = (cid: string) =>
  useQuery({ queryKey: ['npcs', cid], queryFn: () => api.listNPCs(cid), enabled: !!cid })

export const useLocations = (cid: string) =>
  useQuery({ queryKey: ['locations', cid], queryFn: () => api.listLocations(cid), enabled: !!cid })

export const useEvents = (cid: string) =>
  useQuery({ queryKey: ['events', cid], queryFn: () => api.events(cid), enabled: !!cid })

export const useRulesets = () =>
  useQuery({ queryKey: ['rulesets'], queryFn: api.rulesets })

export const useProviders = () =>
  useQuery({ queryKey: ['providers'], queryFn: api.listProviders })

export const useProviderPresets = () =>
  useQuery({ queryKey: ['presets'], queryFn: api.providerPresets })

export const useCombat = (cid: string) =>
  useQuery({ queryKey: ['combat', cid], queryFn: () => api.getCombat(cid), enabled: !!cid })

export const useStartCombat = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { enemy_ids?: string[]; default_enemy_hp?: number } = {}) =>
      api.startCombat(cid, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['combat', cid] }),
  })
}

export const useCombatAction = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof api.combatAction>[1]) => api.combatAction(cid, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['combat', cid] })
      qc.invalidateQueries({ queryKey: ['characters', cid] })
    },
  })
}

export const useEndCombat = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.endCombat(cid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['combat', cid] }),
  })
}

export const useCreateCharacter = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Character>) => api.createCharacter(cid, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['characters', cid] }),
  })
}

export const useCreateNPC = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<NPC>) => api.createNPC(cid, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['npcs', cid] }),
  })
}

export const useCreateLocation = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Location>) => api.createLocation(cid, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['locations', cid] }),
  })
}

// --------------------------- Session 3 --------------------------- //

// Party
export const useParty = (cid: string) =>
  useQuery({ queryKey: ['party', cid], queryFn: () => api.listParty(cid), enabled: !!cid })

export const useAddToParty = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (characterId: string) => api.addToParty(cid, characterId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['party', cid] }),
  })
}

export const useRemoveFromParty = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (characterId: string) => api.removeFromParty(cid, characterId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['party', cid] }),
  })
}

export const useCharacterSchema = (rulesetId?: string) =>
  useQuery({
    queryKey: ['character-schema', rulesetId],
    queryFn: () => api.characterSchema(rulesetId as string),
    enabled: !!rulesetId,
  })

// Factions / World
export const useFactions = (cid: string) =>
  useQuery({ queryKey: ['factions', cid], queryFn: () => api.listFactions(cid), enabled: !!cid })

export const useCreateFaction = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Faction>) => api.createFaction(cid, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['factions', cid] }),
  })
}

export const useUpdateFaction = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Faction> }) =>
      api.updateFaction(cid, id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['factions', cid] }),
  })
}

export const useDeleteFaction = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteFaction(cid, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['factions', cid] }),
  })
}

export const useWorldEvents = (cid: string, revealed?: boolean) =>
  useQuery({
    queryKey: ['world-events', cid, revealed],
    queryFn: () => api.listWorldEvents(cid, revealed),
    enabled: !!cid,
  })

export const useCreateWorldEvent = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<WorldEvent>) => api.createWorldEvent(cid, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['world-events', cid] }),
  })
}

export const useTickWorld = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (force?: boolean) => api.tickWorld(cid, force),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['world-events', cid] })
      qc.invalidateQueries({ queryKey: ['factions', cid] })
    },
  })
}

// Memories
export const useMemories = (
  cid: string,
  params: { tag?: string; min_importance?: number; q?: string } = {},
) =>
  useQuery({
    queryKey: ['memories', cid, params],
    queryFn: () => api.listMemories(cid, params),
    enabled: !!cid,
  })

export const useCreateMemory = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Memory>) => api.createMemory(cid, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memories', cid] }),
  })
}

export const useDeleteMemory = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteMemory(cid, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memories', cid] }),
  })
}

// Sessions
export const useSessions = (cid: string) =>
  useQuery({ queryKey: ['sessions', cid], queryFn: () => api.listSessions(cid), enabled: !!cid })

export const useStartSession = (cid: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.startSession(cid),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sessions', cid] })
      qc.invalidateQueries({ queryKey: ['campaign', cid] })
    },
  })
}

// Custom Rulesets
export const useCustomRulesets = () =>
  useQuery({ queryKey: ['custom-rulesets'], queryFn: api.listCustomRulesets })

export const useCreateCustomRuleset = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<CustomRuleset>) => api.createCustomRuleset(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['custom-rulesets'] })
      qc.invalidateQueries({ queryKey: ['rulesets'] })
    },
  })
}

export const useUpdateCustomRuleset = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CustomRuleset> }) =>
      api.updateCustomRuleset(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['custom-rulesets'] })
      qc.invalidateQueries({ queryKey: ['rulesets'] })
    },
  })
}

export const useDeleteCustomRuleset = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteCustomRuleset(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['custom-rulesets'] })
      qc.invalidateQueries({ queryKey: ['rulesets'] })
    },
  })
}

export const useImportCustomRuleset = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => api.importRuleset(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['custom-rulesets'] })
      qc.invalidateQueries({ queryKey: ['rulesets'] })
    },
  })
}
