# TigerGraph layer

Schema, GSQL queries, and demo seed data for TrustGraph.

## Setup

1. Create a TigerGraph Cloud solution and copy `.env.example` to `.env`.
2. Fill `TG_HOST` with the solution URL, set `TG_GRAPH=TrustGraph`, and create a graph secret in TigerGraph Cloud for `TG_SECRET`.
3. Install dependencies and create the graph + queries:

```bash
pip install -r requirements.txt
python install.py
```

4. Load the demo dataset (60 people, 2 planted sybil rings):

```bash
python seed.py
```

The API uses the same `TG_HOST`, `TG_GRAPH`, and `TG_SECRET` values in `apps/api/.env`.
The client uses the TigerGraph Cloud graph-secret flow, then runs installed queries and
upserts person, vouch, and confirmed payment records. Do not put the graph secret in the web app.

## Queries

| Query | Purpose |
|---|---|
| `trust_score(did)` | Explainable score from voucher trust, credentials, challenges, shared devices |
| `explain_trust(did)` | Returns the vouchers, credentials, devices, and upheld challenges behind a score |
| `sybil_rings(min_mutual, min_devices)` | Flags accounts in mutual-vouch cycles or shared-device clusters |

Run them through the API after installing the queries, or directly from Python:

```bash
python -c "import seed; c = seed.connect(); print(c.runInstalledQuery('trust_score', {'did': 'did:trustgraph:person-001'}))"
```

## Production hardening

- Replace the weighted trust sum with PageRank over `VOUCHED` (TigerGraph Graph Data
  Science library) and persist scores back to `Person.trust_score`.
- Replace the heuristic `sybil_rings` query with Louvain community detection, then rank
  communities by internal edge density and external-edge ratio.
- Ingest `Registered`, `Vouched`, `ChallengeResolved`, and `Revoked` contract events
  through the API indexer instead of seeding.
