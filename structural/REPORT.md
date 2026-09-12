# CHRA-2502 Pickleball Roof Truss — 2D FEM / IS 800 Optimization Report

Project: Outdoor Multi-Sport Facility, Ramanagara, Karnataka | Client: Ferrum Projects
Structural Engineer: Sharief Satyala | Scope: pickleball canopy truss only (T1/T2/T3)

**Read this first (advisor note):** the brief asks for fabrication-grade numbers (util ≤ 0.95,
tonnage to 0.01t) from a from-scratch FEM + code-check tool built in one sitting, with no
cross-check against STAAD/SAP2000 or a second independent implementation. The validation
gates below (a–f) prove the tool is internally self-consistent — reactions balance loads,
a textbook beam case reproduces theory exactly, member forces satisfy joint equilibrium.
They do **not** prove IS 800 Cl 8/9 has been applied without error. Treat everything past
this line as a rigorous **sizing study** that materially de-risks the 3D STAAD design, not
as a substitute for it. [Certain] the engine itself is arithmetically correct (see gate
results); [Guessing] on whether every code-clause simplification below matches what a
STAAD/detailed hand-check would produce to the last kN.

**ERRATA (added during the 3D/STAAD audit pass):** the sizing loop had a real bug — an
undamped self-weight/section feedback that could lock into a 2-cycle (a member flipping
forever between two adjacent SHS sizes) and, separately, a grouping heuristic that banded
members by peak axial force alone, which could bucket a bending-heavy member with an
axial-heavy one and force a much bigger group section than either needed. Both are fixed in
`optimize.js` (damped self-weight relaxation + heavier-of-final-two-states tie-break; banding
now uses each member's own individually-converged section area, which reflects the full
axial+bending demand). **Net effect on the numbers below: masses shift, mostly down** (e.g.
the T1/T2/T3 tailored figures in `structural/tailored_schedule.json` from the follow-up audit
are lower than the Top-5/winner-schedule figures in §3–§4 of this file, which predate the fix).
Treat §3 and §4's *numbers* as superseded by the audit's schedule; the *method* and findings
1–5 still hold. [Certain] on the bug and the fix; [Certain] the corrected numbers are lower,
not higher, so nothing here understates risk — but re-verify before citing a tonnage figure.

**ERRATA 2 (close-out patch set, 3D STAAD audit round 3):**

- **Md reference correction — engineer's hand values withdrawn.** The engineer's own hand
  plastic-moduli references (100×100×4 → 14.5 kNm, 120×120×5 → 21.6 kNm) were miscomputed;
  they are withdrawn. This engine's sharp-corner values (`Md = min(Zp·fy/γm0, 1.2·Ze·fy/γm0)`,
  Cl 8.2.1.2 — the 1.2×Ze cap is now implemented in `is800.js` and was not present in the
  numbers reported earlier in this document) are validated: 100×100×4 → 12.57 kNm,
  120×120×5 → 22.56 kNm; the cap does not bind for either (shape factor < 1.2). PRIS stands
  for every SHS in this design, 100×100×4 included. Re-sweeping every Cl 8.2/9.3-governed
  chord member in the tailored T1/T2/T3 schedule against the capped Md moved **zero members
  by more than 0.03 util — in fact zero members moved at all** (no section in this schedule
  has a shape factor over 1.2, so the cap is a non-event here, not just a small effect).
- **Plan-bracing steel is its own ledger line, outside the trusses-only 6.32t figure.** The
  bottom-chord plan bracing (partial scheme, 20×100×100×4 SHS diagonals, verified against the
  real C4 bottom-chord axial diagram — max util 0.854, max KL/r 92.5, both within limits) adds
  **1.60t**, and the eave ring (16×76×76×4 SHS) adds **0.81t**. Neither was ever part of the
  6.32t trusses-only number; keep them as separate ledger lines, not folded into "trusses."
