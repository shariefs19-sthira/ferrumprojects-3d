'use strict';
const { Model } = require('./fem');

// Test 1: simply supported beam, span L, UDL w, check M_mid = wL^2/8, V_end = wL/2,
// deflection_mid = 5wL^4/384EI. Use 2 elements (node at each end + midspan) with frame elements,
// pin-roller supports (uy fixed both ends, ux fixed at left only), rz free at both ends (simple supports).
function testSimplySupportedBeam() {
  const E = 200000; // MPa
  const B = 150, t = 6; // SHS-ish, use rectangle formula manually
  const A = 4 * t * (B - t);
  const I = (Math.pow(B, 4) - Math.pow(B - 2 * t, 4)) / 12;
  const L = 6000; // mm
  const w = -0.02; // N/mm downward (local y). Using negative to mean "downward" if local y is up... let's just test both signs.

  const m = new Model();
  const n0 = m.addNode(0, 0);
  const n1 = m.addNode(L / 2, 0);
  const n2 = m.addNode(L, 0);
  m.addMember(n0, n1, 'frame', E, A, I, w, 'seg1');
  m.addMember(n1, n2, 'frame', E, A, I, w, 'seg2');
  m.fixSupport(n0, true, true, false); // pin
  m.fixSupport(n2, false, true, false); // roller (uy fixed, ux free)

  const res = m.solve();
  const Mmid = res.results[0].M2; // moment at node1 from seg1 (should equal -results[1].M1 by continuity)
  const Vend = res.results[0].V1;
  const wL2_8 = Math.abs(w) * L * L / 8;
  const wL_2 = Math.abs(w) * L / 2;
  const vmid = res.D[3 * n1 + 1];
  const defl_theory = 5 * Math.abs(w) * Math.pow(L, 4) / (384 * E * I);

  console.log('--- Simply supported beam UDL test ---');
  console.log('w =', w, 'N/mm, L =', L, 'mm, E=', E, 'I=', I);
  console.log('Expected Mmid (wL^2/8) =', wL2_8.toFixed(2), 'N-mm');
  console.log('FEM M at midspan node (seg1.M2) =', Mmid.toFixed(2));
  console.log('FEM M at midspan node (seg2.M1) =', res.results[1].M1.toFixed(2));
  console.log('Expected Vend (wL/2) =', wL_2.toFixed(2), 'N');
  console.log('FEM V1 seg1 =', res.results[0].V1.toFixed(2));
  console.log('Expected deflection mid =', defl_theory.toFixed(4), 'mm');
  console.log('FEM deflection mid =', vmid.toFixed(4), 'mm');
  console.log('Reaction sum check: R uy n0+n2 vs total load', );
  const totalLoad = Math.abs(w) * L;
  const Rsum = Math.abs(res.R[3 * n0 + 1]) + Math.abs(res.R[3 * n2 + 1]);
  console.log('Total applied load =', totalLoad, ' Sum reactions =', Rsum.toFixed(3));
}

function testTrussSimple() {
  // Simple 3-node triangle truss: pin at 0, roller at 2, point load down at node1 (apex)
  const E = 200000;
  const A = 1000; // mm^2
  const m = new Model();
  const n0 = m.addNode(0, 0);
  const n1 = m.addNode(2000, 1500);
  const n2 = m.addNode(4000, 0);
  m.addMember(n0, n1, 'truss', E, A, 0, 0, 'web1');
  m.addMember(n1, n2, 'truss', E, A, 0, 0, 'web2');
  m.addMember(n0, n2, 'truss', E, A, 0, 0, 'bottom'); // this alone would leave rotational dof unconstrained -> but truss-only model, need frame check separately
  m.fixSupport(n0, true, true, true);
  m.fixSupport(n2, false, true, true);
  m.fixSupport(n1, false, false, true); // constrain rotation dof (unused in pure truss) to avoid singularity
  m.addNodalLoad(n1, 0, -10000, 0); // 10 kN down
  const res = m.solve();
  console.log('--- Simple truss test ---');
  for (const r of res.results) console.log(r.idx, r.kind, 'N=', r.N.toFixed(2));
  console.log('Reactions:', res.R.map(v => v.toFixed(2)));
}

testSimplySupportedBeam();
testTrussSimple();
