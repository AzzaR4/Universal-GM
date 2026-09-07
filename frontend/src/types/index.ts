export interface Campaign {
  id: string
  name: string
  description: string
  ruleset_id: string
  campaign_style: string
  narrative_style: string
  gm_config: Record<string, any>
  ruleset_config: Record<string, any>
  world_state: Record<string, any>
  current_location_id: string | null
  current_session_id?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Character {
  id: string
  campaign_id: string
  name: string
  description: string
  is_player_character: boolean
  player_name?: string | null
  ruleset_data: {
    attributes?: Record<string, number>
    skills?: Record<string, number>
    resources?: Record<string, { current: number; max: number }>
  }
  conditions: string[]
  inventory: string[]
  location_id: string | null
  status: string
}

export interface NPC {
  id: string
  campaign_id: string
  name: string
  description: string
  personality: Record<string, any>
  goals: any[]
  knowledge: any[]
  secrets: any[]
  relationships: Record<string, any>
  location_id: string | null
  current_activity: string
  status: string
}

export interface Location {
  id: string
  campaign_id: string
  name: string
  description: string
  atmosphere: string
  connected_location_ids: string[]
  is_discovered: boolean
  lore: Record<string, any>
}

export interface Quest {
  id: string
  campaign_id: string
  title: string
  description: string
  status: string
  objectives: any[]
  notes: string
}

export interface EventLogEntry {
  id: string
  event_type: string
  data: Record<string, any>
  timestamp: string
}

export interface AIProvider {
  id: string
  name: string
  provider_type: string
  endpoint_url: string
  model_name: string
  has_api_key: boolean
  temperature: number
  max_tokens: number
  context_window: number
  extra_params: Record<string, any>
  is_active: boolean
}

export interface ProviderPreset {
  name: string
  endpoint_url: string
  model_name: string
  requires_key: boolean
}

export interface Ruleset {
  id: string
  name: string
  description: string
  status: string
}

export interface DiceRoll {
  notation: string
  num_dice: number
  sides: number
  modifier: number
  rolls: number[]
  total: number
}

export interface DiceResult {
  roll: DiceRoll
  outcome: string
  outcome_label: string
}

export interface Combatant {
  id: string
  name: string
  is_player: boolean
  initiative: number
  hp_current: number
  hp_max: number
  resource: string
  status: string
  is_npc: boolean
}

export interface CombatState {
  active: boolean
  round: number
  turn_index: number
  combatants: Combatant[]
  log: string[]
  current_id: string | null
  is_over: boolean
}

export interface CombatResult {
  outcome: string
  outcome_label: string
  dice: DiceRoll | null
  damage: number
  mechanical_description: string
}

export interface CombatResponse {
  active: boolean
  combat: CombatState | null
  result?: CombatResult
}

export type NarrativeMessage = {
  id: string
  role: 'player' | 'gm' | 'system'
  text: string
  dice?: DiceResult
  streaming?: boolean
}

// --------------------------- Session 3 --------------------------- //

export interface Faction {
  id: string
  campaign_id: string
  name: string
  description: string
  goals: any[]
  resources: number
  influence: number
  disposition: string
  relationships: Record<string, any>
  autonomy_level: string
  last_acted_at: string | null
  created_at: string
}

export interface WorldEvent {
  id: string
  campaign_id: string
  faction_id: string | null
  event_type: string
  title: string
  description: string
  impact: Record<string, any>
  is_revealed: boolean
  created_at: string
}

export interface Memory {
  id: string
  campaign_id: string
  memory_type: string
  subject_id: string | null
  content: string
  importance: number
  keywords: string[]
  tags: string[]
  has_embedding: boolean
  source_action_id: string | null
  created_at: string
}

export interface GameSession {
  id: string
  campaign_id: string
  started_at: string
  ended_at: string | null
  summary: string | null
  key_events: any[]
  player_actions_count: number
  xp_awarded: number | null
}

export interface CustomRuleset {
  id: string
  name: string
  display_name: string
  description: string
  dice_formula: string
  roll_mode: string
  success_threshold: number
  attributes: any[]
  resources: any[]
  skills: any[]
  prompt_instructions: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// The flattened character-schema payload returned by GET /rulesets/:id/character-schema
export interface CharacterSchema {
  id: string
  name: string
  description: string
  schema: Record<string, any>
  attributes?: Record<string, any>
  abilities?: Record<string, any>
  resources?: Record<string, any>
  skills?: Record<string, any>
  [key: string]: any
}
