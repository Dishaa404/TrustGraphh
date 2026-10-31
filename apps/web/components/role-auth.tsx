"use client";

import { useCallback, useEffect, useState } from "react";
import { useAccount, useSignMessage } from "wagmi";
import { API_URL, AuthSession, clearAuthToken, getAuthToken, saveAuthToken, UserRole } from "@/lib/auth";

const roles: { id: UserRole; title: string; detail: string }[] = [
  { id: "donor", title: "Donor", detail: "Create and track Cake Wallet invoices." },
  { id: "receiver", title: "Receiver", detail: "Register your wallet and participate in vouching." },
  { id: "ngo", title: "NGO", detail: "Apply for issuer access; approval is managed by the server." },
];

export function RoleAuth() {
  const { address, isConnected } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [role, setRole] = useState<UserRole>("donor");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadSession = useCallback(async () => {
    const token = getAuthToken();
    if (!token || !API_URL) return;
    try {
      const response = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("Session expired");
      const data = (await response.json()) as AuthSession;
      if (address && data.wallet.toLowerCase() !== address.toLowerCase()) throw new Error("Connect the wallet used for this session");
      setSession(data);
      setRole(data.role);
    } catch {
      clearAuthToken();
      setSession(null);
    }
  }, [address]);

  useEffect(() => { void loadSession(); }, [loadSession]);

  async function login() {
    if (!address) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const challengeResponse = await fetch(`${API_URL}/auth/nonce`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wallet: address, role }),
      });
      const challenge = await challengeResponse.json();
      if (!challengeResponse.ok) throw new Error(challenge.detail ?? "Could not start wallet sign in.");
      const signature = await signMessageAsync({ message: challenge.message });
      const verifyResponse = await fetch(`${API_URL}/auth/verify`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wallet: address, nonce: challenge.nonce, role, signature }),
      });
      const verified = await verifyResponse.json();
      if (!verifyResponse.ok) throw new Error(verified.detail ?? "Wallet authentication failed.");
      saveAuthToken(verified.token);
      await loadSession();
      setNotice(role === "ngo" && verified.approval_status !== "approved" ? "NGO application is pending administrator approval." : "Wallet authenticated.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Wallet authentication failed.");
    } finally { setBusy(false); }
  }

  async function submitNgoApplication(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const token = getAuthToken();
    const form = new FormData(formElement);
    setError(""); setNotice("");
    try {
      const response = await fetch(`${API_URL}/auth/ngo/application`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ organization_name: form.get("organization"), website: form.get("website") || null, registration_id: form.get("registration") }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not submit NGO application.");
      setNotice("NGO application submitted. Access stays pending until the server allowlist is updated.");
      formElement.reset();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not submit NGO application."); }
  }

  async function logout() {
    const token = getAuthToken();
    if (token && API_URL) await fetch(`${API_URL}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => undefined);
    clearAuthToken(); setSession(null); setNotice("Signed out.");
  }

  return <section id="login" className="panel mt-10 scroll-mt-8 rounded-3xl p-6">
    <p className="text-[10px] uppercase tracking-[0.24em] text-emerald-300/80">role based access</p>
    <h2 className="mt-2 text-2xl font-semibold text-white">Donor, receiver, and NGO sign in</h2>
    <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">Sign in with a wallet signature. Signing the login message does not submit a blockchain transaction. Donor and receiver are wallet selected roles; NGO issuer privileges require server approval.</p>
    {session ? <div className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-4">
      <div><p className="text-sm font-semibold capitalize text-white">{session.role} session · {session.approval_status}</p><p className="mt-1 font-mono text-xs text-slate-400">{session.wallet}</p></div>
      <button onClick={logout} className="rounded-full border border-slate-600 px-4 py-2 text-xs text-slate-200">Sign out</button>
    </div> : <>
      <div className="mt-5 grid gap-3 md:grid-cols-3">{roles.map((item) => <button key={item.id} onClick={() => setRole(item.id)} className={`rounded-xl border p-4 text-left ${role === item.id ? "border-emerald-300/60 bg-emerald-400/10" : "border-slate-800 bg-slate-950/40"}`}><span className="text-sm font-semibold text-white">{item.title}</span><span className="mt-1 block text-xs leading-relaxed text-slate-400">{item.detail}</span></button>)}</div>
      <button disabled={!isConnected || busy || !API_URL} onClick={login} className="mt-4 rounded-full bg-emerald-400 px-5 py-2.5 text-sm font-semibold text-emerald-950 disabled:opacity-50">{busy ? "Waiting for signature…" : !API_URL ? "API unavailable" : !isConnected ? "Connect wallet first" : `Sign in as ${role}`}</button>
    </>}
    {session?.role === "ngo" && session.approval_status === "pending" && <form onSubmit={submitNgoApplication} className="mt-5 grid gap-3 rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 md:grid-cols-3"><label className="text-xs text-slate-300">Organization name<input required minLength={2} name="organization" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /></label><label className="text-xs text-slate-300">Registration ID<input required minLength={2} name="registration" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /></label><label className="text-xs text-slate-300">Website (optional)<input type="url" name="website" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" /></label><button className="rounded-full border border-amber-300/30 px-4 py-2 text-xs text-amber-100 md:col-span-3 md:justify-self-start">Submit NGO application</button></form>}
    {notice && <p className="mt-3 text-xs text-emerald-200">{notice}</p>}{error && <p className="mt-3 text-xs text-rose-300">{error}</p>}
  </section>;
}
