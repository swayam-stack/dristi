# DRISTI — Evidence-Centric Criminal Network Intelligence System

Smart India Hackathon 2026 · Problem Statement **26189** — AI-Powered Criminal
Network Analysis System · Ministry of Home Affairs / NCRB · Theme: Blockchain &
Cybersecurity · **Team Innovexa**

One case graph. Many analytical lenses. Every finding evidenced.

---

## What this is

An investigation console that loads CDR, banking, RTO, location and evidence
records into a single case-level knowledge graph, runs independent analytical
modules over it, and raises a subject only where **distinct analytical
families** of evidence agree — with every finding traceable back to the source
record that produced it.

Three things distinguish it from a dashboard over a graph database:

1. **Evidence linkage is a property of the data model**, not a reporting
   feature. Every relationship carries the evidence record it came from.
2. **A subject is raised only on corroboration.** One detector firing alone is
   a lead, not a finding.
3. **It is measured, not demonstrated.** A labelled synthetic corpus with a
   known answer key lets every design choice be scored — including the ones
   that failed.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
streamlit run app.py
```

Opens on `http://localhost:8501`. Thirteen modules in the left sidebar. Neo4j
is optional — see `RUN.md`.

## Measured results

Everything below is recomputed by `export_benchmark.py` from the code in this
repository, scored against `data/_ground_truth.json`. No number is typed in by
hand.

Corpus: **82 persons** (20 in the syndicate), 2,522 calls, 254 transactions,
35 vehicles, 14 locations, 2,811 evidence records. Base rate 20/82 = **24.4%**.

| Measurement | Result |
|---|---|
| **Correlation gate — ≥2 distinct analytical families** | **66.7% precision @ 60% recall** (18 flagged: 12 TP, 6 FP, 8 FN, 56 TN) |
| Key individuals, unweighted eigenvector centrality | P@5 · P@10 · P@20 = 1.00 |
| Transaction anomaly — Isolation Forest (per-row) | F1 0.1154 · AUROC 0.5132 |
| Transaction anomaly — structuring typology detector | P 0.857 · R 0.923 · **F1 0.8889** |
| Evidence linkage coverage | 100% |

**These numbers come from a synthetic corpus whose generator we wrote.** They
are controlled prototype evidence that the pipeline recovers a known structure
and that design choices can be compared under identical conditions. They are
an upper bound, not a prediction of field performance.

### Three findings worth reading before you use this

**The per-row anomaly model scores F1 0.12, and that is correct behaviour.**
Isolation Forest scores each transaction on its own features. Structuring is
*built* to survive exactly that test — six transfers of ₹47,000–49,500 are
unremarkable one at a time. The pattern exists only *across* rows. The typology
detector, which looks across rows, gets 0.89 on the same data. That gap is the
argument for FIU-IND-style typologies over a bigger model.

**Unweighted eigenvector centrality, not weighted.** The edge weight counts how
many times a pair was observed — that is volume, not tie strength. Weighted, it
puts *zero* syndicate members in the top 20. Unweighted, twenty out of twenty.

**One detector firing alone is worse than guessing.** A single family gives
0.30 precision against a 0.244 base rate. Two or more distinct families gives
0.667. That is the entire case for the correlation gate, measured on our own
data rather than asserted.

## Repository layout

```
app.py                  all UI, no computation — one block per module
dristi_core.py          all computation, no UI — loaders, detectors,
                        correlation gate, evidence chain, benchmark
dristi_neo4j.py         optional Neo4j loader; everything works without it
export_benchmark.py     writes deck/dristi_benchmark.json from dristi_core
data/                   six CSVs + _ground_truth.json (the answer key)
deck/                   SIH idea-submission deck and its build scripts
RUN.md                  step-by-step build, Neo4j setup, troubleshooting
```

The UI/computation split matters: the benchmark scores the same functions the
screens call, so the numbers on the Benchmark page are the numbers the console
actually produces.

## Analytical lenses vs detector families

The console has **five analytical lenses** — Network, Communication, Financial,
Temporal, Geospatial. **Three of them currently emit detector families** into
the correlation gate: `structural`, `communication`, `financial`. Temporal and
geospatial are visualised but do not yet produce a scored detector.

`financial` deliberately covers structuring, value outliers, rapid
pass-through *and* high-value transfers as one family, because all four read
the same transactions table. Counting them separately would let one source of
evidence vote twice at the gate — the precise failure the gate exists to
prevent.

GraphSAGE link prediction is **outside** the gate by design: a model prediction
is a candidate lead for an officer, never a corroborating family. It is not
implemented yet and contributes nothing to the benchmark.

## Reproducing the numbers

```bash
python export_benchmark.py
```

Prints the confusion matrix and writes `deck/dristi_benchmark.json`. The deck
build script reads that file, so a slide and the console cannot disagree.

To rebuild the deck you also need the official SIH template; set its path at
the top of `deck/build_dristi_ppt.py`.

## Status

Running in the console today: case graph, network visualisation, entity
traversal, call/transaction/timeline/geospatial analytics, Evidence Desk,
Isolation Forest, FIU-IND typology detectors, the correlation gate, the
evidence chain, and the benchmark harness.

Designed and scheduled: entity resolution for Indic name variants, IndicNER /
MuRIL over FIR text, GraphSAGE link prediction, RBAC with case-level scoping
and a tamper-evident audit log.

## A note on responsible use

Connectivity, transaction patterns, late-night activity and anomaly scores are
**analytical indicators**. They do not establish criminal activity. Every
module says so on screen, a human verification step sits in front of every
output, and nothing here should be read as a determination about any person.

Anomaly ≠ criminality.
