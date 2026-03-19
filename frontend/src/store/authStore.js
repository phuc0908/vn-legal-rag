import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user, token) => set({ user, token, isAuthenticated: !!token }),
      
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
      
      updateUser: (user) => set({ user }),
    }),
    {
      name: 'vn-legal-auth-storage',
    }
  )
)
