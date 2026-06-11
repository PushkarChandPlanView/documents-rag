import { apiClient } from "./client";
import type { TokenResponse } from "@/types";

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/login", { email, password });
    return res.data;
  },

  register: async (
    email: string,
    password: string,
    firstName?: string,
    lastName?: string,
  ): Promise<{ id: string; email: string }> => {
    const res = await apiClient.post("/auth/register", {
      email,
      password,
      first_name: firstName || null,
      last_name: lastName || null,
    });
    return res.data;
  },

  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return res.data;
  },
};
