#!/usr/bin/env python3
"""
CHRA-2502 Pickleball Roof -- 3D STAAD.Pro CONNECT Edition input generator.

Builds the full 9-truss + 18-column + eave-ring + plan-bracing model from the
n=14 Warren fish-belly winner topology (structural/REPORT.md), using PRISM
(explicit AX/IY/IZ/YD/ZD) section properties instead of TABLE lookups, so the
model never depends on a STAAD section-table name resolving in some specific
country/build.

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

Run: python3 generate_staad.py
Output: CHRA2502_3D_Final.std
"""
import math

OUT_PATH = "CHRA2502_3D_Final.std"

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

# --------------------------------------------------------- section catalog --
def shs(B, t):
    """Sharp-corner SHS properties. Returns dict with A(mm^2), I(mm^4), Zp(mm^3), r(mm)."""
    h = B - 2 * t
    A = 4 * t * (B - t)
    I = (B**4 - h**4) / 12
    Zp = (B**3 - h**3) / 4
    r = math.sqrt(I / A)
    return {"B": B, "t": t, "A": A, "I": I, "Zp": Zp, "r": r, "label": f"{B}x{B}x{t} SHS"}

def parse_label(lbl):
    # "150x150x3 SHS" -> (150, 3)
    dims = lbl.split(" ")[0].split("x")
    return int(dims[0]), float(dims[2])

# Grouped sections per truss type, from structural/optimize.js (Node engine),
# deck-lateral-credit-declared case -- see tailored_schedule.json.
SCHEDULE = {
    "T1": {"top_small": "110x110x3 SHS", "top_large": "150x150x3 SHS",
           "bottom_small": "75x75x3.6 SHS", "bottom_large": "100x100x3 SHS",
           "web_small": "40x40x3.6 SHS", "web_large": "60x60x3 SHS"},
    "T2": {"top_small": "120x120x3 SHS", "top_large": "160x160x3 SHS",
           "bottom_small": "100x100x3 SHS", "bottom_large": "90x90x3.6 SHS",
           "web_small": "50x50x3 SHS", "web_large": "60x60x3 SHS"},
    "T3": {"top_small": "150x150x3 SHS", "top_large": "200x200x3 SHS",
           "bottom_small": "120x120x3 SHS", "bottom_large": "140x140x3 SHS",
           "web_small": "50x50x3 SHS", "web_large": "75x75x3 SHS"},
}
COLUMN_SECTION = "150x150x4 SHS"
RING_SECTION = "76x76x4 SHS"       # D-5 ruling
BRACING_SECTION = "100x100x4 SHS"  # D-3 final (round 3) -- partial-bracing scheme, verified above

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

