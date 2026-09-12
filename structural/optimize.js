'use strict';
const { buildTruss, clearHeightOk } = require('./truss');
const { sizingPass, initialSizing, memberLenM, buildComboModel, SERVICE_COMBO } = require('./analyze');
const { sizeMember } = require('./is800');
const { CATALOG } = require('./sections');

const RHO = 7850e-9; // kg/mm^3
const GAMMA_M0 = 1.10;

function converge(truss, Lt, fy, maxIter) {
  let sizing = initialSizing(truss, fy);
  let pass;
  for (let i = 0; i < maxIter; i++) {
    pass = sizingPass(truss, sizing, Lt, fy);
    const changed = pass.newSizing.some((s, idx) => s.section.label !== sizing[idx].section.label);
    sizing = pass.newSizing;
    if (!changed) break;
  }
  return { sizing, pass };
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

function groupMembers(truss, sizing, demandsByMember, fy) {
  const categories = { top: [], bottom: [], web: [] };
  truss.members.forEach((m, i) => {
    const cat = (m.type === 'top') ? 'top' : (m.type === 'bottom') ? 'bottom' : 'web';
    const peak = Math.max(...demandsByMember[i].map(d => Math.abs(d.N)));
    categories[cat].push({ i, peak });
  });
  const newSizing = sizing.slice();
  const groupSummary = [];
  for (const cat of Object.keys(categories)) {
    const list = categories[cat];
    if (list.length === 0) continue;
    list.sort((a, b) => a.peak - b.peak);
    const mid = Math.ceil(list.length / 2);
    const bands = list.length >= 4 ? [list.slice(0, mid), list.slice(mid)] : [list];
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
function runTopology({ n, dMid, webPattern, Lt, fy = 250, L }) {
  const truss = buildTruss({ n, dMid, webPattern, L });
  if (!clearHeightOk(truss)) return { feasible: false, reason: 'clear-height' };

  const step1 = converge(truss, Lt, fy, 12);
  let workTruss = truss, workSizing = step1.sizing, workPass = step1.pass;

  const pruned = pruneLowUtil(truss, step1.sizing, step1.pass, 0.25);
  if (pruned) {
    const step2 = converge(pruned.truss, Lt, fy, 12);
    workTruss = pruned.truss; workSizing = step2.sizing; workPass = step2.pass;
  }

  const grouped = groupMembers(workTruss, workSizing, workPass.demandsByMember, fy);
  // final FEM check with grouped sizes (one more pass to get final report/util per member, no resizing)
  const finalPass = sizingPassNoResize(workTruss, grouped.newSizing, Lt, fy);

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
function sizingPassNoResize(truss, sizing, Lt, fy) {
  const full = sizingPass(truss, sizing, Lt, fy);
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
