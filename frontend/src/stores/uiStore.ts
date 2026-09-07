import { create } from 'zustand'

interface UIState {
  leftPanelOpen: boolean
  rightPanelOpen: boolean
  toggleLeft: () => void
  toggleRight: () => void
}

export const useUIStore = create<UIState>((set) => ({
  leftPanelOpen: true,
  rightPanelOpen: true,
  toggleLeft: () => set((s) => ({ leftPanelOpen: !s.leftPanelOpen })),
  toggleRight: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
}))
