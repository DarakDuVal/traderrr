import { create } from "zustand";
import type { UserResponse } from "@traderrr/types";

interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: UserResponse) => void;
  logout: () => void;
  setToken: (token: string) => void;
  setUser: (user: UserResponse) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  login: (token, user) => set({ accessToken: token, user, isAuthenticated: true }),
  logout: () => set({ accessToken: null, user: null, isAuthenticated: false }),
  setToken: (token) => set({ accessToken: token }),
  setUser: (user) => set({ user }),
}));
