'use strict';
// 2D frame FEM solver. Units: N, mm, MPa (=N/mm^2) throughout -> fully consistent.
// Nodes: 3 DOF each (ux, uy, rz). Two element kinds:
//   'frame' - full 6-dof Euler beam-column (chords: rigid/continuous joints)
//   'truss' - axial-only, 99% moment release approximated as pinned (webs)

function solveGaussian(K, F) {
  const n = F.length;
  // Copy
  const A = K.map(row => row.slice());
  const b = F.slice();
  for (let col = 0; col < n; col++) {
    // pivot
    let piv = col;
    let maxAbs = Math.abs(A[col][col]);
    for (let r = col + 1; r < n; r++) {
      if (Math.abs(A[r][col]) > maxAbs) { maxAbs = Math.abs(A[r][col]); piv = r; }
    }
    if (maxAbs < 1e-9) throw new Error('Singular matrix (unstable structure) at col ' + col);
    if (piv !== col) {
      [A[col], A[piv]] = [A[piv], A[col]];
      [b[col], b[piv]] = [b[piv], b[col]];
    }
    const diag = A[col][col];
    for (let r = col + 1; r < n; r++) {
      const factor = A[r][col] / diag;
      if (factor === 0) continue;
      for (let c = col; c < n; c++) A[r][c] -= factor * A[col][c];
      b[r] -= factor * b[col];
    }
  }
  const x = new Array(n).fill(0);
  for (let r = n - 1; r >= 0; r--) {
    let sum = b[r];
    for (let c = r + 1; c < n; c++) sum -= A[r][c] * x[c];
    x[r] = sum / A[r][r];
  }
  return x;
}

function frameLocalK(E, A, I, L) {
  const EAL = E * A / L;
  const EIL3 = 12 * E * I / (L * L * L);
  const EIL2 = 6 * E * I / (L * L);
  const EIL = 4 * E * I / L;
  const EIL_2 = 2 * E * I / L;
  return [
    [EAL, 0, 0, -EAL, 0, 0],
    [0, EIL3, EIL2, 0, -EIL3, EIL2],
    [0, EIL2, EIL, 0, -EIL2, EIL_2],
    [-EAL, 0, 0, EAL, 0, 0],
    [0, -EIL3, -EIL2, 0, EIL3, -EIL2],
    [0, EIL2, EIL_2, 0, -EIL2, EIL],
  ];
}

// Equivalent nodal load vector (local coords) for UDL w (local +y direction), full 6-dof frame element.
function frameLocalUDL(w, L) {
  return [0, w * L / 2, w * L * L / 12, 0, w * L / 2, -w * L * L / 12];
}

function trussLocalK(E, A, L) {
  const EAL = E * A / L;
  return [[EAL, -EAL], [-EAL, EAL]];
}

class Model {
  constructor() {
    this.nodes = []; // {x,y} mm
    this.members = []; // {n1,n2,kind:'frame'|'truss', E,A,I, udl(local N/mm, +y=away from member... see sign), label}
    this.supports = {}; // nodeIndex -> {ux:bool, uy:bool, rz:bool}
    this.loads = []; // nodal loads {node, fx, fy, mz}
  }
  addNode(x, y) { this.nodes.push({ x, y }); return this.nodes.length - 1; }
  addMember(n1, n2, kind, E, A, I, udl, label) {
    this.members.push({ n1, n2, kind, E, A, I: I || 0, udl: udl || 0, label });
    return this.members.length - 1;
  }
  fixSupport(node, ux, uy, rz) { this.supports[node] = { ux, uy, rz }; }
  addNodalLoad(node, fx, fy, mz) {
    this.loads.push({ node, fx: fx || 0, fy: fy || 0, mz: mz || 0 });
  }

  geom(mi) {
    const m = this.members[mi];
    const p1 = this.nodes[m.n1], p2 = this.nodes[m.n2];
    const dx = p2.x - p1.x, dy = p2.y - p1.y;
    const L = Math.sqrt(dx * dx + dy * dy);
    const c = dx / L, s = dy / L;
    return { L, c, s };
  }

