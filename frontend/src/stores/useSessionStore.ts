import { create } from 'zustand';

interface SessionState {
  user: { id: string; name: string } | null;
  token: string | null;
  setUser: (user: { id: string; name: string }, token: string) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  user: null,
  token: null,
  setUser: (user, token) => set({ user, token }),
  clearSession: () => set({ user: null, token: null }),
})); 