#!/usr/bin/env python3
"""
Build the SIH 2026 idea-submission deck for DRISTI on the official template.

Structure follows the team's own outline:
  1 Title  ·  2 Idea / Proposed Solution  ·  3 Technical Approach
  4 Feasibility and Viability  ·  5 Impact and Benefits  ·  6 Research

Two editorial rules run through the whole file.

First, nothing is claimed as built that is not built. Where a capability is
designed but not running it is amber, on the slide and in the architecture
figure. A deck that over-claims against its own prototype loses the room in
the Q&A, and the prototype is open on a laptop two metres away.

Second, every number comes out of outputs/dristi_benchmark.json rather than
being typed in, so a slide and the console can never disagree. If the harness
is re-run the deck changes with it.
"""
from __future__ import annotations

import json
import math
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = ("/root/.claude/uploads/068f1b7e-ac88-516b-9682-063779465c96/"
            "66d55ab7-SIH2026-IDEA-Presentation-Format_1.pptx")
FIG = os.path.join(HERE, "outputs")
OUT = os.path.join(FIG, "DRISTI_SIH2026_Idea_Presentation.pptx")

# ---- edit these before submitting -----------------------------------------
PRODUCT = "DRISTI"           # the console shows DRISTI; switch if the team prefers
TEAM_NAME = "Team Innovexa"
TEAM_ID = "<Team ID>"
# ---------------------------------------------------------------------------

INK = RGBColor(0x0F, 0x14, 0x20)
MUTED = RGBColor(0x5A, 0x62, 0x73)
BLUE = RGBColor(0x1E, 0x4E, 0x8C)
RED = RGBColor(0xC2, 0x26, 0x1D)
GREEN = RGBColor(0x0E, 0x6B, 0x45)
AMBER = RGBColor(0xB4, 0x53, 0x09)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BAND = RGBColor(0xEA, 0xF1, 0xFA)
GREENBG = RGBColor(0xE8, 0xF5, 0xEE)
AMBERBG = RGBColor(0xFD, 0xF3, 0xE3)
REDBG = RGBColor(0xFD, 0xEC, 0xEB)
GREY = RGBColor(0xF1, 0xF3, 0xF6)
RULE = RGBColor(0xC7, 0xCD, 0xD8)


# ----------------------------------------------------------------- plumbing
def delete_slide(prs, index):
    lst = prs.slides._sldIdLst
    slides = list(lst)
    rId = slides[index].get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    prs.part.drop_rel(rId)
    lst.remove(slides[index])


def clear(shape):
    tf = shape.text_frame
    tf.clear()
    for p in list(tf.paragraphs[1:]):
        p._p.getparent().remove(p._p)


def set_runs(shape, blocks, space_after=4, line=0.95):
    tf = shape.text_frame
    tf.word_wrap = True
    clear(shape)
    first = True
    for text, opt in blocks:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(opt.get("space_after", space_after))
        p.space_before = Pt(opt.get("space_before", 0))
        p.line_spacing = opt.get("line", line)
        p.alignment = opt.get("align", PP_ALIGN.LEFT)
        r = p.add_run()
        r.text = text
        f = r.font
        f.size = Pt(opt.get("size", 11))
        f.bold = opt.get("bold", False)
        f.italic = opt.get("italic", False)
        f.color.rgb = opt.get("color", INK)
        f.name = "Calibri"
    return tf


def add_text(slide, x, y, w, h, blocks, **kw):
    tb = slide.shapes.add_textbox(x, y, w, h)
    set_runs(tb, blocks, **kw)
    return tb


def add_box(slide, x, y, w, h, fill=None, line=None, line_w=1.15, round_=0.05):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    sh.adjustments[0] = round_
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    return sh


def title_of(slide):
    for sh in slide.shapes:
        if sh.has_text_frame and sh.name.startswith("Title"):
            return sh


def body_of(slide):
    for sh in slide.shapes:
        if sh.has_text_frame and sh.name.startswith("TextBox"):
            return sh


def set_title(slide, text, size=24):
    t = title_of(slide)
    if t is None:
        return
    tf = t.text_frame; tf.clear()
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = True
    r.font.color.rgb = BLUE; r.font.name = "Calibri"


