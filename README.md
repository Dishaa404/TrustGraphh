# TrustGraph

Graph-native registry prototype with Base Sepolia contracts, TigerGraph scoring, and Cake Wallet XMR invoices.

A stake-backed on-chain human registry, a TigerGraph social-trust engine, and crypto payments
through Cake Wallet. Built as a take on
Proof of Humanity / BrightID-style personhood verification.

## Monorepo layout

```
apps/web      Next.js frontend + verifier portal
apps/api      FastAPI backend, TigerGraph client, Cake Wallet XMR adapter
contracts     Solidity registry contracts (Hardhat)
graph         TigerGraph schema, GSQL queries, seed data
docs          Hackathon deployment guide
```

## Status

Hackathon prototype. The contracts support stake-backed registration, vouching, challenges,
revocation, withdrawals, and credential anchoring. The web app can submit registration and vouch
transactions after a Base Sepolia deployment. The API connects to TigerGraph for queries and writes,
and creates XMR invoices through an authenticated Monero wallet RPC so a payer can use Cake Wallet.
Contract events are not yet indexed into TigerGraph. Semaphore proofs and production identity
verification are not implemented.

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

For the full wallet-to-contract setup, see [the hackathon deployment guide](docs/hackathon-deployment.md).

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

- **Person** registers with a DID hash and a random demo commitment, backed by a stake. The current flow does not collect or verify biometrics.
- **Vouches** are signed on-chain by already-active humans; activation needs `requiredVouches`.
- **TigerGraph** turns API and seeded vouch data into an explainable trust score and flags likely sybil rings.
- **Credentials** can be hashed and anchored on-chain; encrypted IPFS storage is not implemented yet.
- **Challenges** are stake-backed and resolved by an arbitrator; upheld challenges slash the
  registration stake and revoke the member.

The current web registration action writes a random commitment hash to the contract. It is not a
biometric check, uniqueness proof, or Semaphore proof. TigerGraph returns clearly labelled demo data
when not configured. Cake Wallet payments require a real merchant Monero wallet RPC and XMR; they
are not simulated. Do not treat this prototype as real-world identity verification.

## Environment

See `.env.example` at the repo root and the `.env.example` files in `contracts/` and `apps/api/`.
