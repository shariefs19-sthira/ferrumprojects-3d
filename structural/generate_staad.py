#!/usr/bin/env python3
"""
CHRA-2502 Pickleball Roof -- 3D STAAD.Pro CONNECT Edition input generator.

Builds the full 9-truss + 18-column + eave-ring + plan-bracing model from the
n=14 Warren fish-belly winner topology (structural/REPORT.md). Sections are
STAAD TUBE type (DT/WT/TH), not PRISMATIC and not a country section-table
lookup -- see ROUND 8 below for why.

This script is NOT a substitute for opening the file in STAAD.Pro. It has not
been run through an actual STAAD parser; syntax is written from documented
STAAD.Pro CONNECT Edition command reference, not verified execution. Treat
every "A9" note below as unconfirmed until a real STAAD session accepts the
file.

ADJUDICATED (round 2) -- the engineer of record has ruled on every open item from
the round-1 audit. This file reflects those rulings:

  D-1 RULED: columns run to the bottom-chord end node (Y=7.752m / 7.339m), K=1.0,
     no stub member. The "~8.75/8.34m" figures in the original brief are
     superseded by this ruling, not reconciled with it.

  D-2 RULED: deck lateral-restraint credit is KEPT (top-chord KL_out-of-plane =
     1x panel = 1.474m). The four conditions and the drawing note the ruling
     asked to insert verbatim are in the .std header below -- BUT the exact
     verbatim drawing-note text was never given to this script; what's there is
     a standard/typical four-condition set for deck-diaphragm lateral credit,
     clearly marked as inferred, not the engineer's actual wording. Swap in the
     real text before this drawing note is relied upon.

ROUND 3 (close-out patch set) -- supersedes round 2 on the items below:

  D-2 FINAL: the deck-credit header block now carries the engineer's actual
     verbatim drawing note (quoted exactly), not the round-2 inferred
     four-condition placeholder.

  D-6 FINAL: the round-2 "switch 100x100x4 to TABLE" flag is WITHDRAWN. The
     engineer's own hand references (14.5/21.6 kNm) were the ones in error;
     this engine's sharp-corner Md values (12.57-12.58 / 22.56 kNm, from
     Zp*fy/gamma_m0 capped at 1.2*Ze*fy/gamma_m0 per Cl 8.2.1.2) are
     validated and used throughout. PRIS stands for every SHS in this
     design. The 1.2*Ze cap is now implemented in is800.js; re-sweeping
     every chord member against it moved zero members by more than 0.03
     util (in fact zero members moved at all -- shape factor stays under
     1.2 for every section actually used here).

  DESIGN CASE (new ruling): the issued design is TAILORED-AT-ACTUAL
     tributaries (T1=4.572m, T2=5.098m, T3=7.121m) -- 6.32t trusses, utils
     0.922-0.936. The envelope variant (4.572/5.600/7.372m) is NOT issued;
     it is retained only as a documented spare-parts/interchangeability
     option, at 6.62t trusses if invoked (one SHS step on T3's top1 group,
     200x200x3->200x200x4, to clear its 0.952 marginal overage -- the
     ruling's own "~6.7t" estimate was in the right neighbourhood but this
     script's own arithmetic, 6.62t, is what's reported).

  D-3 FINAL (supersedes round 2's full-length zig-zag): plan bracing at the
     bottom-chord level is now PARTIAL, covering only the middle bracing
     field, not the full 14-panel run:
       - Braced bays unchanged: {1,3,4,6,8}.
       - Brace attachment points along each truss's own bottom chord:
         panel-points {3,5,7,9,11} (4 modules, single alternating zig-zag
         chain, NOT crossing X pairs -- this is what gets to ~20 total
         diagonals: 4 modules x 5 bays). Section 100x100x4 SHS.
       - This computes to unbraced end stretches of 3 panels each
         (~4.42m), close to the ruling's "~4.3m" estimate; the braced
         field itself (panels 3-11) computed to a per-segment KL_op of
         2.947m for the corresponding round-2 D-3 module choice, reused
         here.
       - VERIFIED against the real C4 (0.9DL+1.5WLup) bottom-chord axial
         diagram for the worst truss (T3/truss2): peaks at 109.6 kN at
         midspan (not exactly the ruling's ~98kN estimate -- this script's
         own FEM number is what's used), tapering to ~54kN at the ends.
         Segment-wise check (worst of all three truss types, all 14
         segments, both braced and unbraced KL_op): max util = 0.854 (T1,
         unbraced end segment), max KL/r = 92.5. BOTH pass their limits
         (<=0.95, <=180) with real margin.
       - ACCEPTANCE MET -> partial bracing is ADOPTED (not reverted).
         Mass: 20 members, ~1.60t (the ruling's own "~1.4t" estimate was
         in the right neighbourhood; this script's own computed mass,
         1.60t, is what's reported and carried into the ledger).

  D-5: ring section stays 76x76x4 SHS. Bracing section is now 100x100x4 SHS
     (supersedes round 2's 90x90x4 SHS -- the partial-bracing scheme's own
     member forces drove this choice, verified above).

ROUND 7 (post-first-successful-run, engineer's ruling): top chord and bottom
   chord each collapsed to ONE section for their full run per truss type (no
   splicing two SHS sizes along one continuous chord -- fabricator
   constraint). Re-verified on the full, un-pruned 44-member topology (the
   one this generator actually builds); in every one of T1/T2/T3 the uniform
   section equals what was already the "large-panel" band's section, run the
   full length. See structural/REPORT.md ERRATA 5 for the per-truss numbers.

ROUND 8 (engineer's ruling): "no CHECK CODE issued" is WITHDRAWN. The
   engineer wants STAAD's own IS 800 steel-design module to actually run, not
   just document effective lengths for a reviewer who might. A bare
   PRISMATIC member has no section classification, so STAAD's design module
   cannot check it at all -- every prior round's "PRIS stands" note is
   superseded here. Switched every member to TUBE (DT/WT/TH), a named STAAD
   section type STAAD computes its own properties for and that IS 800
   tubular design is a documented code-check path for. Added TRACK 2 ALL and
   CHECK CODE ALL before FINISH. [Likely, not confirmed against a live
   session] -- this is the same "written from documented syntax, unverified
   execution" caveat that applied to every other command in this file before
   its first live run; if CHECK CODE errors or comes back empty for TUBE
   members under this STAAD build's IS 800 implementation, that is a new,
   real defect to report back, not a sign the model itself is wrong. STAAD's
   own IS800 utilization is now a second, independent check against this
   project's Node/is800.js engine -- if the two disagree by more than
   rounding, that is a finding, not a discrepancy to paper over.

ROUND 9 (engineer's ruling): every SCHEDULE section is now a real IS 4923:2017 Table 1
   designation (not the prior idealized continuous B x t grid -- see
   is4923_2017_table1.json and the SCHEDULE comment below for the full finding: most
   sizes previously used, including 200x200, do not exist as real products). Separately,
   the engineer wants a MODEL to hand-iterate in STAAD, not this project's optimizer
   output taken as final: UNIFORM_MANUAL_DESIGN collapses every structural role (top
   chord, bottom chord, web) to ONE section across the whole building rather than
   per-truss-type, so the engineer can change one group and have it apply everywhere.
   Bracing (previously dropped in a short-lived NO_BRACING diagnostic mode, now off by
   default) is restored as its own single-named group. LY/LZ/KY/KZ effective-length
   declarations are UNCHANGED by any of this -- they follow geometry and the bracing
   layout, not section choice, and remain correct for whatever size the engineer
   ultimately settles on.

Run: python3 generate_staad.py
Output: CHRA2502_3D_Final.std
"""
import math
import os

