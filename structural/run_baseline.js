'use strict';
const { buildTruss, maxDmidAllowed, clearHeightOk } = require('./truss');
const { sizingPass, initialSizing, buildComboModel, SERVICE_COMBO, memberLenM } = require('./analyze');

const L = 20.630;
console.log('Max d_mid allowed by +6.096m clear-height constraint at L=20.63m:', maxDmidAllowed(L).toFixed(4), 'm');

const truss = buildTruss({ n: 8, dMid: 2.449, webPattern: 'pratt', L });
console.log('Clear height OK:', clearHeightOk(truss), 'min bottom-chord elevation =', truss.minBotY.toFixed(4), 'm');
console.log('Members:', truss.members.length, '(top', truss.members.filter(m=>m.type==='top').length,
  'bottom', truss.members.filter(m=>m.type==='bottom').length,
  'vertical', truss.members.filter(m=>m.type==='vertical').length,
  'diagonal', truss.members.filter(m=>m.type==='diagonal').length, ')');

const Lt = 7.372; // T3 tributary, worst case
let sizing = initialSizing(truss, 250);
let pass;
for (let iter = 1; iter <= 8; iter++) {
  pass = sizingPass(truss, sizing, Lt, 250);
  const changed = pass.newSizing.some((s, i) => s.section.label !== sizing[i].section.label);
  sizing = pass.newSizing;
  console.log(`iter ${iter}: changed=${changed}`);
  if (!changed) break;
}

console.log('\n--- Reaction / load balance check (gate a): applied + reaction should sum to ~0 ---');
for (const rc of pass.reactionCheck) {
  const err = Math.abs(rc.totalAppliedY + rc.totalReactY) / Math.abs(rc.totalAppliedY || 1);
  console.log(rc.combo, 'applied=', rc.totalAppliedY.toFixed(1), 'N  reaction=', rc.totalReactY.toFixed(1), 'err=', (err*100).toFixed(4), '%');
}

console.log('\n--- Member sizing summary (after convergence) ---');
for (const r of pass.report) {
  console.log(r.ti, r.type, r.section, 'util=', r.util ? r.util.toFixed(3) : r.error, r.governing ? r.governing.clause + ' @ ' + r.governing.combo : '');
}

// gate c: midspan top chord axial force vs hand calc N=275kN
const midTop = pass.demandsByMember.findIndex((d, i) => truss.members[i].type === 'top' && Math.abs(memberLenM(truss, truss.members[i]) * (i)) >= 0); // placeholder
// find the top-chord member whose midpoint x is closest to L/2
let bestIdx = -1, bestDist = Infinity;
truss.members.forEach((m, i) => {
  if (m.type !== 'top') return;
  const a = truss.topNodes[m.a[1]], b = truss.topNodes[m.b[1]];
  const midx = (a.x + b.x) / 2;
  const dist = Math.abs(midx - L / 2);
  if (dist < bestDist) { bestDist = dist; bestIdx = i; }
});
console.log('\n--- Gate c: midspan top chord axial ---');
const midDemands = pass.demandsByMember[bestIdx];
const c1 = midDemands.find(d => d.comboName === 'C1_1.5(DL+LL)');
console.log('Member', bestIdx, 'C1 axial N =', c1.N.toFixed(1), 'N =', (c1.N/1000).toFixed(1), 'kN  (hand calc ~ -275 kN compression)');

// gate d: end diagonal
let endDiagIdx = -1, minX = Infinity;
truss.members.forEach((m, i) => {
  if (m.type !== 'diagonal') return;
  const get = (g, idx2) => (g === 'T' ? truss.topNodes[idx2] : truss.botNodes[idx2]);
  const a = get(m.a[0], m.a[1]);
  if (a.x < minX) { minX = a.x; endDiagIdx = i; }
});
console.log('\n--- Gate d: end diagonal ---');
const endDemands = pass.demandsByMember[endDiagIdx];
const c1e = endDemands.find(d => d.comboName === 'C1_1.5(DL+LL)');
console.log('Member', endDiagIdx, 'C1 axial N =', (c1e.N/1000).toFixed(1), 'kN (hand calc ~ 254 kN tension, assumes parallel chords)');

// Direct joint equilibrium check at B0 (support) to explain any gate-d mismatch:
// sum vertical components of end-vertical, bottom-chord-seg0, end-diagonal, + reaction should = 0
{
  const b0 = truss.botNodes[0], b1 = truss.botNodes[1], t0 = truss.topNodes[0], t1 = truss.topNodes[1];
  const endVertIdx = truss.members.findIndex(m => m.type === 'vertical' && m.end && m.a[1] === 0);
  const bottomSeg0Idx = truss.members.findIndex(m => m.type === 'bottom' && m.a[1] === 0);
  const Nvert = pass.demandsByMember[endVertIdx].find(d => d.comboName === 'C1_1.5(DL+LL)').N;
  const Nbot0 = pass.demandsByMember[bottomSeg0Idx].find(d => d.comboName === 'C1_1.5(DL+LL)').N;
  const Ndiag = c1e.N;
  const sinVert = 1.0; // purely vertical member
  const sinBot0 = (b1.y - b0.y) / Math.hypot(b1.x - b0.x, b1.y - b0.y);
  const sinDiag = (t1.y - b0.y) / Math.hypot(t1.x - b0.x, t1.y - b0.y);
  const reaction = pass.reactionCheck.find(r => r.combo === 'C1_1.5(DL+LL)').totalReactY; // both supports; approx split later
  console.log('\n--- Joint B0 equilibrium decomposition (why gate-d simple formula misses) ---');
  console.log('bottom-chord-seg0 slope (rise/length) =', sinBot0.toFixed(4), ' end-diagonal slope =', sinDiag.toFixed(4));
  console.log('N_end_vertical =', (Nvert/1000).toFixed(1), 'kN, vertical component =', (Nvert*sinVert/1000).toFixed(1), 'kN');
  console.log('N_bottom_seg0 =', (Nbot0/1000).toFixed(1), 'kN, vertical component =', (Nbot0*sinBot0/1000).toFixed(1), 'kN');
  console.log('N_end_diagonal =', (Ndiag/1000).toFixed(1), 'kN, vertical component =', (Ndiag*sinDiag/1000).toFixed(1), 'kN');
  console.log('Sum of member vertical components =', ((Nvert*sinVert+Nbot0*sinBot0+Ndiag*sinDiag)/1000).toFixed(1), 'kN (should equal -reaction at B0)');
}

// gate e: deflection under service load
const { model, femToTruss, idx } = buildComboModel(truss, sizing, Lt, SERVICE_COMBO);
const res = model.solve();
const midBotNode = idx['B' + (truss.n / 2)];
const midTopNode = idx['T' + (truss.n / 2)];
console.log('\n--- Gate e: service deflection at midspan ---');
console.log('Bottom-chord midnode vertical deflection =', res.D[3*midBotNode+1].toFixed(2), 'mm (hand calc ~15-35mm range expected)');
console.log('Top-chord midnode vertical deflection =', res.D[3*midTopNode+1].toFixed(2), 'mm');
console.log('Deflection limit L/250 =', (L*1000/250).toFixed(1), 'mm, L/300(LL only, not computed separately here) =', (L*1000/300).toFixed(1), 'mm');
