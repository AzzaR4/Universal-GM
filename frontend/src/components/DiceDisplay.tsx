import { Badge } from '../lib/ui'
import type { DiceResult } from '../types'

const OUTCOME_COLOR: Record<string, 'green' | 'ember' | 'red' | 'ink'> = {
  critical_success: 'green',
  success: 'green',
  partial: 'ember',
  failure: 'red',
  critical_failure: 'red',
  none: 'ink',
}

export default function DiceDisplay({ dice }: { dice: DiceResult }) {
  const { roll } = dice
  return (
    <div className="animate-fade-in rounded-xl border border-ink-700 bg-ink-900/80 p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-widest text-ink-600">
          Dice Result
        </span>
        <Badge color={OUTCOME_COLOR[dice.outcome] || 'ink'}>{dice.outcome_label}</Badge>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <div className="flex gap-2">
          {roll.rolls.map((r, i) => (
            <div
              key={i}
              className="animate-dice flex h-11 w-11 items-center justify-center rounded-lg border-2 border-ember-500/60 bg-ink-800 text-lg font-bold text-ember-400"
            >
              {r}
            </div>
          ))}
        </div>
        <div className="text-ink-600">
          <span className="font-mono text-sm">{roll.notation}</span>
          {roll.modifier !== 0 && (
            <span className="font-mono text-sm"> {roll.modifier > 0 ? `+${roll.modifier}` : roll.modifier}</span>
          )}
        </div>
        <div className="ml-auto text-right">
          <div className="text-3xl font-bold text-ink-100">{roll.total}</div>
          <div className="text-[10px] uppercase tracking-wide text-ink-600">Total</div>
        </div>
      </div>
    </div>
  )
}
