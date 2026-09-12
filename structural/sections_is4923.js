'use strict';
// Real IS 4923:2017 (Third Revision) Table 1 -- Dimensions and Properties of Square
// Hollow Sections. Every row below was extracted programmatically (pdftotext -layout,
// then a regex parse -- see is4923_2017_table1.json) from the actual embedded text
// layer of the official BIS document (via BSB Edge, legitimate free non-commercial
// distribution), NOT eyeballed off a screenshot or scan. Zero transcription risk on
// the numbers themselves.
//
// Confirms: there is NO 200x200 SHS in either the 1997 or 2017 edition -- the table
// jumps directly from 180x180 to 220x220. Any design calling for "200x200 SHS" is
// specifying a section that does not exist and cannot be procured.
//
// Units as printed: B/D/t in mm, weight in kg/m, A in cm^2, I in cm^4, r in cm,
// Ze/Zp in cm^3. Converted below to the mm-based units (mm^2/mm^4/mm/mm^3) the rest
// of this project's engine (is800.js/optimize.js/analyze.js) uses, matching
// sections.js's shsProps() output shape for drop-in use.

const fs = require('fs');
const path = require('path');
const TABLE1 = JSON.parse(fs.readFileSync(path.join(__dirname, 'is4923_2017_table1.json'), 'utf8'));

function toMmProps(row) {
  return {
    type: 'SHS', B: row.B, H: row.B, t: row.t,
    A: row.A_cm2 * 100,     // cm^2 -> mm^2
    I: row.I_cm4 * 1e4,     // cm^4 -> mm^4
    Zp: row.Zp_cm3 * 1e3,   // cm^3 -> mm^3
    Ze: row.Ze_cm3 * 1e3,   // cm^3 -> mm^3
    r: row.r_cm * 10,       // cm -> mm
    weight_kgm: row.weight_kgm, // kept for direct cross-check against A*rho*1000 if ever wanted
    label: `${row.B}x${row.B}x${row.t} SHS`,
  };
}

// Full official table (83 real, orderable designations, 25x25 through 400x400).
const OFFICIAL_CATALOG = TABLE1.map(toMmProps).sort((a, b) => a.A - b.A);

// Practical subset: t >= 3.0mm (corrosion allowance / handling / weld-quality floor
// for an outdoor structure -- an engineering judgment call, not a code requirement;
// IS 4923 itself permits thinner walls, e.g. 25x25x2.0). This is the catalog actually
// used for CHRA-2502's re-sizing.
const PRACTICAL_CATALOG = OFFICIAL_CATALOG.filter(s => s.t >= 3.0);

module.exports = { TABLE1, OFFICIAL_CATALOG, PRACTICAL_CATALOG };
