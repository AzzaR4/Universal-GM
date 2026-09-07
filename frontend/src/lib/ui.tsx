import clsx from 'clsx'
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'

export function Button({
  children,
  variant = 'primary',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
}) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50',
        variant === 'primary' &&
          'bg-gradient-to-b from-ember-500 to-ember-600 text-ink-950 hover:from-ember-400 hover:to-ember-500 shadow-lg shadow-ember-600/20',
        variant === 'secondary' &&
          'bg-ink-700 text-ink-100 hover:bg-ink-600 border border-ink-600',
        variant === 'ghost' && 'text-ink-100 hover:bg-ink-700',
        variant === 'danger' && 'bg-red-900/60 text-red-100 hover:bg-red-800 border border-red-800',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={clsx(
        'w-full rounded-lg bg-ink-900 border border-ink-600 px-3 py-2 text-sm text-ink-100 placeholder-ink-600 outline-none focus:border-ember-500 focus:ring-1 focus:ring-ember-500/40 transition',
        className,
      )}
      {...props}
    />
  )
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={clsx(
        'w-full rounded-lg bg-ink-900 border border-ink-600 px-3 py-2 text-sm text-ink-100 placeholder-ink-600 outline-none focus:border-ember-500 focus:ring-1 focus:ring-ember-500/40 transition resize-none',
        className,
      )}
      {...props}
    />
  )
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={clsx(
        'rounded-xl border border-ink-700 bg-ink-800/60 backdrop-blur p-4 shadow-xl',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink-600">
      {children}
    </label>
  )
}

export function PanelTitle({ children }: { children: ReactNode }) {
  return (
    <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-ember-400/90 border-b border-ink-700 pb-2">
      {children}
    </h3>
  )
}

export function Badge({
  children,
  color = 'ink',
}: {
  children: ReactNode
  color?: 'ink' | 'ember' | 'arcane' | 'green' | 'red'
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
        color === 'ink' && 'bg-ink-700 text-ink-100',
        color === 'ember' && 'bg-ember-600/20 text-ember-400 border border-ember-600/40',
        color === 'arcane' && 'bg-arcane-600/20 text-arcane-400 border border-arcane-600/40',
        color === 'green' && 'bg-green-900/40 text-green-300 border border-green-800',
        color === 'red' && 'bg-red-900/40 text-red-300 border border-red-800',
      )}
    >
      {children}
    </span>
  )
}
