import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userEmail: string | null;
  isAuthenticated: boolean;
  setTokens: (access: string, refresh: string, email?: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      userEmail: null,
      isAuthenticated: false,

      setTokens: (access, refresh, email) =>
        set({
          accessToken: access,
          refreshToken: refresh,
          userEmail: email ?? null,
          isAuthenticated: true,
        }),

      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          userEmail: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: "doc-intel-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        userEmail: state.userEmail,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
