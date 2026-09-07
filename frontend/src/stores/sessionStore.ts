import { create } from 'zustand'
import type { DiceResult, NarrativeMessage } from '../types'

interface SessionState {
  messages: NarrativeMessage[]
  currentDice: DiceResult | null
  isStreaming: boolean
  error: string | null
  addMessage: (msg: NarrativeMessage) => void
  appendToMessage: (id: string, chunk: string) => void
  finalizeMessage: (id: string) => void
  setDice: (dice: DiceResult | null) => void
  setStreaming: (v: boolean) => void
  setError: (e: string | null) => void
  reset: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  messages: [],
  currentDice: null,
  isStreaming: false,
  error: null,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  appendToMessage: (id, chunk) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, text: m.text + chunk } : m,
      ),
    })),
  finalizeMessage: (id) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, streaming: false } : m,
      ),
    })),
  setDice: (dice) => set({ currentDice: dice }),
  setStreaming: (v) => set({ isStreaming: v }),
  setError: (e) => set({ error: e }),
  reset: () => set({ messages: [], currentDice: null, isStreaming: false, error: null }),
}))
