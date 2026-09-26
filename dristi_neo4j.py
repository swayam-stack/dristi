"""
Optional Neo4j mirror.

The console runs fine without it — the analytics use the in-process NetworkX
graph. This module pushes the same graph into Neo4j so the prototype is genuinely
database-backed, and so the graph can be explored in Neo4j Browser.

Set the connection in .streamlit/secrets.toml or as environment variables:

    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=your-password

Then:  python dristi_neo4j.py --load
"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import dristi_core as core


def _cfg() -> Tuple[str, str, str]:
    uri = os.environ.get("NEO4J_URI", "")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD", "")
    if not uri:
        try:
            import streamlit as st
            uri = st.secrets.get("NEO4J_URI", "")
            user = st.secrets.get("NEO4J_USER", user)
            pwd = st.secrets.get("NEO4J_PASSWORD", pwd)
        except Exception:
            pass
    return uri, user, pwd


def driver():
    uri, user, pwd = _cfg()
    if not uri:
        return None
    from neo4j import GraphDatabase
    return GraphDatabase.driver(uri, auth=(user, pwd))


def status() -> Tuple[str, str]:
    uri, _, _ = _cfg()
    if not uri:
        return ("offline", "No NEO4J_URI configured — running on the local graph engine")
    try:
        drv = driver()
        with drv.session() as s:
            n = s.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        drv.close()
        return ("online", f"Neo4j connected — {n} nodes")
    except Exception as e:
        return ("error", f"Neo4j configured but unreachable: {e}")


def load(data_dir: str = "data", wipe: bool = True) -> Dict[str, Any]:
    """Push persons, vehicles, transactions, locations, evidence and the call
    graph into Neo4j, with the evidence record carried on every relationship."""
    d = core.load_data(data_dir)
    drv = driver()
    if drv is None:
        raise RuntimeError("NEO4J_URI is not set")
    stats = {}
    with drv.session() as s:
        if wipe:
            s.run("MATCH (n) DETACH DELETE n")
        s.run("CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)")

        s.run("""UNWIND $rows AS r
                 MERGE (p:Person {name: r.name})
                 SET p.person_id=r.person_id, p.age=toInteger(r.age),
                     p.address=r.address, p.phone=toString(r.phone)""",
              rows=d["persons"].to_dict("records"))
        stats["persons"] = len(d["persons"])

        s.run("""UNWIND $rows AS r
                 MERGE (l:Location {location_id: r.location_id})
                 SET l.name=r.location_name, l.latitude=toFloat(r.latitude),
                     l.longitude=toFloat(r.longitude)""",
              rows=d["locations"].to_dict("records"))

        s.run("""UNWIND $rows AS r
                 MERGE (e:Evidence {evidence_id: r.evidence_id})
                 SET e.source_type=r.source_type, e.source_file=r.source_file,
                     e.description=r.description""",
              rows=d["evidence"].to_dict("records"))
        stats["evidence"] = len(d["evidence"])

        s.run("""UNWIND $rows AS r
                 MATCH (o:Person {name: r.owner})
                 MERGE (v:Vehicle {vehicle_id: r.vehicle_id})
                 SET v.registration=r.registration, v.vehicle_type=r.vehicle_type
                 MERGE (o)-[rel:OWNS]->(v)
                 SET rel.evidence_id=r.evidence_id, rel.confidence=0.98""",
              rows=d["vehicles"].to_dict("records"))
        stats["vehicles"] = len(d["vehicles"])

        calls = d["calls"].copy()
        calls["timestamp"] = calls["timestamp"].astype(str)
        s.run("""UNWIND $rows AS r
                 MATCH (a:Person {name: r.caller}), (b:Person {name: r.receiver})
                 MERGE (a)-[c:CALLED {evidence_id: r.evidence_id}]->(b)
                 SET c.timestamp=r.timestamp, c.duration=toInteger(r.duration),
                     c.location_id=r.location_id, c.confidence=0.98,
                     c.source='calls.csv'""",
              rows=calls.to_dict("records"))
        stats["calls"] = len(calls)

        txns = d["transactions"].copy()
        txns["timestamp"] = txns["timestamp"].astype(str)
        s.run("""UNWIND $rows AS r
                 MATCH (a:Person {name: r.sender}), (b:Person {name: r.receiver})
                 MERGE (t:Transaction {transaction_id: r.transaction_id})
                 SET t.amount=toFloat(r.amount), t.timestamp=r.timestamp
                 MERGE (a)-[s1:SENT]->(t) SET s1.evidence_id=r.evidence_id,
                                             s1.confidence=0.98, s1.source='transactions.csv'
                 MERGE (t)-[s2:RECEIVED_BY]->(b) SET s2.evidence_id=r.evidence_id,
                                                     s2.confidence=0.98""",
              rows=txns.to_dict("records"))
        stats["transactions"] = len(txns)
    drv.close()
    return stats


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--data", default="data")
    a = ap.parse_args()
    print(status()[1])
    if a.load:
        print(json.dumps(load(a.data), indent=2))
