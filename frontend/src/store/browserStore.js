import { create } from 'zustand'

export const useBrowserStore = create((set) => ({
  // Selections
  selectedChude: null,
  selectedDemuc: null,
  selectedChuong: null,
  selectedMuc: null,

  // Lists
  demucs: [],
  chuongs: [],
  mucs: [],
  dieus: [],

  // Setters
  setSelections: (updates) => set((state) => ({ ...state, ...updates })),

  resetToChude: (chude) => set({
    selectedChude: chude,
    selectedDemuc: null,
    selectedChuong: null,
    selectedMuc: null,
    demucs: [],
    chuongs: [],
    mucs: [],
    dieus: []
  }),

  resetToDemuc: (demuc) => set({
    selectedDemuc: demuc,
    selectedChuong: null,
    selectedMuc: null,
    chuongs: [],
    mucs: [],
    dieus: []
  }),

  resetToChuong: (chuong) => set({
    selectedChuong: chuong,
    selectedMuc: null,
    mucs: [],
    dieus: []
  }),

  resetToMuc: (muc) => set({
    selectedMuc: muc,
    dieus: []
  }),

  setDemucs: (demucs) => set({ demucs }),
  setChuongs: (chuongs) => set({ chuongs }),
  setMucs: (mucs) => set({ mucs }),
  setDieus: (dieus) => set({ dieus }),
}))
