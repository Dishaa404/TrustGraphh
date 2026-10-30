# Base Sepolia hackathon deployment

This deploys the Solidity registries to Base Sepolia and runs the web/API demo locally. TigerGraph handles graph queries and live API writes. Cake Wallet is the payer app for XMR; the API creates invoice subaddresses through an authenticated merchant Monero wallet-RPC service. Contract events are not indexed into TigerGraph, and Semaphore proofs are not implemented. Registration stores a random commitment hash; it is not biometric or proof-of-personhood verification.

## 1. Configure and deploy contracts

Use a dedicated testnet wallet, fund it with Base Sepolia ETH, and keep its key local. From the repository root:

```bash
cd contracts
cp .env.example .env
```

Set `PRIVATE_KEY`, and optionally `BASE_SEPOLIA_RPC_URL` and `TREASURY_ADDRESS` in `contracts/.env`. Never use a mainnet key or commit this file. Then:

```bash
npm ci
npm test
npm run compile
npm run deploy:baseSepolia
```

The deployment command refuses a non-Base-Sepolia chain and prints both contract addresses. Save the `PersonhoodRegistry` address.

The registry starts with three required vouches but no active members. In the web app, connect the deployer/owner wallet and temporarily select **Enable initial registrations (0)**. Register three distinct demo wallets, then reconnect the owner and select **Restore 3-vouch rule**. New registrations can then be activated by those members' on-chain vouches.

## 2. Configure TigerGraph

Create a TigerGraph Cloud solution and graph secret. Copy the example and set its endpoint, graph name, and secret:

```bash
cd graph
cp .env.example .env
python -m pip install -r requirements.txt
python install.py
python seed.py
```

Use `TG_GRAPH=TrustGraph`. The seed script loads 60 demo people and two planted sybil rings. Copy the same `TG_HOST`, `TG_GRAPH`, and `TG_SECRET` values into `apps/api/.env`. The API uses TigerGraph for trust, explanation, and sybil queries, and writes API-created people, vouches, and XMR payment events into the graph. Keep the graph secret server-side; it does not belong in the web app.

## 3. Configure Cake Wallet XMR payments

Cake Wallet is the payer wallet. The API needs a separately controlled merchant Monero wallet exposed through `monero-wallet-rpc`; it creates a fresh receive subaddress and Monero URI per invoice, then checks incoming transfers. Start the wallet RPC with authentication, bind it to localhost, and point it at a dedicated wallet. For example:

```bash
monero-wallet-rpc --rpc-bind-ip 127.0.0.1 --rpc-bind-port 18088 --wallet-file <dedicated-wallet-file> --password <wallet-password> --rpc-login trustgraph:<rpc-password> --daemon-address <monerod-url>
```

Set these values in `apps/api/.env`:

```env
CAKE_MONERO_WALLET_RPC_URL=http://127.0.0.1:18088/json_rpc
CAKE_MONERO_WALLET_RPC_USER=trustgraph
CAKE_MONERO_WALLET_RPC_PASSWORD=<rpc-password>
PAYMENT_PROVIDER=cake
```

Cake Wallet scans the QR code or opens the Monero payment URI. The app is non-custodial; the merchant receive wallet remains under your control. Base Sepolia does not make XMR a testnet asset, so only create invoices you intend to fund. The adapter rejects missing RPC configuration and never generates sample receive addresses.

## 4. Run the API

In a terminal, copy `apps/api/.env.example` to `apps/api/.env`, configure TigerGraph and Cake Wallet values above, then:

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Without TigerGraph credentials, graph endpoints return labelled demo responses. API state is in memory and resets when the process restarts.

## 5. Run the web app

In another terminal, set the deployed registry address and API URL in `apps/web/.env.local`:

```bash
cd apps/web
cp .env.example .env.local
npm ci
npm run dev
```

Open `http://localhost:3000`, connect an injected wallet, switch it to Base Sepolia, and register. The page reads the registration stake from the contract and links submitted transactions to BaseScan. It also creates Cake Wallet invoices through the API and shows the returned payment QR code.

## Checks

Run `python -m pytest -q` in `apps/api`, `npm test` in `contracts`, and `npm run build` in `apps/web`. GitHub Actions runs these checks on pushes to `main` and pull requests. A deployment still needs a funded Base Sepolia deployer and live TigerGraph and Monero wallet-RPC credentials.
