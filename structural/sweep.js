'use strict';
const { runTopology } = require('./optimize');
const { maxDmidAllowed } = require('./truss');

const L = 20.630;
const LT_T3 = 7.372;
const dMidMax = maxDmidAllowed(L); // ~2.4495
const N_LIST = [6, 7, 8, 9, 10, 12, 14, 16];
const DMID_LIST = [2.00, 2.15, 2.30, Math.round((dMidMax - 0.0005) * 1000) / 1000];
const PATTERNS = ['pratt', 'warren'];

const results = [];
for (const n of N_LIST) {
  for (const dMid of DMID_LIST) {
    for (const wp of PATTERNS) {
      let r;
      try {
        r = runTopology({ n, dMid, webPattern: wp, Lt: LT_T3, L });
      } catch (e) {
        r = { feasible: false, reason: 'ERROR: ' + e.message };
      }
      results.push({ n, dMid, webPattern: wp, r });
    }
  }
}

const feasible = results.filter(x => x.r.feasible && !x.r.anyOver);
feasible.sort((a, b) => a.r.mass - b.r.mass);

console.log('Total configs tried:', results.length, ' feasible & util<=0.95:', feasible.length);
console.log('\nRank | n | dMid | pattern | mass/truss(kg) | maxUtil | deflection(mm) | LB_mass(kg) | ratio');
feasible.slice(0, 12).forEach((x, idx) => {
  const r = x.r;
  console.log(
    (idx + 1) + ' | ' + x.n + ' | ' + x.dMid.toFixed(3) + ' | ' + x.webPattern + ' | ' +
    r.mass.toFixed(1) + ' | ' + r.maxUtil.toFixed(3) + ' | ' + r.deflection.toFixed(1) + ' | ' +
    r.lowerBoundMass.toFixed(1) + ' | ' + (r.mass / r.lowerBoundMass).toFixed(2)
  );
});

const infeasible = results.filter(x => !x.r.feasible || x.r.anyOver);
console.log('\nInfeasible/over-util count:', infeasible.length);
const reasons = {};
infeasible.forEach(x => { const k = x.r.reason || (x.r.anyOver ? 'util>0.95' : 'unknown'); reasons[k] = (reasons[k]||0)+1; });
console.log(reasons);

require('fs').writeFileSync(__dirname + '/sweep_results.json', JSON.stringify(results.map(x => ({
  n: x.n, dMid: x.dMid, webPattern: x.webPattern,
  feasible: x.r.feasible, mass: x.r.mass, lowerBoundMass: x.r.lowerBoundMass,
  maxUtil: x.r.maxUtil, anyOver: x.r.anyOver, deflection: x.r.deflection, droppedCount: x.r.droppedCount,
  reason: x.r.reason,
})), null, 2));
console.log('\nSaved sweep_results.json');
