'use strict';
// SHS (square hollow section) property generator, sharp-corner approximation.
// A = 2t(B+H-2t) with B=H for SHS.  I = (B^4-(B-2t)^4)/12.  Zp = (B^3-(B-2t)^3)/4.
// Units: mm in, mm^2/mm^3/mm^4 out.

function shsProps(B, t) {
  const h = B - 2 * t;
  if (h <= 0) return null;
  const A = 2 * t * (2 * B - 2 * t); // = 4t(B-t)
  const I = (Math.pow(B, 4) - Math.pow(h, 4)) / 12;
  const Zp = (Math.pow(B, 3) - Math.pow(h, 3)) / 4;
  const Ze = 2 * I / B;
  const r = Math.sqrt(I / A);
  return { type: 'SHS', B, H: B, t, A, I, Zp, Ze, r, label: `${B}x${B}x${t} SHS` };
}

// Standard-ish B (mm) and t (mm) grid, sharp-corner formulas per spec.
const B_LIST = [40, 50, 60, 65, 70, 75, 80, 90, 100, 110, 120, 125, 130, 140, 150, 160, 180, 200];
const T_LIST = [3, 3.6, 4, 4.5, 5, 6, 7, 8];

function buildCatalog() {
  const cat = [];
  for (const B of B_LIST) {
    for (const t of T_LIST) {
      if (t >= B / 2 - 1) continue; // avoid degenerate/unrealistic thin-wall ratio
      if (B / t < 8) continue; // avoid ultra-thick unrealistic sections
      const p = shsProps(B, t);
      if (p) cat.push(p);
    }
  }
  cat.sort((a, b) => a.A - b.A);
  return cat;
}

const CATALOG = buildCatalog();

module.exports = { shsProps, CATALOG };