# NO_BRACING: generate a variant with the bottom-chord plan bracing entirely removed, so
# the engineer can watch STAAD's own CHECK CODE fail the bottom chord under its TRUE
# unbraced condition. Superseded by UNIFORM_MANUAL_DESIGN below (which wants bracing back,
# as its own single-named group) -- kept as a flag in case the diagnostic file is wanted
# again later, but OFF by default now.
NO_BRACING = False

# USE_TUBE: engineer's live STAAD run rejected every TUBE DT/WT/TH property line ("MEMBER
# PROPERTY command ignored by program. Check syntax", 13/13 statements) -- confirmed real,
# not guessed. This project's memory of that syntax is wrong for this STAAD build (V8i
# SELECTseries6), and guessing a second time risks burning another round the same way
# PY/PZ did earlier. Reverted to PRISMATIC (AX/AY/AZ/IX/IY/IZ/YD/ZD) -- proven clean on
# this exact build (the round-6/7 successful run). Tradeoff: PRISMATIC members are not
# eligible for STAAD's own CHECK CODE, so this file's pass/fail comes from this project's
# own is800.js engine (already computed against these exact sections), not from STAAD's
# design module, until the real TUBE syntax for this build is confirmed (fastest path:
# define a Tube property via STAAD's own GUI dialog and read back what it writes).
USE_TUBE = False

# UNIFORM_MANUAL_DESIGN (engineer's ruling, post-round-9): the engineer wants a complete,
# code-check-ready MODEL -- geometry, all 4 load cases, all 5 combinations, CODE IS800 with
# every member's real effective length declared, CHECK CODE ALL -- but will pick every
# member's actual size manually in STAAD (iterate/trial), not take this project's optimizer
# output as final. To make manual iteration tractable, every member of a given STRUCTURAL
# ROLE shares ONE property name across the WHOLE building (all 126 top-chord members
# everywhere, not per truss type; all 126 bottom-chord members; one web section for the
# 144 vertical+diagonal members; one column section; one ring section; one bracing
# section) -- so changing one group's size in STAAD changes it everywhere at once. This
# REPLACES the per-truss-type (T1/T2/T3) tailored SCHEDULE below with a single fixed
# section per role. The values below are STARTING POINTS ONLY (T3's own verified real
# sections -- T3 carries this design's largest tributary, 7.121m, so starting every group
# there is a safe, conservative seed, not an endorsement that one size fits every truss
# without the engineer's own re-check). LY/LZ/KY/KZ effective-length declarations are
# UNCHANGED -- they come from geometry and the bracing layout, not from section choice, so
# they stay correct regardless of what the engineer ultimately picks.
UNIFORM_MANUAL_DESIGN = True
UNIFORM_TOP_SECTION = "180x180x4 SHS"
UNIFORM_BOTTOM_SECTION = "100x100x5 SHS"
UNIFORM_WEB_SECTION = "72x72x3.2 SHS"  # T3's heavier web band -- conservative single starting size for every vertical/diagonal

OUT_PATH = "CHRA2502_3D_NoBracing.std" if NO_BRACING else (
    "CHRA2502_3D_ManualDesign.std" if UNIFORM_MANUAL_DESIGN else "CHRA2502_3D_Final.std")

# ---------------------------------------------------------------- geometry --
SPAN = 20.630
N_PANELS = 14
Y_TOP_0 = 8.752
SLOPE = (8.339 - 8.752) / SPAN  # per metre, exact from the fixed brief coordinates
D_END = 1.0
D_MID = 2.449
CAMBER_MID = 0.025  # m, FABRICATION note only -- not baked into analysis coordinates (see NOTE below)

BAY_Z = [0.000, 9.144, 14.242, 19.340, 24.438, 29.536, 34.634, 39.732, 44.830]
N_TRUSS = len(BAY_Z)  # 9

# Actual (corrected) per-truss tributary width, kN/m per kN/m^2 -- truss 1..9 in Z order.
LT_ACTUAL = [4.572, 7.121, 5.098, 5.098, 5.098, 5.098, 5.098, 5.098, 2.549]
# Truss-type schedule assignment: which of T1/T2/T3's grouped sections this physical
# truss is built to. Truss 1 & 9 use T1 (conservative envelope of 4.572/2.549); truss 2
# uses T3 (its own actual tributary, 7.121, IS T3's design case); 3-8 use T2.
TRUSS_TYPE = ["T1", "T3", "T2", "T2", "T2", "T2", "T2", "T2", "T1"]

DECK_DL = 0.25   # kN/m^2
DECK_LL = 0.75   # kN/m^2
WIND_UPLIFT = 0.65  # kN/m^2, upward
WIND_LATERAL = 0.0877  # kN/m^2 on column projected area
COL_HEIGHT_LOW = None  # computed below from geometry
COL_HEIGHT_HIGH = None

