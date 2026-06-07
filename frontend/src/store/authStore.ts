import { create } from "zustand";
import { persist } from "zustand/middleware";

function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return {};
  }
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userEmail: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
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
      isAdmin: false,

      setTokens: (access, refresh, email) => {
        const payload = decodeJwtPayload(access);
        set({
          accessToken: access,
          refreshToken: refresh,
          userEmail: email ?? null,
          isAuthenticated: true,
          isAdmin: Boolean(payload.is_admin),
        });
      },

      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          userEmail: null,
          isAuthenticated: false,
          isAdmin: false,
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
