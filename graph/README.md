# TigerGraph layer

Schema, GSQL queries, and demo seed data for TrustGraph.

## Setup

1. Create a TigerGraph Savanna instance and copy `.env.example` to `.env`.
2. Fill `TG_HOST`, `TG_USERNAME`, `TG_PASSWORD`, and the secret from the Savanna console.
3. Install dependencies and create the graph + queries:

```bash
pip install -r requirements.txt
python install.py
```

4. Load the demo dataset (60 people, 2 planted sybil rings):

```bash
python seed.py
```

## Queries

| Query | Purpose |
|---|---|
| `trust_score(did)` | Explainable score from voucher trust, credentials, challenges, shared devices |
| `explain_trust(did)` | Returns the vouchers, credentials, devices, and upheld challenges behind a score |
| `sybil_rings(min_mutual, min_devices)` | Flags accounts in mutual-vouch cycles or shared-device clusters |

Run them from the GSQL shell or through the API:

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
