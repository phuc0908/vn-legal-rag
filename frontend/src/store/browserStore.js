import { create } from 'zustand'

export const useBrowserStore = create((set) => ({
  // Selections
  selectedChude: null,
  selectedDemuc: null,
  selectedChuong: null,

  // Lists
  demucs: [],
  chuongs: [],
  dieus: [],

  // Setters
  setSelections: (updates) => set((state) => ({ ...state, ...updates })),

  resetToChude: (chude) => set({
    selectedChude: chude,
    selectedDemuc: null,
    selectedChuong: null,
    demucs: [],
    chuongs: [],
    dieus: []
  }),

  resetToDemuc: (demuc) => set({
    selectedDemuc: demuc,
    selectedChuong: null,
    chuongs: [],
    dieus: []
  }),

  resetToChuong: (chuong) => set({
    selectedChuong: chuong,
    dieus: []
  }),

  setDemucs: (demucs) => set({ demucs }),
  setChuongs: (chuongs) => set({ chuongs }),
  setDieus: (dieus) => set({ dieus }),
}))
