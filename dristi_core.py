"""
DRISTI core — data loading, graph construction and all analytics.

Deliberately separate from the UI. app.py renders; this file computes. That
split matters because it means the benchmark can score exactly the functions
the screens display, rather than a parallel reimplementation that might quietly
differ.

No Neo4j dependency here. The graph is built in NetworkX so the application
runs whether or not a database is available; dristi_neo4j.py mirrors the same
graph into Neo4j when credentials are present.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd

# DRISTI's operating thresholds, in one place so the screens and the benchmark
# cannot drift apart.
LATE_NIGHT_START, LATE_NIGHT_END = 22, 5
HIGH_VALUE = 60_000
CASH_REPORTING_THRESHOLD = 50_000
STRUCTURING_BAND = 0.12
STRUCTURING_WINDOW_DAYS = 4.0
STRUCTURING_MIN_COUNT = 3
IF_CONTAMINATION = 0.10


# ==========================================================================
# Loading
# ==========================================================================

def load_data(data_dir: str = "data") -> Dict[str, pd.DataFrame]:
    def rd(name: str) -> pd.DataFrame:
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)

    d = {
        "persons": rd("persons.csv"),
        "calls": rd("calls.csv"),
        "transactions": rd("transactions.csv"),
        "vehicles": rd("vehicles.csv"),
        "locations": rd("locations.csv"),
        "evidence": rd("evidence.csv"),
    }
    for key in ("calls", "transactions"):
        if not d[key].empty:
            col = "timestamp"
            d[key][col] = pd.to_datetime(d[key][col], errors="coerce")
            d[key]["hour"] = d[key][col].dt.hour
            d[key]["weekday"] = d[key][col].dt.weekday
            d[key]["late_night"] = d[key]["hour"].apply(is_late_hour)
    return d


def load_ground_truth(data_dir: str = "data") -> Optional[Dict[str, Any]]:
    path = os.path.join(data_dir, "_ground_truth.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# Columns computed for the anomaly model, not for a human to read. Kept out
# of every investigator-facing table - a screen full of `weekday` and
# `late_night` booleans is implementation detail leaking into an interface an
# officer is meant to trust.
INTERNAL_COLUMNS = ["hour", "weekday", "late_night"]


def display(df: "pd.DataFrame", drop: Optional[List[str]] = None) -> "pd.DataFrame":
    cols = [c for c in df.columns if c not in (drop or INTERNAL_COLUMNS)]
    return df[cols]


def is_late_hour(h: int) -> bool:
    return bool(h >= LATE_NIGHT_START or h < LATE_NIGHT_END)


# ==========================================================================
# Graphs
# ==========================================================================

def build_full_graph(d: Dict[str, pd.DataFrame], max_txn_nodes: int = 120) -> nx.Graph:
    """
    The heterogeneous view shown in the Network Graph module: people, vehicles
    and transactions as nodes, exactly as the original prototype rendered it.

    Transactions are capped because past a few hundred nodes a force layout
    stops being a picture of a network and becomes a picture of a hairball.
    The cap keeps the largest transactions, which are the ones worth looking at.
    """
    g = nx.Graph()
    for _, p in d["persons"].iterrows():
        g.add_node(p["name"], kind="Person", label=p["name"],
                   person_id=p.get("person_id", ""), phone=str(p.get("phone", "")),
                   address=p.get("address", ""))

    for _, v in d["vehicles"].iterrows():
        g.add_node(v["vehicle_id"], kind="Vehicle", label=v["vehicle_id"],
                   registration=v.get("registration", ""))
        if v["owner"] in g:
            g.add_edge(v["owner"], v["vehicle_id"], relationship="OWNS",
                       evidence_id=v.get("evidence_id", ""))

    txns = d["transactions"]
    if not txns.empty:
        keep = txns.nlargest(min(max_txn_nodes, len(txns)), "amount")
        for _, t in keep.iterrows():
            g.add_node(t["transaction_id"], kind="Transaction",
                       label=t["transaction_id"], amount=float(t["amount"]))
            if t["sender"] in g:
                g.add_edge(t["sender"], t["transaction_id"], relationship="SENT",
                           evidence_id=t.get("evidence_id", ""))
            if t["receiver"] in g:
                g.add_edge(t["receiver"], t["transaction_id"],
                           relationship="RECEIVED_BY",
                           evidence_id=t.get("evidence_id", ""))

    # call edges between people, carrying their supporting evidence
    agg: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for _, c in d["calls"].iterrows():
        a, b = c["caller"], c["receiver"]
        if a in g and b in g and a != b:
            agg[tuple(sorted((a, b)))].append(str(c.get("evidence_id", "")))
    for (a, b), evs in agg.items():
        g.add_edge(a, b, relationship="CALLED", calls=len(evs),
                   evidence_id=evs[0], evidence_ids=evs[:8])
    return g


def build_person_graph(d: Dict[str, pd.DataFrame]) -> nx.Graph:
    """
    Person-to-person only: the view the analytics reason over. Two people are
    linked if they called each other, moved money, or share a vehicle — and the
    edge remembers which of those it was, and which records say so.
    """
    g = nx.Graph()
    for _, p in d["persons"].iterrows():
        g.add_node(p["name"], person_id=p.get("person_id", ""),
                   phone=str(p.get("phone", "")), address=p.get("address", ""))

    def link(a: str, b: str, why: str, ev: str) -> None:
        if a not in g or b not in g or a == b:
            return
        if g.has_edge(a, b):
            e = g[a][b]
            e["reasons"].add(why)
            e["weight"] += 1
            if ev and len(e["evidence_ids"]) < 12:
                e["evidence_ids"].append(ev)
        else:
            g.add_edge(a, b, reasons={why}, weight=1,
                       evidence_ids=[ev] if ev else [])

    for _, c in d["calls"].iterrows():
        link(c["caller"], c["receiver"], "phone_contact", str(c.get("evidence_id", "")))
    for _, t in d["transactions"].iterrows():
        link(t["sender"], t["receiver"], "financial_transfer", str(t.get("evidence_id", "")))

    owners: Dict[str, List[str]] = defaultdict(list)
    for _, v in d["vehicles"].iterrows():
        owners[v["registration"]].append(v["owner"])
    for reg, who in owners.items():
        for i in range(len(who)):
            for j in range(i + 1, len(who)):
                link(who[i], who[j], "shared_vehicle", "")
    return g


# ==========================================================================
# Network intelligence
# ==========================================================================

def connectivity_table(pg: nx.Graph) -> pd.DataFrame:
    if pg.number_of_nodes() == 0:
        return pd.DataFrame()
    deg = dict(pg.degree())
    # Eigenvector centrality is only defined on a connected graph -
    # networkx raises AmbiguousSolution otherwise. A bare try/except here
    # silently returns all-zero scores, which turns the "ranking" into
    # whatever order the rows happened to arrive in. Compute it per
    # component instead, scaled by component size so scores stay comparable.
    eig: Dict[str, float] = {n: 0.0 for n in pg}
    n_total = max(1, pg.number_of_nodes())
    for comp in nx.connected_components(pg):
        if len(comp) < 3:
            continue
        sub = pg.subgraph(comp)
        try:
            # weight=None deliberately. The edge weight here counts how many
            # times a pair was observed, which is volume, not tie strength.
            # Feeding volume in as strength makes a chatty pair look central:
            # measured on this corpus, weighted eigenvector puts zero syndicate
            # members in the top 20, unweighted puts twenty out of twenty.
            part = nx.eigenvector_centrality_numpy(sub, weight=None)
        except Exception:
            try:
                part = nx.eigenvector_centrality(sub, max_iter=1000, weight=None)
            except Exception:
                part = {n: 0.0 for n in sub}
        share = len(comp) / n_total
        for n, v in part.items():
            eig[n] = v * share
    btw = nx.betweenness_centrality(pg) if pg.number_of_edges() else {n: 0.0 for n in pg}
    rows = [{
        "person": n,
        "connections": deg.get(n, 0),
        "eigenvector": round(eig.get(n, 0.0), 4),
        "betweenness": round(btw.get(n, 0.0), 4),
        "call_links": sum(1 for m in pg.neighbors(n)
                          if "phone_contact" in pg[n][m]["reasons"]),
        "money_links": sum(1 for m in pg.neighbors(n)
                           if "financial_transfer" in pg[n][m]["reasons"]),
    } for n in pg.nodes()]
    return pd.DataFrame(rows).sort_values("eigenvector", ascending=False).reset_index(drop=True)


def detect_communities(pg: nx.Graph) -> Dict[str, int]:
    if pg.number_of_edges() == 0:
        return {}
    try:
        parts = nx.community.louvain_communities(pg, weight="weight", seed=7)
    except Exception:
        parts = list(nx.connected_components(pg))
    return {n: i for i, part in enumerate(parts) for n in part}


def shortest_path_between(pg: nx.Graph, a: str, b: str) -> List[Dict[str, Any]]:
    if a not in pg or b not in pg or a == b:
        return []
    try:
        path = nx.shortest_path(pg, a, b)
    except nx.NetworkXNoPath:
        return []
    hops = []
    for u, v in zip(path, path[1:]):
        e = pg[u][v]
        hops.append({"from": u, "to": v,
                     "why": ", ".join(sorted(e["reasons"])),
                     "records": e["evidence_ids"][:3],
                     "observations": e["weight"]})
    return hops


# ==========================================================================
# Behavioural analytics
# ==========================================================================

def isolation_forest_scores(txns: pd.DataFrame) -> pd.DataFrame:
    """The prototype's existing model: one row in, one score out."""
    if txns.empty or len(txns) < 8:
        return txns.assign(anomaly_score=0.0, analysis_result="insufficient data")
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import RobustScaler

    X = txns[["amount", "hour", "weekday", "late_night"]].astype(float).values
    Xs = RobustScaler().fit_transform(X)
    clf = IsolationForest(n_estimators=300, contamination=IF_CONTAMINATION,
                          random_state=11, n_jobs=1).fit(Xs)
    score = -clf.score_samples(Xs)
    cut = float(np.quantile(score, 1 - IF_CONTAMINATION))
    out = txns.copy()
    out["anomaly_score"] = np.round(score, 4)
    out["analysis_result"] = np.where(score >= cut, "Potentially unusual",
                                      "Within observed pattern")
    return out