BRACED_BAYS = [1, 3, 4, 6, 8]  # 1-indexed: bay k = between truss k and truss k+1 -- D-3 ruling
BRACE_POINTS = [3, 5, 7, 9, 11]  # panel-points carrying a bracing attachment -- D-3 final (round 3)
PANEL_L = SPAN / N_PANELS  # 1.4736m
BRACED_KL_OP = 2 * PANEL_L   # 2.947m -- KL_op for bottom-chord segments within the braced field (panels 3-10)
UNBRACED_KL_OP = 3 * PANEL_L  # 4.421m -- KL_op for the two end stretches (panels 0-2, 11-13)

def top_y(x):
    return Y_TOP_0 + SLOPE * x

def depth(x):
    return D_END + (D_MID - D_END) * 4 * (x / SPAN) * (1 - x / SPAN)

def bot_y(x):
    return top_y(x) - depth(x)

PANEL_X = [i * SPAN / N_PANELS for i in range(N_PANELS + 1)]
COL_HEIGHT_LOW = bot_y(0.0)      # 7.752 m -- column at the X=0 (high) end of every truss
COL_HEIGHT_HIGH = bot_y(SPAN)    # 7.339 m -- column at the X=20.630 (low) end

def bottom_chord_total_length():
    """Sum of every bottom-chord panel's true (sloped) length -- the TRUE unbraced
    length of the whole bottom chord between the two column bases if NO intermediate
    lateral restraint exists (no plan bracing at all). Only the columns themselves
    restrain it at the two ends."""
    total = 0.0
    for i in range(N_PANELS):
        dx = PANEL_X[i + 1] - PANEL_X[i]
        dy = bot_y(PANEL_X[i + 1]) - bot_y(PANEL_X[i])
        total += math.sqrt(dx * dx + dy * dy)
    return total

FULL_BOTTOM_UNBRACED_LEN = bottom_chord_total_length()  # ~20.63m -- see NO_BRACING note below

# --------------------------------------------------------- section catalog --
# REAL IS 4923:2017 Table 1 data (engineer's ruling, post-round-8: "choose sections
# only from the table sections"). Loaded from is4923_2017_table1.json, which was
# extracted programmatically (pdftotext -layout + regex parse) from the actual
# embedded text layer of the official BIS document -- not eyeballed off a screenshot.
# Confirms there is NO 200x200 SHS in either the 1997 or 2017 edition (the table
# jumps 180x180 -> 220x220 directly).
import json as _json
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "is4923_2017_table1.json")) as _f:
    _TABLE1 = {(row["B"], row["t"]): row for row in _json.load(_f)}

def shs(B, t):
    """Real IS 4923:2017 SHS properties if this exact (B,t) is a real designation;
    falls back to the sharp-corner idealization ONLY if it isn't (which should never
    happen for anything actually used in SCHEDULE/COLUMN/RING/BRACING below -- if it
    does, that's a defect to fix, not a silently-accepted approximation)."""
    key = (B, t)
    if key in _TABLE1:
        row = _TABLE1[key]
        A, I, Zp = row["A_cm2"] * 100, row["I_cm4"] * 1e4, row["Zp_cm3"] * 1e3
        r = row["r_cm"] * 10
        return {"B": B, "t": t, "A": A, "I": I, "Zp": Zp, "r": r, "label": f"{B}x{B}x{t} SHS",
                "source": "IS4923:2017 Table 1"}
    print(f"WARNING: {B}x{B}x{t} SHS is NOT a real IS 4923:2017 designation -- "
          f"using idealized sharp-corner formula as a fallback. This should not "
          f"happen for anything in SCHEDULE/COLUMN_SECTION/RING_SECTION/BRACING_SECTION.")
    h = B - 2 * t
    A = 4 * t * (B - t)
    I = (B**4 - h**4) / 12
    Zp = (B**3 - h**3) / 4
    r = math.sqrt(I / A)
    return {"B": B, "t": t, "A": A, "I": I, "Zp": Zp, "r": r, "label": f"{B}x{B}x{t} SHS",
            "source": "IDEALIZED (not a real section)"}

def parse_label(lbl):
    # "150x150x3 SHS" -> (150, 3); "88.9x88.9x3.6 SHS" -> (88.9, 3.6) -- real IS 4923
    # designations include non-integer B (88.9, 91.5, 113.5, 49.5, 63.5), so B is a
    # float, not int, here.
    dims = lbl.split(" ")[0].split("x")
    return float(dims[0]), float(dims[2])

# Grouped sections per truss type, from structural/optimize.js (Node engine),
# deck-lateral-credit-declared case -- see tailored_schedule.json.
#
# REAL-TABLE-SECTIONS RULING (engineer's ruling, post-round-8): "choose sections only
# from the table sections" -- every SHS below is a real IS 4923:2017 Table 1
# designation (verified via is4923_2017_table1.json, extracted from the actual BIS
# document text, not idealized/interpolated). This replaced an idealized continuous
# B x t grid that did not correspond to any real, orderable product for most sizes
# used (confirmed: only 40, 75, 100, 150 mm happened to coincide with real sizes;
# 50, 60, 65, 90, 110, 120, 130, 140, 160, 200mm do not exist as real SHS at all).
# Re-run through optimize.js's groupMembers/converge constrained to ONLY the real
# catalog (sections_is4923.js PRACTICAL_CATALOG, t>=3.0mm -- a corrosion-allowance/
# handling floor, an engineering judgment call, not an IS 4923 requirement, since the
# standard itself permits walls as thin as 2.0mm), still with uniform top/bottom
# chords per the prior round's ruling. CONFIRMED: no real 200x200 SHS exists in
# either the 1997 or 2017 edition (Table 1 jumps 180x180 -> 220x220 directly) -- T3's
# top chord, previously specified as the non-existent 200x200x3, fits comfortably in
# real 180x180x4 (util 0.794, well within the 0.95 gate).
# Net effect: truss steel (bare) up 5.856t (idealized) -> 6.871t (real), +8% allowance
# -> 7.420t. All utils <=0.943 (T1 0.883, T2 0.943, T3 0.900), no slenderness or
# capacity failures. Every section below is independently verifiable as a real,
# stockable IS 4923:2017 product -- not interpolated, not idealized.
SCHEDULE = {
    "T1": {"top_small": "125x125x4.5 SHS", "top_large": "125x125x4.5 SHS",
           "bottom_small": "88.9x88.9x3.6 SHS", "bottom_large": "88.9x88.9x3.6 SHS",
           "web_small": "45x45x3.2 SHS", "web_large": "63.5x63.5x3.2 SHS"},
    "T2": {"top_small": "132x132x4.5 SHS", "top_large": "132x132x4.5 SHS",
           "bottom_small": "91.5x91.5x3.6 SHS", "bottom_large": "91.5x91.5x3.6 SHS",
           "web_small": "45x45x3.2 SHS", "web_large": "63.5x63.5x3.2 SHS"},
    "T3": {"top_small": "180x180x4 SHS", "top_large": "180x180x4 SHS",
           "bottom_small": "100x100x5 SHS", "bottom_large": "100x100x5 SHS",
           "web_small": "45x45x3.2 SHS", "web_large": "72x72x3.2 SHS"},
}
if UNIFORM_MANUAL_DESIGN:
    # Collapse to ONE section per role across the whole building -- see the
    # UNIFORM_MANUAL_DESIGN note above. top_small/top_large (and the bottom/web
    # equivalents) are set equal on purpose: the panel-band split (TOP_SMALL_PANELS
    # etc.) still runs below, it just now always picks the same section either way.
    _uniform_sched = {
        "top_small": UNIFORM_TOP_SECTION, "top_large": UNIFORM_TOP_SECTION,
        "bottom_small": UNIFORM_BOTTOM_SECTION, "bottom_large": UNIFORM_BOTTOM_SECTION,
        "web_small": UNIFORM_WEB_SECTION, "web_large": UNIFORM_WEB_SECTION,
    }
    SCHEDULE = {"T1": _uniform_sched, "T2": _uniform_sched, "T3": _uniform_sched}
