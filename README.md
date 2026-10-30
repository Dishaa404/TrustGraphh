# TrustGraph

Graph-native proof-of-personhood and credential verification.

A stake-backed on-chain human registry, a TigerGraph social-trust engine, zero-knowledge
membership proofs, and crypto payments (Cake Wallet / Rodo). Built as a stronger take on
Proof of Humanity / BrightID-style personhood verification.

## Monorepo layout

```
apps/web      Next.js frontend + verifier portal
apps/api      FastAPI backend, TigerGraph client, payment adapters
contracts     Solidity registry contracts (Hardhat)
graph         TigerGraph schema, GSQL queries, seed data
infra         Deployment / local infrastructure
docs          Architecture, demo script, benchmark notes
```

## Status

Phase 0/1 scaffolding in progress:

- [x] Personhood registry (register / vouch / challenge / revoke / withdraw)
- [x] Credential registry (issue / revoke / validity)
- [x] TigerGraph schema + trust queries + seed script
- [x] FastAPI skeleton (health, persons, trust, payments, credentials)
- [x] Next.js shell
- [ ] Semaphore ZK membership proofs (Phase 4)
- [ ] Live Base Sepolia deployment (Phase 1)

## Quickstart

### Contracts

```bash
cd contracts
npm install
npx hardhat test
```

Deploy to Base Sepolia after copying `.env.example` to `.env`:

```bash
npx hardhat run scripts/deploy.ts --network baseSepolia
```

### API

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

### TigerGraph

Follow `graph/README.md` to create the `TrustGraph` graph, install the queries, and seed
synthetic humans (including planted sybil rings) with `graph/seed.py`.

## Core model

- **Person** registers with a DID hash and biometric hash (hash only, never raw data), backed by a stake.
- **Vouches** are signed on-chain by already-active humans; activation needs `requiredVouches`.
- **TigerGraph** turns the vouch graph into an explainable trust score, detects sybil communities,
  and propagates revocations to downstream credentials.
- **Credentials** are hashed and anchored on-chain, with encrypted contents in IPFS.
- **Challenges** are stake-backed and resolved by an arbitrator; upheld challenges slash the
  registration stake and revoke the member.

## Environment

See `.env.example` at the repo root and the `.env.example` files in `contracts/` and `apps/api/`.
