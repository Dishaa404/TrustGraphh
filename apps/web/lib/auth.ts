export type UserRole = "donor" | "receiver" | "ngo";
export type AuthSession = {
  authenticated: true;
  wallet: string;
  role: UserRole;
  approval_status: "approved" | "pending" | "not_applicable";
};

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");
const TOKEN_KEY = "trustgraph.session";

export function getAuthToken() {
  return typeof window === "undefined" ? null : window.sessionStorage.getItem(TOKEN_KEY);
}

export function saveAuthToken(token: string) {
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken() {
  window.sessionStorage.removeItem(TOKEN_KEY);
}
