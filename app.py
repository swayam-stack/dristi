"""
DRISTI — Investigation Intelligence Console.

Streamlit front end. Keeps the original prototype's layout and visual identity
(dark surface, red accent, module list in the sidebar) and adds the three
modules the idea submission claims: Evidence Chain, Multi-Signal Correlation,
and a Benchmark that scores the console's own analytics on screen.

    streamlit run app.py
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dristi_core as core

st.set_page_config(page_title="DRISTI — Investigation Intelligence Console",
                   page_icon="🔥", layout="wide",
                   initial_sidebar_state="expanded")

DATA_DIR = os.environ.get("DRISTI_DATA", "data")

RED = "#ff3b30"
AMBER = "#ffa726"
GREEN = "#00e676"
DIM = "#8b8f99"

CSS = """
<style>
  .stApp { background: radial-gradient(1200px 600px at 12% -10%, #2a0b0c 0%, #0b0708 55%); }
  section[data-testid="stSidebar"] { background:#0e0a0b; border-right:1px solid #2a1b1d; }
  h1,h2,h3,h4 { color:#f3eff0 !important; letter-spacing:.3px; }
  p, span, label, li, div[data-testid="stMarkdownContainer"] { color:#cfc7c9; }
  .brand { font-size:30px; font-weight:800; letter-spacing:7px; color:#ff3b30;
           text-shadow:0 0 18px rgba(255,59,48,.55); margin:0; }
  .brandsub { font-size:10.5px; letter-spacing:2.6px; color:#8b8f99; margin:2px 0 14px; }
  .hero { border:1px solid #3a1416; border-radius:12px; padding:20px 24px; margin-bottom:8px;
          background:linear-gradient(120deg,#210b0d 0%,#140a0b 60%,#0f0809 100%); }
  .hero h1 { font-size:44px; letter-spacing:12px; margin:0; color:#fff;
             text-shadow:0 0 26px rgba(255,59,48,.6); }
  .hero .tag { font-size:11px; letter-spacing:3.4px; color:#b9b1b3; margin-top:4px; }
  .pill { display:inline-block; margin-top:12px; padding:5px 14px; border-radius:16px;
          font-size:11px; letter-spacing:1.4px; border:1px solid #ff3b30; color:#ff8b84;
          background:rgba(255,59,48,.10); }
  .online { border:1px solid #145c37; background:rgba(0,230,118,.08); color:#00e676;
            border-radius:9px; padding:10px 12px; font-weight:700; font-size:13px; }
  .note { border-left:3px solid #ffa726; background:rgba(255,167,38,.07);
          padding:11px 14px; border-radius:6px; color:#f0d9a8; font-size:13px; margin:12px 0; }
  .lvl { padding:2px 9px; border-radius:10px; font-size:11px; font-weight:700; }
  .card { border:1px solid #2a1b1d; background:#140e0f; border-radius:9px;
          padding:12px 14px; margin:8px 0; }
  .chain { border-left:2px solid #ff3b30; padding:2px 0 10px 12px; margin-left:5px; }
  .chain .lbl { color:#ff8b84; font-size:10.5px; letter-spacing:1.6px; font-weight:700; }
  .mono { font-family:ui-monospace,Consolas,monospace; font-size:12px; color:#bdb5b7; }
  [data-testid="stMetricValue"] { color:#ff6a60 !important; }
  .stDataFrame { border:1px solid #2a1b1d; border-radius:8px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

PLOT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cfc7c9", size=12),
            xaxis=dict(gridcolor="#2a1b1d"), yaxis=dict(gridcolor="#2a1b1d"),
            margin=dict(l=10, r=10, t=30, b=10))


# ==========================================================================
# Load once
# ==========================================================================

@st.cache_data(show_spinner="Loading the case…")
def _load(data_dir: str):
    d = core.load_data(data_dir)
    truth = core.load_ground_truth(data_dir)
    return d, truth


@st.cache_data(show_spinner="Building the evidence graph…")
def _graphs(data_dir: str):
    d = core.load_data(data_dir)
    return core.build_person_graph(d), core.build_full_graph(d)


@st.cache_data(show_spinner="Running analytics…")
def _analysis(data_dir: str):
    d = core.load_data(data_dir)
    pg = core.build_person_graph(d)
    dets = core.run_all_detectors(d, pg)
    corr = core.correlate(dets)
    return dets, corr


if not os.path.exists(os.path.join(DATA_DIR, "persons.csv")):
    st.error(f"No data found in `{DATA_DIR}/`. Put the CSVs there and reload.")
    st.stop()

D, TRUTH = _load(DATA_DIR)
PG, FG = _graphs(DATA_DIR)
DETECTIONS, CORR = _analysis(DATA_DIR)
CONN = core.connectivity_table(PG)
COMMS = core.detect_communities(PG)
NAMES = sorted(D["persons"]["name"])

try:
    import dristi_neo4j
    NEO_STATUS = dristi_neo4j.status()
except Exception:
    NEO_STATUS = ("offline", "Neo4j module not configured — running on the local graph")


# ==========================================================================
# Sidebar
# ==========================================================================

with st.sidebar:
    st.markdown('<p class="brand">🔥 DRISTI</p>', unsafe_allow_html=True)
    st.markdown('<p class="brandsub">INVESTIGATION INTELLIGENCE CONSOLE</p>',
                unsafe_allow_html=True)
    st.markdown('<div class="online">● DRISTI CORE ONLINE</div>', unsafe_allow_html=True)
    ok = NEO_STATUS[0] == "online"
    st.caption(("NEO4J KNOWLEDGE GRAPH CONNECTED" if ok
                else "LOCAL GRAPH ENGINE · NEO4J OPTIONAL"))
    st.divider()
    st.markdown("**SELECT MODULE**")
    MODULE = st.radio("module", [
        "Dashboard", "Persons", "Network Graph", "Call Network", "Transactions",
        "Vehicles", "Evidence", "Timeline Analysis", "Geospatial Analysis",
        "Analytics", "Multi-Signal Correlation", "Evidence Chain", "Benchmark",
    ], label_visibility="collapsed")
    st.divider()
    st.markdown("**GRAPH STATUS**")
    c1, c2 = st.columns(2)
    c1.metric("PERSONS", len(D["persons"]))
    c2.metric("CALLS", len(D["calls"]))
    c1.metric("TXNS", len(D["transactions"]))
    c2.metric("EVIDENCE", len(D["evidence"]))
    c1.metric("VEHICLES", len(D["vehicles"]))
    c2.metric("LOCATIONS", len(D["locations"]))
    st.caption("SIH 2026 PROTOTYPE · human-in-the-loop investigation system")


def hero(title: str, sub: str = "") -> None:
    st.markdown(
        '<div class="hero"><h1>DRISTI</h1>'
        '<div class="tag">AI-POWERED CRIMINAL NETWORK ANALYSIS SYSTEM</div>'
        '<span class="pill">● DRISTI CORE // NEO4J INTELLIGENCE // HUMAN VERIFIED</span>'
        '</div>', unsafe_allow_html=True)
    st.markdown(f"## {title}")
    if sub:
        st.caption(sub)


HITL = ('<div class="note"><b>HUMAN-IN-THE-LOOP:</b> network connectivity, transaction '
        'patterns, late-night activity and AI anomaly scores are analytical indicators '
        'only. They do not establish criminal activity. Investigators must examine the '
        'underlying evidence and context.</div>')

LEVEL_COLOR = {"HIGH": RED, "MEDIUM": AMBER, "LOW": GREEN, "NONE": DIM}


def badge(level: str) -> str:
    c = LEVEL_COLOR.get(level, DIM)
    return (f'<span class="lvl" style="color:{c};border:1px solid {c};'
            f'background:{c}1a">{level}</span>')


# ==========================================================================
# Modules
# ==========================================================================

if MODULE == "Dashboard":
    hero("DRISTI Investigation Intelligence",
         "Knowledge graph · behavioural analysis · temporal analysis · "
         "geospatial analysis · AI analytics")
    a, b, c, d_ = st.columns(4)
    a.metric("PERSONS", len(D["persons"]))
    b.metric("CALL RECORDS", len(D["calls"]))
    c.metric("TRANSACTIONS", len(D["transactions"]))
    d_.metric("EVIDENCE RECORDS", len(D["evidence"]))
    a, b, c, d_ = st.columns(4)
    a.metric("GRAPH EDGES", PG.number_of_edges())
    b.metric("GROUPS DETECTED", len(set(COMMS.values())) if COMMS else 0)
    hi = int((CORR["level"] == "HIGH").sum()) if not CORR.empty else 0
    med = int((CORR["level"] == "MEDIUM").sum()) if not CORR.empty else 0
    c.metric("HIGH SIGNALS", hi)
    d_.metric("MEDIUM SIGNALS", med)

    st.markdown("### Top investigative signals")
    if CORR.empty:
        st.info("No signals.")
    else:
        for _, r in CORR.head(8).iterrows():
            st.markdown(
                f'<div class="card">{badge(r["level"])} &nbsp; <b>{r["person"]}</b> '
                f'&nbsp;<span class="mono">score {r["score"]:.2f} · '
                f'{r["families"]} distinct analytical families · {r["family_list"]}</span></div>',
                unsafe_allow_html=True)
    st.markdown(HITL, unsafe_allow_html=True)

elif MODULE == "Persons":
    hero("Persons", "Individuals recorded in the knowledge graph.")
    st.dataframe(D["persons"], use_container_width=True, height=280)
    who = st.selectbox("Select a person", NAMES)
    st.markdown("### Connected Investigation Records")
    rows = []
    for nb in PG.neighbors(who):
        e = PG[who][nb]
        rows.append({"relationship": ", ".join(sorted(e["reasons"])),
                     "connected_entity": nb, "entity_type": "Person",
                     "observations": e["weight"],
                     "evidence": ", ".join(e["evidence_ids"][:3])})
    for _, v in D["vehicles"][D["vehicles"]["owner"] == who].iterrows():
        rows.append({"relationship": "OWNS", "connected_entity": v["vehicle_id"],
                     "entity_type": "Vehicle", "observations": 1,
                     "evidence": v.get("evidence_id", "")})
    st.dataframe(pd.DataFrame(rows).sort_values("observations", ascending=False)
                 if rows else pd.DataFrame(), use_container_width=True, height=300)
    st.markdown(HITL, unsafe_allow_html=True)

elif MODULE == "Network Graph":
    hero("DRISTI Knowledge Graph", "Visualisation of recorded graph entities and "
                                   "relationships.")
    c1, c2 = st.columns([1, 2])
    with c1:
        scope = st.radio("View", ["Person network", "Full heterogeneous graph"])
    with c2:
        g0 = PG if scope == "Person network" else FG
        max_n = st.slider("Nodes to draw (highest degree first)", 30,
                          max(40, g0.number_of_nodes()),
                          min(120, g0.number_of_nodes()), step=10)
        hide_iso = st.checkbox("Hide unconnected nodes", value=True,
                               help="A node with no edges is flung to the edge of a "
                                    "force layout and drags everything else into a "
                                    "corner. Hidden by default.")
    g = g0
    keep = [n for n, _ in sorted(g.degree(), key=lambda x: -x[1])[:max_n]]
    if hide_iso:
        keep = [n for n in keep if g.degree(n) > 0]
    sub = g.subgraph(keep)

    # Lay out the largest component on its own. Including detached fragments
    # in a single spring layout pushes them to the frame edge and squeezes the
    # part anyone actually wants to look at into a corner.
    comps = sorted(nx.connected_components(sub), key=len, reverse=True)
    pos = {}
    if comps:
        main = sub.subgraph(comps[0])
        pos = nx.spring_layout(main, seed=7, iterations=160,
                               k=2.2 / max(1, np.sqrt(main.number_of_nodes())))
        for i, comp in enumerate(comps[1:], start=1):
            ang = 2 * np.pi * i / max(1, len(comps) - 1)
            cx, cy = 1.45 * np.cos(ang), 1.45 * np.sin(ang)
            for j, n in enumerate(sorted(comp)):
                pos[n] = (cx + 0.05 * j, cy)

    ex, ey = [], []
    for u, v in sub.edges():
        if u in pos and v in pos:
            ex += [pos[u][0], pos[v][0], None]
            ey += [pos[u][1], pos[v][1], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines",
                             line=dict(width=0.6, color="rgba(255,59,48,.30)"),
                             hoverinfo="none"))
    nodes = [n for n in sub.nodes() if n in pos]
    kinds = [sub.nodes[n].get("kind", "Person") for n in nodes]
    cmap = {"Person": RED, "Vehicle": "#ffd54f", "Transaction": "#ff9800"}
    lvl = dict(zip(CORR["person"], CORR["level"])) if not CORR.empty else {}
    colors = [LEVEL_COLOR.get(lvl.get(n, ""), cmap.get(k, RED)) if k == "Person"
              else cmap.get(k, RED) for n, k in zip(nodes, kinds)]

    # Label only what is readable: the highest-degree nodes and anything the
    # correlation layer raised. Drawing all 82 names produces a smear, not a
    # graph - the labels stop being information and become texture.
    ranked = sorted(nodes, key=lambda n: -sub.degree(n))
    labelled = set(ranked[:14]) | {n for n in nodes if lvl.get(n) == "HIGH"}
    text = [str(n) if n in labelled else "" for n in nodes]

    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
        mode="markers+text", text=text, textposition="top center",
        textfont=dict(size=11, color="#e6dfe1"),
        marker=dict(size=[9 + 1.7 * min(12, sub.degree(n)) for n in nodes],
                    color=colors, line=dict(width=0.8, color="#0b0708")),
        hovertext=[f"{n} · {sub.degree(n)} connections"
                   + (f" · {lvl[n]}" if n in lvl else "") for n in nodes],
        hoverinfo="text"))
    fig.update_layout(**PLOT, height=660, showlegend=False,
                      xaxis_visible=False, yaxis_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Showing {len(nodes)} of {g.number_of_nodes()} nodes. Person nodes are "
               "coloured by assessed signal level where one exists — red HIGH, amber "
               "MEDIUM, green LOW, grey none. Only the highest-degree nodes and every "
               "HIGH subject are labelled; hover for the rest.")

    st.markdown("### Graph Relationship Records")
    rr = [{"source": u, "relationship": ", ".join(sorted(dd["reasons"]))
           if "reasons" in dd else dd.get("relationship", ""), "target": v,
           "observations": dd.get("weight", dd.get("calls", 1))}
          for u, v, dd in sub.edges(data=True)]
    st.dataframe(pd.DataFrame(rr).head(300), use_container_width=True, height=260)

elif MODULE == "Call Network":
    hero("Call Network", "Communication records held in the knowledge graph.")
    calls = D["calls"]
    top = calls["caller"].value_counts().head(15).reset_index()
    top.columns = ["caller", "calls"]
    fig = px.bar(top, x="caller", y="calls", title="Recorded calls by caller")
    fig.update_traces(marker_color=RED)
    fig.update_layout(**PLOT, height=340)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Late-Night Calls")
    st.caption(f"{core.LATE_NIGHT_START:02d}:00 – {core.LATE_NIGHT_END:02d}:00")
    late = calls[calls["late_night"]]
    st.dataframe(core.display(late).head(300), use_container_width=True, height=280)
    st.metric("Late-night calls", f"{len(late):,}",
              f"{len(late)/max(1,len(calls)):.1%} of all calls")
    st.markdown(HITL, unsafe_allow_html=True)

elif MODULE == "Transactions":
    hero("Transaction Intelligence", "Financial transaction records stored in the "
                                     "knowledge graph.")
    t = D["transactions"]
    a, b, c = st.columns(3)
    a.metric("TOTAL VALUE", f"₹{t['amount'].sum():,.0f}")
    b.metric("AVERAGE", f"₹{t['amount'].mean():,.0f}")
    c.metric("MAXIMUM", f"₹{t['amount'].max():,.0f}")

    st.markdown("### High-Value Transactions")
    # default sits at the 90th percentile of this case rather than a fixed
    # rupee figure, so the table is never empty on a corpus of small transfers
    default_hv = float(max(core.HIGH_VALUE, np.quantile(t["amount"], 0.90)))
    mn = st.number_input("Minimum amount", value=round(default_hv, -2), step=5000.0)
    hv = t[t["amount"] >= mn].sort_values("amount", ascending=False)
    st.caption(f"{len(hv)} of {len(t)} transactions at or above this amount "
               f"({len(hv)/max(1,len(t)):.0%})")
    st.dataframe(core.display(hv), use_container_width=True, height=240)

    st.markdown("### Late-Night Transactions")
    st.dataframe(core.display(t[t["late_night"]]).head(200), use_container_width=True, height=220)

    by_sender = t.groupby("sender")["amount"].sum().nlargest(15).reset_index()
    fig = px.bar(by_sender, x="sender", y="amount", title="Transaction value by sender")
    fig.update_traces(marker_color=RED)
    fig.update_layout(**PLOT, height=340)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(HITL, unsafe_allow_html=True)

elif MODULE == "Vehicles":
    hero("Vehicle Intelligence", "Vehicle ownership relationships in the knowledge graph.")
    st.dataframe(D["vehicles"], use_container_width=True, height=380)
    fig = px.pie(D["vehicles"], names="vehicle_type", title="Vehicle types",
                 hole=0.45)
    fig.update_layout(**PLOT, height=340)
    st.plotly_chart(fig, use_container_width=True)

elif MODULE == "Evidence":
    hero("Evidence Desk", "Evidence records associated with investigation data.")
    ev = D["evidence"]
    st.dataframe(ev, use_container_width=True, height=380)
    dist = ev["source_type"].value_counts().reset_index()
    dist.columns = ["source_type", "records"]
    fig = px.pie(dist, names="source_type", values="records",
                 title="Evidence source distribution", hole=0.45)
    fig.update_layout(**PLOT, height=340)
    st.plotly_chart(fig, use_container_width=True)
    total = len(D["calls"]) + len(D["transactions"]) + len(D["vehicles"])
    st.metric("Evidence linkage coverage", f"{len(ev)/max(1,total):.0%}",
              "every call, transaction and vehicle resolves to a source record")

elif MODULE == "Timeline Analysis":
    hero("Timeline Analysis", "Chronological view of recorded events associated with "
                              "a person.")
    who = st.selectbox("Select person", NAMES)
    rows = []
    for _, c in D["calls"][(D["calls"]["caller"] == who) |
                           (D["calls"]["receiver"] == who)].iterrows():
        other = c["receiver"] if c["caller"] == who else c["caller"]
        rows.append({"event_type": "CALL", "timestamp": c["timestamp"],
                     "counterpart": other, "value": c["duration"],
                     "evidence_id": c.get("evidence_id", "")})
    for _, t in D["transactions"][(D["transactions"]["sender"] == who) |
                                  (D["transactions"]["receiver"] == who)].iterrows():
        other = t["receiver"] if t["sender"] == who else t["sender"]
        rows.append({"event_type": "TRANSACTION", "timestamp": t["timestamp"],
                     "counterpart": other, "value": t["amount"],
                     "evidence_id": t.get("evidence_id", "")})
    tl = pd.DataFrame(rows).sort_values("timestamp") if rows else pd.DataFrame()
    st.dataframe(tl, use_container_width=True, height=260)
    if not tl.empty:
        fig = px.scatter(tl, x="timestamp", y="event_type", color="event_type",
                         size=[8] * len(tl), hover_data=["counterpart", "value"],
                         title=f"Timeline — {who}",
                         color_discrete_sequence=[RED, "#ffd54f"])
        fig.update_layout(**PLOT, height=330)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(HITL, unsafe_allow_html=True)

elif MODULE == "Geospatial Analysis":
    hero("Geospatial Event View", "DRISTI geospatial intelligence.")
    loc = D["locations"]
    st.dataframe(loc, use_container_width=True, height=220)
    counts = D["calls"]["location_id"].value_counts().reset_index()
    counts.columns = ["location_id", "events"]
    m = loc.merge(counts, on="location_id", how="left").fillna({"events": 0})
    fig = px.scatter_map(m, lat="latitude", lon="longitude", size="events",
                         hover_name="location_name", size_max=34, zoom=4,
                         color_discrete_sequence=[RED],
                         map_style="carto-darkmatter") \
        if hasattr(px, "scatter_map") else \
        px.scatter_mapbox(m, lat="latitude", lon="longitude", size="events",
                          hover_name="location_name", size_max=34, zoom=4,
                          color_discrete_sequence=[RED],
                          mapbox_style="carto-darkmatter")
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=470,
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(HITL, unsafe_allow_html=True)

elif MODULE == "Analytics":
    hero("DRISTI AI Analytics",
         "Graph statistics · behavioural signals · transaction analysis · "
         "machine-learning indicators")
    st.markdown(HITL, unsafe_allow_html=True)

    st.markdown("### 1 · Network connectivity")
    st.dataframe(CONN.head(20), use_container_width=True, height=280)

    st.markdown("### 2 · AI transaction anomaly detection")
    scored = core.isolation_forest_scores(D["transactions"])
    a, b, c, d_ = st.columns(4)
    a.metric("ANALYSED", len(scored))
    b.metric("POTENTIAL SIGNALS",
             int((scored["analysis_result"] == "Potentially unusual").sum()))
    c.metric("TOTAL VALUE", f"₹{D['transactions']['amount'].sum():,.0f}")
    d_.metric("MODEL", "IsolationForest")
    st.dataframe(scored.nlargest(20, "anomaly_score")[
        ["transaction_id", "sender", "receiver", "amount", "timestamp",
         "anomaly_score", "analysis_result"]], use_container_width=True, height=280)
    st.caption("Scores each transaction on its own features. See the Benchmark "
               "module for how this compares with the typology detectors below.")

    st.markdown("### 3 · Typology detectors")
    st.caption("Patterns that exist across transactions rather than within one — "
               "a per-row outlier model cannot see these.")
    typ = (core.detect_structuring(D["transactions"])
           + core.detect_rapid_passthrough(D["transactions"])
           + core.detect_value_outliers(D["transactions"]))
    if typ:
        st.dataframe(pd.DataFrame([{ "person": t["person"], "detector": t["detector"],
                                     "description": t["description"],
                                     "score": round(t["score"], 3)} for t in typ]),
                     use_container_width=True, height=260)
    else:
        st.info("No typology pattern detected in this corpus.")

elif MODULE == "Multi-Signal Correlation":
    hero("Multi-Signal Correlation",
         "A subject is raised only where DISTINCT analytical families agree.")
    st.markdown(
        '<div class="note"><b>Why this module exists:</b> every analytic here produces '
        'false positives. What makes a subject worth an officer\'s time is not a high '
        'score on one dimension, it is agreement between dimensions whose errors are '
        'drawn from different sources. Subjects supported by a single family are '
        'shown, but not '
        'escalated.</div>', unsafe_allow_html=True)
    if CORR.empty:
        st.info("No detections.")
    else:
        a, b, c = st.columns(3)
        a.metric("HIGH", int((CORR["level"] == "HIGH").sum()))
        b.metric("MEDIUM", int((CORR["level"] == "MEDIUM").sum()))
        c.metric("LOW", int((CORR["level"] == "LOW").sum()))
        st.dataframe(CORR, use_container_width=True, height=420)
        # Colour runs weak -> strong with the number of agreeing families.
        # Colouring by level name put green on the single-family bar, which
        # reads as "fine" when it is in fact the least corroborated case.
        counts = (CORR.groupby("families").size().reset_index(name="subjects")
                  .sort_values("families"))
        shade = {1: "#6b6f78", 2: AMBER, 3: RED, 4: RED, 5: RED}
        fig = px.bar(counts, x="families", y="subjects", text="subjects",
                     title="Subjects by number of distinct corroborating families")
        fig.update_traces(marker_color=[shade.get(int(f), DIM)
                                        for f in counts["families"]])
        fig.update_xaxes(dtick=1, title="distinct analytical families in agreement")
        fig.update_layout(**PLOT, height=330)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Grey = one family only, and therefore not escalated. "
                   "Amber = two. Red = three or more.")

elif MODULE == "Evidence Chain":
    hero("Evidence Chain",
         "Finding → why it was surfaced → graph context → relationships → source record.")
    who = st.selectbox("Select a subject",
                       list(CORR["person"]) if not CORR.empty else NAMES)
    ch = core.evidence_chain(who, DETECTIONS, CORR, PG, D)

    st.markdown(f'<div class="chain"><div class="lbl">1 · INSIGHT</div>'
                f'{badge(ch["level"])} &nbsp; {ch["statement"]}</div>',
                unsafe_allow_html=True)

    html = '<div class="chain"><div class="lbl">2 · WHY IT WAS SURFACED</div>'
    for r in ch["reasons"]:
        html += (f'<div>• <b>[{r["family"]}]</b> {r["description"]} '
                 f'<span class="mono">(score {r["score"]:.2f}, detector '
                 f'{r["detector"]})</span></div>')
    st.markdown(html + "</div>", unsafe_allow_html=True)

    html = '<div class="chain"><div class="lbl">3 · GRAPH CONTEXT</div>'
    for n in ch["neighbours"][:8]:
        html += (f'<div>• {n["person"]} <span class="mono">{n["why"]} · '
                 f'{n["observations"]} observation(s)</span></div>')
    st.markdown(html + "</div>", unsafe_allow_html=True)

    html = '<div class="chain"><div class="lbl">4 · SOURCE RECORDS</div>'
    for rec in ch["records"]:
        html += (f'<div class="card"><span class="mono">{rec["evidence_id"]} · '
                 f'{rec["source_type"]} · {rec["source_file"]}</span><br>'
                 f'{rec["description"]}</div>')
    if not ch["records"]:
        html += '<div class="mono">No source record attached to this finding.</div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)
    st.markdown(HITL, unsafe_allow_html=True)

elif MODULE == "Benchmark":
    hero("DRISTI-Bench", "The console scoring its own analytics against a known "
                         "answer key.")
    if not TRUTH:
        st.warning("`_ground_truth.json` is not present in the data folder, so nothing "
                   "can be scored. It ships with the synthetic data pack.")
        st.stop()

    B = core.run_benchmark(D, PG, DETECTIONS, CORR, TRUTH)
    c = B["corpus"]
    st.caption(f"{c['persons']} persons · {c['calls']:,} calls · {c['transactions']} "
               f"transactions · {c['syndicate']} in the syndicate "
               f"(base rate {B['base_rate']:.1%})")

    a, b, cc, d_ = st.columns(4)
    a.metric("Key individuals P@5", f"{B['key_individuals']['precision_at_5']:.2f}",
             f"baseline {B['base_rate']:.2f}")
    b.metric("Key individuals P@10", f"{B['key_individuals']['precision_at_10']:.2f}")
    cc.metric("Evidence coverage", f"{B['evidence_coverage']:.0%}")
    d_.metric("Isolation Forest AUROC", f"{B['isolation_forest']['auroc']:.2f}")

    st.markdown("### Anomaly detection — model versus typology")
    comp = pd.DataFrame([
        {"method": "Isolation Forest (per-transaction features)",
         **{k: B["isolation_forest"][k] for k in ("precision", "recall", "f1")}},
        {"method": "Structuring typology detector (across transactions)",
         **{k: B["structuring_typology"][k] for k in ("precision", "recall", "f1")}},
    ])
    st.dataframe(comp, use_container_width=True)
    st.markdown(
        '<div class="note"><b>The finding:</b> the per-transaction model scores far '
        'lower, and that is not a defect in the model. Structuring is built to look '
        'ordinary one transaction at a time — the pattern only exists across rows, so '
        'no per-row model can see it. Measuring this is how we knew to add typology '
        'detectors rather than a larger model.</div>', unsafe_allow_html=True)

    st.markdown("### Does corroboration help?")
    ab = B["corroboration"]
    tab = pd.DataFrame([
        {"subject raised on": "Random pick (base rate)", "precision": ab["random_baseline"]},
        {"subject raised on": "One family only", "precision": ab["one_family"]},
        {"subject raised on": "Two or more families", "precision": ab["two_plus"]},
        {"subject raised on": "Three or more families", "precision": ab["three_plus"]},
    ])
    fig = px.bar(tab, x="precision", y="subject raised on", orientation="h",
                 range_x=[0, 1], text="precision")
    fig.update_traces(marker_color=[DIM, AMBER, RED, RED])
    fig.update_layout(**PLOT, height=300, yaxis_title="", xaxis_title="precision")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Recall of the syndicate at two or more families: "
               f"{ab['recall_two_plus']:.0%}")

    with st.expander("Full benchmark JSON"):
        st.json(B)
    st.markdown(
        '<div class="note">Measured on a synthetic corpus with a known answer key. It '
        'shows the pipeline recovers a known structure and lets design choices be '
        'compared under identical conditions. It is an upper bound on real-world '
        'performance, not a prediction of it.</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("🔥 DRISTI | SIH 2026 | AI-Powered Investigation Intelligence · "
           "Knowledge Graph · AI Analytics · Timeline · Geospatial · Human-in-the-loop")
