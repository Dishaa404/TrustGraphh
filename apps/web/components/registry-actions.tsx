"use client";

import { useEffect, useMemo, useState } from "react";
import {
  useAccount,
  useReadContract,
  useWaitForTransactionReceipt,
  useWriteContract,
} from "wagmi";
import { baseSepolia } from "wagmi/chains";
import { formatEther, isAddress, keccak256, stringToHex } from "viem";
import { useSwitchChain } from "wagmi";
import { API_URL, getAuthToken } from "@/lib/auth";

const registryAddress = process.env.NEXT_PUBLIC_PERSONHOOD_REGISTRY_ADDRESS as
  | `0x${string}`
  | undefined;

const registryAbi = [
  {
    type: "function",
    name: "registrationStake",
    stateMutability: "view",
    inputs: [],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    type: "function",
    name: "register",
    stateMutability: "payable",
    inputs: [
      { name: "didHash", type: "bytes32" },
      { name: "commitmentHash", type: "bytes32" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "vouch",
    stateMutability: "nonpayable",
    inputs: [{ name: "didHash", type: "bytes32" }],
    outputs: [],
  },
  { type: "function", name: "owner", stateMutability: "view", inputs: [], outputs: [{ name: "", type: "address" }] },
  { type: "function", name: "requiredVouches", stateMutability: "view", inputs: [], outputs: [{ name: "", type: "uint32" }] },
  { type: "function", name: "challengeStake", stateMutability: "view", inputs: [], outputs: [{ name: "", type: "uint256" }] },
  { type: "function", name: "challengeWindow", stateMutability: "view", inputs: [], outputs: [{ name: "", type: "uint64" }] },
  {
    type: "function",
    name: "setConfig",
    stateMutability: "nonpayable",
    inputs: [
      { name: "registrationStake_", type: "uint256" },
      { name: "challengeStake_", type: "uint256" },
      { name: "requiredVouches_", type: "uint32" },
      { name: "challengeWindow_", type: "uint64" },
    ],
    outputs: [],
  },
] as const;

function newCommitment() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return keccak256(`0x${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`);
}

export function RegistryActions() {
  const { address, isConnected, chain } = useAccount();
  const { switchChain, isPending: isSwitching } = useSwitchChain();
  const [targetDidHash, setTargetDidHash] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [indexedHash, setIndexedHash] = useState<string | null>(null);
  const [syncTransaction, setSyncTransaction] = useState(false);
  const { data: stake } = useReadContract({
    address: registryAddress,
    abi: registryAbi,
    functionName: "registrationStake",
    query: { enabled: Boolean(registryAddress) },
  });
  const { data: owner } = useReadContract({ address: registryAddress, abi: registryAbi, functionName: "owner", query: { enabled: Boolean(registryAddress) } });
  const { data: requiredVouches } = useReadContract({ address: registryAddress, abi: registryAbi, functionName: "requiredVouches", query: { enabled: Boolean(registryAddress) } });
  const { data: challengeStake } = useReadContract({ address: registryAddress, abi: registryAbi, functionName: "challengeStake", query: { enabled: Boolean(registryAddress) } });
  const { data: challengeWindow } = useReadContract({ address: registryAddress, abi: registryAbi, functionName: "challengeWindow", query: { enabled: Boolean(registryAddress) } });
  const { data: hash, error: writeError, isPending, writeContract } = useWriteContract();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });

  useEffect(() => {
    if (!syncTransaction || !isSuccess || !hash || !API_URL || indexedHash === hash) return;
    const token = getAuthToken();
    if (!token) {
      setMessage("Transaction confirmed on Base Sepolia. Sign in as receiver to sync it to the trust graph.");
      setIndexedHash(hash);
      return;
    }
    setIndexedHash(hash);
    void fetch(`${API_URL}/chain/index/${hash}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }).then(async (response) => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Graph event sync failed.");
      setMessage(`Transaction confirmed and ${body.indexed_events} registry event(s) synced to TigerGraph.`);
    }).catch((cause) => {
      setError(cause instanceof Error ? cause.message : "Graph event sync failed.");
    });
  }, [hash, indexedHash, isSuccess, syncTransaction]);

  const didHash = useMemo(
    () => (address ? keccak256(stringToHex(address.toLowerCase())) : undefined),
    [address],
  );

  async function register() {
    setError("");
    setMessage("");
    setSyncTransaction(true);
    if (!registryAddress || !didHash || stake === undefined) {
      setError("Registry is not configured or the stake could not be read.");
      return;
    }
    try {
      writeContract({
        address: registryAddress,
        abi: registryAbi,
        functionName: "register",
        args: [didHash, newCommitment()],
        value: stake,
        chainId: baseSepolia.id,
      });
      setMessage("Registration submitted to Base Sepolia.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not submit registration.");
    }
  }

  function vouch() {
    setError("");
    setMessage("");
    setSyncTransaction(true);
    if (!registryAddress || !/^0x[0-9a-fA-F]{64}$/.test(targetDidHash)) {
      setError("Enter a 32-byte DID hash (0x followed by 64 hex characters).");
      return;
    }
    writeContract({
      address: registryAddress,
      abi: registryAbi,
      functionName: "vouch",
      args: [targetDidHash as `0x${string}`],
      chainId: baseSepolia.id,
    });
    setMessage("Vouch submitted to Base Sepolia.");
  }

  function setVouchThreshold(value: 0 | 3) {
    setError("");
    setMessage("");
    setSyncTransaction(false);
    if (!registryAddress || stake === undefined || challengeStake === undefined || challengeWindow === undefined) {
      setError("Could not read registry configuration.");
      return;
    }
    writeContract({
      address: registryAddress,
      abi: registryAbi,
      functionName: "setConfig",
      args: [stake, challengeStake, value, challengeWindow],
      chainId: baseSepolia.id,
    });
    setMessage(`Registry owner submitted a change to ${value} required vouches.`);
  }

  if (!registryAddress || !isAddress(registryAddress)) {
    return (
      <div className="panel rounded-2xl p-5 text-sm text-slate-300">
        Deploy the registry, then set <code>NEXT_PUBLIC_PERSONHOOD_REGISTRY_ADDRESS</code> in
        <code> apps/web/.env.local</code> to enable on-chain registration.
      </div>
    );
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <div className="panel rounded-2xl p-5">
        <h3 className="font-semibold text-white">Register on Base Sepolia</h3>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">
          Registration stakes {stake === undefined ? "…" : `${formatEther(stake)} ETH`} and records a
          random commitment hash. It is a hackathon demo commitment, not biometric verification.
        </p>
        {didHash && <p className="mt-3 break-all font-mono text-[10px] text-slate-500">DID hash: {didHash}</p>}
        {!isConnected ? (
          <p className="mt-4 text-xs text-amber-200">Connect a wallet to continue.</p>
        ) : chain?.id !== baseSepolia.id ? (
          <button
            className="mt-4 rounded-full bg-emerald-400 px-4 py-2 text-xs font-semibold text-emerald-950 disabled:opacity-50"
            disabled={isSwitching}
            onClick={() => switchChain({ chainId: baseSepolia.id })}
          >
            {isSwitching ? "Switching…" : "Switch to Base Sepolia"}
          </button>
        ) : (
          <button
            className="mt-4 rounded-full bg-emerald-400 px-4 py-2 text-xs font-semibold text-emerald-950 disabled:opacity-50"
            disabled={isPending || isConfirming || stake === undefined}
            onClick={register}
          >
            {isPending ? "Confirm in wallet…" : isConfirming ? "Waiting for confirmation…" : "Register and stake"}
          </button>
        )}
      </div>

      {address?.toLowerCase() === owner?.toLowerCase() && (
        <div className="panel rounded-2xl border-amber-400/20 p-5 lg:col-span-2">
          <h3 className="font-semibold text-white">Owner setup for a fresh registry</h3>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            This registry starts with no active people, so nobody can vouch yet. The owner can
            temporarily set the threshold to zero, register three demo wallets, then restore the
            threshold to three before inviting anyone else.
          </p>
          <p className="mt-2 text-xs text-slate-400">Current required vouches: {requiredVouches?.toString() ?? "…"}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="rounded-full border border-amber-300/30 px-4 py-2 text-xs text-amber-100 disabled:opacity-50" disabled={chain?.id !== baseSepolia.id || isPending || isConfirming} onClick={() => setVouchThreshold(0)}>
              Enable initial registrations (0)
            </button>
            <button className="rounded-full border border-slate-600 px-4 py-2 text-xs text-slate-200 disabled:opacity-50" disabled={chain?.id !== baseSepolia.id || isPending || isConfirming} onClick={() => setVouchThreshold(3)}>
              Restore 3-vouch rule
            </button>
          </div>
        </div>
      )}

      <div className="panel rounded-2xl p-5">
        <h3 className="font-semibold text-white">Vouch for a pending person</h3>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">
          Active registry members can vouch by the person’s 32-byte DID hash. Each wallet can vouch once.
        </p>
        <label className="mt-4 block text-[10px] uppercase tracking-wide text-slate-500" htmlFor="target-did-hash">
          Target DID hash
        </label>
        <input
          id="target-did-hash"
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-200 outline-none focus:border-emerald-400"
          placeholder="0x… (32 bytes)"
          value={targetDidHash}
          onChange={(event) => setTargetDidHash(event.target.value)}
        />
        <button
          className="mt-3 rounded-full border border-slate-600 px-4 py-2 text-xs font-semibold text-slate-200 disabled:opacity-50"
          disabled={!isConnected || isPending || isConfirming || chain?.id !== baseSepolia.id}
          onClick={vouch}
        >
          Submit vouch
        </button>
      </div>

      {(message || error || writeError || isSuccess) && (
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs">
          {error || writeError ? <p className="text-rose-300">{error || writeError?.message}</p> : <p className="text-emerald-200">{isSuccess ? "Transaction confirmed." : message}</p>}
          {hash && (
            <a className="mt-1 inline-block text-sky-300 underline" href={`https://sepolia.basescan.org/tx/${hash}`} target="_blank" rel="noreferrer">
              View transaction on BaseScan
            </a>
          )}
        </div>
      )}
    </div>
  );
}
