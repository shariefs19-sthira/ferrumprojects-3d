'use strict';
const { buildTruss, clearHeightOk } = require('./truss');
const { sizingPass, initialSizing, memberLenM, buildComboModel, SERVICE_COMBO } = require('./analyze');
const { sizeMember } = require('./is800');
const { CATALOG } = require('./sections');

const RHO = 7850e-9; // kg/mm^3
const GAMMA_M0 = 1.10;

// Self-weight depends on the section chosen for capacity, and capacity choice depends
// (slightly) on self-weight -- a member sitting right at a catalog boundary can enter a
// stable 2-cycle (flipping between two adjacent SHS sizes forever) that plain damping does
// not reliably kill within a bounded iteration count (verified: 50% damping still cycled at
// ~10% amplitude after 25 iterations for a real case in this model). So: run the damped
// iteration for a fixed budget, then break any remaining 2-cycle deterministically by taking
// the LARGER (heavier, conservative -- guaranteed a previously-valid, util<=0.95 candidate)
// of the final two iterations' sections for every member, and re-evaluate (no further
// resizing) to get the report that matches what's actually returned.
function converge(truss, Lt, fy, maxIter, opts) {
  maxIter = maxIter || 40;
  let sizing = initialSizing(truss, fy).map(s => ({ ...s, swA: s.section.A }));
  let prevSizing = sizing;
  let pass;
  for (let i = 0; i < maxIter; i++) {
    pass = sizingPass(truss, sizing, Lt, fy, opts);
    let maxRelChange = 0;
    const nextSizing = pass.newSizing.map((s, idx) => {
      const oldSwA = sizing[idx].swA;
      const swA = 0.5 * oldSwA + 0.5 * s.section.A; // damped relaxation
      maxRelChange = Math.max(maxRelChange, Math.abs(swA - oldSwA) / oldSwA);
      return { ...s, swA };
    });
    prevSizing = sizing;
    sizing = nextSizing;
    if (maxRelChange < 0.005) { prevSizing = sizing; break; }
  }
  // Tie-break any still-oscillating member toward the heavier of the last two states.
  const finalSizing = sizing.map((s, idx) => {
    const prev = prevSizing[idx];
    return (prev.section.A > s.section.A) ? { ...prev, swA: prev.section.A } : { ...s, swA: s.section.A };
  });
  const finalPass = sizingPassNoResize(truss, finalSizing, Lt, fy, opts);
  return { sizing: finalSizing, pass: finalPass };
}

function pruneLowUtil(truss, sizing, pass, threshold) {
  const keepIdx = [];
  truss.members.forEach((m, i) => {
    if (m.type === 'top' || m.type === 'bottom' || (m.end)) { keepIdx.push(i); return; } // never delete chords or end verticals
    if (pass.report[i].util !== undefined && pass.report[i].util < threshold) return; // drop
    keepIdx.push(i);
  });
  if (keepIdx.length === truss.members.length) return null; // nothing pruned
  const newMembers = keepIdx.map(i => truss.members[i]);
  const newSizing = keepIdx.map(i => sizing[i]);
  const newTruss = { ...truss, members: newMembers };
  return { truss: newTruss, sizing: newSizing, droppedCount: truss.members.length - keepIdx.length };
}

function massOfMember(truss, m, sizing_ti) {
  const L = memberLenM(truss, m) * 1000; // mm
  return sizing_ti.section.A * L * RHO; // kg
}

function totalMass(truss, sizing) {
  let kg = 0;
  truss.members.forEach((m, i) => { kg += massOfMember(truss, m, sizing[i]); });
  return kg;
}

function lowerBoundMass(truss, sizing, demandsByMember) {
  let kg = 0;
  truss.members.forEach((m, i) => {
    const fy = sizing[i].fy;
    const Nmax = Math.max(...demandsByMember[i].map(d => Math.abs(d.N)));
    const Areq = Nmax * GAMMA_M0 / fy; // mm^2, fully-stressed ideal (no buckling reduction)
    const L = memberLenM(truss, m) * 1000;
    kg += Areq * L * RHO;
  });
  return kg;
}

