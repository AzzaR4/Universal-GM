import type { ReactNode } from 'react'

export default function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-ink-700 bg-ink-800 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink-100">{title}</h3>
          <button onClick={onClose} className="text-ink-600 hover:text-ink-100">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