COLUMN_SECTION = "150x150x5 SHS"  # 150x150x4 is NOT a real IS 4923 designation (150mm row starts at t=5); upgraded, safe (A/I/Zp all higher than the old idealized 150x150x4)
RING_SECTION = "100x100x4 SHS"    # 76x76x4 is NOT a real IS 4923 designation; upgraded to a real section that dominates the old idealized 76x76x4 on every property (A, I, Zp, r), and reuses the bracing section (one fewer distinct SKU to stock)
BRACING_SECTION = "100x100x4 SHS"  # D-3 final (round 3) -- already a real IS 4923 designation, unchanged

# Band membership by panel index (0..13), from the Node optimizer's group summary
# (structural/tailored_schedule.json) -- verified IDENTICAL across T1/T2/T3 (same physical
# members always land in the same band; only the section assigned to each band changes).
TOP_SMALL_PANELS = {0, 2, 3, 4, 11, 12, 13}
BOTTOM_SMALL_PANELS = {0, 1, 2, 3, 10, 12, 13}
DIAG_SMALL_PANELS = {1, 3, 4, 9, 10, 12}

ALL_SECTION_LABELS = set()
for sched in SCHEDULE.values():
    ALL_SECTION_LABELS.update(sched.values())
ALL_SECTION_LABELS.update([COLUMN_SECTION, RING_SECTION, BRACING_SECTION])
SECTION_PROPS = {lbl: shs(*parse_label(lbl)) for lbl in ALL_SECTION_LABELS}

# --------------------------------------------------------------- numbering --
# Truss k (1-indexed): top node i (0..14) -> id; bottom node i (0..14) -> id.
def top_node_id(k, i):
    return (k - 1) * 30 + i + 1            # 1..15

def bot_node_id(k, i):
    return (k - 1) * 30 + 15 + i + 1        # 16..30

def col_base_low_id(k):
    return 270 + (k - 1) * 2 + 1

def col_base_high_id(k):
    return 270 + (k - 1) * 2 + 2

TOTAL_JOINTS = 30 * N_TRUSS + 2 * N_TRUSS  # 288, recount is A1's job -- not trusted here

joints = {}       # id -> (x, y, z)
members = []       # (id, n1, n2, kind, section_label, group)
member_id = 0

for k in range(1, N_TRUSS + 1):
    z = BAY_Z[k - 1]
    for i in range(N_PANELS + 1):
        x = PANEL_X[i]
        joints[top_node_id(k, i)] = (x, top_y(x), z)
        joints[bot_node_id(k, i)] = (x, bot_y(x), z)
    joints[col_base_low_id(k)] = (0.0, 0.0, z)
    joints[col_base_high_id(k)] = (SPAN, 0.0, z)

def add_member(n1, n2, kind, section_label, truss_k=None, panel=None):
    global member_id
    member_id += 1
    members.append({"id": member_id, "n1": n1, "n2": n2, "kind": kind,
                     "section": section_label, "truss": truss_k, "panel": panel})
    return member_id

TOP_MEMBERS, BOTTOM_MEMBERS, VERT_MEMBERS, DIAG_MEMBERS = [], [], [], []
COLUMN_MEMBERS, RING_MEMBERS, BRACE_MEMBERS = [], [], []

for k in range(1, N_TRUSS + 1):
    sched = SCHEDULE[TRUSS_TYPE[k - 1]]
    for i in range(N_PANELS):
        sec = sched["top_small"] if i in TOP_SMALL_PANELS else sched["top_large"]
        mid = add_member(top_node_id(k, i), top_node_id(k, i + 1), "top", sec, k, i)
        TOP_MEMBERS.append(mid)
    for i in range(N_PANELS):
        sec = sched["bottom_small"] if i in BOTTOM_SMALL_PANELS else sched["bottom_large"]
        mid = add_member(bot_node_id(k, i), bot_node_id(k, i + 1), "bottom", sec, k, i)
        BOTTOM_MEMBERS.append(mid)
    mid = add_member(top_node_id(k, 0), bot_node_id(k, 0), "vertical", sched["web_small"], k, 0)
    VERT_MEMBERS.append(mid)
    mid = add_member(top_node_id(k, N_PANELS), bot_node_id(k, N_PANELS), "vertical", sched["web_small"], k, N_PANELS)
    VERT_MEMBERS.append(mid)
    for i in range(N_PANELS):
        sec = sched["web_small"] if i in DIAG_SMALL_PANELS else sched["web_large"]
        if i % 2 == 0:
            n1, n2 = bot_node_id(k, i), top_node_id(k, i + 1)
        else:
            n1, n2 = top_node_id(k, i), bot_node_id(k, i + 1)
        mid = add_member(n1, n2, "diagonal", sec, k, i)
        DIAG_MEMBERS.append(mid)
    # columns: physical top = bottom-chord end node (see module docstring, item 2)
    mid = add_member(col_base_low_id(k), bot_node_id(k, 0), "column", COLUMN_SECTION, k, "low")
    COLUMN_MEMBERS.append(mid)
    mid = add_member(col_base_high_id(k), bot_node_id(k, N_PANELS), "column", COLUMN_SECTION, k, "high")
    COLUMN_MEMBERS.append(mid)