w("STAAD SPACE")
w(f"START JOB INFORMATION")
w(f"ENGINEER Sharief Satyala")
w(f"JOB NAME CHRA-2502 Pickleball Roof - 3D Global Model")
w(f"END JOB INFORMATION")
w("* ================================================================")
w("* GENERATED FILE -- CLOSE-OUT PATCH SET (ROUND 3). See generate_staad.py")
w("* docstring for the full ruling history. Summary of what's built in below:")
w("*")
w("*  D-1: column top node = bottom-chord end node (Y=7.752 / 7.339m), K=1.0,")
w("*      no stub. The brief's separate '~8.75/8.34m' figures are superseded.")
w("*")
w("*  D-2: DECK LATERAL-RESTRAINT CREDIT IS DECLARED for the top chord")
w("*      (KL_op = 1.0 x panel = 1.474m). Without it the worst truss's top")
w("*      chord does not close within the 40-200mm SHS catalog -- this")
w("*      declaration is load-bearing. Drawing note (verbatim, engineer-issued):")
w("*")
w("*      NOTE: THE STRUCTURAL DECK SHALL BE MECHANICALLY FASTENED TO THE TRUSS")
w("*      TOP CHORD AT EVERY CREST (SCREWS AT <= 300 mm CENTRES) PRIOR TO")
w("*      IMPOSITION OF ANY SUPERIMPOSED LOAD. THIS FASTENING CONSTITUTES THE")
w("*      LATERAL RESTRAINT SYSTEM TO THE TOP CHORD IN COMPRESSION (KL = 1.474 m)")
w("*      AND FORMS PART OF THE ROOF DIAPHRAGM. ADHESIVE-ONLY, CLIP-ONLY OR")
w("*      INTERMITTENT FASTENING SYSTEMS VOID THE TOP-CHORD CAPACITY SHOWN ON")
w("*      THESE DRAWINGS AND SHALL NOT BE SUBSTITUTED WITHOUT RECERTIFICATION BY")
w("*      THE STRUCTURAL ENGINEER. DECK FASTENER PULL-OUT AND SHEAR CAPACITIES")
w("*      SHALL BE CERTIFIED BY THE DECK SUPPLIER FOR BOTH GRAVITY AND NET")
w("*      UPLIFT (0.82 kN/m2) CONDITIONS.")
w("*")
w("*  D-3 FINAL: braced bays = {1,3,4,6,8} (5 of 8). Plan bracing at the")
w("*      BOTTOM-chord level, PARTIAL coverage only -- a single zig-zag chain")
w("*      through panel-points {3,5,7,9,11} (4 modules/bay x 5 bays = 20")
w("*      diagonals), section 100x100x4 SHS, ~1.60t. Bottom-chord KL_op is")
w("*      segment-wise: 2.947m within the braced field (panels 3-10), 4.421m")
w("*      at the two unbraced end stretches (panels 0-2, 11-13). Verified")
w("*      against the real C4 (0.9DL+1.5WLup) bottom-chord axial diagram")
w("*      (peaks 109.6kN at midspan, worst truss) -- max util 0.854, max")
w("*      KL/r 92.5, both within limits. ACCEPTANCE MET, scheme ADOPTED.")
w("*")
w("*  D-5: ring = 76x76x4 SHS. Plan bracing = 100x100x4 SHS (per D-3 final).")
w("*")
w("*  D-6 FINAL: PRIS stands for every SHS in this design, including")
w("*      100x100x4 (the round-2 'switch to TABLE' flag on it is withdrawn --")
w("*      the engineer's own hand Md references were the ones in error; this")
w("*      engine's Zp*fy/gamma_m0 values, capped at 1.2*Ze*fy/gamma_m0 per")
w("*      Cl 8.2.1.2, are validated). PRIS carries AY/AZ (shear area) and")
w("*      PY/PZ (plastic modulus) -- PY/PZ flagged [Guessing] as possibly")
w("*      unsupported by STAAD's PRIS command; delete those two tokens per")
w("*      line if the parser rejects them.")
w("*")
w("*  DESIGN CASE: this file is TAILORED-AT-ACTUAL tributaries (T1=4.572m,")
w("*      T2=5.098m, T3=7.121m) -- 6.32t trusses. The envelope variant")
w("*      (4.572/5.600/7.372m, 6.62t if invoked) is NOT built into this file;")
w("*      it is a documented spare-parts/interchangeability option only.")
w("*")
w("*  25mm midspan camber remains a FABRICATION note only, not built into")
w("*  these joint coordinates (analysis uses the theoretical line).")
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

w("* D-6 ruling: AY/AZ (shear area, 2*t*(B-2t) per wall pair) added below. PY/PZ (plastic")
w("* modulus) added too, but [Guessing] STAAD's PRIS may not accept them as inputs at all --")
w("* if the parser rejects the PY/PZ tokens, delete them from every PRIS line below.")
for sec_label, ids in by_section.items():
    p = SECTION_PROPS[sec_label]
    ax = p["A"] / 1e6         # mm^2 -> m^2
    iy = p["I"] / 1e12        # mm^4 -> m^4 (weak axis, SHS symmetric so IY=IZ)
    iz = p["I"] / 1e12
    ix = 2 * p["I"] / 1e12     # torsion constant approx for a closed square tube: ~2*I (thin-wall box)
    yd = p["B"] / 1000.0
    zd = p["B"] / 1000.0
    ay = az = 2 * p["t"] * (p["B"] - 2 * p["t"]) / 1e6  # m^2, two walls carry shear each direction
    py = pz = p["Zp"] / 1e9  # mm^3 -> m^3
    id_ranges = ranges(ids)
    range_str = " ".join(f"{a} TO {b}" if a != b else f"{a}" for a, b in id_ranges)
    w(f"* {sec_label}  (A={p['A']:.0f}mm2 I={p['I']:.0f}mm4 Zp={p['Zp']:.0f}mm3 -- sharp-corner formula)")
    w(f"{range_str} PRIS AX {ax:.6f} AY {ay:.6f} AZ {az:.6f} IX {ix:.8f} IY {iy:.8f} IZ {iz:.8f} "
      f"YD {yd:.4f} ZD {zd:.4f} PY {py:.8f} PZ {pz:.8f}")

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
    print(f"D-6 validated {B}x{B}x{t} SHS: Md={md:.2f}kNm (plastic={md_p:.2f}, 1.2Ze-cap={md_c:.2f}){capped} -- PRIS stands")
