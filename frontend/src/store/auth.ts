"use client";
import { create } from "zustand";
import { api, setTokens, type Tokens } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => Promise<void>;
  loadMe: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  async login(email, password) {
    const r = await api<{ user: User; tokens: Tokens }>("/auth/login", {
      method: "POST", auth: false, body: JSON.stringify({ email, password }),
    });
    setTokens(r.tokens);
    set({ user: r.user });
  },
  async register(email, password, full_name) {
    const r = await api<{ user: User; tokens: Tokens }>("/auth/register", {
      method: "POST", auth: false, body: JSON.stringify({ email, password, full_name }),
    });
    setTokens(r.tokens);
    set({ user: r.user });
  },
  async logout() {
    try { await api("/auth/logout", { method: "POST" }); } catch { /* ignore */ }
    setTokens(null);
    set({ user: null });
  },
  async loadMe() {
    set({ loading: true });
    try { set({ user: await api<User>("/auth/me") }); }
    catch { set({ user: null }); }
    finally { set({ loading: false }); }
  },
}));