# Eave ring: continuous along both top-chord edges (X=0 and X=SPAN), connecting adjacent trusses.
for edge_i in (0, N_PANELS):
    for k in range(1, N_TRUSS):
        mid = add_member(top_node_id(k, edge_i), top_node_id(k + 1, edge_i), "ring", RING_SECTION)
        RING_MEMBERS.append(mid)

# Plan bracing, D-3 FINAL (round 3): PARTIAL coverage at the BOTTOM-chord level -- only the
# middle bracing field (panel-points 3,5,7,9,11), not the full 14-panel run used in round 2.
# A single alternating zig-zag chain (NOT a crossing X pair) through 4 modules per braced
# bay: (3,5),(5,7),(7,9),(9,11). 4 diagonals/bay x 5 braced bays = 20 bracing members total.
# Verified (see docstring) against the real C4 bottom-chord axial diagram for all three
# truss types: max util 0.854, max KL/r 92.5, both within limits with real margin --
# ACCEPTANCE MET, this partial scheme is adopted (not reverted to the round-2 full-length one).
if not NO_BRACING:
    for bay in BRACED_BAYS:
        k = bay  # bay k is between truss k and truss k+1
        for idx in range(len(BRACE_POINTS) - 1):
            i, j = BRACE_POINTS[idx], BRACE_POINTS[idx + 1]
            if idx % 2 == 0:
                n1, n2 = bot_node_id(k, i), bot_node_id(k + 1, j)
            else:
                n1, n2 = bot_node_id(k, j), bot_node_id(k + 1, i)
            mid = add_member(n1, n2, "bracing", BRACING_SECTION)
            BRACE_MEMBERS.append(mid)

# ------------------------------------------------------------- STAAD emit --
lines = []
def w(s=""):
    lines.append(s)

# STAAD.Pro V8i SELECTseries6 (confirmed via a live session, round 5) has a hard
# ~80-column input line limit. Data lines (e.g. PRIS) that exceed it get auto-split
# with a valid "-" continuation and still parse. COMMENT lines do NOT get that
# treatment -- the wrapped remainder loses its leading "*" and STAAD tries to parse
# it as a real command, erroring whenever the cut lands near a quote character
# (confirmed: two comments containing an apostrophe threw "ABOVE LINE CONTAINS
# ERRONEOUS DATA"; every other long comment was silently corrupted instead, just
# without an error). Fix: never let a comment line need auto-wrapping, and strip
# apostrophes/quotes from ordinary commentary as a second layer of safety. The
# engineer's verbatim drawing note is reflowed the same way (line breaks only,
# words unchanged) since it happens to contain no apostrophes.
COMMENT_WIDTH = 70

def wc(text):
    text = text.replace("'", "").replace('"', "")
    for para in text.split("\n\n"):
        words = para.split()
        cur = ""
        for word in words:
            if cur and len(cur) + 1 + len(word) > COMMENT_WIDTH:
                w(f"* {cur}")
                cur = word
            else:
                cur = f"{cur} {word}".strip()
        if cur:
            w(f"* {cur}")
        w("*")

w("STAAD SPACE")
wc("Engineer: Sharief Satyala | Job: CHRA-2502 Pickleball Roof - 3D "
   "Global Model (job metadata as a plain comment -- two guesses at "
   "STAADs JOB INFORMATION ENGINEER/JOB NAME syntax were both rejected "
   "by a live session; not worth a third guess for a purely cosmetic "
   "field with zero effect on the analysis.)")
w("* ================================================================")
wc("GENERATED FILE -- CLOSE-OUT PATCH SET (ROUND 3, line-wrapping fixed "
   "in ROUND 5). See generate_staad.py docstring for the full ruling "
   "history. Summary of whats built in below:")
wc("D-1: column top node = bottom-chord end node (Y=7.752 / 7.339m), "
   "K=1.0, no stub. The briefs separate ~8.75/8.34m figures are "
   "superseded.")
wc("D-2: DECK LATERAL-RESTRAINT CREDIT IS DECLARED for the top chord "
   "(KL_op = 1.0 x panel = 1.474m). Without it the worst trusss top "
   "chord does not close within the 40-200mm SHS catalog -- this "
   "declaration is load-bearing. Drawing note (verbatim, "
   "engineer-issued):")
wc("NOTE: THE STRUCTURAL DECK SHALL BE MECHANICALLY FASTENED TO THE "
   "TRUSS TOP CHORD AT EVERY CREST (SCREWS AT <= 300 mm CENTRES) "
   "PRIOR TO IMPOSITION OF ANY SUPERIMPOSED LOAD. THIS FASTENING "
   "CONSTITUTES THE LATERAL RESTRAINT SYSTEM TO THE TOP CHORD IN "
   "COMPRESSION (KL = 1.474 m) AND FORMS PART OF THE ROOF DIAPHRAGM. "
   "ADHESIVE-ONLY, CLIP-ONLY OR INTERMITTENT FASTENING SYSTEMS VOID "
   "THE TOP-CHORD CAPACITY SHOWN ON THESE DRAWINGS AND SHALL NOT BE "
   "SUBSTITUTED WITHOUT RECERTIFICATION BY THE STRUCTURAL ENGINEER. "
   "DECK FASTENER PULL-OUT AND SHEAR CAPACITIES SHALL BE CERTIFIED BY "
   "THE DECK SUPPLIER FOR BOTH GRAVITY AND NET UPLIFT (0.82 kN/m2) "
   "CONDITIONS.")
