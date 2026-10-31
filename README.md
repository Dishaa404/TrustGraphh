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
graph         TigerGraph schema, GSQL queries, sample data loader
docs          Hackathon deployment guide
```

## Status

Live MVP foundation, still not a verified-personhood production service. The contracts support stake-backed registration, vouching, challenges,
revocation, withdrawals, and credential anchoring. The web app can submit registration and vouch
transactions after a Base Sepolia deployment. The API connects to TigerGraph for queries and writes,
and creates XMR invoices through an authenticated Monero wallet RPC so a payer can use Cake Wallet.
Base Sepolia registry events can be indexed into TigerGraph after the receiver signs in and the API
validates the mined transaction receipt. Off-chain vouch writes are rejected; contract events are the
source of truth. Semaphore proofs and independent real-world identity verification are not implemented.

Wallet sign-in supports donor, receiver, and NGO roles. The backend issues short-lived bearer
sessions after an Ethereum wallet signature; the signature is only a login proof and does not send a
transaction. Donor and receiver roles are self-selected. NGO issuer access requires the wallet to be
listed in the API's `VERIFIED_NGO_WALLETS` setting; other NGO wallets can submit an application and
remain pending. Local development can use in-memory storage; production/Vercel deployments require
`DATABASE_URL` pointing to PostgreSQL for sessions and API records.

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

Follow `graph/README.md` to create the `TrustGraph` graph, install the queries, and load sample
records for development with `graph/seed.py`.

## Core model

- **Person** registers with a DID hash and a random commitment, backed by a stake. The current flow does not collect or verify biometrics.
- **Vouches** are signed on-chain by already-active humans; activation needs `requiredVouches`.
- **TigerGraph** turns indexed Base Sepolia registry data into explainable trust scores and Sybil-ring signals.
- **Credentials** can be hashed and anchored on-chain; encrypted IPFS storage is not implemented yet.
- **Challenges** are stake-backed and resolved by an arbitrator; upheld challenges slash the
  registration stake and revoke the member.

The current web registration action writes a random commitment hash to the contract. It is not a
biometric check, uniqueness proof, or Semaphore proof. Graph data is unavailable until TigerGraph is
configured. Cake Wallet payments require a real merchant Monero wallet RPC and XMR. Do not treat this
service as real-world identity verification.

## Environment

See `.env.example` at the repo root and the `.env.example` files in `contracts/` and `apps/api/`.
