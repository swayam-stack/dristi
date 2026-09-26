#!/usr/bin/env python3
"""
Figures for the DRISTI idea-submission deck.

  fig_flow.png   slide 2 — fragmented evidence to a verified investigative signal
  fig_arch.png   slide 3 — full architecture and where each component sits

Colour carries meaning in both: green is running in the console today, amber
dashed is designed and scheduled. Anything we cannot open on the prototype is
amber. Graph ML is drawn on its own branch, deliberately bypassing the
correlation gate — a model prediction is a lead for an officer to chase, never
one of the independent families that agreement is counted over.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")

INK = "#0F1420"
MUTED = "#5A6273"
GREEN, GREENBG = "#0E6B45", "#E8F5EE"
AMBER, AMBERBG = "#B45309", "#FDF3E3"
RED, REDBG = "#C2261D", "#FDECEB"
BLUE, BLUEBG = "#1E4E8C", "#EAF1FA"
LILAC = "#EFEDF8"

STYLE = {"run": (GREENBG, GREEN, "solid"),
         "next": (AMBERBG, AMBER, (0, (4, 2.4))),
         "core": (REDBG, RED, "solid"),
         "flat": (BLUEBG, BLUE, "solid"),
         "grey": ("#F1F3F6", "#9AA1AE", "solid")}


def mkbox(ax, x, y, w, h, title, sub=None, kind="run", tsize=13, ssize=10.5,
          sub2=None, sub2col=AMBER, lsp=1.0, centre=False):
    fc, ec, ls = STYLE[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=0.10",
                                fc=fc, ec=ec, lw=1.9, linestyle=ls, zorder=2))
    tx, ha = (x + w / 2, "center") if centre else (x + 0.20, "left")
    ty = y + h - 0.30 if sub else y + h / 2
    ax.text(tx, ty, title, fontsize=tsize, fontweight="bold", color=INK,
            va="center", ha=ha, zorder=3, linespacing=1.2)
    if sub:
        ax.text(tx, ty - 0.34, sub, fontsize=ssize, color=MUTED, va="center",
                ha=ha, zorder=3, linespacing=lsp)
    if sub2:
        ax.text(tx, ty - 0.66, sub2, fontsize=ssize, color=sub2col, va="center",
                ha=ha, zorder=3, fontweight="bold", linespacing=lsp)


def down(ax, x, y0, y1, color="#9AA1AE", lw=1.5):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>",
                                 mutation_scale=17, lw=lw, color=color, zorder=1))


# ======================================================== SLIDE 2 — THE FLOW
def flow():
    W, H = 7.6, 8.62
    fig, ax = plt.subplots(figsize=(W, H), dpi=150)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    fig.patch.set_facecolor("white")

    x, w = 0.22, W - 0.44
    stages = [
        ("FRAGMENTED EVIDENCE",
         "CDR  ·  Bank  ·  RTO  ·  FIR  ·  Location  ·  Evidence files", "grey", 0.90),
        ("UNIFIED CASE GRAPH",
         "Persons · Phones · Vehicles · Transactions · Locations · Evidence\n"
         "every relationship carries the record it came from", "core", 1.06),
        ("FIVE ANALYTICAL LENSES",
         "Network  ·  Communication  ·  Financial  ·  Temporal  ·  Geospatial\n"
         "three of these emit detectors into the benchmark today", "run", 1.06),
        ("MULTI-SIGNAL CORRELATION",
         "raised only where DISTINCT analytical families agree\n"
         "\u22652 families: 66.7% precision @ 60% recall  (base rate 24.4%)", "run", 1.06),
        ("EVIDENCE-BACKED INVESTIGATIVE SIGNAL",
         "finding  →  why  →  which record says so", "run", 0.90),
        ("HUMAN VERIFICATION",
         "an indicator, never a determination of criminality", "core", 0.90),
    ]
    gap = 0.52
    total = sum(h for *_, h in stages) + gap * (len(stages) - 1)
    y = H - 0.15 - total
    ys = []
    for title, sub, kind, h in reversed(stages):
        ys.append((y, h))
        mkbox(ax, x, y, w, h, title, sub, kind, tsize=13.5, ssize=10.5,
              lsp=1.35, centre=True)
        y += h + gap
    for (y0, h0), (y1, _) in zip(ys, ys[1:]):
        down(ax, W / 2, y1 - 0.06, y0 + h0 + 0.06)

    fig.savefig(os.path.join(OUT, "fig_flow.png"), bbox_inches="tight",
                facecolor="white", pad_inches=0.10)
    print("wrote fig_flow.png")


# ================================================ SLIDE 3 — THE ARCHITECTURE
def arch():
    W, H = 23.4, 12.9
    X0, XW = 2.55, W - 2.85
    fig, ax = plt.subplots(figsize=(W, H), dpi=150)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    fig.patch.set_facecolor("white")

    def box(*a, **k):
        mkbox(ax, *a, **k)

    def band(y, t):
        ax.text(X0, y, t, fontsize=11, fontweight="bold", color=MUTED,
                va="center", ha="left")

    ax.text(0.28, H - 0.42, "DRISTI — system architecture", fontsize=25,
            fontweight="bold", color=INK, va="center")
    ax.text(0.28, H - 0.86,
            "One case-level knowledge graph in Neo4j, read by separate analytical "
            "modules — every finding tied back to its source record, every raise "
            "requiring corroboration, an investigator in front of the output.",
            fontsize=12.5, color=MUTED, va="center")
    for lx, lab, kind in [(0.30, "running in the console today", "run"),
                          (4.15, "designed, next phase", "next"),
                          (7.05, "the backbone", "core")]:
        fc, ec, ls = STYLE[kind]
        ax.add_patch(FancyBboxPatch((lx, H - 1.42), 0.42, 0.24,
                                    boxstyle="round,pad=0,rounding_size=0.06",
                                    fc=fc, ec=ec, lw=1.6, linestyle=ls))
        ax.text(lx + 0.54, H - 1.30, lab, fontsize=11, color=INK, va="center")

    # safeguards rail
    ax.add_patch(FancyBboxPatch((0.28, 0.22), 1.92, H - 2.02,
                                boxstyle="round,pad=0,rounding_size=0.10",
                                fc=LILAC, ec="#C9C4E4", lw=1.5, zorder=1))
    ax.text(1.24, H - 2.02, "SAFEGUARDS", fontsize=11, fontweight="bold",
            color=MUTED, ha="center", va="center")
    rail = [("Human-in-the-loop\nverification", "RUNNING", GREEN),
            ("Analytical indicator,\nnever a conclusion", "RUNNING", GREEN),
            ("Evidence linkage\non every record", "RUNNING", GREEN),
            ("Corroboration gate\nbefore any raise", "RUNNING", GREEN),
            ("Role-based access\n+ case scoping", "NEXT", AMBER),
            ("Tamper-evident\naudit log", "NEXT", AMBER),
            ("Field-level\nredaction", "NEXT", AMBER)]
    ry = H - 2.80
    for t, st, c in rail:
        ax.text(1.24, ry, t, fontsize=10, color=BLUE, ha="center", va="center",
                linespacing=1.35)
        ax.text(1.24, ry - 0.36, st, fontsize=9.2, fontweight="bold", color=c,
                ha="center", va="center")
        ry -= 1.14
    ax.text(1.24, 0.46, "ALL LAYERS", fontsize=10, fontweight="bold",
            color=MUTED, ha="center", va="center")

    # 1 sources
    band(H - 1.92, "1 · INVESTIGATION DATA")
    w4 = (XW - 3 * 0.16) / 4
    for i, (t, s, k) in enumerate([
            ("Structured records", "CDR · transactions · RTO · persons · locations", "run"),
            ("Documents", "FIR · case diary · statements · intelligence", "next"),
            ("Multimedia", "CCTV · images · audio → OCR / CV / ASR", "next"),
            ("Federation with CCTNS / ICJS", "read-only connectors, not another silo", "next")]):
        box(X0 + i * (w4 + 0.16), H - 2.92, w4, 0.78, t, s, k, tsize=12.5, ssize=10)
    down(ax, X0 + XW / 2, H - 2.96, H - 3.36)

    # 2 ingestion
    band(H - 3.56, "2 · INGESTION, EXTRACTION AND RESOLUTION")
    w3 = (XW - 2 * 0.16) / 3
    for i, (t, s, k) in enumerate([
            ("Ingestion and normalisation", "CSV → typed nodes and relationships, via Cypher", "run"),
            ("Entity / relation extraction", "deterministic patterns first, Indic NER after", "next"),
            ("Entity resolution", "“Ravi Kumar” · “R. Kumar” → one reversible identity", "next")]):
        box(X0 + i * (w3 + 0.16), H - 4.52, w3, 0.78, t, s, k, tsize=12.5, ssize=10)
    down(ax, X0 + XW / 2, H - 4.56, H - 4.96)

    # 3 backbone
    band(H - 5.16, "3 · THE BACKBONE")
    box(X0, H - 6.50, XW, 1.16, "PROVENANCE-AWARE EVIDENCE GRAPH — Neo4j, one graph per case",
        "Person · Vehicle · Transaction · Call · Location · Evidence — heterogeneous entities and "
        "the relationships between them (CALLED, OWNS, SENT, SEEN_AT)",
        "core", tsize=15, ssize=11,
        sub2="Every relationship carries its evidence record, confidence and source.   "
             "Next: extraction method and epistemic status on the edge.")
    down(ax, X0 + XW / 2, H - 6.54, H - 6.94)

    # 4 lenses (five only - Graph ML is deliberately not one of them)
    band(H - 7.14, "4 · FIVE ANALYTICAL LENSES — different questions of the same graph")
    w5 = (XW - 4 * 0.14) / 5
    for i, (t, s) in enumerate([
            ("Network", "eigenvector centrality —\nfamily: structural"),
            ("Communication", "late-night contact —\nfamily: communication"),
            ("Financial", "value, structuring, flow —\nfamily: financial"),
            ("Temporal", "per-subject chronology —\nno detector family yet"),
            ("Geospatial", "locations and movement —\nno detector family yet")]):
        box(X0 + i * (w5 + 0.14), H - 8.16, w5, 0.90, t, s, "run", tsize=12.5,
            ssize=9.8, lsp=1.35)
    box(X0, H - 9.02, XW, 0.80,
        "Behavioural anomaly detection — Isolation Forest  +  FIU-IND typology detectors: "
        "structuring, rapid pass-through, value outliers",
        "both score the same transactions against the answer key — the typology detectors reach "
        "F1 0.89 where the per-transaction model reaches 0.12", "run", tsize=12.5, ssize=10)

    # 5 the gate, with Graph ML routed around it
    band(H - 9.24, "5 · CORRELATION — the gate")
    gw = XW * 0.705
    down(ax, X0 + gw / 2, H - 9.06, H - 9.44)
    box(X0, H - 10.30, gw, 0.86,
        "MULTI-SIGNAL CORRELATION — raise a subject only where DISTINCT analytical families agree",
        "three detector families reach the gate today — financial, communication, structural.  "
        "\u22652 families: 66.7% precision @ 60% recall against a 24.4% base rate.",
        "run", tsize=13, ssize=10)
    box(X0 + gw + 0.24, H - 10.30, XW - gw - 0.24, 0.86,
        "Graph ML — GraphSAGE link prediction",
        "a CANDIDATE LEAD routed AROUND the gate\n"
        "never a corroborating family · not in the benchmark",
        "next", tsize=11.5, ssize=9.6, lsp=1.32)

    # 6 evidence and evaluation
    band(H - 10.54, "6 · EVIDENCE AND EVALUATION")
    down(ax, X0 + gw / 2, H - 10.34, H - 10.72)
    box(X0, H - 11.42, XW * 0.49, 0.74, "Evidence chain — finding → why → source record",
        "every raise expands to the source file and row behind it", "run",
        tsize=11.5, ssize=10)
    box(X0 + XW * 0.51, H - 11.42, XW * 0.49, 0.74,
        "Benchmark harness — scored against a labelled answer key",
        "precision@k, F1, AUROC and corroboration lift, recomputed in the console",
        "run", tsize=11.5, ssize=10)

    # 7 console - both the gated output and the ML leads land here
    down(ax, X0 + gw / 2, H - 11.46, H - 11.84)
    down(ax, X0 + gw + 0.24 + (XW - gw - 0.24) / 2, H - 10.34, H - 11.84)
    box(X0, 0.30, XW, 0.76, "INVESTIGATOR CONSOLE  —  13 modules",
        "dashboard · persons · network · calls · transactions · vehicles · evidence · timeline · "
        "geospatial · analytics · multi-signal correlation · evidence chain · benchmark",
        "flat", tsize=13, ssize=10)

    fig.savefig(os.path.join(OUT, "fig_arch.png"), bbox_inches="tight",
                facecolor="white", pad_inches=0.14)
    print("wrote fig_arch.png")


if __name__ == "__main__":
    flow()
    arch()
