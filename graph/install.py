"""Create the TrustGraph schema and install all GSQL queries.

Usage:
    python install.py

Environment (or graph/.env):
    TG_HOST, TG_USERNAME, TG_PASSWORD, TG_SECRET, TG_GRAPH
"""

from __future__ import annotations

import os
import pathlib
import sys

import pyTigerGraph as tg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).parent
load_dotenv(ROOT / ".env")


def connect() -> tg.TigerGraphConnection:
    host = os.environ.get("TG_HOST")
    username = os.environ.get("TG_USERNAME")
    password = os.environ.get("TG_PASSWORD")
    graph = os.environ.get("TG_GRAPH", "TrustGraph")
    secret = os.environ.get("TG_SECRET", "")

    if not host or not username or not password:
        sys.exit("Set TG_HOST, TG_USERNAME and TG_PASSWORD first.")

    conn = tg.TigerGraphConnection(
        host=host,
        username=username,
        password=password,
        graphname=graph,
        tgCloud=True,
    )
    if secret:
        conn.getToken(secret)
    return conn


def main() -> None:
    conn = connect()
    graph = os.environ.get("TG_GRAPH", "TrustGraph")

    schema = (ROOT / "schema.gsql").read_text(encoding="utf-8")
    print("Creating schema...")
    print(conn.gsql(schema))

    for path in sorted((ROOT / "queries").glob("*.gsql")):
        print(f"Installing query {path.name}...")
        source = path.read_text(encoding="utf-8")
        print(conn.gsql(f"USE GRAPH {graph}\n{source}"))

    print(conn.gsql(f"USE GRAPH {graph}\nINSTALL QUERY ALL"))
    print("Done.")


if __name__ == "__main__":
    main()