  solve() {
    const nDof = this.nodes.length * 3;
    const K = Array.from({ length: nDof }, () => new Array(nDof).fill(0));
    const F = new Array(nDof).fill(0);
    const memEq = []; // store local equivalent load vector per member for recovery

    const dofOf = (node) => [3 * node, 3 * node + 1, 3 * node + 2];

    for (let mi = 0; mi < this.members.length; mi++) {
      const m = this.members[mi];
      const { L, c, s } = this.geom(mi);
      if (m.kind === 'frame') {
        const kl = frameLocalK(m.E, m.A, m.I, L);
        // rotation matrix 6x6
        const T = [
          [c, s, 0, 0, 0, 0],
          [-s, c, 0, 0, 0, 0],
          [0, 0, 1, 0, 0, 0],
          [0, 0, 0, c, s, 0],
          [0, 0, 0, -s, c, 0],
          [0, 0, 0, 0, 0, 1],
        ];
        // kg = T' * kl * T
        const kg = matMulT(T, matMul(kl, T));
        const dofs = [...dofOf(m.n1), ...dofOf(m.n2)];
        addToGlobal(K, kg, dofs);

        let feqLocal = [0, 0, 0, 0, 0, 0];
        if (m.udl) {
          feqLocal = frameLocalUDL(m.udl, L);
          // transform local eq load to global: Fglobal = T' * feqLocal
          const fg = vecMulT(T, feqLocal);
          for (let i = 0; i < 6; i++) F[dofs[i]] += fg[i];
        }
        memEq.push({ T, feqLocal, dofs, kl, kind: 'frame' });
      } else {
        // truss: only translational stiffness contributes; rotational dof untouched
        const EAL = m.E * m.A / L;
        const cc = c * c, ss = s * s, cs = c * s;
        const kg4 = [
          [EAL * cc, EAL * cs, -EAL * cc, -EAL * cs],
          [EAL * cs, EAL * ss, -EAL * cs, -EAL * ss],
          [-EAL * cc, -EAL * cs, EAL * cc, EAL * cs],
          [-EAL * cs, -EAL * ss, EAL * cs, EAL * ss],
        ];
        const dofs = [3 * m.n1, 3 * m.n1 + 1, 3 * m.n2, 3 * m.n2 + 1];
        addToGlobal(K, kg4, dofs);
        memEq.push({ dofs, L, c, s, kind: 'truss', E: m.E, A: m.A });
      }
    }

    for (const ld of this.loads) {
      const d = dofOf(ld.node);
      F[d[0]] += ld.fx; F[d[1]] += ld.fy; F[d[2]] += ld.mz;
    }

    // Apply supports via penalty-free elimination: build reduced system
    const fixedDofs = new Set();
    for (const [nodeStr, sup] of Object.entries(this.supports)) {
      const node = Number(nodeStr);
      const d = dofOf(node);
      if (sup.ux) fixedDofs.add(d[0]);
      if (sup.uy) fixedDofs.add(d[1]);
      if (sup.rz) fixedDofs.add(d[2]);
    }
    const freeDofs = [];
    for (let i = 0; i < nDof; i++) if (!fixedDofs.has(i)) freeDofs.push(i);

    const nf = freeDofs.length;
    const Kff = Array.from({ length: nf }, () => new Array(nf).fill(0));
    const Ff = new Array(nf).fill(0);
    for (let i = 0; i < nf; i++) {
      Ff[i] = F[freeDofs[i]];
      for (let j = 0; j < nf; j++) Kff[i][j] = K[freeDofs[i]][freeDofs[j]];
    }
    const uf = solveGaussian(Kff, Ff);
    const D = new Array(nDof).fill(0);
    for (let i = 0; i < nf; i++) D[freeDofs[i]] = uf[i];

    // Reactions
    const R = new Array(nDof).fill(0);
    for (let i = 0; i < nDof; i++) {
      let sum = 0;
      for (let j = 0; j < nDof; j++) sum += K[i][j] * D[j];
      R[i] = sum - F[i];
    }

    // Recover member forces
    const results = [];
    for (let mi = 0; mi < this.members.length; mi++) {
      const eq = memEq[mi];
      const m = this.members[mi];
      if (eq.kind === 'frame') {
        const dg = eq.dofs.map(d => D[d]);
        const dl = vecMul(eq.T, dg); // local displacements
        const fl = vecMul(eq.kl, dl); // elastic force
        for (let i = 0; i < 6; i++) fl[i] -= eq.feqLocal[i];
        // fl = [N1,V1,M1,N2,V2,M2] in local coords
        results.push({
          idx: mi, kind: 'frame', N1: -fl[0], V1: fl[1], M1: fl[2], N2: fl[3], V2: -fl[4], M2: fl[5],
          udl: m.udl, L: this.geom(mi).L,
        });
      } else {
        const dofs = eq.dofs;
        const dg = dofs.map(d => D[d]);
        const c = eq.c, s = eq.s;
        const axial_disp = ((dg[2] - dg[0]) * c + (dg[3] - dg[1]) * s);
        const N = eq.E * eq.A / eq.L * axial_disp; // tension +
        results.push({ idx: mi, kind: 'truss', N, L: eq.L });
      }
    }
    return { D, R, results, freeDofs, fixedDofs: [...fixedDofs] };
  }
}

function matMul(A, B) {
  const n = A.length, m = B[0].length, k = B.length;
  const C = Array.from({ length: n }, () => new Array(m).fill(0));
  for (let i = 0; i < n; i++)
    for (let j = 0; j < m; j++) {
      let s = 0;
      for (let p = 0; p < k; p++) s += A[i][p] * B[p][j];
      C[i][j] = s;
    }
  return C;
}
function matMulT(T, B) {
  // T' * B  (T is square)
  const n = T.length, m = B[0].length;
  const C = Array.from({ length: n }, () => new Array(m).fill(0));
  for (let i = 0; i < n; i++)
    for (let j = 0; j < m; j++) {
      let s = 0;
      for (let p = 0; p < n; p++) s += T[p][i] * B[p][j];
      C[i][j] = s;
    }
  return C;
}
function vecMul(A, v) {
  const n = A.length;
  const r = new Array(n).fill(0);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let j = 0; j < v.length; j++) s += A[i][j] * v[j];
    r[i] = s;
  }
  return r;
}
function vecMulT(T, v) {
  const n = T.length;
  const r = new Array(n).fill(0);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let j = 0; j < n; j++) s += T[j][i] * v[j];
    r[i] = s;
  }
  return r;
}
function addToGlobal(K, kg, dofs) {
  const n = dofs.length;
  for (let i = 0; i < n; i++)
    for (let j = 0; j < n; j++) K[dofs[i]][dofs[j]] += kg[i][j];
}

module.exports = { Model };
