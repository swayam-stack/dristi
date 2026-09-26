#!/usr/bin/env python3
"""
Write the deck's benchmark JSON straight out of dristi_core.

Why this exists: the deck used to read a JSON produced by a SECOND, standalone
benchmark script that carried its own copy of the family logic. Two
implementations of the same measurement will disagree the moment one of them
is edited, and the one on the slide is the one nobody re-runs. This script
makes the console's own functions the single source: whatever the Benchmark
module shows an officer is exactly what the slide prints.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dristi_core as C

HERE = os.path.dirname(os.path.abspath(__file__))
# Written next to the deck build scripts. Override with DRISTI_BENCH_OUT if the
# deck lives somewhere else.
DEST = os.environ.get("DRISTI_BENCH_OUT",
                      os.path.join(HERE, "deck", "dristi_benchmark.json"))


def main() -> None:
    d = C.load_data()
    pg = C.build_person_graph(d)
    dets = C.run_all_detectors(d, pg)
    corr = C.correlate(dets)
    truth = json.load(open(os.path.join(HERE, "data", "_ground_truth.json"),
                           encoding="utf-8"))
    b = C.run_benchmark(d, pg, dets, corr, truth)

    synd = set(truth["syndicate_members"])
    n_persons = b["corpus"]["persons"]
    two = {r["person"] for _, r in corr.iterrows() if r["families"] >= 2}
    tp = len(two & synd)
    fp = len(two - synd)
    fn = len(synd - two)
    tn = n_persons - tp - fp - fn
    assert tp + fp + fn + tn == n_persons, "confusion matrix must cover the corpus"

    out = dict(b)
    # The deck quotes the >=2 gate and nothing else, so its full confusion
    # matrix travels with the file rather than being recomputed by hand.
    out["gate_two_plus"] = {
        "flagged": len(two), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(tp / len(two), 4),
        "recall": round(tp / len(synd), 4),
        "evaluated_population": n_persons,
        "ground_truth_positives": len(synd),
    }
    # run_benchmark's corpus block omits these two; the deck quotes both, so
    # they are counted here rather than typed into a slide.
    out["corpus"]["evidence"] = len(d["evidence"])
    out["corpus"]["locations"] = len(d["locations"])
    out["families_in_gate"] = list(C.BENCHMARK_FAMILIES)
    out["level_counts"] = {lv: int((corr["level"] == lv).sum())
                           for lv in ("HIGH", "MEDIUM", "LOW", "NONE")}

    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    with open(DEST, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", DEST)
    print(json.dumps(out["gate_two_plus"], indent=1))
    print("levels:", out["level_counts"])


if __name__ == "__main__":
    main()
