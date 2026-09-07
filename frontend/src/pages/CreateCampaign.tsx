import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useRulesets } from '../hooks/queries'
import { Badge, Button, Card, Input, Label, Textarea } from '../lib/ui'

const STEPS = ['Basics', 'Ruleset', 'Rules Config', 'GM Behaviour', 'First Character']

const ATTR_DEFAULTS = ['Might', 'Agility', 'Wits', 'Presence']

export default function CreateCampaign() {
  const navigate = useNavigate()
  const { data: rulesets } = useRulesets()
  const [step, setStep] = useState(0)
  const [submitting, setSubmitting] = useState(false)

  // Step 1
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [campaignStyle, setCampaignStyle] = useState('Classic fantasy adventure')
  const [narrativeStyle, setNarrativeStyle] = useState('Vivid and cinematic')
  // Step 2
  const [rulesetId, setRulesetId] = useState('generic')
  // Step 3
  const [resolutionMode, setResolutionMode] = useState('rules_light')
  const [defaultDice, setDefaultDice] = useState('2d6')
  const [attributes, setAttributes] = useState<string[]>(ATTR_DEFAULTS)
  const [hp, setHp] = useState(10)
  // Step 4
  const [difficulty, setDifficulty] = useState(3)
  const [lethality, setLethality] = useState(3)
  const [descLength, setDescLength] = useState('medium')
  // Step 5
  const [charName, setCharName] = useState('')
  const [charDesc, setCharDesc] = useState('')

  const canNext =
    (step === 0 && name.trim()) ||
    step === 1 ||
    step === 2 ||
    step === 3 ||
    (step === 4 && charName.trim())

  async function finish() {
    setSubmitting(true)
    try {
      const ruleset_config = {
        resolution_mode: resolutionMode,
        use_dice: resolutionMode !== 'narrative_only',
        default_dice: defaultDice,
        attributes: attributes
          .filter((a) => a.trim())
          .map((a) => ({ name: a, abbreviation: a.slice(0, 3).toUpperCase(), default: 5, min: 1, max: 10 })),
        resources: [{ name: 'Health', abbreviation: 'HP', default: hp, max: hp }],
      }
      const gm_config = {
        difficulty,
        lethality,
        description_length: descLength,
        campaign_style: campaignStyle,
        narrative_style: narrativeStyle,
      }
      const campaign = await api.createCampaign({
        name,
        description,
        ruleset_id: rulesetId,
        campaign_style: campaignStyle,
        narrative_style: narrativeStyle,
        ruleset_config,
        gm_config,
      })
      await api.createCharacter(campaign.id, {
        name: charName,
        description: charDesc,
        is_player_character: true,
      })
      navigate(`/campaigns/${campaign.id}/play`)
    } catch (e: any) {
      alert(`Failed to create campaign: ${e.message}`)
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto min-h-screen max-w-2xl px-6 py-10">
      <button onClick={() => navigate('/')} className="mb-4 text-sm text-ink-600 hover:text-ink-100">
        ← Back
      </button>
      <h1 className="mb-2 text-3xl font-bold text-ink-100">Forge a New Campaign</h1>

      {/* Stepper */}
      <div className="mb-8 mt-6 flex items-center gap-1">
        {STEPS.map((s, i) => (
          <div key={s} className="flex flex-1 items-center">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                i <= step ? 'bg-ember-500 text-ink-950' : 'bg-ink-700 text-ink-600'
              }`}
            >
              {i + 1}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-0.5 flex-1 ${i < step ? 'bg-ember-500' : 'bg-ink-700'}`} />
            )}
          </div>
        ))}
      </div>
      <p className="mb-4 text-sm font-semibold text-ember-400">
        Step {step + 1} / {STEPS.length}: {STEPS[step]}
      </p>

      <Card>
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <Label>Campaign Name *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="The Shadow of Ravenhollow" />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="A brooding tale of…" />
            </div>
            <div>
              <Label>Campaign Style</Label>
              <Input value={campaignStyle} onChange={(e) => setCampaignStyle(e.target.value)} />
            </div>
            <div>
              <Label>Narrative Style</Label>
              <Input value={narrativeStyle} onChange={(e) => setNarrativeStyle(e.target.value)} />
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-3">
            {rulesets?.map((rs) => (
              <button
                key={rs.id}
                disabled={rs.status !== 'available'}
                onClick={() => setRulesetId(rs.id)}
                className={`w-full rounded-lg border p-4 text-left transition disabled:opacity-40 ${
                  rulesetId === rs.id
                    ? 'border-ember-500 bg-ember-600/10'
                    : 'border-ink-600 bg-ink-900 hover:border-ink-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink-100">{rs.name}</span>
                  <Badge color={rs.status === 'available' ? 'green' : 'ink'}>{rs.status}</Badge>
                </div>
                <p className="mt-1 text-sm text-ink-600">{rs.description}</p>
              </button>
            ))}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <Label>Resolution Mode</Label>
              <div className="grid grid-cols-3 gap-2">
                {['rules_heavy', 'rules_light', 'narrative_only'].map((m) => (
                  <button
                    key={m}
                    onClick={() => setResolutionMode(m)}
                    className={`rounded-lg border px-3 py-2 text-xs font-medium capitalize ${
                      resolutionMode === m
                        ? 'border-ember-500 bg-ember-600/10 text-ember-400'
                        : 'border-ink-600 bg-ink-900 text-ink-100'
                    }`}
                  >
                    {m.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label>Default Dice</Label>
              <Input value={defaultDice} onChange={(e) => setDefaultDice(e.target.value)} placeholder="2d6" />
            </div>
            <div>
              <Label>Attributes</Label>
              <div className="space-y-2">
                {attributes.map((a, i) => (
                  <div key={i} className="flex gap-2">
                    <Input
                      value={a}
                      onChange={(e) => {
                        const next = [...attributes]
                        next[i] = e.target.value
                        setAttributes(next)
                      }}
                    />
                    <Button variant="ghost" onClick={() => setAttributes(attributes.filter((_, j) => j !== i))}>
                      ✕
                    </Button>
                  </div>
                ))}
                <Button variant="secondary" onClick={() => setAttributes([...attributes, ''])}>
                  + Add Attribute
                </Button>
              </div>
            </div>
            <div>
              <Label>Starting Health (HP)</Label>
              <Input type="number" value={hp} onChange={(e) => setHp(parseInt(e.target.value) || 1)} />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6">
            <SliderRow label="Difficulty" value={difficulty} onChange={setDifficulty} />
            <SliderRow label="Lethality" value={lethality} onChange={setLethality} />
            <div>
              <Label>Description Length</Label>
              <div className="grid grid-cols-3 gap-2">
                {['brief', 'medium', 'lavish'].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDescLength(d)}
                    className={`rounded-lg border px-3 py-2 text-xs font-medium capitalize ${
                      descLength === d
                        ? 'border-ember-500 bg-ember-600/10 text-ember-400'
                        : 'border-ink-600 bg-ink-900 text-ink-100'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <p className="text-sm text-ink-600">Create the player character who will explore this world.</p>
            <div>
              <Label>Character Name *</Label>
              <Input value={charName} onChange={(e) => setCharName(e.target.value)} placeholder="Aria Nightwind" />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={3} value={charDesc} onChange={(e) => setCharDesc(e.target.value)} placeholder="A wandering ranger with a troubled past…" />
            </div>
            <p className="text-xs text-ink-600">
              Attributes start at their defaults and can be tuned later in the game screen.
            </p>
          </div>
        )}
      </Card>

      <div className="mt-6 flex justify-between">
        <Button variant="secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>
          ← Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button disabled={!canNext} onClick={() => setStep(step + 1)}>
            Next →
          </Button>
        ) : (
          <Button disabled={!canNext || submitting} onClick={finish}>
            {submitting ? 'Creating…' : '✦ Begin Adventure'}
          </Button>
        )}
      </div>
    </div>
  )
}

function SliderRow({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (v: number) => void
}) {
  const labels = ['', 'Gentle', 'Easy', 'Balanced', 'Hard', 'Brutal']
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <Label>{label}</Label>
        <span className="text-xs font-semibold text-ember-400">{labels[value]}</span>
      </div>
      <input
        type="range"
        min={1}
        max={5}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full accent-ember-500"
      />
    </div>
  )
}
