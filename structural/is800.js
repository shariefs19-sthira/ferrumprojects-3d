'use strict';
// IS 800:2007 checks. Units: N, mm, MPa. gamma_m0 = 1.10.
const { CATALOG } = require('./sections');

const GAMMA_M0 = 1.10;
const E_STEEL = 200000; // MPa

function chiCurveA(lambda) {
  const alpha = 0.21; // SHS/RHS Table 10 curve 'a'
  const phi = 0.5 * (1 + alpha * (lambda - 0.2) + lambda * lambda);
  const chi = 1 / (phi + Math.sqrt(Math.max(phi * phi - lambda * lambda, 0)));
  return Math.min(chi, 1.0);
}

function fcd(fy, KLr) {
  if (KLr <= 1e-6) return fy / GAMMA_M0;
  const lambda = (KLr / Math.PI) * Math.sqrt(fy / E_STEEL);
  const chi = chiCurveA(lambda);
  return { fcd: chi * fy / GAMMA_M0, lambda, chi };
}

// demand: { N, M, KL_ip, KL_op } lengths in mm; r comes from the candidate section being tried.
function memberUtilization(section, fy, demand) {
  const { N, M } = demand;
  const KLr = Math.max(demand.KL_ip / section.r, demand.KL_op / section.r);
  const Zp = section.Zp;
  const Md = 1.0 * Zp * fy / GAMMA_M0; // betab=1 (plastic/compact SHS), no LTB reduction (closed section)
  const Mratio = M ? M / Md : 0;

  if (N >= 0) {
    // tension (+ some bending)
    const Td = section.A * fy / GAMMA_M0;
    const util = N / Td + Mratio; // Cl 9.3.2 simplified linear interaction, no amplification (conservative)
    return { util, KLr, clause: M ? '9.3 beam-column (tension)' : '6.2 tension', Nd: Td, Md };
  } else {
    // compression (+ some bending) -- Cl 7.1.2 + Cl 9.3.1.1
    const { fcd: fcdVal, lambda } = fcd(fy, KLr);
    const Pd = section.A * fcdVal;
    const ny = Math.abs(N) / Pd;
    let Ky = 1 + (lambda - 0.2) * ny;
    Ky = Math.min(Ky, 1 + 0.8 * ny);
    const Cmy = 0.9; // Table 18, member with transverse UDL, ends not held against rotation independently
    const util = Math.abs(N) / Pd + Ky * Cmy * Mratio;
    return { util, KLr, clause: M ? '9.3.1.1 beam-column' : '7.1.2 compression', Nd: Pd, Md, lambda };
  }
}

// demands: array of {N, M, KLr_ip, KLr_op, comboName}
// slenderLimit: max allowed KL/r (180 comp, 350 tension; use 180 if member can reverse into compression)
function sizeMember(demands, fy, slenderLimitComp, slenderLimitTen, opts) {
  opts = opts || {};
  const minA = opts.minA || 0;
  let best = null;
  for (const section of CATALOG) {
    if (section.A < minA) continue;
    let maxUtil = 0, governing = null, slenderOk = true;
    for (const d of demands) {
      const KLr = Math.max(d.KL_ip / section.r, d.KL_op / section.r);
      const limit = d.N < 0 ? slenderLimitComp : slenderLimitTen;
      if (KLr > limit) slenderOk = false;
      const r = memberUtilization(section, fy, d);
      if (r.util > maxUtil) { maxUtil = r.util; governing = { ...r, combo: d.comboName, N: d.N, M: d.M }; }
    }
    if (!slenderOk) continue;
    if (maxUtil <= 0.95) {
      best = { section, maxUtil, governing };
      break; // catalog sorted ascending by area -> first feasible is lightest
    }
  }
  return best;
}

module.exports = { GAMMA_M0, E_STEEL, chiCurveA, fcd, memberUtilization, sizeMember };