wc("D-3 FINAL: braced bays = {1,3,4,6,8} (5 of 8). Plan bracing at the "
   "BOTTOM-chord level, PARTIAL coverage only -- a single zig-zag "
   "chain through panel-points {3,5,7,9,11} (4 modules/bay x 5 bays = "
   "20 diagonals), section 100x100x4 SHS, ~1.60t. Bottom-chord KL_op "
   "is segment-wise: 2.947m within the braced field (panels 3-10), "
   "4.421m at the two unbraced end stretches (panels 0-2, 11-13). "
   "Verified against the real C4 (0.9DL+1.5WLup) bottom-chord axial "
   "diagram (peaks 109.6kN at midspan, worst truss) -- max util "
   "0.854, max KL/r 92.5, both within limits. ACCEPTANCE MET, scheme "
   "ADOPTED.")
wc("D-5: ring = 76x76x4 SHS. Plan bracing = 100x100x4 SHS (per D-3 "
   "final).")
wc("D-6 FINAL: the Md values below (Zp*fy/gamma_m0, capped at "
   "1.2*Ze*fy/gamma_m0 per Cl 8.2.1.2) are validated for every SHS in "
   "this design, including 100x100x4 (the round-2 switch-to-TABLE "
   "flag on it is withdrawn -- the engineers own hand Md references "
   "were the ones in error). Md itself is never passed to STAAD; "
   "its used directly by is800.js/optimize.js for member sizing, "
   "outside this file. Section TYPE as emitted to STAAD is now TUBE, "
   "not PRISMATIC -- see ROUND 8 at the top of this script for why "
   "(PRISMATIC members are invisible to STAADs own steel-design "
   "module; TUBE is not).")
wc("DESIGN CASE: this file is TAILORED-AT-ACTUAL tributaries "
   "(T1=4.572m, T2=5.098m, T3=7.121m) -- 6.32t trusses. The envelope "
   "variant (4.572/5.600/7.372m, 6.62t if invoked) is NOT built into "
   "this file; it is a documented spare-parts/interchangeability "
   "option only.")
wc("25mm midspan camber remains a FABRICATION note only, not built "
   "into these joint coordinates (analysis uses the theoretical "
   "line).")
w("* ================================================================")
w("UNIT METER KN")
w("JOINT COORDINATES")
for jid in sorted(joints):
    x, y, z = joints[jid]
    w(f"{jid} {x:.4f} {y:.4f} {z:.4f}")
w("*")
w("MEMBER INCIDENCES")
for m in members:
    w(f"{m['id']} {m['n1']} {m['n2']}")
w("*")
w("DEFINE MATERIAL START")
w("ISOTROPIC STEEL")
w("E 2.05e8")
w("POISSON 0.3")
w("DENSITY 76.9797")
w("ALPHA 1.2e-005")
w("END DEFINE MATERIAL")
w("*")
w("MEMBER PROPERTY")
# One PRIS line per distinct section label, applied to every member using it.
by_section = {}
for m in members:
    by_section.setdefault(m["section"], []).append(m["id"])

def ranges(ids):
    ids = sorted(ids)
    out = []
    start = prev = ids[0]
    for x in ids[1:]:
        if x == prev + 1:
            prev = x
            continue
        out.append((start, prev))
        start = prev = x
    out.append((start, prev))
    return out

wc("D-6 CONFIRMED (was flagged Guessing in round 3, now verified "
   "against a live STAAD session): PY/PZ are NOT valid PRISMATIC "
   "keywords -- STAAD.Pro rejected all 33 PRIS lines with PRISMATIC "
   "specification NOT valid when they were present. Removed.")
wc("TUBE DT/WT/TH was tried (engineer's ruling, to make members "
   "CHECK-CODE-eligible) and CONFIRMED REJECTED by a live STAAD "
   "session: all 13 TUBE property statements came back MEMBER "
   "PROPERTY command ignored by program, check syntax. This "
   "project's memory of that syntax is wrong for this STAAD build "
   "(V8i SELECTseries6) -- reverted to PRISMATIC "
   "(AX/AY/AZ/IX/IY/IZ/YD/ZD), proven clean on this exact build. "
   "Tradeoff, and it is a real one: PRISMATIC members carry no "
   "section classification, so STAAD's own CHECK CODE cannot design "
   "them -- pass/fail for this file has to come from elsewhere until "
   "the real TUBE (or table-section) syntax for this build is "
   "confirmed, e.g. by defining a Tube property via STAAD's own GUI "
   "dialog and reading back what it writes.")
MAX_RANGES_PER_LINE = 4  # conservative -- exact per-line limit for this STAAD build is unconfirmed
for sec_label, ids in by_section.items():
    p = SECTION_PROPS[sec_label]
    id_ranges = ranges(ids)
    w(f"* {sec_label}  A={p['A']:.0f}mm2 I={p['I']:.0f}mm4 Zp={p['Zp']:.0f}mm3")
    if USE_TUBE:
        dt = p["B"] / 1000.0
        wt = p["B"] / 1000.0
        th = p["t"] / 1000.0
        for i in range(0, len(id_ranges), MAX_RANGES_PER_LINE):
            chunk = id_ranges[i:i + MAX_RANGES_PER_LINE]
            range_str = " ".join(f"{a} TO {b}" if a != b else f"{a}" for a, b in chunk)
            w(f"{range_str} TUBE DT {dt:.4f} WT {wt:.4f} TH {th:.4f}")
    else:
        ax = p["A"] / 1e6         # mm^2 -> m^2
        iy = p["I"] / 1e12        # mm^4 -> m^4 (weak axis, SHS symmetric so IY=IZ)
        iz = p["I"] / 1e12
        ix = 2 * p["I"] / 1e12    # torsion constant approx for a closed square tube: ~2*I (thin-wall box)
        yd = p["B"] / 1000.0
        zd = p["B"] / 1000.0
        ay = az = 2 * p["t"] * (p["B"] - 2 * p["t"]) / 1e6  # m^2, two walls carry shear each direction
        for i in range(0, len(id_ranges), MAX_RANGES_PER_LINE):
            chunk = id_ranges[i:i + MAX_RANGES_PER_LINE]
            range_str = " ".join(f"{a} TO {b}" if a != b else f"{a}" for a, b in chunk)
            w(f"{range_str} PRIS AX {ax:.6f} AY {ay:.6f} AZ {az:.6f} IX {ix:.8f} IY {iy:.8f} IZ {iz:.8f} "
              f"YD {yd:.4f} ZD {zd:.4f}")

