# DRISTI console — build and run guide

Step by step. Do them in order; each step leaves you with something that works,
so if a later step breaks you can still demo the earlier one.

---

## Step 1 — Get it running (10 minutes, no Neo4j)

Unzip `dristi_app` anywhere. Open a Command Prompt in that folder.

```
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

It opens `http://localhost:8501` by itself. Left sidebar has all thirteen
modules.

Streamlit is far more reliable on Windows than the uvicorn setup that kept
exiting — it runs its own server and does not need hypercorn.

**Stop here and click every module once.** If all thirteen render, you have a
working demo and everything after this is improvement, not rescue.

---

## Step 2 — Understand the three files (15 minutes)

Only three files matter. Read them in this order.

**`dristi_core.py`** — all the computation, no UI. Data loading, both graphs,
every detector, the correlation gate, the evidence chain, the benchmark.
Thresholds are constants at the top, in one place, so the screens and the
benchmark cannot drift apart:

```python
LATE_NIGHT_START, LATE_NIGHT_END = 22, 5
HIGH_VALUE = 60_000
CASH_REPORTING_THRESHOLD = 50_000
```

**`app.py`** — all the UI, no computation. The sidebar, then one `elif MODULE ==
"..."` block per screen. To change a screen, find its block. To add one, add a
name to the `st.radio` list and a matching block.

**`dristi_neo4j.py`** — optional. Everything works without it.

The split matters: because the benchmark scores the same functions the screens
call, the numbers on the Benchmark page are the numbers the console actually
produces.

---

## Step 3 — Add Neo4j (30 minutes, optional but worth it)

The console works on its in-process graph. Neo4j makes "NEO4J KNOWLEDGE GRAPH
CONNECTED" literally true and lets you show the graph in Neo4j Browser.

1. Install **Neo4j Desktop** from neo4j.com/download.
2. Create a local DBMS, set a password, press Start.
3. In the app folder create `.streamlit/secrets.toml`:

```toml
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your-password"
```

4. Load the graph:

```
python dristi_neo4j.py --load
```

5. Restart Streamlit. The sidebar caption switches to
   **NEO4J KNOWLEDGE GRAPH CONNECTED**.

Every relationship written to Neo4j carries `evidence_id`, `confidence` and
`source` — that is your provenance pillar, in the database, not on a slide.

Try this in Neo4j Browser, it demos well:

```cypher
MATCH (a:Person)-[c:CALLED]->(b:Person)
RETURN a.name, b.name, c.timestamp, c.evidence_id
LIMIT 25
```

---

## Step 4 — Know what the numbers mean (do this before you present)

Open the **Benchmark** module. It scores the console's own analytics against
`data/_ground_truth.json`.

| What it measures | Result on this corpus |
|---|---|
| Key individuals, eigenvector centrality | P@5 1.00 · P@10 1.00 · P@20 1.00 |
| Key individuals, raw connection count (what the console displays) | P@5 1.00 · P@10 1.00 · P@20 0.75 |
| Isolation Forest on transactions | F1 0.12 · AUROC 0.51 |
| Structuring typology detector | precision 0.857 · recall 0.923 · **F1 0.889** |
| Evidence linkage | 100% |
| Corroboration gate: ≥2 distinct analytical families | **66.7% precision @ 60% recall** (base rate 24.4%) |

**Three things you must be able to explain.**

**The Isolation Forest scores 0.12 and that is correct behaviour.** It scores
each transaction on its own features. Structuring is designed to survive that:
six transfers of ₹47,000–49,500 are unremarkable one at a time. The pattern
exists only across rows. The typology detector, which looks across rows, gets
0.89 on the same data. Present this as a finding, not a weakness — it is why
the roadmap says typology detectors rather than a bigger model.

**Unweighted eigenvector centrality, not weighted.** The edge weight counts how
many times a pair was observed, which is volume, not tie strength. Weighted, it
puts *zero* syndicate members in the top 20. Unweighted, it puts twenty out of
twenty. If someone asks why not weighted, that is the answer.

**A single indicator is barely better than guessing.** One family gives 0.30
against a 0.244 base rate; two or more distinct analytical families gives 0.667
at 60% recall (18 flagged: 12 TP, 6 FP). Three families flags one person, so it
is not reported as a performance claim.
That is the whole case for the correlation gate, measured on your own data.

---

## Step 5 — Swap in your own data

The console reads six CSVs from `data/`. Keep the column names and it will read
anything:

```
persons.csv       person_id, name, age, address, phone
calls.csv         caller, receiver, timestamp, duration, location_id, evidence_id
transactions.csv  transaction_id, sender, receiver, amount, timestamp, location_id, evidence_id
vehicles.csv      vehicle_id, registration, owner, vehicle_type, evidence_id
locations.csv     location_id, location_name, latitude, longitude
evidence.csv      evidence_id, source_type, source_file, description
```

`caller`, `receiver`, `sender`, `owner` are person **names**, matching the
original prototype's loader.

The Benchmark module needs `_ground_truth.json`. Without it that one module
shows a warning and everything else works normally.

To regenerate the synthetic case with a different seed, use
`dristi_data_export.py` from the data pack.

---

## Step 6 — What to add next, in order of value

1. **Entity resolution.** Right now one person is one row. Real data has
   "Ravi Kumar", "R. Kumar" and "Kumar, Ravi" as three. This is the change that
   gets harder the longer you leave it, because every module assumes a stable
   name.
2. **NLP over FIR text.** Deterministic patterns first (phone numbers, RTO
   marks, account tokens), a locality gazetteer for places, an Indic NER model
   for names last.
3. **Link prediction.** Only after 1 and 2 — a GNN on a graph with broken
   identity learns the wrong thing.

---

## If something breaks

- **`ModuleNotFoundError`** → the virtual environment is not active. Check for
  `(.venv)` at the start of your prompt.
- **Blank page / stale numbers after changing data** → press **C** in the app,
  or the ⋮ menu → *Clear cache*, then **R** to rerun. Streamlit caches the data
  load and the analytics.
- **"No data found in data/"** → you are running `streamlit run app.py` from the
  wrong folder. `cd` into the app folder first.
- **Neo4j "unreachable"** → the DBMS is not started in Neo4j Desktop, or the
  password in `secrets.toml` is wrong. The console keeps working regardless.
- **Map does not render** → older Plotly. `pip install -U plotly`.
