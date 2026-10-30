"use client";

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { keccak256, stringToHex } from "viem";
import { useAccount } from "wagmi";
import { getAuthToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type PaymentIntent = {
  id: string;
  asset: string;
  amount: number;
  address: string;
  uri: string;
  status: string;
};

export function CakePayment() {
  const { address } = useAccount();
  const [amount, setAmount] = useState("0.01");
  const [intent, setIntent] = useState<PaymentIntent | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function createIntent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setStatus("");
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/payments/intent`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getAuthToken() ?? ""}` },
        body: JSON.stringify({
          payer_did: address
            ? `did:trustgraph:${keccak256(stringToHex(address.toLowerCase()))}`
            : "",
          payer_wallet: address,
          amount: Number(amount),
          asset: "XMR",
          provider: "cake",
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not create Cake Wallet invoice.");
      setIntent(body as PaymentIntent);
      setStatus("pending");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create payment intent.");
    } finally {
      setLoading(false);
    }
  }

  async function checkStatus() {
    if (!intent) return;
    try {
      const response = await fetch(`${API_URL}/payments/${encodeURIComponent(intent.id)}`, {
        headers: { Authorization: `Bearer ${getAuthToken() ?? ""}` },
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Could not check payment status.");
      setStatus(body.status);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not check payment status.");
    }
  }

  return (
    <div className="panel rounded-3xl p-6">
      <div>
        <p className="text-[10px] uppercase tracking-[0.24em] text-emerald-300/80">Cake Wallet · XMR</p>
        <h2 className="mt-2 text-xl font-semibold text-white">Create a Monero invoice</h2>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">
          The API asks the configured merchant wallet for a fresh subaddress and Monero payment URI.
          Open the URI in Cake Wallet, then check the wallet RPC for payment confirmations.
        </p>
      </div>

      {!intent ? (
        <form className="mt-5 flex flex-wrap items-end gap-3" onSubmit={createIntent}>
          <label className="text-[10px] uppercase tracking-wide text-slate-500" htmlFor="xmr-amount">
            Amount (XMR)
            <input
              id="xmr-amount"
              className="mt-1 block w-40 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-200 outline-none focus:border-emerald-400"
              type="number"
              min="0.000000000001"
              step="0.000000000001"
              required
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />
          </label>
          <button
            className="rounded-full bg-emerald-400 px-4 py-2 text-xs font-semibold text-emerald-950 disabled:opacity-50"
            disabled={loading || !address}
          >
            {loading ? "Requesting address…" : "Create Cake Wallet invoice"}
          </button>
          {!address && <p className="w-full text-xs text-amber-200">Connect your wallet to link the payment to its graph identity.</p>}
        </form>
      ) : (
        <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="font-mono text-xs text-slate-300">{intent.id}</span>
            <span className="rounded-full bg-amber-400/10 px-2 py-1 text-[10px] uppercase text-amber-200">{status || intent.status}</span>
          </div>
          <p className="mt-3 text-xs text-slate-400">{intent.amount} XMR</p>
          <div className="mt-3 inline-block rounded-xl bg-white p-3">
            <QRCodeSVG value={intent.uri} size={176} level="M" />
          </div>
          <p className="mt-2 break-all rounded-lg bg-slate-900 p-3 font-mono text-[10px] text-slate-300">{intent.address}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a className="rounded-full bg-emerald-400 px-4 py-2 text-xs font-semibold text-emerald-950" href={intent.uri}>
              Open in Cake Wallet
            </a>
            <button className="rounded-full border border-slate-700 px-4 py-2 text-xs text-slate-200" onClick={checkStatus}>
              Check payment
            </button>
            <button className="rounded-full border border-slate-700 px-4 py-2 text-xs text-slate-400" onClick={() => { setIntent(null); setStatus(""); }}>
              New invoice
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-xs text-rose-300">{error}</p>}
    </div>
  );
}
