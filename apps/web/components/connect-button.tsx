"use client";

import { LogOut, Wallet } from "lucide-react";
import { useState } from "react";
import { useAccount, useConnect, useDisconnect } from "wagmi";

export function ConnectButton() {
  const { address, isConnected } = useAccount();
  const { connectAsync, connectors, isPending } = useConnect();
  const { disconnect } = useDisconnect();
  const [connectionError, setConnectionError] = useState("");

  if (isConnected && address) {
    return (
      <button
        onClick={() => disconnect()}
        className="group flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm font-medium text-emerald-200 transition hover:border-emerald-300/60 hover:bg-emerald-400/15"
      >
        <span className="h-2 w-2 rounded-full bg-emerald-400" />
        <span className="font-mono text-xs">
          {address.slice(0, 6)}...{address.slice(-4)}
        </span>
        <LogOut className="h-3.5 w-3.5 opacity-60 transition group-hover:opacity-100" />
      </button>
    );
  }

  const injectedConnector = connectors.find((candidate) => candidate.id === "injected");
  const walletConnectConnector = connectors.find((candidate) => candidate.id === "walletConnect");

  async function handleConnect(connectorId: string) {
    const connector = connectors.find((candidate) => candidate.uid === connectorId);
    if (!connector) {
      setConnectionError("This wallet connection is not configured. Set NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID to enable Cake Wallet.");
      return;
    }

    setConnectionError("");
    try {
      if (connector.id === "injected") {
        const provider = await connector.getProvider();
        if (!provider) {
          setConnectionError("No browser wallet was detected. Use the Cake Wallet button to connect from your phone, or install MetaMask, Coinbase Wallet, or Rabby.");
          return;
        }
      }
      await connectAsync({ connector });
    } catch (cause) {
      setConnectionError(cause instanceof Error ? cause.message : "Wallet connection failed. Check the wallet and try again.");
    }
  }

  return (
    <div className="flex max-w-64 flex-col items-end gap-1">
      <button
        onClick={() => injectedConnector && void handleConnect(injectedConnector.uid)}
        disabled={isPending || !injectedConnector}
        className="flex items-center gap-2 rounded-full bg-emerald-400 px-4 py-2 text-sm font-semibold text-emerald-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Wallet className="h-4 w-4" />
        {isPending ? "Connecting..." : "Browser wallet"}
      </button>
      {walletConnectConnector && (
        <button
          onClick={() => void handleConnect(walletConnectConnector.uid)}
          disabled={isPending}
          className="rounded-full border border-emerald-400/30 px-4 py-2 text-xs font-medium text-emerald-100 transition hover:border-emerald-300/60 disabled:opacity-50"
        >
          Connect Cake Wallet (QR)
        </button>
      )}
      {connectionError ? (
        <p role="alert" className="max-w-64 text-right text-xs text-rose-200">{connectionError}</p>
      ) : (
        <p className="text-right text-[10px] text-slate-500">
          {walletConnectConnector
            ? "Scan with Cake Wallet. Select Base Sepolia when prompted."
            : "Cake Wallet connection needs NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID."}
        </p>
      )}
    </div>
  );
}