def detect_structuring(txns: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Repeated transfers just below the cash reporting threshold, inside a tight
    window. The Isolation Forest cannot find this: each transfer is ordinary on
    its own, and the pattern exists only across rows.
    """
    if txns.empty:
        return []
    lo = CASH_REPORTING_THRESHOLD * (1 - STRUCTURING_BAND)
    band = txns[(txns["amount"] >= lo) & (txns["amount"] < CASH_REPORTING_THRESHOLD)]
    out: List[Dict[str, Any]] = []
    for sender, grp in band.groupby("sender"):
        grp = grp.sort_values("timestamp")
        rows = grp.to_dict("records")
        best: List[Dict[str, Any]] = []
        i = 0
        for j in range(len(rows)):
            while (rows[j]["timestamp"] - rows[i]["timestamp"]).total_seconds() > \
                    STRUCTURING_WINDOW_DAYS * 86400:
                i += 1
            if j - i + 1 > len(best):
                best = rows[i:j + 1]
        if len(best) >= STRUCTURING_MIN_COUNT:
            span = (best[-1]["timestamp"] - best[0]["timestamp"]).days + 1
            day_word = "day" if span == 1 else "days"
            out.append({
                "person": sender, "detector": "structuring", "family": "financial",
                "count": len(best), "total": float(sum(r["amount"] for r in best)),
                "window_days": span,
                "description": (f"{len(best)} transfers of INR "
                                f"{int(min(r['amount'] for r in best)):,}–"
                                f"{int(max(r['amount'] for r in best)):,} within "
                                f"{span} {day_word}, each below the INR "
                                f"{CASH_REPORTING_THRESHOLD:,} reporting threshold"),
                "transaction_ids": [r["transaction_id"] for r in best],
                "evidence_ids": [r.get("evidence_id", "") for r in best],
                "score": min(1.0, 0.45 + 0.09 * len(best)),
            })
    return out


def detect_value_outliers(txns: pd.DataFrame, min_history: int = 4,
                          z_cut: float = 3.0) -> List[Dict[str, Any]]:
    """A transfer far outside a subject's OWN history — not a global rupee
    cutoff, which only ever finds the wealthy."""
    if txns.empty:
        return []
    out = []
    per: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in txns.to_dict("records"):
        per[r["sender"]].append(r)
        per[r["receiver"]].append(r)
    for person, rows in per.items():
        if len(rows) < min_history + 1:
            continue
        amts = np.array([r["amount"] for r in rows], dtype=float)
        logs = np.log1p(amts)
        med, mad = float(np.median(logs)), float(np.median(np.abs(logs - np.median(logs))))
        if mad < 1e-6:
            continue
        z = 0.6745 * (logs - med) / mad
        idx = [i for i in range(len(rows)) if z[i] > z_cut]
        if not idx:
            continue
        top = max(idx, key=lambda i: z[i])
        out.append({
            "person": person, "detector": "value_outlier", "family": "financial",
            "count": len(idx),
            "description": (f"{len(idx)} transaction(s) far outside this subject's own "
                            f"baseline; largest INR {int(rows[top]['amount']):,} against "
                            f"a median of INR {int(np.median(amts)):,}"),
            "transaction_ids": [rows[i]["transaction_id"] for i in idx][:6],
            "evidence_ids": [rows[i].get("evidence_id", "") for i in idx][:6],
            "score": min(1.0, 0.35 + 0.12 * len(idx)),
        })
    return out


def detect_rapid_passthrough(txns: pd.DataFrame, window_hours: float = 36.0,
                             retain: float = 0.25) -> List[Dict[str, Any]]:
    """Money in, money straight out again — the mule/funnel signature."""
    if txns.empty:
        return []
    ins: Dict[str, List[Dict]] = defaultdict(list)
    outs: Dict[str, List[Dict]] = defaultdict(list)
    for r in txns.to_dict("records"):
        ins[r["receiver"]].append(r)
        outs[r["sender"]].append(r)
    res = []
    for person, got in ins.items():
        sent = outs.get(person, [])
        if not sent:
            continue
        hits = []
        for i in got:
            for o in sent:
                dt = (o["timestamp"] - i["timestamp"]).total_seconds() / 3600.0
                if 0 < dt <= window_hours and o["amount"] >= i["amount"] * (1 - retain):
                    hits.append((i, o))
                    break
        if len(hits) >= 2:
            moved = sum(o["amount"] for _, o in hits)
            res.append({
                "person": person, "detector": "rapid_passthrough",
                "family": "financial", "count": len(hits),
                "description": (f"{len(hits)} instance(s) of funds received and forwarded "
                                f"within {window_hours:.0f}h retaining under "
                                f"{int(retain*100)}% (INR {int(moved):,} moved)"),
                "transaction_ids": [r["transaction_id"] for pair in hits for r in pair][:6],
                "evidence_ids": [r.get("evidence_id", "") for pair in hits for r in pair][:6],
                "score": min(1.0, 0.3 + 0.15 * len(hits)),
            })
    return res


def late_night_activity(d: Dict[str, pd.DataFrame], quantile: float = 0.85
                        ) -> List[Dict[str, Any]]:
    calls = d["calls"]
    if calls.empty:
        return []
    late = calls[calls["late_night"]]
    counts: Dict[str, int] = defaultdict(int)
    recs: Dict[str, List[str]] = defaultdict(list)
    for r in late.to_dict("records"):
        for who in (r["caller"], r["receiver"]):
            counts[who] += 1
            if len(recs[who]) < 8:
                recs[who].append(str(r.get("evidence_id", "")))
    if not counts:
        return []
    cut = float(np.quantile(list(counts.values()), quantile))
    return [{
        "person": p, "detector": "late_night_contact", "family": "communication",
        "count": n,
        "description": f"{n} calls inside the {LATE_NIGHT_START:02d}:00–"
                       f"{LATE_NIGHT_END:02d}:00 window",
        "evidence_ids": recs[p], "transaction_ids": [],
        "score": min(0.9, 0.3 + 0.03 * n),
    } for p, n in counts.items() if n >= cut]


def high_value_activity(d: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    txns = d["transactions"]
    if txns.empty:
        return []
    hv = txns[txns["amount"] >= HIGH_VALUE]
    per: Dict[str, List[Dict]] = defaultdict(list)
    for r in hv.to_dict("records"):
        per[r["sender"]].append(r)
        per[r["receiver"]].append(r)
    return [{
        # Family is "financial", not a separate "financial_value": this detector
        # reads the same transactions table as structuring, value_outlier and
        # rapid_passthrough. Counting it as a second family would let one source
        # of evidence vote twice at the correlation gate, which is exactly the
        # failure the gate exists to prevent.
        "person": p, "detector": "high_value_transfer", "family": "financial",
        "count": len(rows),
        "description": f"{len(rows)} transaction(s) at or above INR {HIGH_VALUE:,} "
                       f"(largest INR {int(max(r['amount'] for r in rows)):,})",
        "transaction_ids": [r["transaction_id"] for r in rows][:6],
        "evidence_ids": [r.get("evidence_id", "") for r in rows][:6],
        "score": min(0.9, 0.35 + 0.15 * len(rows)),
    } for p, rows in per.items()]


def structural_prominence(conn: pd.DataFrame, top_frac: float = 0.25
                          ) -> List[Dict[str, Any]]:
    if conn.empty:
        return []
    cut = max(1, int(len(conn) * top_frac))
    out = []
    for i, r in conn.head(cut).iterrows():
        out.append({
            "person": r["person"], "detector": "network_centrality",
            "family": "structural", "count": int(r["connections"]),
            "description": (f"structurally prominent: eigenvector centrality "
                            f"{r['eigenvector']:.3f}, {int(r['connections'])} direct "
                            f"contacts (rank {i+1} of {len(conn)})"),
            "evidence_ids": [], "transaction_ids": [],
            "score": round(0.35 + 0.5 * (1 - i / max(1, cut)), 4),
        })
    return out


# ==========================================================================
# Multi-signal correlation
# ==========================================================================

NON_CORROBORATING: Set[str] = set()      # model-only families would go here

# One weight per DISTINCT SOURCE of evidence, not per detector. Everything
# derived from the transactions table is one family. "geospatial" is declared
# because the lens exists in the console, but no detector emits it yet, so the
# gate currently sees at most three families: financial, communication,
# structural. The benchmark reports that ceiling rather than implying five.
FAMILY_WEIGHT = {
    "financial": 0.95,
    "communication": 0.8, "structural": 0.85, "geospatial": 0.8,
}
BENCHMARK_FAMILIES = ("financial", "communication", "structural")


def run_all_detectors(d: Dict[str, pd.DataFrame], pg: nx.Graph) -> List[Dict[str, Any]]:
    txns = d["transactions"]
    conn = connectivity_table(pg)
    dets: List[Dict[str, Any]] = []
    dets += detect_structuring(txns)
    dets += detect_value_outliers(txns)
    dets += detect_rapid_passthrough(txns)
    dets += late_night_activity(d)
    dets += high_value_activity(d)
    dets += structural_prominence(conn)
    return dets


def correlate(detections: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Combine within a family by noisy-OR, then across families — and gate on how
    many INDEPENDENT families agree. The gate is the point: without it, one
    noisy detector is enough to put a name in front of an officer.
    """
    by_person: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    comps: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for det in detections:
        by_person[det["person"]][det["family"]].append(float(det["score"]))
        comps[det["person"]].append(det)

    rows = []
    for person, fams in by_person.items():
        fam_score = {}
        for fam, scores in fams.items():
            prod = 1.0
            for sc in scores:
                prod *= (1 - max(0.0, min(1.0, sc)))
            fam_score[fam] = round(1 - prod, 4)
        corroborating = sorted(f for f, v in fam_score.items()
                               if f not in NON_CORROBORATING and v >= 0.35)
        prod = 1.0
        for fam, v in fam_score.items():
            prod *= (1 - FAMILY_WEIGHT.get(fam, 0.5) * v)
        score = round(1 - prod, 4)
        n = len(corroborating)
        if n >= 3 and score >= 0.75:
            level = "HIGH"
        elif n >= 2 and score >= 0.55:
            level = "MEDIUM"
        elif n >= 1:
            level = "LOW"
        else:
            level = "NONE"
        rows.append({
            "person": person, "level": level, "score": score,
            "families": n, "family_list": ", ".join(corroborating),
            "detectors": ", ".join(sorted({c["detector"] for c in comps[person]})),
            "n_detections": len(comps[person]),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    df["_o"] = df["level"].map(order)
    return df.sort_values(["_o", "families", "score"], ascending=False)\
             .drop(columns="_o").reset_index(drop=True)


# ==========================================================================
# Evidence chain
# ==========================================================================

def evidence_chain(person: str, detections: List[Dict[str, Any]],
                   correlation: pd.DataFrame, pg: nx.Graph,
                   d: Dict[str, pd.DataFrame], max_records: int = 8) -> Dict[str, Any]:
    """finding → why it fired → graph context → relationships → source records"""
    mine = [x for x in detections if x["person"] == person]
    row = correlation[correlation["person"] == person]
    level = row.iloc[0]["level"] if len(row) else "NONE"
    fams = row.iloc[0]["family_list"] if len(row) else ""

    neighbours = []
    if person in pg:
        for nb in pg.neighbors(person):
            e = pg[person][nb]
            neighbours.append({
                "person": nb, "why": ", ".join(sorted(e["reasons"])),
                "observations": e["weight"], "records": e["evidence_ids"][:3],
            })
        neighbours.sort(key=lambda x: -x["observations"])

    wanted: List[str] = []
    for det in sorted(mine, key=lambda x: -x["score"]):
        for ev in det.get("evidence_ids", []):
            if ev and ev not in wanted:
                wanted.append(ev)
    for nb in neighbours[:4]:
        for ev in nb["records"]:
            if ev and ev not in wanted:
                wanted.append(ev)

    ev_df = d["evidence"]
    records = []
    if not ev_df.empty and wanted:
        sub = ev_df[ev_df["evidence_id"].isin(wanted[:max_records])]
        records = sub.to_dict("records")

    statement = (f"{person} was surfaced because {len(fams.split(', ')) if fams else 0} "
                 f"distinct analytical famil(ies) agree ({fams or 'none'}). "
                 f"Assessed level: {level}. This indicates where attention may be "
                 f"warranted; it is not a determination of criminality.")
    return {
        "person": person, "level": level, "statement": statement,
        "reasons": sorted(mine, key=lambda x: -x["score"]),
        "neighbours": neighbours[:10],
        "records": records,
    }


# ==========================================================================
# Benchmark
# ==========================================================================

def _prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)}


def _auc(y: Sequence[int], s: Sequence[float]) -> float:
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return 0.5
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv)
    ranks = np.empty(len(allv), dtype=float)
    ranks[order] = np.arange(1, len(allv) + 1)
    for v in np.unique(allv):
        m = allv == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def run_benchmark(d: Dict[str, pd.DataFrame], pg: nx.Graph,
                  detections: List[Dict[str, Any]], correlation: pd.DataFrame,
                  truth: Dict[str, Any]) -> Dict[str, Any]:
    syndicate: Set[str] = set(truth["syndicate_members"])
    anom_txn: Set[str] = set(truth["anomalous_transactions"])
    names = list(d["persons"]["name"])
    base = len(syndicate) / max(1, len(names))

    scored = isolation_forest_scores(d["transactions"])
    y = [1 if t in anom_txn else 0 for t in scored["transaction_id"]]
    if_flag = set(scored[scored["analysis_result"] == "Potentially unusual"]["transaction_id"])
    if_res = _prf(len(if_flag & anom_txn), len(if_flag - anom_txn),
                  len(anom_txn - if_flag))
    if_res["auroc"] = round(_auc(y, scored["anomaly_score"]), 4)

    struct = detect_structuring(d["transactions"])
    st_flag = {t for s in struct for t in s["transaction_ids"]}
    st_res = _prf(len(st_flag & anom_txn), len(st_flag - anom_txn),
                  len(anom_txn - st_flag))

    conn = connectivity_table(pg)
    ranked = list(conn["person"])                       # eigenvector order
    by_count = list(conn.sort_values("connections", ascending=False)["person"])
    ki = {f"precision_at_{k}": round(
        sum(1 for n in ranked[:k] if n in syndicate) / k, 4) for k in (5, 10, 20)}
    ki_count = {f"precision_at_{k}": round(
        sum(1 for n in by_count[:k] if n in syndicate) / k, 4) for k in (5, 10, 20)}

    lv: Dict[str, Set[str]] = defaultdict(set)
    for _, r in correlation.iterrows():
        lv[r["level"]].add(r["person"])
    one = {r["person"] for _, r in correlation.iterrows() if r["families"] == 1}
    two = {r["person"] for _, r in correlation.iterrows() if r["families"] >= 2}
    three = {r["person"] for _, r in correlation.iterrows() if r["families"] >= 3}

    def prec(s: Set[str]) -> float:
        return round(len(s & syndicate) / len(s), 4) if s else 0.0

    total = len(d["calls"]) + len(d["transactions"]) + len(d["vehicles"])
    linked = (d["calls"]["evidence_id"].notna().sum()
              + d["transactions"]["evidence_id"].notna().sum()
              + d["vehicles"]["evidence_id"].notna().sum()) if total else 0

    return {
        "base_rate": round(base, 4),
        "corpus": {"persons": len(names), "calls": len(d["calls"]),
                   "transactions": len(d["transactions"]),
                   "vehicles": len(d["vehicles"]), "syndicate": len(syndicate)},
        "isolation_forest": if_res,
        "structuring_typology": st_res,
        "key_individuals": ki,
        "key_individuals_by_raw_connection_count": ki_count,
        "evidence_coverage": round(linked / total, 4) if total else 0.0,
        "corroboration": {
            "random_baseline": round(base, 4),
            "one_family": prec(one), "two_plus": prec(two), "three_plus": prec(three),
            "n_one": len(one), "n_two_plus": len(two), "n_three_plus": len(three),
            "recall_two_plus": round(len(two & syndicate) / max(1, len(syndicate)), 4),
        },
    }