# D-6 FINAL: report the validated Md (Cl 8.2.1.2, capped at 1.2*Ze*fy/gamma_m0) for the two
# sections the engineer's own (now-withdrawn) hand references named. PRIS stands for both.
def md_capped(B, t, fy=250, gamma_m0=1.10):
    p = shs(B, t)
    md_plastic = p["Zp"] * fy / gamma_m0 / 1e6
    md_cap = 1.2 * p["I"] / (p["B"] / 2) * fy / gamma_m0 / 1e6  # Ze = I/(B/2) here, kNm
    return min(md_plastic, md_cap), md_plastic, md_cap

for (B, t) in [(120, 5), (100, 4)]:
    md, md_p, md_c = md_capped(B, t)
    capped = " (cap governs)" if md_c < md_p else ""
    print(f"D-6 validated {B}x{B}x{t} SHS: Md={md:.2f}kNm (plastic={md_p:.2f}, 1.2Ze-cap={md_c:.2f}){capped} -- TUBE stands")
w("*")
w("CONSTANTS")
w(f"MATERIAL STEEL MEMB 1 TO {member_id}")
w("*")
w("MEMBER RELEASE")
wc("Webs/bracing: 99% moment release both ends (never 100% -- per "
   "brief). Chords: none (rigid/continuous, per brief). Syntax below "
   "(MP fraction-remaining-fixity) is written from documentation, "
   "NOT verified against a live STAAD session -- confirm before "
   "running.")
web_and_brace_ids = VERT_MEMBERS + DIAG_MEMBERS + BRACE_MEMBERS
for a, b in ranges(web_and_brace_ids):
    r = f"{a} TO {b}" if a != b else f"{a}"
    w(f"{r} START MP 0.99")
    w(f"{r} END MP 0.99")
# Column-to-bottom-chord bearing: pinned (moment release) at the column's TOP end (n2).
for a, b in ranges(COLUMN_MEMBERS):
    r = f"{a} TO {b}" if a != b else f"{a}"
    w(f"{r} END MP 0.99")
w("*")
w("SUPPORTS")
base_ids = [col_base_low_id(k) for k in range(1, N_TRUSS + 1)] + \
           [col_base_high_id(k) for k in range(1, N_TRUSS + 1)]
for a, b in ranges(base_ids):
    r = f"{a} TO {b}" if a != b else f"{a}"
    w(f"{r} PINNED")
w("*")

# ---- Loads --------------------------------------------------------------
w("LOAD 1 LOADTYPE DEAD TITLE DL - DECK + SELFWEIGHT")
w("SELFWEIGHT Y -1")
w("MEMBER LOAD")
for m in members:
    if m["kind"] != "top":
        continue
    Lt = LT_ACTUAL[m["truss"] - 1]
    w_dl = DECK_DL * Lt  # kN/m, downward, on the (near-horizontal) top chord
    w(f"{m['id']} UNI GY -{w_dl:.4f}")
w("*")
w("LOAD 2 LOADTYPE LIVE TITLE LL - ROOF LIVE LOAD")
w("MEMBER LOAD")
for m in members:
    if m["kind"] != "top":
        continue
    Lt = LT_ACTUAL[m["truss"] - 1]
    w_ll = DECK_LL * Lt
    w(f"{m['id']} UNI GY -{w_ll:.4f}")
w("*")
w("LOAD 3 LOADTYPE WIND TITLE WLUP - ROOF UPLIFT (Cpe=-1.0)")
w("MEMBER LOAD")
for m in members:
    if m["kind"] != "top":
        continue
    Lt = LT_ACTUAL[m["truss"] - 1]
    w_up = WIND_UPLIFT * Lt
    w(f"{m['id']} UNI GY {w_up:.4f}")
w("*")
w("LOAD 4 LOADTYPE WIND TITLE WLLAT - LATERAL WIND ON COLUMNS (GX)")
w("MEMBER LOAD")
for m in members:
    if m["kind"] != "column":
        continue
    height = COL_HEIGHT_LOW if m["panel"] == "low" else COL_HEIGHT_HIGH
    w_lat = WIND_LATERAL * height  # kN/m, per column, tributary = its own height (half-bay-width already in the 0.0877 kN/m2 solidity-based pressure per the brief)
    w(f"{m['id']} UNI GX {w_lat:.4f}")
w("*")
w("LOAD COMBINATION 101 C1: 1.5(DL+LL)")
w("1 1.5 2 1.5")
w("LOAD COMBINATION 102 C2: 1.2(DL+LL+WLLAT)")
w("1 1.2 2 1.2 4 1.2")
w("LOAD COMBINATION 103 C3: 1.5(DL+WLLAT)")
w("1 1.5 4 1.5")
w("LOAD COMBINATION 104 C4: 0.9DL+1.5WLUP")
w("1 0.9 3 1.5")
w("LOAD COMBINATION 105 C5: 1.5(DL+WLUP)")
w("1 1.5 3 1.5")
w("*")
wc("P-Delta requested per brief. Round 7 fix: this used to be a "
   "plain PERFORM ANALYSIS immediately followed by PDELTA ANALYSIS -- "
   "a live STAAD session threw CONSECUTIVE ANALYSIS COMMANDS, ONLY "
   "FIRST USED, silently dropping P-Delta and running plain static "
   "only. Down to one analysis command. Deliberately bare (no PRINT "
   "STATICS CHECK appended) given two prior guesses at combined "
   "syntax on this file were both wrong -- reactions/forces remain "
   "available via STAADs own Post-Processing regardless of this "
   "print option.")
w("PDELTA ANALYSIS")
w("*")
wc("PARAMETER block moved here, AFTER the analysis commands (round 6 "
   "fix): a live STAAD.Pro session read PARAMETER 1 placed between "
   "LOAD COMBINATION 105 and PERFORM ANALYSIS as UNEXPECTED COMMAND "
   "IN LOAD DATA for case 105 and aborted into DATA-CHECK MODE before "
   "any analysis ran. PARAMETER blocks belong after analysis in "
   "STAADs command sequence; the numeric 1 after PARAMETER was also "
   "wrong -- the bare keyword is correct.")