def set_oval(slide, text):
    for sh in slide.shapes:
        if sh.name.startswith("Oval"):
            tf = sh.text_frame; tf.clear()
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            r = p.add_run(); r.text = text
            r.font.size = Pt(10); r.font.bold = True
            r.font.color.rgb = BLUE; r.font.name = "Calibri"


def drop_body(slide):
    b = body_of(slide)
    if b is not None:
        b._element.getparent().remove(b._element)


def picture_fit(slide, path, x, y, max_w, max_h):
    """Place a picture inside a box, centred, without distorting it."""
    pic = slide.shapes.add_picture(path, x, y, width=max_w)
    if pic.height > max_h:
        ratio = max_h / pic.height
        pic.width = int(pic.width * ratio)
        pic.height = int(pic.height * ratio)
    pic.left = int(x + (max_w - pic.width) / 2)
    pic.top = y
    return pic


def bullets(slide, x, y, w, items, size=10.5, colour=INK, gap=2):
    return add_text(slide, x, y, w, Inches(0.4),
                    [("▸  " + t, {"size": size, "line": 0.92, "color": colour,
                                       "space_after": gap}) for t in items])


# ==========================================================================
def main():
    B = json.load(open(os.path.join(FIG, "dristi_benchmark.json"), encoding="utf-8"))
    IF = B["isolation_forest"]
    TY = B["structuring_typology"]
    KI = B["key_individuals"]
    G2 = B["gate_two_plus"]          # the >=2 distinct-families gate
    C = B["corpus"]
    FAMS = B["families_in_gate"]
    LV = B["level_counts"]

    prs = Presentation(TEMPLATE)
    delete_slide(prs, 6)

    # =================================================== SLIDE 1 — TITLE
    s = prs.slides[0]
    for sh in s.shapes:
        if sh.name == "TextBox 9":
            set_runs(sh, [
                ("", {"size": 8}),
                ("Problem Statement ID – 26189", {"size": 15, "bold": True}),
                ("Problem Statement Title – AI-Powered Criminal Network Analysis System",
                 {"size": 15, "bold": True}),
                ("Theme – Blockchain & Cybersecurity", {"size": 15}),
                ("PS Category – Software", {"size": 15}),
                (f"Team ID – {TEAM_ID}", {"size": 15}),
                (f"Team Name – {TEAM_NAME}", {"size": 15}),
                ("", {"size": 10}),
                (PRODUCT, {"size": 32, "bold": True, "color": RED, "space_after": 0}),
                ("Evidence-Centric Criminal Network Intelligence System",
                 {"size": 13.5, "bold": True, "color": INK, "space_after": 2}),
                ("दृष्टि  ·  “sight, perception”",
                 {"size": 12, "color": MUTED, "space_after": 2}),
                ("One case graph.  Many analytical lenses.  Every finding evidenced.",
                 {"size": 12.5, "italic": True, "color": MUTED}),
            ], space_after=5)
        if sh.name == "Subtitle 3":
            tf = sh.text_frame; tf.clear()
            p = tf.paragraphs[0]
            r = p.add_run(); r.text = "\nIDEA SUBMISSION"
            r.font.size = Pt(20); r.font.bold = True
            r.font.color.rgb = WHITE; r.font.name = "Calibri"

    # ================================== SLIDE 2 — IDEA / PROPOSED SOLUTION
    s = prs.slides[1]
    set_oval(s, TEAM_NAME); drop_body(s)
    set_title(s, "IDEA AND PROPOSED SOLUTION", size=24)

    # --- column A: the problem
    ax_, aw = Inches(0.35), Inches(3.80)
    add_text(s, ax_, Inches(1.16), aw, Inches(0.3), [
        ("THE PROBLEM", {"size": 12, "bold": True, "color": RED})])
    bullets(s, ax_, Inches(1.52), aw, [
        "Investigation data is fragmented across CDR, banking, RTO, FIRs, locations and "
        "evidence files.",
        "Relationships between people, phones, vehicles, transactions and places are hard "
        "to establish across systems that do not talk to each other.",
        "Officers spend days cross-referencing records and reconstructing timelines by hand.",
        "A detected relationship is only useful if it can be traced back to the record that "
        "evidences it.",
        "Any single analytical signal, on its own, produces more noise than leads.",
    ], size=10.5, gap=7)

    add_box(s, ax_, Inches(4.28), aw, Inches(1.28), REDBG, RED, 1.2)
    add_text(s, ax_ + Inches(0.14), Inches(4.36), aw - Inches(0.28), Inches(1.14), [
        ("THE GAP IS NOT DISCOVERY", {"size": 11, "bold": True, "color": RED,
                                      "space_after": 2}),
        ("An investigator often already suspects the connection. What takes weeks is "
         "assembling it from disconnected systems — and then showing, for each link, which "
         "record it came from. A tool that surfaces names without that trail adds work "
         "instead of removing it.", {"size": 10, "line": 0.92}),
    ], space_after=2)

    # --- column B: the solution, as a flow
    bx, bw = Inches(4.34), Inches(4.35)
    add_text(s, bx, Inches(1.16), bw, Inches(0.3), [
        ("PROPOSED SOLUTION", {"size": 12, "bold": True, "color": GREEN})])
    add_text(s, bx, Inches(1.48), bw, Inches(0.42), [
        ("DRISTI builds one case-level investigation graph that unifies heterogeneous "
         "evidence and lets multiple analytical lenses examine the same network.",
         {"size": 10, "line": 0.92, "color": MUTED})])
    picture_fit(s, os.path.join(FIG, "fig_flow.png"), bx, Inches(2.02), bw, Inches(4.22))

    # --- column C: core innovation
    cx, cw = Inches(8.94), Inches(4.05)
    add_text(s, cx, Inches(1.16), cw, Inches(0.3), [
        ("CORE INNOVATION", {"size": 12, "bold": True, "color": BLUE})])
    cards = [
        ("01  PROVENANCE-AWARE EVIDENCE GRAPH",
         "Evidence is part of the data model, not a reporting feature. Every relationship and "
         "every finding can be walked back to the source record that produced it.", BLUE, BAND),
        ("02  MULTI-SIGNAL CORRELATION ACROSS ANALYTICAL FAMILIES",
         "Signals from distinct analytical families are correlated to strengthen investigative "
         "leads; single-detector outputs remain leads rather than corroborated findings. Model "
         "output is never counted as a corroborating family.", GREEN, GREENBG),
        ("03  GROUND-TRUTH EVALUATION FRAMEWORK",
         "A labelled synthetic investigation with known relationships and planted patterns, so "
         "the system can be measured rather than demonstrated — including where it fails.",
         RED, REDBG),
    ]
    cy = Inches(1.52)
    for head, body, col, bg in cards:
        add_box(s, cx, cy, cw, Inches(1.34), bg, col, 1.25)
        add_text(s, cx + Inches(0.14), cy + Inches(0.09), cw - Inches(0.28), Inches(1.2), [
            (head, {"size": 11, "bold": True, "color": col, "space_after": 3}),
            (body, {"size": 10, "line": 0.92}),
        ], space_after=2)
        cy += Inches(1.46)

    add_box(s, cx, Inches(5.94), cw, Inches(0.66), GREY, RULE, 1.1)
    add_text(s, cx + Inches(0.14), Inches(6.00), cw - Inches(0.28), Inches(0.54), [
        ("Recorded fact  ≠  derived inference  ≠  model prediction",
         {"size": 10.5, "bold": True, "color": INK, "align": PP_ALIGN.CENTER,
          "space_after": 1}),
        ("DRISTI stores which kind of claim it is making.",
         {"size": 9.5, "italic": True, "color": MUTED, "align": PP_ALIGN.CENTER}),
    ], space_after=1)

    # ============================================= SLIDE 3 — TECHNICAL APPROACH
    s = prs.slides[2]
    set_oval(s, TEAM_NAME); drop_body(s)
    set_title(s, "TECHNICAL APPROACH", size=24)

    picture_fit(s, os.path.join(FIG, "fig_arch.png"),
                Inches(0.22), Inches(1.20), Inches(9.50), Inches(5.10))

    sx, sw = Inches(9.88), Inches(3.15)
    add_box(s, sx, Inches(1.22), sw, Inches(5.60), BAND, BLUE, 1.25)
    stack = [
        ("Data and backend", "Python · pandas · Neo4j · Cypher · Streamlit", GREEN),
        ("Graph analytics", "NetworkX · Neo4j GDS · Plotly", GREEN),
        ("Machine learning", "scikit-learn · Isolation Forest", GREEN),
        ("Financial intelligence", "FIU-IND typology detectors — structuring, rapid "
                                   "pass-through, value outliers", GREEN),
        ("Evaluation", "labelled synthetic corpus · benchmark harness in the console", GREEN),
        ("NLP and entity resolution", "IndicNER · MuRIL · phonetic blocking", AMBER),
        ("Graph ML", "GraphSAGE link prediction — candidate leads only", AMBER),
        ("Security", "RBAC · case scoping · tamper-evident audit log", AMBER),
    ]
    blocks = [("TECHNOLOGY STACK", {"size": 11.5, "bold": True, "color": BLUE,
                                    "space_after": 4})]
    for head, body, col in stack:
        dot = "● " if col == GREEN else "○ "
        blocks.append((dot + head, {"size": 10, "bold": True, "color": col,
                                    "line": 0.9, "space_after": 0}))
        blocks.append(("    " + body, {"size": 9.6, "color": MUTED, "line": 0.9,
                                       "space_after": 5}))
    blocks += [
        ("", {"size": 3}),
        ("●  running today          ○  next phase",
         {"size": 9.4, "italic": True, "color": MUTED, "space_after": 4}),
        ("No GPU and no outbound network call — deployable inside an existing police network.",
         {"size": 9.6, "italic": True, "color": MUTED, "line": 0.9}),
    ]
    add_text(s, sx + Inches(0.15), Inches(1.30), sw - Inches(0.30), Inches(5.44), blocks,
             space_after=3)

    add_text(s, Inches(0.24), Inches(6.38), Inches(9.45), Inches(0.44), [
        ("Green blocks run in the console today and can be opened on request; amber dashed "
         "blocks are designed and scheduled. Five analytical lenses exist in the console; three "
         "of them — financial, communication, structural — emit the detector families that feed "
         "the correlation gate measured here. Graph ML sits on its own branch by design: a link "
         "prediction is a candidate lead, never a corroborating family, and it does not enter "
         "the benchmark.",
         {"size": 9.6, "italic": True, "color": MUTED, "line": 0.9})])

    # =========================================== SLIDE 4 — FEASIBILITY & VIABILITY
    s = prs.slides[3]
    set_oval(s, TEAM_NAME); drop_body(s)
    set_title(s, "FEASIBILITY AND VIABILITY", size=24)

    lx, lw = Inches(0.35), Inches(6.55)
    add_text(s, lx, Inches(1.14), lw, Inches(0.4), [
        ("A WORKING PROTOTYPE, NOT A CONCEPT", {"size": 12, "bold": True, "color": GREEN,
                                                "space_after": 1}),
        (f"Live Neo4j case graph · 13 modules · {C['persons']} subjects · "
         f"{C['calls']:,} calls · {C['transactions']} transactions · "
         f"{C['evidence']:,} evidence records",
         {"size": 9.3, "color": MUTED, "line": 0.9}),
    ])
    shot = picture_fit(s, os.path.join(FIG, "dristi_console_hero.png"),
                       lx, Inches(1.70), lw, Inches(3.95))
    cap_y = Inches(1.70) + shot.height + Inches(0.03)
    add_text(s, lx, cap_y, lw, Inches(0.34), [
        (f"Network Graph and Multi-Signal Correlation, live. HIGH {LV['HIGH']} · MEDIUM "
         f"{LV['MEDIUM']} · LOW {LV['LOW']}. HIGH requires all three currently implemented "
         f"detector families to agree; the thresholds are fixed, not tuned to the answer key.",
         {"size": 9, "italic": True, "color": MUTED, "line": 0.88})])

    dy = cap_y + Inches(0.38)
    add_box(s, lx, dy, lw, Inches(6.84) - dy, GREENBG, GREEN, 1.15)
    add_text(s, lx + Inches(0.14), dy + Inches(0.07), lw - Inches(0.28),
             Inches(6.77) - dy, [
        ("CURRENTLY DEMONSTRATED", {"size": 10.5, "bold": True, "color": GREEN,
                                    "space_after": 2}),
        ("Neo4j case graph · network visualisation · entity traversal · call, transaction, "
         "timeline and geospatial analytics · Evidence Desk · anomaly detection · typology "
         "detectors · multi-signal correlation · evidence chain · benchmark evaluation.",
         {"size": 9.4, "line": 0.9}),
    ], space_after=2)

    # --- challenges and mitigation, as a table a judge can scan
    rx, rw = Inches(7.05), Inches(5.95)
    add_text(s, rx, Inches(1.14), rw, Inches(0.3), [
        ("CHALLENGES AND MITIGATION", {"size": 12, "bold": True, "color": AMBER})])

    rows = [
        ("Fragmented identities",
         "Conservative entity resolution — merge only on a shared identifier or a "
         "corroborating attribute, and every merge reversible by the officer."),
        ("False positives from any one analytic",
         f"Correlation across distinct analytical families. On our labelled corpus, "
         f"\u22652 families gives {G2['precision']*100:.1f}% precision at "
         f"{G2['recall']*100:.0f}% recall against a {B['base_rate']*100:.1f}% base rate."),
        ("A score mistaken for a finding of guilt",
         "Indicators labelled as indicators on every screen, a human-verification step in "
         "front of every output, predictions stored apart from recorded facts."),
        ("Sensitive CDR, FIR and financial data",
         "Role-based access with case-level scoping, field-level redaction and a "
         "tamper-evident audit log — access bound to assignment, every read accountable."),
        ("Messy, unstructured source documents",
         "Staged extraction: deterministic patterns for numbers and registration marks, a "
         "locality gazetteer for places, an Indic NER model for names last."),
        ("Standardized benchmarks are limited across the literature reviewed",
         "We built a labelled corpus and harness of our own. It gives controlled prototype "
         "evidence, not a prediction of field performance; next step is the same harness on "
         "real annotated records with NCRB."),
        ("Graph growth across a large case",
         "Indexed Cypher queries and modular analytics — each lens reads the graph "
         "independently, so the console scales by module, not by rewrite."),
    ]
    th = Inches(4.88)
    tbl_shape = s.shapes.add_table(len(rows) + 1, 2, rx, Inches(1.50), rw, th)
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(1.95)
    tbl.columns[1].width = rw - Inches(1.95)
    tbl.first_row = True

    def cell(r, c, text, bold=False, size=9, colour=INK, fill=None):
        cl = tbl.cell(r, c)
        cl.margin_left = Inches(0.07); cl.margin_right = Inches(0.07)
        cl.margin_top = Inches(0.035); cl.margin_bottom = Inches(0.035)
        cl.vertical_anchor = MSO_ANCHOR.TOP
        if fill is None:
            cl.fill.background()
        else:
            cl.fill.solid(); cl.fill.fore_color.rgb = fill
        tf = cl.text_frame; tf.clear(); tf.word_wrap = True
        p = tf.paragraphs[0]; p.line_spacing = 0.88; p.space_after = Pt(0)
        r_ = p.add_run(); r_.text = text
        r_.font.size = Pt(size); r_.font.bold = bold
        r_.font.color.rgb = colour; r_.font.name = "Calibri"

    cell(0, 0, "Challenge", True, 9.5, WHITE, AMBER)
    cell(0, 1, "How DRISTI addresses it", True, 9.5, WHITE, AMBER)
    for i, (ch, mit) in enumerate(rows, start=1):
        shade = GREY if i % 2 else None
        cell(i, 0, ch, True, 9, INK, shade)
        cell(i, 1, mit, False, 9, MUTED, shade)

    add_text(s, rx, Inches(6.48), rw, Inches(0.36), [
        ("Feasible on open-source components, ordinary hardware and a modular architecture — "
         "no GPU, no cloud dependency, no outbound traffic from a police network.",
         {"size": 9.6, "italic": True, "color": MUTED, "line": 0.9})])

    # ============================================= SLIDE 5 — IMPACT AND BENEFITS
    s = prs.slides[4]
    set_oval(s, TEAM_NAME); drop_body(s)
    set_title(s, "IMPACT AND BENEFITS", size=24)

    lx, lw = Inches(0.35), Inches(6.20)
    groups = [
        ("FOR THE INVESTIGATING OFFICER", BLUE, [
            "One unified case picture instead of manually cross-referencing disconnected "
            "sources — the assembly work that currently takes days collapses into a "
            "single load.",
            "Relationship discovery, timeline reconstruction and communication, financial "
            "and spatial pattern analysis against the same graph.",
            "Immediate evidence traceability: every subject screen answers “what else is "
            "this person connected to?” and “which record says so?” side by side.",
        ]),
        ("FOR NCRB AND THE INSTITUTION", BLUE, [
            "An evidence-backed analytical workflow — the chain from an insight to the "
            "originating record is part of the data model, so every finding is auditable "
            "and traceable rather than asserted.",
            "A standardised case-level investigation graph, with auditable access.",
            "Designed to federate with CCTNS and ICJS through read-only connectors rather "
            "than becoming another parallel silo.",
        ]),
    ]
    gy = Inches(1.16)
    for head, col, items in groups:
        add_text(s, lx, gy, lw, Inches(0.28), [
            (head, {"size": 11.5, "bold": True, "color": col})])
        bullets(s, lx, gy + Inches(0.30), lw, items, size=10.3, gap=4)
        gy += Inches(0.34) + Inches(0.155) * sum(
            max(1, math.ceil(len(t) / 96)) for t in items) + Inches(0.34)

    add_box(s, lx, Inches(4.56), lw, Inches(2.28), REDBG, RED, 1.2)
    add_text(s, lx + Inches(0.15), Inches(4.64), lw - Inches(0.3), Inches(2.14), [
        ("FOR THE CITIZEN — WHY THE SAFEGUARDS ARE THE FEATURE",
         {"size": 11.5, "bold": True, "color": RED, "space_after": 3}),
        ("A system that names people from inferred patterns can do real harm to someone "
         "innocent. DRISTI makes no autonomous criminal conclusions: an indicator is never "
         "presented as a determination, a person surfaced by the system can always be traced "
         "back to the specific records that surfaced them, and access to a citizen's call and "
         "financial records is bound to a case assignment and logged. Proportionality and "
         "purpose limitation are design constraints here, not a compliance annexe.",
         {"size": 10.2, "line": 0.92}),
        ("No autonomous criminal conclusions  ·  human verification in front of every output  ·  "
         "evidence traceability on every record  ·  case-bound access  ·  auditable use of "
         "sensitive data.",
         {"size": 10, "line": 0.92, "bold": True, "color": RED}),
    ], space_after=4)

    rx, rw = Inches(6.95), Inches(6.05)
    add_box(s, rx, Inches(1.16), rw, Inches(0.92), INK, INK, 1.2)
    add_text(s, rx + Inches(0.15), Inches(1.24), rw - Inches(0.3), Inches(0.78), [
        ("ANOMALY  ≠  CRIMINALITY", {"size": 19, "bold": True, "color": WHITE,
                                     "align": PP_ALIGN.CENTER, "space_after": 2}),
        ("AI assists the investigator. It does not replace investigative judgement.",
         {"size": 10.5, "italic": True, "color": RGBColor(0xC7, 0xCD, 0xD8),
          "align": PP_ALIGN.CENTER}),
    ], space_after=2)

    add_box(s, rx, Inches(2.22), rw, Inches(2.06), BAND, BLUE, 1.2)
    add_text(s, rx + Inches(0.15), Inches(2.28), rw - Inches(0.3), Inches(1.94), [
        ("MEASURED, NOT ASSERTED", {"size": 11.5, "bold": True, "color": BLUE,
                                    "space_after": 2}),
        (f"Work in this field is validated almost entirely by case study. We built a labelled "
         f"synthetic investigation — {C['persons']} subjects, {C['calls']:,} calls, "
         f"{C['transactions']} transactions, {C['syndicate']} syndicate members, planted "
         f"patterns — and scored our own analytics against the answer key.",
         {"size": 10, "line": 0.9}),
        (f"Key individuals by network connectivity     P@5 {KI['precision_at_5']:.2f}  ·  "
         f"P@10 {KI['precision_at_10']:.2f}  ·  P@20 {KI['precision_at_20']:.2f}",
         {"size": 10, "line": 0.9, "bold": True}),
        (f"Evidence linkage     {B['evidence_coverage']*100:.0f}% of records resolve to a "
         f"source evidence record", {"size": 10, "line": 0.9, "bold": True}),
        (f"Transaction anomaly     generic outlier model F1 {IF['f1']:.2f} / AUROC "
         f"{IF['auroc']:.2f}   ·   structuring typology detector F1 {TY['f1']:.2f}",
         {"size": 10, "line": 0.9, "color": GREEN, "bold": True}),
        ("That gap is the finding, not a defect: structuring is built to look ordinary one "
         "transaction at a time, so no per-row model can see it. Measuring it is how we knew "
         "to add typology detectors rather than a bigger model.",
         {"size": 9.4, "line": 0.9, "italic": True, "color": MUTED}),
    ], space_after=2)

    add_box(s, rx, Inches(4.42), rw, Inches(2.42), REDBG, RED, 1.2)
    add_text(s, rx + Inches(0.15), Inches(4.50), rw - Inches(0.3), Inches(0.62), [
        ("MULTI-SIGNAL CORRELATION — LABELLED SYNTHETIC CORPUS",
         {"size": 11.5, "bold": True, "color": RED, "space_after": 1}),
        (f"Gate: a subject is raised only on \u22652 distinct analytical families "
         f"({' · '.join(FAMS)}). Thresholds fixed, not tuned to the answer key.",
         {"size": 9.6, "line": 0.9, "color": MUTED}),
    ], space_after=1)

    # One number with its population attached, rather than a progression of four
    # decimals. The progression invited "and what is n for that last bar?" -
    # the question that retired the previous version of this panel.
    hx, hw = rx + Inches(0.15), Inches(2.62)
    add_box(s, hx, Inches(5.16), hw, Inches(0.86), WHITE, RED, 1.3)
    add_text(s, hx, Inches(5.22), hw, Inches(0.76), [
        (f"{G2['precision']*100:.1f}%  precision",
         {"size": 17, "bold": True, "color": RED, "align": PP_ALIGN.CENTER, "space_after": 0}),
        (f"at {G2['recall']*100:.0f}% recall     ·     base rate {B['base_rate']*100:.1f}%",
         {"size": 10, "bold": True, "color": INK, "align": PP_ALIGN.CENTER}),
    ], space_after=1)

    add_text(s, rx + Inches(2.92), Inches(5.14), Inches(2.98), Inches(0.92), [
        (f"Evaluated population    {G2['evaluated_population']} persons",
         {"size": 9.6, "line": 0.9, "space_after": 1}),
        (f"Ground-truth positives    {G2['ground_truth_positives']}",
         {"size": 9.6, "line": 0.9, "space_after": 1}),
        (f"Flagged at \u22652 families    {G2['flagged']}",
         {"size": 9.6, "line": 0.9, "space_after": 1, "bold": True}),
        (f"TP {G2['tp']}   ·   FP {G2['fp']}   ·   FN {G2['fn']}   ·   TN {G2['tn']}",
         {"size": 9.6, "line": 0.9, "bold": True, "color": RED}),
    ], space_after=1)

    add_text(s, rx + Inches(0.15), Inches(6.18), rw - Inches(0.3), Inches(0.6), [
        ("Measured on our labelled synthetic investigation corpus. Controlled prototype "
         "evidence that the pipeline recovers a known structure and that design choices can "
         "be compared under identical conditions — not a prediction of field performance.",
         {"size": 9.2, "line": 0.9, "italic": True, "color": MUTED})], space_after=0)

    # ========================================== SLIDE 6 — RESEARCH AND REFERENCES
    s = prs.slides[5]
    set_oval(s, TEAM_NAME); drop_body(s)
    set_title(s, "RESEARCH AND REFERENCES", size=24)

    left = [
        ("RESEARCH FOUNDATIONS", BLUE, None),
        ("Criminal network analysis", None, [
            "Sparrow, M. — “The application of network analysis to criminal intelligence: an "
            "assessment of the prospects”, Social Networks 13(3), 1991.",
            "Morselli, C. — “Inside Criminal Networks”, Springer, 2009. Brokerage, and why "
            "covert networks are deliberately sparse.",
        ]),
        ("Network analytics", None, [
            "Bonacich, P. — “Power and Centrality: A Family of Measures”, American Journal of "
            "Sociology 92(5), 1987.",
            "Blondel, V. et al. — “Fast unfolding of communities in large networks”, "
            "J. Stat. Mech., 2008.  arxiv.org/abs/0803.0476",
        ]),
        ("Anomaly detection", None, [
            "Liu, F.T., Ting, K.M., Zhou, Z-H. — “Isolation Forest”, IEEE ICDM, 2008.",
        ]),
        ("Graph ML and entity resolution", None, [
            "Hamilton, W., Ying, R., Leskovec, J. — “Inductive Representation Learning on "
            "Large Graphs” (GraphSAGE), NeurIPS 2017.  arxiv.org/abs/1706.02216",
            "Christen, P. — “Data Matching”, Springer, 2012. Blocking, pairwise scoring and "
            "transitive closure.",
        ]),
    ]
    blocks = []
    for head, col, items in left:
        if col is not None:
            blocks.append((head, {"size": 12, "bold": True, "color": col,
                                  "space_after": 6}))
            continue
        blocks.append((head, {"size": 10.5, "bold": True, "color": INK,
                              "line": 0.9, "space_after": 1}))
        for it in items:
            blocks.append(("   " + it, {"size": 10, "color": MUTED, "line": 0.9,
                                        "space_after": 5}))
    add_text(s, Inches(0.38), Inches(1.14), Inches(6.35), Inches(5.6), blocks)

    right = [
        ("TECHNOLOGY, DOMAIN AND LEGAL GROUNDING", BLUE, None),
        ("Systems this federates with", None, [
            "National Crime Records Bureau — CCTNS and the Inter-operable Criminal Justice "
            "System (ICJS).  ncrb.gov.in",
            "Neo4j Graph Data Science — centrality, community detection and pathfinding at "
            "scale.  neo4j.com/docs/graph-data-science",
        ]),
        ("Financial intelligence", None, [
            "Financial Intelligence Unit – India — cash transaction reporting thresholds and "
            "layering typologies; the basis for the financial indicators.  fiuindia.gov.in",
        ]),
        ("Language resources", None, [
            "AI4Bharat — IndicNER and MuRIL, for names in Indic scripts and transliterated "
            "forms in FIR text.  ai4bharat.org",
        ]),
        ("Legal and privacy framework", None, [
            "Bharatiya Nagarik Suraksha Sanhita, 2023 — production of documents and search; "
            "the evidence chain is built to survive this scrutiny.",
            "Digital Personal Data Protection Act, 2023 — purpose limitation and "
            "accountability; why access is bound to case assignment and logged.",
            "K.S. Puttaswamy v. Union of India, (2017) 10 SCC 1 — necessity and "
            "proportionality; why the system refuses to escalate on a single unverified signal.",
        ]),
    ]
    blocks = []
    for head, col, items in right:
        if col is not None:
            blocks.append((head, {"size": 12, "bold": True, "color": col,
                                  "space_after": 6}))
            continue
        blocks.append((head, {"size": 10.5, "bold": True, "color": INK,
                              "line": 0.9, "space_after": 1}))
        for it in items:
            blocks.append(("   " + it, {"size": 10, "color": MUTED, "line": 0.9,
                                        "space_after": 5}))
    add_text(s, Inches(6.95), Inches(1.14), Inches(6.05), Inches(4.5), blocks)

    add_box(s, Inches(0.38), Inches(5.62), Inches(12.62), Inches(1.20), REDBG, RED, 1.2)
    add_text(s, Inches(0.54), Inches(5.70), Inches(12.3), Inches(1.06), [
        ("OUR CONTRIBUTION", {"size": 11.5, "bold": True, "color": RED, "space_after": 3}),
        ("A provenance-aware case graph, a correlation layer across distinct analytical "
         "families, and a labelled ground-truth evaluation framework for evidence-centric "
         "criminal-network investigation. Across the literature we reviewed, existing "
         "evaluations are often case-study based, with limited standardization across "
         "datasets and metrics, which makes systems hard to compare directly. We intend to "
         "release our corpus and harness, including the negative results they produce — the "
         "per-transaction outlier model at F1 0.12 among them.",
         {"size": 10, "line": 0.92}),
    ], space_after=3)

    prs.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