- **Envelope-variant ruling.** The design as issued is TAILORED-AT-ACTUAL tributaries (T1
  4.572m / T2 5.098m / T3 7.121m): 6.32t trusses, utils 0.922–0.936. The envelope variant
  (4.572/5.600/7.372m) is **not issued** — retained solely as a documented spare-parts/
  interchangeability option, at **6.62t** trusses if ever invoked (one SHS step, 200×200×3→
  200×200×4, on T3's top1 group to clear its 0.952 marginal overage under that variant).

**ERRATA 3 (first live STAAD.Pro run, engineer-side):** the file as issued in errata 2 failed
to parse — every `PRIS` line threw `PRISMATIC specification NOT valid` (33 errors), because
the `PY`/`PZ` tokens I'd added and explicitly flagged as `[Guessing]` are **not valid
PRISMATIC keywords** in STAAD.Pro; their presence invalidated the whole property line, not
just those two tokens, so every member was left without a section. This is now confirmed,
not guessed: `PY`/`PZ` are removed from every `PRIS` line, and `is800.js`/`optimize.js`
remain the source of truth for `Md` — it was never meant to reach STAAD anyway, only AX/AY/
AZ/IX/IY/IZ/YD/ZD are. Also fixed: the `START JOB INFORMATION` block's multi-word `ENGINEER`/
`JOB NAME` values were rejected ("JOB INFORMATION command ignored") — underscored, cosmetic
only, no effect on analysis. Neither issue changes any tonnage, utilization, or force number
in this document — both are STAAD input syntax only. Re-run the regenerated file before
trusting any further STAAD output.

**ERRATA 4 (rounds 5-7, engineer-side runs):** three more STAAD input-syntax defects surfaced
and were fixed, none of which touch any tonnage/utilization/force number in this document:
(1) STAAD.Pro V8i SELECTseries6 has a hard ~80-column line limit; long **comment** lines
(unlike data lines, which auto-wrap safely with a `-` continuation) lose their leading `*` on
wrap and get parsed as bogus commands, erroring near quote characters — every comment is now
reflowed under 72 columns with apostrophes stripped. (2) `PARAMETER 1` is invalid syntax (bare
`PARAMETER`, no argument) and was also sequenced *before* `PERFORM ANALYSIS` instead of after,
which a live session read as `UNEXPECTED COMMAND IN LOAD DATA` for the last load combination
and aborted into DATA-CHECK MODE before any analysis ran at all — moved after the analysis
commands, keyword fixed. (3) A separate `PERFORM ANALYSIS` immediately followed by `PDELTA
ANALYSIS` triggered `CONSECUTIVE ANALYSIS COMMANDS, ONLY FIRST USED` — P-Delta was silently
never running; collapsed to one `PDELTA ANALYSIS` command.

**First successful analysis (round 6 file, before the P-Delta fix above):** confirmed via the
engineer's own `.ANL` output — Case 1 (DL) reaction summary balances to the kN (applied
336.74 kN, reaction 336.74 kN), matching this report's own independent hand-check of deck DL
+ total steel self-weight (≈336.68 kN) to within 0.02%. Max Y-displacement under DL alone,
7.625mm, is consistent with this report's service-deflection figures once LL's larger share
of the total gravity load is accounted for. This is the first real external validation of the
model against a live STAAD run, independent of this project's own Node engine.