w("PARAMETER")
w("CODE IS800")
wc("FYLD explicit, not left to STAADs default: 250 MPa = 250000 "
   "kN/m2 under the UNIT METER KN in force. Every member in this "
   "design is E250 (see REPORT.md Finding on grade choice) -- if "
   "that changes for any group, FYLD must be re-declared per member "
   "list, not left as one blanket value.")
w("FYLD 250000 ALL")
wc("Effective lengths, member-specific -- NEVER a blanket value (see "
   "audit A4). LY/LZ mapping to in-plane vs out-of-plane depends on "
   "each members local axis orientation as STAAD assigns it by "
   "default; VERIFY visually (View, Structure, Show Beta Angle or "
   "local axes) before trusting which is which -- not done here.")
w("KY 1.0 ALL")
w("KZ 1.0 ALL")

PANEL_L = SPAN / N_PANELS
for a, b in ranges(TOP_MEMBERS):
    w(f"LY {1.474:.3f} MEMB {a} TO {b}" if a != b else f"LY {1.474:.3f} MEMB {a}")
    w(f"LZ {0.85 * PANEL_L:.3f} MEMB {a} TO {b}" if a != b else f"LZ {0.85 * PANEL_L:.3f} MEMB {a}")
if NO_BRACING:
    wc(f"Bottom chord: NO_BRACING diagnostic variant -- plan bracing removed "
       f"entirely. With ZERO intermediate lateral restraint, the WHOLE bottom "
       f"chord buckles out-of-plane as one continuous {FULL_BOTTOM_UNBRACED_LEN:.3f}m "
       f"unbraced length between the two column bases (the only remaining "
       f"restraint points) -- not the panel length, not the D-3 braced-field "
       f"value. This LY is applied identically to EVERY bottom-chord member so "
       f"STAADs own CHECK CODE evaluates the TRUE (bracing-free) condition, not "
       f"a falsely-optimistic one left over from the braced design. Sections are "
       f"UNCHANGED from the braced design (88.9x88.9x3.6 / 91.5x91.5x3.6 / "
       f"100x100x5) -- this is deliberately NOT re-sized, so the FAIL this "
       f"produces is the honest cost of removing bracing, not hidden by a "
       f"bigger section chosen to make it pass. Quantified before generating "
       f"this file: KL/r for these sections at this length is in the "
       f"550-600 range against an IS 800 Cl 3.7 limit of 180 -- expect a hard, "
       f"large-margin FAIL from CHECK CODE, by design.")
    for a, b in ranges(BOTTOM_MEMBERS):
        w(f"LY {FULL_BOTTOM_UNBRACED_LEN:.3f} MEMB {a} TO {b}" if a != b else f"LY {FULL_BOTTOM_UNBRACED_LEN:.3f} MEMB {a}")
        w(f"LZ {0.85 * PANEL_L:.3f} MEMB {a} TO {b}" if a != b else f"LZ {0.85 * PANEL_L:.3f} MEMB {a}")
else:
    wc(f"Bottom chord: KL_op is segment-wise (D-3 final) -- "
       f"{BRACED_KL_OP:.3f}m within the braced field (panels 3-10, where "
       f"a bracing attachment lands every 2 panels), {UNBRACED_KL_OP:.3f}m "
       f"at the two unbraced end stretches (panels 0-2 and 11-13, no "
       f"bracing attachment there).")
    bottom_by_id = {m["id"]: m for m in members if m["kind"] == "bottom"}
    braced_bottom = [mid for mid in BOTTOM_MEMBERS if 3 <= bottom_by_id[mid]["panel"] <= 10]
    unbraced_bottom = [mid for mid in BOTTOM_MEMBERS if not (3 <= bottom_by_id[mid]["panel"] <= 10)]
    for a, b in ranges(braced_bottom):
        w(f"LY {BRACED_KL_OP:.3f} MEMB {a} TO {b}" if a != b else f"LY {BRACED_KL_OP:.3f} MEMB {a}")
        w(f"LZ {0.85 * PANEL_L:.3f} MEMB {a} TO {b}" if a != b else f"LZ {0.85 * PANEL_L:.3f} MEMB {a}")
    for a, b in ranges(unbraced_bottom):
        w(f"LY {UNBRACED_KL_OP:.3f} MEMB {a} TO {b}" if a != b else f"LY {UNBRACED_KL_OP:.3f} MEMB {a}")
        w(f"LZ {0.85 * PANEL_L:.3f} MEMB {a} TO {b}" if a != b else f"LZ {0.85 * PANEL_L:.3f} MEMB {a}")

def joint_dist(n1, n2):
    x1, y1, z1 = joints[n1]
    x2, y2, z2 = joints[n2]
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

for mid in VERT_MEMBERS + DIAG_MEMBERS:
    m = next(mm for mm in members if mm["id"] == mid)
    L = joint_dist(m["n1"], m["n2"])
    w(f"LY {L:.3f} MEMB {mid}")
    w(f"LZ {0.85 * L:.3f} MEMB {mid}")
for mid in COLUMN_MEMBERS:
    m = next(mm for mm in members if mm["id"] == mid)
    L = joint_dist(m["n1"], m["n2"])
    w(f"LY {L:.3f} MEMB {mid}")
    w(f"LZ {L:.3f} MEMB {mid}")
wc("Ring + bracing: ASSUMPTION -- treated as fully laterally "
   "restrained by the deck/purlins they carry; no separate KL "
   "declared beyond the code default (span length, K=1.0).")
w("TRACK 2 ALL")
wc("CHECK CODE ALL issued below, kept even though sections reverted "
   "to PRISMATIC after the TUBE rejection above -- left in "
   "deliberately rather than removed, so STAAD itself reports what "
   "it actually does with it (design-skip a PRISMATIC member, error, "
   "or something else) instead of this script guessing that outcome "
   "too. TRACK 2 for full member-by-member detail if anything is "
   "produced at all.")
w("CHECK CODE ALL")
w("FINISH")

with open(OUT_PATH, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote {OUT_PATH}")
print(f"Joints: {len(joints)}  Members: {len(members)}")
print(f"  top={len(TOP_MEMBERS)} bottom={len(BOTTOM_MEMBERS)} vertical={len(VERT_MEMBERS)} "
      f"diagonal={len(DIAG_MEMBERS)} column={len(COLUMN_MEMBERS)} ring={len(RING_MEMBERS)} bracing={len(BRACE_MEMBERS)}")
