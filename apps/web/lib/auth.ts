export type UserRole = "donor" | "receiver" | "ngo";
export type AuthSession = {
  authenticated: true;
  wallet: string;
  role: UserRole;
  approval_status: "approved" | "pending" | "not_applicable";
  demo?: boolean;
};

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");
const TOKEN_KEY = "trustgraph.session";
const DEMO_SESSION_KEY = "trustgraph.demo-session";

export function getAuthToken() {
  return typeof window === "undefined" ? null : window.sessionStorage.getItem(TOKEN_KEY);
}

export function saveAuthToken(token: string) {
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken() {
  window.sessionStorage.removeItem(TOKEN_KEY);
}

export function getDemoSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  const value = window.sessionStorage.getItem(DEMO_SESSION_KEY);
  if (!value) return null;
  try { return JSON.parse(value) as AuthSession; } catch { return null; }
}

export function saveDemoSession(session: AuthSession) {
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.setItem(DEMO_SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event("trustgraph-auth"));
}

export function clearDemoSession() {
  window.sessionStorage.removeItem(DEMO_SESSION_KEY);
  window.dispatchEvent(new Event("trustgraph-auth"));
}
