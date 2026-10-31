# Base Sepolia hackathon deployment

This deploys the Solidity registries to Base Sepolia and runs the web/API locally. TigerGraph handles graph queries and indexed registry events. Cake Wallet is the payer app for XMR; the API creates invoice subaddresses through an authenticated merchant wallet-RPC service. Semaphore proofs are not implemented. Registration stores a random commitment hash; it is not biometric or proof-of-personhood verification.

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

The registry starts with three required vouches but no active members. In the web app, connect the deployer/owner wallet and temporarily select **Enable initial registrations (0)**. Register three distinct wallets, then reconnect the owner and select **Restore 3-vouch rule**. New registrations can then be activated by those members' on-chain vouches.

## 2. Configure TigerGraph

Create a TigerGraph Cloud solution and graph secret. Copy the example and set its endpoint, graph name, and secret:

```bash
cd graph
cp .env.example .env
python -m pip install -r requirements.txt
python install.py
```

Use `TG_GRAPH=TrustGraph`. Copy the same `TG_HOST`, `TG_GRAPH`, and `TG_SECRET` values into the API environment. The API uses TigerGraph for trust, explanation, and sybil queries, and writes indexed Base Sepolia people/vouches and XMR payment events into the graph. Keep the graph secret server-side; it does not belong in the web app. `graph/seed.py` is for local query development only; do not run it against the live graph.

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

Without TigerGraph credentials, graph endpoints report that the service is unconfigured. Local development uses in-memory storage when `DATABASE_URL` is unset. Vercel/production requires a PostgreSQL `DATABASE_URL`; it stores sessions, login challenges, people, credentials, payment intents, and NGO applications across function instances.

### Role sign-in and NGO approval

The web app offers donor, receiver, and NGO wallet sign-in. A login signature is role-bound, used once,
and produces a 12-hour bearer session. Donor/receiver roles are self-selected wallet roles. To approve
an NGO issuer, set `VERIFIED_NGO_WALLETS` in the API environment to a comma-separated list of approved
wallet addresses (lowercase comparison is automatic), then redeploy the API. NGO wallets outside that
list can submit an application but cannot issue or revoke credentials until approved.

## 5. Run the web app

In another terminal, set the deployed registry address and API URL in `apps/web/.env.local`:

```bash
cd apps/web
cp .env.example .env.local
npm ci
npm run dev
```

Open `http://localhost:3000`, connect an injected wallet, switch it to Base Sepolia, and register. The page reads the registration stake from the contract and links submitted transactions to BaseScan. It also creates Cake Wallet invoices through the API and shows the returned payment QR code.


## 6. Deploy a live MVP to Vercel

Use a managed PostgreSQL database and configure its pooled `DATABASE_URL` on the API project. Do not use an
in-memory store or a local SQLite file for Vercel functions. Import this repository twice in Vercel:

1. API project root: `apps/api`. Set `APP_ENV=production`, `DATABASE_URL`, `API_CORS_ORIGINS` to the
   frontend's production origin, `BASE_SEPOLIA_RPC_URL`, `PERSONHOOD_REGISTRY_ADDRESS`, and
   server-only `TG_HOST`, `TG_GRAPH`, `TG_SECRET`, and `VERIFIED_NGO_WALLETS`. Add the Cake wallet-RPC variables only when you have a secured, remotely
   reachable Monero wallet RPC service; `127.0.0.1` will refer to the Vercel function itself.
2. Web project root: `apps/web`. Set `NEXT_PUBLIC_API_URL` to the deployed API origin and
   `NEXT_PUBLIC_PERSONHOOD_REGISTRY_ADDRESS` to the deployed registry address. Leave
   `NEXT_PUBLIC_BASE_PATH` empty or unset for the Vercel domain.
3. Redeploy both projects after configuring variables. Check API `/health`, then the site should
   report the API and TigerGraph as connected when both are reachable and the graph queries are
   installed.

After a receiver transaction confirms, the web app asks the API to verify its receipt against the
configured Base Sepolia registry. Verified `Registered`, `Vouched`, `Activated`, `Challenged`,
`ChallengeResolved`, and `Revoked` events are then written to the API store and TigerGraph.

The API creates the small `trustgraph_store` JSONB table on first start. The database URL must point
to PostgreSQL and allow TLS from Vercel where required by the provider. Local in-memory mode is for
development only. Back up the database before schema changes or production data migrations.

## Checks

Run `python -m pytest -q` in `apps/api`, `npm test` in `contracts`, and `npm run build` in `apps/web`. GitHub Actions runs these checks on pushes to `main` and pull requests. A deployment still needs a funded Base Sepolia deployer and live TigerGraph and Monero wallet-RPC credentials.
