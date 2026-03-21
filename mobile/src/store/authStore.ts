import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { AuthState, User } from '../types'

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user: User | null, token: string) =>
        set({ user, token, isAuthenticated: !!token }),

      logout: () => set({ user: null, token: null, isAuthenticated: false }),

      updateUser: (user: User) => set({ user }),
    }),
    {
      name: 'vn-legal-auth-storage',
      // AsyncStorage thay cho localStorage
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
)
