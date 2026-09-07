import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Character, Location, NPC } from '../types'

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