w("*")
w("CONSTANTS")
w(f"MATERIAL STEEL MEMB 1 TO {member_id}")
w("*")
w("MEMBER RELEASE")
w("* Webs/bracing: 99% moment release both ends (never 100% -- per brief). Chords: none")
w("* (rigid/continuous, per brief). Syntax below (MP fraction-remaining-fixity) is written")
w("* from documentation, NOT verified against a live STAAD session -- confirm before running.")
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
w("*")
w("PARAMETER 1")
w("CODE IS800")
w("* Effective lengths, member-specific -- NEVER a blanket value (see audit A4).")
w("* LY/LZ mapping to in-plane vs out-of-plane depends on each member's local axis")
w("* orientation as STAAD assigns it by default; VERIFY visually (View > Structure >")
w("* Show Beta Angle / local axes) before trusting which is which -- not done here.")
w("KY 1.0 ALL")
w("KZ 1.0 ALL")

def joint_dist(n1, n2):
    x1, y1, z1 = joints[n1]
    x2, y2, z2 = joints[n2]
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

PANEL_L = SPAN / N_PANELS
for a, b in ranges(TOP_MEMBERS):
    w(f"LY {1.474:.3f} MEMB {a} TO {b}" if a != b else f"LY {1.474:.3f} MEMB {a}")
    w(f"LZ {0.85 * PANEL_L:.3f} MEMB {a} TO {b}" if a != b else f"LZ {0.85 * PANEL_L:.3f} MEMB {a}")
w(f"* Bottom chord: KL_op is segment-wise (D-3 final) -- {BRACED_KL_OP:.3f}m within the braced")
w(f"* field (panels 3-10, where a bracing attachment lands every 2 panels), {UNBRACED_KL_OP:.3f}m")
w(f"* at the two unbraced end stretches (panels 0-2 and 11-13, no bracing attachment there).")
bottom_by_id = {m["id"]: m for m in members if m["kind"] == "bottom"}
braced_bottom = [mid for mid in BOTTOM_MEMBERS if 3 <= bottom_by_id[mid]["panel"] <= 10]
unbraced_bottom = [mid for mid in BOTTOM_MEMBERS if not (3 <= bottom_by_id[mid]["panel"] <= 10)]
for a, b in ranges(braced_bottom):
    w(f"LY {BRACED_KL_OP:.3f} MEMB {a} TO {b}" if a != b else f"LY {BRACED_KL_OP:.3f} MEMB {a}")
    w(f"LZ {0.85 * PANEL_L:.3f} MEMB {a} TO {b}" if a != b else f"LZ {0.85 * PANEL_L:.3f} MEMB {a}")
for a, b in ranges(unbraced_bottom):
    w(f"LY {UNBRACED_KL_OP:.3f} MEMB {a} TO {b}" if a != b else f"LY {UNBRACED_KL_OP:.3f} MEMB {a}")
    w(f"LZ {0.85 * PANEL_L:.3f} MEMB {a} TO {b}" if a != b else f"LZ {0.85 * PANEL_L:.3f} MEMB {a}")
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
w("* Ring + bracing: ASSUMPTION -- treated as fully laterally restrained by the deck/purlins")
w("* they carry; no separate KL declared beyond the code default (span length, K=1.0).")
w("*")
w("* NOTE: no CHECK CODE issued -- member sizing/utilization in this project comes from")
w("* the independent Node stiffness engine (structural/optimize.js), not from STAAD's")
w("* own IS800 design module. This PARAMETER block documents the effective-length basis")
w("* for a reviewer who DOES want to run STAAD's CHECK CODE as a second opinion.")
w("*")
w("PERFORM ANALYSIS PRINT STATICS CHECK")
w("* P-Delta requested per brief -- CONNECT Edition syntax below;")
w("* NOT verified against an actual STAAD session (A9 -- confirm before running).")
w("PDELTA ANALYSIS")
w("FINISH")

with open(OUT_PATH, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote {OUT_PATH}")
print(f"Joints: {len(joints)}  Members: {len(members)}")
print(f"  top={len(TOP_MEMBERS)} bottom={len(BOTTOM_MEMBERS)} vertical={len(VERT_MEMBERS)} "
      f"diagonal={len(DIAG_MEMBERS)} column={len(COLUMN_MEMBERS)} ring={len(RING_MEMBERS)} bracing={len(BRACE_MEMBERS)}")
