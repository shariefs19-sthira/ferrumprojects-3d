'use strict';
const { Model } = require('./fem');
const { CATALOG } = require('./sections');
const { sizeMember, memberUtilization, E_STEEL } = require('./is800');

const RHO = 7850e-9; // kg/mm^3
const G = 9.80665; // m/s^2
const RING_BRACE_OP = 2580; // mm, bottom chord out-of-plane bracing spacing (fixed per brief)

function selfWeightUDL(section) { // N/mm, downward
  return -(section.A * RHO * G); // kg/mm*g = N/mm ; negative = local "down" convention (matches gravity tests)
}

// key for a truss node group id
function nodeKey(g, i) { return g + i; }

function buildNodeMaps(truss, model) {
  const idx = {};
  truss.topNodes.forEach((p, i) => { idx[nodeKey('T', i)] = model.addNode(p.x * 1000, p.y * 1000); });
  truss.botNodes.forEach((p, i) => { idx[nodeKey('B', i)] = model.addNode(p.x * 1000, p.y * 1000); });
  return idx;
}

function memberLenM(truss, m) {
  const get = (g, i) => (g === 'T' ? truss.topNodes[i] : truss.botNodes[i]);
  const p1 = get(m.a[0], m.a[1]), p2 = get(m.b[0], m.b[1]);
  return Math.hypot(p2.x - p1.x, p2.y - p1.y);
}

// Build FEM model for one combo. sizing[i] = {section, fy} for truss.members[i].
// gravityUdl[i] (N/mm, deck DL+LL combined per horizontal metre before combo factors) only meaningful for 'top' members.
// Returns {model, femToTruss: array parallel to model.members}
function buildComboModel(truss, sizing, Lt, combo) {
  const model = new Model();
  const idx = buildNodeMaps(truss, model);
  const femToTruss = [];
  const DECK_DL = 0.25, DECK_LL = 0.75, WIND_UPLIFT = 0.65; // kN/m^2 == N/mm per metre trib width (see note)

  truss.members.forEach((m, ti) => {
    const n1 = idx[nodeKey(m.a[0], m.a[1])];
    const n2 = idx[nodeKey(m.b[0], m.b[1])];
    const { section, fy } = sizing[ti];
    const kind = (m.type === 'top' || m.type === 'bottom') ? 'frame' : 'truss';
    const Lmm = memberLenM(truss, m) * 1000;

    let udl = 0;
    if (kind === 'frame') {
      const sw = selfWeightUDL(section) * combo.fDL; // self-weight always "DL" factor
      let ext = 0;
      if (m.type === 'top') {
        const get = (g, i) => (g === 'T' ? truss.topNodes[i] : truss.botNodes[i]);
        const p1 = get(m.a[0], m.a[1]), p2 = get(m.b[0], m.b[1]);
        const dxHoriz = Math.abs(p2.x - p1.x) * 1000; // mm horizontal projection
        const scale = dxHoriz / Lmm; // preserves total applied force when smearing over true (sloped) length
        const dl = -(DECK_DL * Lt) * scale; // N/mm, downward
        const ll = -(DECK_LL * Lt) * scale;
        const wl = +(WIND_UPLIFT * Lt) * scale; // upward suction
        ext = combo.fDL * dl + combo.fLL * ll + combo.fWL * wl;
      }
      udl = sw + ext;
    }

    const fi = model.addMember(n1, n2, kind, E_STEEL, section.A, section.I || 0, udl, m.type + ti);
    femToTruss.push(ti);

    if (kind === 'truss') {
      // lump self-weight to end nodes
      const wPerLen = -(section.A * RHO * G) * combo.fDL; // N/mm downward
      const wTotal = wPerLen * Lmm;
      model.addNodalLoad(n1, 0, wTotal / 2, 0);
      model.addNodalLoad(n2, 0, wTotal / 2, 0);
    }
  });

  // supports: left pin at B0, right roller at Bn
  model.fixSupport(idx[nodeKey('B', 0)], true, true, false);
  model.fixSupport(idx[nodeKey('B', truss.n)], false, true, false);

  return { model, femToTruss, idx };
}

function maxMomentAlong(M1, M2, V1, w, L) {
  let best = Math.max(Math.abs(M1), Math.abs(M2));
  if (Math.abs(w) > 1e-12) {
    const xstar = -V1 / w;
    if (xstar > 0 && xstar < L) {
      const Mstar = M1 + V1 * xstar + w * xstar * xstar / 2;
      best = Math.max(best, Math.abs(Mstar));
    }
  }
  return best;
}