function groupMembers(truss, sizing, demandsByMember, fy, opts) {
  opts = opts || {};
  const categories = { top: [], bottom: [], web: [] };
  truss.members.forEach((m, i) => {
    const cat = (m.type === 'top') ? 'top' : (m.type === 'bottom') ? 'bottom' : 'web';
    // Rank by the individually-converged section's area, not raw peak axial force: area already
    // reflects each member's own combined axial+bending (beam-column) demand via the code check,
    // whereas banding by |N| alone can bucket a bending-heavy member with an axial-heavy one and
    // force the whole band to a much bigger section than either needed on its own.
    categories[cat].push({ i, peak: sizing[i].section.A });
  });
  const newSizing = sizing.slice();
  const groupSummary = [];
  for (const cat of Object.keys(categories)) {
    const list = categories[cat];
    if (list.length === 0) continue;
    list.sort((a, b) => a.peak - b.peak);
    const mid = Math.ceil(list.length / 2);
    // opts.uniformChords: one section for the whole top chord and one for the whole bottom
    // chord (fabricator constraint -- no splicing between two SHS sizes along a continuous
    // chord run). Web members are unaffected -- they're discrete cut-to-length pieces anyway.
    const forceSingleBand = opts.uniformChords && (cat === 'top' || cat === 'bottom');
    const bands = (!forceSingleBand && list.length >= 4) ? [list.slice(0, mid), list.slice(mid)] : [list];
    bands.forEach((band, bi) => {
      if (band.length === 0) return;
      const demands = [];
      band.forEach(({ i }) => demands.push(...demandsByMember[i]));
      const anyCompression = demands.some(d => d.N < 0);
      const slenderLimitTen = anyCompression ? 180 : 350;
      const best = sizeMember(demands, fy, 180, slenderLimitTen);
      if (!best) { groupSummary.push({ cat, band: bi, error: 'NO_SECTION', members: band.map(b => b.i) }); return; }
      band.forEach(({ i }) => { newSizing[i] = { section: best.section, fy }; });
      groupSummary.push({ cat, band: bi, section: best.section.label, util: best.maxUtil, governing: best.governing, members: band.map(b => b.i), count: band.length });
    });
  }
  return { newSizing, groupSummary };
}

function serviceDeflection(truss, sizing, Lt) {
  const { model, idx } = buildComboModel(truss, sizing, Lt, SERVICE_COMBO);
  const res = model.solve();
  const mid = truss.n % 2 === 0 ? truss.n / 2 : (truss.n - 1) / 2;
  const node = idx['B' + mid];
  return Math.abs(res.D[3 * node + 1]);
}

// Full pipeline for one topology, sized for a single tributary width Lt.
// opts.deckLateralCredit (default false/conservative) controls top-chord out-of-plane KL --
// see effectiveLengths() in analyze.js.
function runTopology({ n, dMid, webPattern, Lt, fy = 250, L, opts }) {
  const truss = buildTruss({ n, dMid, webPattern, L });
  if (!clearHeightOk(truss)) return { feasible: false, reason: 'clear-height' };

  const step1 = converge(truss, Lt, fy, 40, opts);
  let workTruss = truss, workSizing = step1.sizing, workPass = step1.pass;

  const pruned = pruneLowUtil(truss, step1.sizing, step1.pass, 0.25);
  if (pruned) {
    const step2 = converge(pruned.truss, Lt, fy, 40, opts);
    workTruss = pruned.truss; workSizing = step2.sizing; workPass = step2.pass;
  }

  const grouped = groupMembers(workTruss, workSizing, workPass.demandsByMember, fy, opts);
  // final FEM check with grouped sizes (one more pass to get final report/util per member, no resizing)
  const finalPass = sizingPassNoResize(workTruss, grouped.newSizing, Lt, fy, opts);

  const mass = totalMass(workTruss, grouped.newSizing);
  const lb = lowerBoundMass(workTruss, grouped.newSizing, finalPass.demandsByMember);
  const defl = serviceDeflection(workTruss, grouped.newSizing, Lt);

  const maxUtil = Math.max(...finalPass.report.filter(r => r.util !== undefined).map(r => r.util));
  const anyOver = finalPass.report.some(r => r.util !== undefined && r.util > 0.95);

  return {
    feasible: true, n, dMid, webPattern, truss: workTruss, sizing: grouped.newSizing,
    groupSummary: grouped.groupSummary, mass, lowerBoundMass: lb, deflection: defl,
    maxUtil, anyOver, report: finalPass.report, demandsByMember: finalPass.demandsByMember,
    droppedCount: pruned ? pruned.droppedCount : 0,
  };
}

// Like sizingPass but does NOT resize -- just recomputes demands/util for the given fixed sizing (for reporting).
function sizingPassNoResize(truss, sizing, Lt, fy, opts) {
  const full = sizingPass(truss, sizing, Lt, fy, opts);
  // sizingPass already resizes; we want the util of the GIVEN sizing, not resized.
  // Recompute utils directly against provided sizing using its own demands.
  const { memberUtilization } = require('./is800');
  const report = truss.members.map((m, ti) => {
    const demands = full.demandsByMember[ti];
    const sec = sizing[ti].section;
    let maxUtil = 0, governing = null;
    for (const d of demands) {
      const r = memberUtilization(sec, sizing[ti].fy, d);
      if (r.util > maxUtil) { maxUtil = r.util; governing = { ...r, combo: d.comboName, N: d.N, M: d.M }; }
    }
    return { ti, type: m.type, section: sec.label, util: maxUtil, governing };
  });
  return { report, demandsByMember: full.demandsByMember, reactionCheck: full.reactionCheck };
}

module.exports = { runTopology, totalMass, lowerBoundMass, converge, pruneLowUtil, groupMembers, serviceDeflection, sizingPassNoResize };