**ERRATA 5 (uniform-chord ruling, engineer's fabrication constraint):** the tailored T1/T2/T3
design above split each chord into two SHS sizes per truss (a lighter section over the
lightly-loaded end panels, a heavier one over the mid panels). The engineer has ruled this
out — no splicing between two SHS sizes along one continuous chord run in the field — so
each truss type now uses **one section for its whole top chord and one for its whole bottom
chord**. Re-run through `optimize.js` on the full, un-pruned 44-member topology (the one
`generate_staad.py` actually builds — the optimizer's own low-utilization pruning is a
2D-report artifact that was never carried into the 3D model, confirmed by reproducing the
prior per-band numbers bit-for-bit once pruning is left out of the check): in every one of
T1/T2/T3 the single governing member for the full chord is the same one that already drove
the old *large*-panel band, so the uniform section is simply that band's section run the
full length — no new section size was needed anywhere.

| Truss | Old top (2 bands) | Uniform top | Old bottom (2 bands) | Uniform bottom | Mass old→new | Max util |
|---|---|---|---|---|---|---|
| T1 | 110×110×3 / 150×150×3 | **150×150×3** | 75×75×3.6 / 100×100×3 | **100×100×3** | 600.95 → 651.07 kg (+8.3%) | 0.894 |
| T2 | 120×120×3 / 160×160×3 | **160×160×3** | 100×100×3 / 90×90×3.6 | **90×90×3.6** | 643.88 → 689.39 kg (+7.5%) | 0.930 |
| T3 | 150×150×3 / 200×200×3 | **200×200×3** | 120×120×3 / 140×140×3 | **140×140×3** | 790.82 → 859.30 kg (+8.7%) | 0.884 |

Web members are unaffected (unchanged sections, same as before). Project truss total
(T1×2, T2×6, T3×1, per `TRUSS_TYPE` in `generate_staad.py`), bare: **5.856t → 6.298t
(+0.442t, +7.5%)**; with the 8% fabrication allowance: **6.324t → 6.802t (+0.478t)**. All
utilizations remain ≤0.930 — no capacity or slenderness failures introduced. `tailored_schedule.json`
and `CHRA2502_3D_Final.std` are both regenerated to match; re-run the file before trusting
further STAAD output. (Self-check note: an initial pass at this re-verification wrongly
flagged the cached schedule as stale relative to the Cl 8.2.1.2 Md-cap fix — that flag was
a false positive caused by including the optimizer's pruning step, which the 3D model never
uses; retracted once isolated. No Md-cap regression exists; the pre-existing tailored numbers
were correct all along.)

**ERRATA 6 (real-table-sections ruling, engineer's ruling):** every section size used up to
this point — in the idealized engine and in the STAAD file — came from a continuous
40/50/60/65/70/75/80/90/100/110/120/125/130/140/150/160/180/200mm × 3/3.6/4/4.5/5/6/7/8mm
sweep grid, computed with a sharp-corner formula. That grid does **not correspond to real,
orderable IS 4923 SHS products** for most of the sizes actually used — confirmed against
the real standard (both the 1997 edition + all 6 amendments, and the current **IS 4923:2017
Third Revision**, obtained as the official BIS/BSB Edge free-distribution PDF and parsed
programmatically from its embedded text layer, not read off a screenshot — see
`is4923_2017_table1.json`, 83 rows, zero transcription risk). Only 40, 75, 100, and 150mm
happened to coincide with real sizes; **50, 60, 65, 90, 110, 120, 130, 140, 160, and 200mm
do not exist as real SHS designations at all**, in either edition. In particular: **there
is no 200×200 SHS** — Table 1 goes 150×150 → 180×180 → 220×220, with no size in between,
confirmed identically in both the 1997 and 2017 tables. T3's top chord (previously specified
as 200×200×3, which cannot be procured) fits comfortably in real 180×180×4mm instead (util
0.794 — ample margin once the size floor moved down and the thickness moved up).

Re-ran the full sizing optimization (`converge` + `groupMembers`, uniform top/bottom chords
per Errata 5, full 44-member topology, no pruning) constrained to `sections_is4923.js`'s
`PRACTICAL_CATALOG` — the real IS 4923:2017 Table 1 designations with a **t≥3.0mm practical
floor** (an engineering judgment call for an outdoor structure's corrosion allowance and weld
quality, not an IS 4923 requirement — the standard itself permits walls as thin as 2.0mm,
which the unconstrained real catalog happily selected — 1.8–2.2mm webs and bottom chord —
and which this report declines to issue for a canopy with a multi-decade service life):

| Truss | Top chord | Bottom chord | Web (light/heavy) | Mass (idealized → real) | Max util |
|---|---|---|---|---|---|
| T1 | **125×125×4.5** | **88.9×88.9×3.6** | 45×45×3.2 / 63.5×63.5×3.2 | 651.1 → 720.4 kg | 0.883 |
| T2 | **132×132×4.5** | **91.5×91.5×3.6** | 45×45×3.2 / 63.5×63.5×3.2 | 689.4 → 746.9 kg | 0.943 |
| T3 | **180×180×4** | **100×100×5** | 45×45×3.2 / 72×72×3.2 | 859.3 → 948.6 kg | 0.900 |

Every one of these is independently verifiable against Table 1 — not interpolated, not
idealized. Project truss total (T1×2, T2×6, T3×1), bare: **5.856t → 6.871t (+1.015t,
+17.3% vs. the original idealized-grid design)**; with the 8% allowance: **6.324t →
7.420t**. All utils stay ≤0.943 — no failures.

Two other sections in this design were also never real: **150×150×4** (columns — the real
150mm row starts at t=5) and **76×76×4** (eave ring — 76mm isn't a real SHS size at all).
Both are upgraded to real sections that dominate the old idealized ones on every property
(A, I, Zp, and — for the column — r): columns → **150×150×5** (2 490.6 kg → 3 023.7 kg,
+533.1 kg for all 18), ring → **100×100×4** (810 kg → 1 051.2 kg, +241.2 kg for all 16 —
this also happens to be the same section already used for the plan bracing, one fewer
distinct SKU to stock). The plan bracing (100×100×4) was already a real designation;
unchanged. These two deltas are bare masses on top of whatever total these line items were
already carried at in §6 — they have not been re-folded into a fresh Section 6 total here,
since that would require re-validating splices/masts/etc. against the same real-sections
standard, which is outside this pass's scope.

`generate_staad.py`'s `shs()` now looks up real Table 1 properties directly (with a
loud console warning if anything ever falls through to the idealized formula — confirmed
firing only for the historical D-6 hand-check comparison point, 120×120×5, which was never
part of the actual design). `tailored_schedule.json` and `CHRA2502_3D_Final.std` are both
regenerated against the real catalog.

---

## 0. Input Echo (as modeled)

| Parameter | Value used |
|---|---|
| Span (worst case) | 20.630 m, pin (left) – roller (right) |
| Top chord | straight, (0, 8.752) → (20.630, 8.339) m, fixed — never varied |
| Bottom chord | faceted parabolic fish-belly, end depth 1.000 m, d_mid variable |
| Clear-height floor | +6.096 m (20 ft) at lowest bottom-chord point |
| Tributary widths | T1 = 4.572 m (×2), T2 = 5.600 m (×6), T3 = 7.372 m (×1) |
| Dead load (deck) | 0.25 kN/m² + actual member self-weight (iterated) |
| Live load | 0.75 kN/m² |
| Wind uplift | 0.65 kN/m² upward on top chord (Cpe = −1.0) |
| Combos | C1 1.5(DL+LL), C2 1.2(DL+LL+WL), C3 1.5(DL+WL), C4 0.9DL+1.5WL |
| Steel | Fe410/E250 (fy=250 MPa), E=2×10⁵ MPa, γm0=1.10 |
| Sections | SHS only, sharp-corner (A=2t(B+H−2t)), B 40–200 mm, t 3–8 mm |
| Buckling curve | 'a' (α=0.21) per Table 10 for SHS |
| Effective lengths | top chord ip 0.85·panel / op 1.0·panel; bottom chord ip 0.85·panel / op 2.58 m fixed; webs ip 0.85·L / op 1.0·L |
| Panel counts explored | n = 6, 7, 8, 9, 10, 12, 14, 16 |
| d_mid explored | 2.00, 2.15, 2.30, 2.449 m (see finding #1 — 2.6 m is geometrically impossible) |
| Web patterns | Pratt (verticals+diagonals) and Warren (diagonals only) |

## 1. Findings that change the brief's own numbers

**Finding 1 — d_mid cannot reach 2.6 m.** With the top-chord coordinates fixed as given,
y_top(mid) = 8.752 − 0.02×10.315 = 8.5457 m. The +6.096 m clear-height floor caps
d_mid at **8.5457 − 6.096 = 2.4495 m**, not 2.6 m as the optimization range states. The
stated baseline (d_mid = 2.45 m) is itself ~0.5 mm over this cap — I used 2.449 m for
every run. [Certain] — this falls directly out of the fixed, non-negotiable top-chord line;
it's arithmetic, not a modeling choice.

**Finding 2 — the brief's own gate-c/d reference numbers use an inconsistent load factor.**
Working the stated combo `1.5(DL+LL)` against T3's own tributary gives
w = 1.5×(0.25+0.75)×7.372 = **11.06 kN/m**, not the 12.72 kN/m implied by the brief's
"w_factored = 1.725 × 7.372". The reference V=131 kN / M=675 kNm / N=275 kN all trace back
to that 12.72 kN/m, i.e. an effective factor of 1.725 that doesn't match combo C1 as
literally stated. Recomputing with the correct 11.06 kN/m gives M≈588 kNm, N≈240 kN —
which is what gate (c) is actually checked against below (and passes). [Certain] on the
arithmetic; [Guessing] on what the brief intended (maybe a rounded self-weight allowance).

**Finding 3 — gate (d)'s hand formula assumes parallel chords; this truss doesn't have them.**
The simplified `N_end ≈ (V − wLp/2)/sinθ` formula implicitly assumes the bottom chord is
horizontal (zero vertical load path of its own). In this fish-belly truss the end-panel
bottom chord drops steeply (slope ≈ 0.26), so it carries a large vertical component itself
— direct joint-equilibrium decomposition at the support (below) shows the FEM's end-member
forces balance the reaction to <0.3%, while the hand formula misses by ~28–40% and even
gets the **sign** wrong (predicts tension; FEM gives compression) for the Pratt topology.
This is a known limitation of that hand formula for non-parallel-chord trusses, not a model
defect — I'm treating the direct equilibrium check as the authoritative gate here and
reporting the hand-formula mismatch rather than stopping. [Certain] on the equilibrium
closure; [Likely] on the root cause explanation.

**Finding 4 — the two cheapest topology families are Warren, which the brief didn't
license.** The web-configuration menu given is "Pratt-style ... or fan truss." Warren
(diagonals only, no interior verticals) is a third, distinct family — lighter here because
removing verticals lets the diagonals run closer to the panel points, but it is *not* one
of the two options actually authorized. I've reported the true optimum (Warren) and, at
rank 6, the best-*explicitly-compliant* Pratt option, so the choice is visible rather than
buried. [Certain] on the classification; this is a scope call for the client/engineer, not me.

**Finding 5 — the theoretical lower-bound ratio (2.1–2.7×) breaching the "1.5 = not
converged" threshold reflects the lower-bound formula, not non-convergence.** The brief's
`Mass_LB = Σ|N|·L·ρ/(fy/γm0)` formula uses the *bare yield stress*, with **zero buckling
reduction**, for every member — including webs and the top chord, which are compression-
governed with χ often 0.4–0.6 at these slendernesses. A bound that ignores buckling
entirely will always sit far below any real compression-governed truss; comparing against
it is really measuring "how much of my mass is buckling-driven," not "how much slack is
left in the design." I report it exactly as specified below, flagged.

## 2. Validation Gates

Run on both the as-briefed baseline (n=8, Pratt, d_mid=2.449m, T3 loading) and the winner
(n=14, Warren, d_mid=2.449m, T3 loading).

| Gate | Requirement | Baseline result | Winner result |
|---|---|---|---|
| (a) Load balance | \|ΣR+ΣF\|/ΣF < 1% | 0.004–0.05% across C1–C4 | 0.006–0.07% across C1–C4 |
| (b) Stability | no singular/zero-stiffness modes | solved cleanly, 64/64 sweep configs | solved cleanly |
| (c) Midspan top-chord axial | within 10% of hand calc | −248.5 kN vs. −240.2 kN (corrected hand calc, Finding 2) = 3.5% | −247.7 kN vs. −240.2 kN = 3.1% |
| (d) End web force | within 15% of hand calc | see Finding 3 — hand formula not applicable to this geometry; direct joint equilibrium closes to <0.3% | same conclusion |
| (e) Deflection sanity | 15–35 mm at midspan, service DL+LL | 31.5 mm | 21.0 mm |
| (f) Mass conservation | Σ(section×length) = reported tonnage | true by construction (mass computed directly from final section×length, no separate tally) | same |

**Gates a, b, c, e pass outright. Gate d's literal formula does not apply to a
non-parallel-chord truss (Finding 3); I substituted rigorous nodal equilibrium, which
closes to <0.3%, as the applicable check. I am proceeding on that basis rather than
halting — flagged for the engineer of record to concur or overrule.**

## 3. Top-5 Configurations (ranked by mass per truss, T3-governed, all 9 trusses built identical)

| Rank | Family | d_mid (m) | Panels | Sections | Grade | Mass/truss bare (kg) | Max util | Service deflection (mm) | 9-truss total incl. 8% (t) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Warren fish-belly | 2.449 | 14 | SHS chords+webs | E250 | 776.1 | 0.917 | 21.0 | 7.544 |
| 2 | Warren fish-belly | 2.30 | 16 | SHS chords+webs | E250 | 780.1 | 0.940 | 29.9 | 7.583 |
| 3 | Warren fish-belly | 2.30 | 14 | SHS chords+webs | E250 | 790.3 | 0.950 | 23.8 | 7.682 |
| 4 | Warren fish-belly | 2.15 | 16 | SHS chords+webs | E250 | 793.1 | 0.914 | 32.1 | 7.709 |
| 5 | Warren fish-belly | 2.00 | 16 | SHS chords+webs | E250 | 808.4 | 0.949 | 34.5 | 7.858 |
| *6 (best Pratt-compliant)* | *Pratt fish-belly* | *2.30* | *12* | *SHS chords+webs* | *E250* | *869.9* | *0.900* | *32.9* | *8.456* |

All 64 (panel-count × d_mid × pattern) combinations tried; 30 were feasible with util ≤ 0.95,
4 failed the clear-height constraint outright, 30 exceeded util 0.95 (mostly n≤8 with
oversized panels driving top-chord local bending past what a ≤200mm SHS can carry — see
`sweep_results.json`). Family names describe the fixed profile constraints (straight top
chord, faceted parabolic bottom chord) — no parallel-chord or shallow-parabolic family was
competitive once the clear-height cap forced d_mid this high anyway.

## 4. WINNER — Detailed Member Schedule
**n = 14 panels, Warren web pattern, d_mid = 2.449 m, all SHS, E250, sized for T3 (7.372 m
tributary), applied identically to all 9 trusses per the brief's "design for worst case"
instruction. 2 near-zero-force end verticals deleted in the prune step (util < 0.25 in the
initial pass); 42 members remain, grouped into the 6 permitted groups.**

| Group | Section | Grade | Members | Max util | Governing check |
|---|---|---|---|---|---|
| Top chord — band A (end panels) | 180×180×3 SHS | E250 | 7 | 0.900 | Cl 9.3.1.1 beam-column, C1 (N=−225.4 kN, M=15.09 kNm) |
| Top chord — band B (mid panels) | 180×180×3 SHS | E250 | 7 | 0.948 | Cl 9.3.1.1 beam-column, C1 (N=−246.8 kN, M=15.20 kNm) |
| Bottom chord — band A (end panels) | 130×130×3 SHS | E250 | 7 | 0.932 | Cl 9.3/9.3.2 tension+bending, C1 (N=+216.3 kN, M=5.07 kNm) |
| Bottom chord — band B (mid panels) | 140×140×3 SHS | E250 | 7 | 0.919 | Cl 9.3/9.3.2 tension+bending, C1 (N=+244.9 kN, M=5.07 kNm) |
| Webs — band A (light diagonals) | 50×50×3 SHS | E250 | 7 | 0.790 | Cl 7.1.2 compression, C1 (N=−36.6 kN) |
| Webs — band B (heavy diagonals) | 75×75×3 SHS | E250 | 7 | 0.890 | Cl 7.1.2 compression, C1 (N=−149.1 kN) |

Every group's governing case is combo C1 (1.5(DL+LL), gravity) — the uplift-reversal combo
C4 never governs sizing for this geometry/tributary, though it was checked for every member
in every pass (bottom-chord slenderness limit was held at KL/r ≤ 180 throughout, anticipating
reversal, per the brief).

Note on tension members: E350 was made available for pure-tension members per the brief's
option, but for every group here the *governing* check is combined axial+bending (chords) or
compression (webs, since Warren diagonals see load reversal panel-to-panel), where E350's
higher fy buys nothing against a buckling- or bending-capacity-limited section — so E250
throughout is both lighter-touch on procurement and not leaving capacity on the table.

## 5. Optimization Metrics

- Fully-stressed lower-bound mass (winner, no buckling reduction): **334.4 kg/truss**
- Practical mass (winner, grouped, 8% allowance not yet added): **776.1 kg/truss**
- Ratio practical/lower-bound: **2.32** — see Finding 5; this is buckling reduction, not slack.
- Groups with util < 0.60: **none**. Lowest is the light web band at 0.79 — the winner has
  no over-designed groups by the brief's own threshold.
- Members deleted in the prune step: 2 (end verticals, util 0.06–0.14 in the ground structure
  — the frame-continuous chords carry that local reaction directly once the vertical is gone,
  confirmed stable by re-solving, no singular matrix).

## 6. Project Tonnage Statement

| Item | Mass |
|---|---|
| Trusses (winner, T3-governed, ×9, +8%) | **7.54 t** |
| Perimeter columns (150×150×4, 18 nos.) | 2.90 t |
| Eave ring + braced bays | 1.00 t |
| Splices/connections allowance | 0.50 t |
| Football stepped lattice masts | 2.85 t |
| **TOTAL STRUCTURAL STEEL** | **14.79 t** |

vs. client commitment (20 t): **achieves target, 5.21 t margin.**
vs. optimized target (17 t): **achieves target, 2.21 t margin.**

**[Guessing] — take the margin with a grain of salt.** 14.79 t against a 17–20 t envelope
the client and engineer set based on real fabricated-truss experience is a wide gap for a
tool with no independent cross-check. The likeliest places this model is lighter than a
real fabricated truss will be: (1) connections/gussets/splices here are a flat 0.5t
allowance for all 9 trusses combined — that's thin; (2) no bolt-hole/net-section deduction
on tension members (assumed fully welded, Ag=An); (3) 3mm-wall SHS dominates every group,
which is efficient on paper but pushes toward minimum practical wall thickness across the
board — a fabricator may reasonably want a thicker minimum for handling/robustness on a
20m-plus truss. If the client's 17t/20t figures came from a comparable real project, I'd
weight that more than this model until STAAD reconciles it.

**Pratt-compliant alternative** (rank 6 above, if Warren is not acceptable per Finding 4):
9×869.9kg×1.08 = 8.46t trusses → total structural steel **15.71 t** — still under both targets.

**Optimize-T1/T2/T3-separately alternative** (winner topology, sized per own tributary
instead of one identical design): T1=699.0kg, T2=664.0kg, T3=776.1kg →
(2×699.0+6×664.0+1×776.1)×1.08/1000 = **6.65 t** trusses, saving ~0.89t vs. the conservative
identical-truss approach, at the cost of 3 distinct truss designs instead of 1.

## 7. Honest Limitations

- This is a **2D planar analysis covering gravity (DL/LL) and wind uplift (WL) only.**
  It does not model, and cannot be used to certify, the lateral wind load path (0.0877
  kN/m² on frame solidity), which requires a 3D global model connecting trusses, columns,
  bracing and the eave ring.
- Diaphragm action of the roof deck is **not verified** — the deck is assumed to only load
  the top chord vertically, with no in-plane shear transfer checked.
- Global (whole-building) stability, second-order (P-Δ) effects, and foundation interaction
  are **not checked** here.
- Section properties use the sharp-corner idealization the brief specified; real rolled SHS
  have corner radii that trim A and I slightly (typically a few percent) versus a real
  fabricator's catalog — check against the actual mill catalog before issuing for fabrication.
- Angles were not used anywhere (all-SHS, per the brief's allowance) — if the fabricator's
  shop is angle-tooled rather than tube-tooled, re-run with the angle section family; the
  mass outcome will differ (angles typically need larger gross area for the same net
  capacity due to eccentricity/bolt-hole effects not modeled here).
- Cl 8.2.2 lateral-torsional buckling was treated as non-governing for these closed (SHS)
  sections per standard practice — this is a defensible simplification for tubes, not a
  universally-skippable check; note it as an assumption, not an omission.
- **These all remain open items for the 3D STAAD/SAP2000 sign-off model** before this
  design is issued for fabrication.

## 8. How to reproduce

```
node structural/run_baseline.js   # baseline (n=8, Pratt, d_mid=2.449) + gates a,c,d,e
node structural/sweep.js          # full 64-config sweep, writes sweep_results.json
```
`fem.js` includes an inline validated unit test (`test_fem.js`) against the textbook
simply-supported UDL beam case (M=wL²/8, V=wL/2, deflection=5wL⁴/384EI) — all four match
theory to the number of decimal places printed.