const COMBOS = [
  { name: 'C1_1.5(DL+LL)', fDL: 1.5, fLL: 1.5, fWL: 0 },
  { name: 'C2_1.2(DL+LL+WL)', fDL: 1.2, fLL: 1.2, fWL: 1.2 },
  { name: 'C3_1.5(DL+WL)', fDL: 1.5, fLL: 0, fWL: 1.5 },
  { name: 'C4_0.9DL+1.5WL', fDL: 0.9, fLL: 0, fWL: 1.5 },
];
const SERVICE_COMBO = { name: 'service_DL+LL', fDL: 1.0, fLL: 1.0, fWL: 0 };

function effectiveLengths(truss, m, Lmm) {
  if (m.type === 'top') return { KL_ip: 0.85 * Lmm, KL_op: Lmm };
  if (m.type === 'bottom') return { KL_ip: 0.85 * Lmm, KL_op: RING_BRACE_OP };
  return { KL_ip: 0.85 * Lmm, KL_op: 1.0 * Lmm }; // vertical/diagonal webs
}

// One pass: given current sizing, run 4 combos, collect demands per member, re-size.
function sizingPass(truss, sizing, Lt, defaultFy) {
  const demandsByMember = truss.members.map(() => []);
  const reactionCheck = [];

  for (const combo of COMBOS) {
    const { model, femToTruss } = buildComboModel(truss, sizing, Lt, combo);
    const res = model.solve();
    // load balance gate
    let totalAppliedY = 0;
    for (const ld of model.loads) totalAppliedY += ld.fy;
    for (const mem of model.members) {
      if (mem.udl) totalAppliedY += mem.udl * model.geom(model.members.indexOf(mem)).L;
    }
    let totalReactY = 0;
    for (const [nodeStr] of Object.entries(model.supports)) {
      const node = Number(nodeStr);
      totalReactY += res.R[3 * node + 1];
    }
    reactionCheck.push({ combo: combo.name, totalAppliedY, totalReactY });

    res.results.forEach((r, fi) => {
      const ti = femToTruss[fi];
      const m = truss.members[ti];
      const Lmm = memberLenM(truss, m) * 1000;
      const { KL_ip, KL_op } = effectiveLengths(truss, m, Lmm);
      if (r.kind === 'frame') {
        const Mmax = maxMomentAlong(r.M1, r.M2, r.V1, model.members[fi].udl, r.L);
        const Naxial = (r.N1 + r.N2) / 2; // N1==N2 for axial-only; average is robust either way. Tension = +.
        demandsByMember[ti].push({ N: Naxial, M: Mmax, KL_ip, KL_op, comboName: combo.name });
      } else {
        demandsByMember[ti].push({ N: r.N, M: 0, KL_ip, KL_op, comboName: combo.name });
      }
    });
  }

  const newSizing = sizing.slice();
  const report = [];
  truss.members.forEach((m, ti) => {
    const slenderLimitComp = 180;
    const anyCompression = demandsByMember[ti].some(d => d.N < 0);
    const slenderLimitTen = anyCompression ? 180 : 350; // reversal -> stricter limit, per brief for bottom chord & generally
    const fy = sizing[ti].fy; // grade decided once, kept stable through iteration
    const best = sizeMember(demandsByMember[ti], fy, slenderLimitComp, slenderLimitTen);
    if (!best) {
      report.push({ ti, type: m.type, error: 'NO_SECTION_FOUND' });
      newSizing[ti] = sizing[ti];
    } else {
      newSizing[ti] = { section: best.section, fy };
      report.push({ ti, type: m.type, section: best.section.label, util: best.maxUtil, governing: best.governing });
    }
  });

  return { newSizing, report, demandsByMember, reactionCheck };
}

function initialSizing(truss, fy) {
  const seed = CATALOG.find(s => s.B === 100 && s.t === 5) || CATALOG[10];
  return truss.members.map(() => ({ section: seed, fy }));
}

module.exports = {
  buildComboModel, sizingPass, initialSizing, COMBOS, SERVICE_COMBO, effectiveLengths,
  memberLenM, maxMomentAlong, selfWeightUDL,
};
