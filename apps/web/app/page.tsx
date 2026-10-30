"use client";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  CreditCard,
  Fingerprint,
  GitBranch,
  Globe2,
  Link2,
  Network,
  ScanFace,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";

import { ConnectButton } from "@/components/connect-button";

type Health = {
  status: string;
  services: { tigergraph: string; payments: string };
};

type Rings = {
  flagged: string[];
  source: string;
};

type RingRow = {
  name: string;
  signal: string;
  risk: "critical" | "high" | "medium";
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const demoRings: RingRow[] = [
  { name: "ring-a / 5 accounts", signal: "mutual vouches + shared emulator", risk: "critical" },
  { name: "ring-b / 5 accounts", signal: "fully connected vouch cluster", risk: "high" },
  { name: "person-017", signal: "shared household device", risk: "medium" },
];

const steps = [
  {
    icon: Fingerprint,
    title: "Register",
    body: "Connect a wallet, pay the stake, and commit a biometric hash. Raw biometrics never leave the device.",
  },
  {
    icon: Users,
    title: "Get vouched",
    body: "Existing humans vouch on-chain. TigerGraph scores the vouch graph and activates the member.",
  },
  {
    icon: ShieldCheck,
    title: "Prove personhood",
    body: "Generate a Semaphore proof that you are in the verified set without revealing which member you are.",
  },
  {
    icon: CreditCard,
    title: "Pay any rail",
    body: "Cake Wallet handles XMR, BTC and USDC. Rodo plugs into the same payment adapter interface.",
  },
];

function Gauge({ score }: { score: number }) {
  const degrees = Math.round((score / 100) * 360);

  return (
    <div className="relative h-44 w-44">
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(#34d399 0deg ${degrees}deg, rgba(148, 163, 184, 0.12) ${degrees}deg 360deg)`,
        }}
      />
      <div className="absolute inset-3 flex flex-col items-center justify-center rounded-full bg-[#080d13]">
        <span className="text-4xl font-semibold tracking-tight text-white">{score}</span>
        <span className="text-[10px] uppercase tracking-[0.22em] text-slate-500">trust score</span>
      </div>
    </div>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="panel rounded-2xl p-5">
      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function RiskChip({ risk }: { risk: RingRow["risk"] }) {
  const styles = {
    critical: "border-rose-400/30 bg-rose-400/10 text-rose-200",
    high: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    medium: "border-sky-400/30 bg-sky-400/10 text-sky-200",
  };

  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${styles[risk]}`}>
      {risk}
    </span>
  );
}

export default function Home() {
  const [apiOnline, setApiOnline] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [rings, setRings] = useState<Rings | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const [healthResponse, ringsResponse] = await Promise.all([
          fetch(`${API_URL}/health`, { signal: controller.signal }),
          fetch(`${API_URL}/graph/rings`, { signal: controller.signal }),
        ]);

        if (!healthResponse.ok || !ringsResponse.ok) {
          throw new Error("API unavailable");
        }

        const healthData = (await healthResponse.json()) as Health;
        const ringsData = (await ringsResponse.json()) as Rings;

        setHealth(healthData);
        setRings(ringsData);
        setApiOnline(true);
      } catch {
        setApiOnline(false);
      }
    }

    load();
    return () => controller.abort();
  }, []);

  const ringRows: RingRow[] =
    rings && rings.flagged.length > 0
      ? rings.flagged.slice(0, 6).map((flag) => {
          const [did, ...signals] = flag.split("|");
          return {
            name: did.replace("did:trustgraph:", ""),
            signal: signals.join(" · "),
            risk: "critical" as const,
          };
        })
      : demoRings;

  const graphMode = health?.services.tigergraph ?? "demo";
  const paymentProvider = health?.services.payments ?? "cake";

  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] grid-bg" />

      <div className="relative mx-auto max-w-6xl px-6 pb-20">
        <nav className="flex items-center justify-between py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-400/15 ring-1 ring-emerald-400/30">
              <Network className="h-5 w-5 text-emerald-300" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-white">TrustGraph</p>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-500">
                proof of personhood
              </p>
            </div>
          </div>

          <div className="hidden items-center gap-7 text-sm text-slate-400 md:flex">
            <a className="transition hover:text-white" href="#how">
              How it works
            </a>
            <a className="transition hover:text-white" href="#trust">
              Trust engine
            </a>
            <a className="transition hover:text-white" href="#detection">
              Sybil detection
            </a>
            <a className="transition hover:text-white" href="#payments">
              Payments
            </a>
          </div>

          <ConnectButton />
        </nav>

        <section className="grid items-center gap-12 pt-12 md:grid-cols-[1.05fr_0.95fr] md:pt-16">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1 text-[11px] font-medium text-emerald-200">
              <Sparkles className="h-3.5 w-3.5" />
              Graph-native verification, not linear vouching
            </div>

            <h1 className="mt-6 max-w-xl text-4xl font-semibold leading-[1.05] tracking-tight text-white md:text-6xl">
              Proof of personhood,
              <span className="bg-gradient-to-r from-emerald-300 via-teal-200 to-sky-300 bg-clip-text text-transparent">
                {" "}
                backed by the graph.
              </span>
            </h1>

            <p className="mt-6 max-w-lg text-base leading-relaxed text-slate-400">
              A stake-backed human registry on Base, a TigerGraph trust engine that explains every
              score, and zero-knowledge proofs that answer one question: is this a unique human?
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <a
                href="#how"
                className="flex items-center gap-2 rounded-full bg-emerald-400 px-5 py-2.5 text-sm font-semibold text-emerald-950 transition hover:bg-emerald-300"
              >
                Start verification
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="#detection"
                className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/60 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-slate-500"
              >
                <ScanFace className="h-4 w-4 text-emerald-300" />
                Inspect the detector
              </a>
            </div>

            <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    apiOnline ? "bg-emerald-400" : "bg-amber-400"
                  }`}
                />
                API {apiOnline ? "online" : "offline"}
              </span>
              <span className="flex items-center gap-1.5">
                <GitBranch className="h-3.5 w-3.5" />
                TigerGraph: {graphMode}
              </span>
              <span className="flex items-center gap-1.5">
                <CreditCard className="h-3.5 w-3.5" />
                Payments: {paymentProvider}
              </span>
              <span className="flex items-center gap-1.5">
                <Globe2 className="h-3.5 w-3.5" />
                Base Sepolia
              </span>
            </div>
          </div>

          <div className="panel relative rounded-3xl p-6 shadow-glow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">live trust graph</p>
                <p className="mt-1 font-mono text-xs text-slate-300">did:trustgraph:person-001</p>
              </div>
              <span className="flex items-center gap-1.5 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-2.5 py-1 text-[10px] text-emerald-200">
                <Activity className="h-3 w-3" />
                explainable
              </span>
            </div>

            <div className="mt-6 flex items-center justify-center">
              <Gauge score={92} />
            </div>

            <div className="mt-6 space-y-3">
              {[
                ["Vouch graph", "0.82", "w-[82%]"],
                ["Credential diversity", "0.64", "w-[64%]"],
                ["Device overlap", "0.12", "w-[12%]"],
                ["Challenge history", "0.00", "w-[2%]"],
              ].map(([label, value, width]) => (
                <div key={label}>
                  <div className="mb-1 flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-mono text-slate-300">{value}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className={`h-full rounded-full bg-gradient-to-r from-emerald-400 to-teal-300 ${width}`} />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-[11px] text-slate-400">
              <BadgeCheck className="h-4 w-4 shrink-0 text-emerald-300" />
              Activated by 3 trusted vouchers. 2 valid credentials. 0 shared devices.
            </div>
          </div>
        </section>

        <section className="mt-16 grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Humans seeded" value="60" detail="5 trusted roots" />
          <Stat
            label="Sybil rings"
            value={rings?.flagged.length ? String(rings.flagged.length) : "2"}
            detail="planted + detected"
          />
          <Stat label="Avg trust" value="92" detail="with evidence path" />
          <Stat label="Registration stake" value="0.001" detail="ETH on Base Sepolia" />
        </section>

        <section id="how" className="mt-20 scroll-mt-8">
          <div className="flex items-end justify-between gap-6">
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-emerald-300/80">the flow</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white md:text-3xl">
                Four steps from wallet to proof
              </h2>
            </div>
            <p className="hidden max-w-xs text-sm text-slate-500 md:block">
              Every step writes a compact event on-chain. TigerGraph keeps the full trust context
              queryable.
            </p>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-4">
            {steps.map((step, index) => (
              <div key={step.title} className="panel panel-hover rounded-2xl p-5">
                <div className="flex items-center justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800/80 ring-1 ring-slate-700">
                    <step.icon className="h-4 w-4 text-emerald-300" />
                  </div>
                  <span className="font-mono text-[10px] text-slate-600">0{index + 1}</span>
                </div>
                <h3 className="mt-4 text-sm font-semibold text-white">{step.title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="trust" className="mt-20 grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="panel rounded-3xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-[0.24em] text-sky-300/80">trust engine</p>
                <h2 className="mt-2 text-xl font-semibold text-white">Every score has a receipt</h2>
              </div>
              <Link2 className="h-5 w-5 text-slate-600" />
            </div>

            <div className="mt-6 overflow-hidden rounded-xl border border-slate-800">
              <div className="grid grid-cols-[1fr_auto_auto] bg-slate-900/70 px-4 py-2 text-[10px] uppercase tracking-wide text-slate-500">
                <span>signal</span>
                <span>weight</span>
                <span>contribution</span>
              </div>
              {[
                ["Vouches from trusted humans", "40%", "+32.8"],
                ["Valid credentials", "25%", "+16.0"],
                ["Account age", "10%", "+10.0"],
                ["Challenge history", "15%", "-0.0"],
                ["Device overlap penalty", "10%", "-1.2"],
              ].map(([signal, weight, value]) => (
                <div
                  key={signal}
                  className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-t border-slate-800/80 px-4 py-2.5 text-xs"
                >
                  <span className="text-slate-300">{signal}</span>
                  <span className="font-mono text-slate-500">{weight}</span>
                  <span className={value.startsWith("-") ? "font-mono text-rose-300" : "font-mono text-emerald-300"}>
                    {value}
                  </span>
                </div>
              ))}
            </div>

            <p className="mt-4 text-xs leading-relaxed text-slate-500">
              GSQL returns the contributing paths, not just a number. Verifiers can audit why an
              account is trusted before accepting a proof.
            </p>
          </div>

          <div className="panel rounded-3xl p-6">
            <p className="text-[10px] uppercase tracking-[0.24em] text-emerald-300/80">credential graph</p>
            <h2 className="mt-2 text-xl font-semibold text-white">Revocation propagates</h2>

            <div className="mt-5 space-y-3">
              {[
                ["issuer:gov", "KYC credential", "valid", "emerald"],
                ["issuer:uni", "Education credential", "valid", "emerald"],
                ["issuer:employer", "Employment credential", "revoked", "rose"],
              ].map(([issuer, type, status, tone]) => (
                <div
                  key={type}
                  className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-3"
                >
                  <div>
                    <p className="text-xs font-medium text-slate-200">{type}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-slate-500">{issuer}</p>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] ${
                      tone === "rose"
                        ? "bg-rose-400/10 text-rose-300"
                        : "bg-emerald-400/10 text-emerald-300"
                    }`}
                  >
                    {status}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-5 flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3 text-[11px] leading-relaxed text-amber-200/80">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              Revoking a slashed issuer flags every downstream credential in one GSQL traversal.
            </div>
          </div>
        </section>

        <section id="detection" className="mt-20 grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="panel rounded-3xl p-6">
            <p className="text-[10px] uppercase tracking-[0.24em] text-rose-300/80">sybil detection</p>
            <h2 className="mt-2 text-xl font-semibold text-white">Rings, not just accounts</h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              Mutual-vouch cycles, shared devices, and dense internal communities are scored
              together. The demo plants two rings of five accounts inside sixty honest humans.
            </p>
            <div className="mt-5 grid grid-cols-2 gap-2">
              <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                <p className="font-mono text-lg text-emerald-300">10</p>
                <p className="text-[10px] uppercase tracking-wide text-slate-500">planted accounts</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                <p className="font-mono text-lg text-rose-300">2</p>
                <p className="text-[10px] uppercase tracking-wide text-slate-500">rings to find</p>
              </div>
            </div>
          </div>

          <div className="panel rounded-3xl p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Flagged clusters</h2>
              <span className="font-mono text-[10px] text-slate-500">
                source: {rings?.source ?? "demo"}
              </span>
            </div>

            <div className="mt-4 divide-y divide-slate-800/80">
              {ringRows.map((row) => (
                <div key={`${row.name}-${row.signal}`} className="flex items-center gap-3 py-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-400/10 ring-1 ring-rose-400/20">
                    <AlertTriangle className="h-4 w-4 text-rose-300" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-xs text-slate-200">{row.name}</p>
                    <p className="truncate text-[11px] text-slate-500">{row.signal}</p>
                  </div>
                  <RiskChip risk={row.risk} />
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="payments" className="mt-20 grid gap-3 lg:grid-cols-[1fr_1fr]">
          <div className="panel rounded-3xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-[0.24em] text-emerald-300/80">payments</p>
                <h2 className="mt-2 text-xl font-semibold text-white">One adapter, two rails</h2>
              </div>
              <CreditCard className="h-5 w-5 text-slate-600" />
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-emerald-400/25 bg-emerald-400/5 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-white">Cake Wallet</span>
                  <span className="rounded-full bg-emerald-400/15 px-2 py-0.5 text-[10px] text-emerald-300">
                    active
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">
                  Monero subaddresses for privacy, plus BTC and USDC on Base.
                </p>
                <div className="mt-3 flex gap-1.5">
                  {["XMR", "BTC", "USDC"].map((asset) => (
                    <span
                      key={asset}
                      className="rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-[10px] text-slate-300"
                    >
                      {asset}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-white">Rodo</span>
                  <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                    adapter ready
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">
                  Same intent API, same webhook. Drop in credentials to switch rails.
                </p>
                <div className="mt-3 font-mono text-[10px] text-slate-500">
                  POST /payments/intent
                </div>
              </div>
            </div>
          </div>

          <div className="panel rounded-3xl p-6">
            <p className="text-[10px] uppercase tracking-[0.24em] text-slate-500">payment intent</p>
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-300">pay_7f3a...91c2</span>
                <span className="rounded-full bg-amber-400/10 px-2 py-0.5 text-[10px] text-amber-300">
                  pending
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 text-xs">
                <div>
                  <p className="text-slate-500">asset</p>
                  <p className="mt-1 font-mono text-slate-200">XMR</p>
                </div>
                <div>
                  <p className="text-slate-500">amount</p>
                  <p className="mt-1 font-mono text-slate-200">0.042</p>
                </div>
              </div>
              <div className="mt-4 rounded-lg bg-slate-900/80 px-3 py-2 font-mono text-[10px] text-slate-400">
                8A1b...9F4c
              </div>
              <div className="mt-3 flex items-center gap-2 text-[11px] text-slate-500">
                <Activity className="h-3.5 w-3.5 text-emerald-400" />
                confirms in 1 network confirmation
              </div>
            </div>
          </div>
        </section>

        <footer className="mt-20 flex flex-col items-start justify-between gap-4 border-t border-slate-800/80 pt-6 text-xs text-slate-500 md:flex-row md:items-center">
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-emerald-300" />
            TrustGraph - proof of personhood, explained by the graph.
          </div>
          <div className="flex items-center gap-4">
            <span>Base Sepolia</span>
            <span>TigerGraph</span>
            <span>Cake Wallet</span>
          </div>
        </footer>
      </div>
    </main>
  );
}
