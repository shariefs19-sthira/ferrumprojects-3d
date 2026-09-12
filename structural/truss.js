'use strict';
// Geometry generator for the mono-slope / fish-belly pickleball truss.
// Fixed top-chord line per brief: (0,8.752) -> (20.630,8.339) meters.
const TOP0 = { x: 0, y: 8.752 };
const SPAN_DEFAULT = 20.630;
const SLOPE = (8.339 - 8.752) / 20.630; // per meter, exact from given coordinates
const D_END = 1.0; // m, end depth
const CLEAR_LINE = 6.096; // m, 20ft

function buildTruss({ n, dMid, webPattern, L }) {
  L = L || SPAN_DEFAULT;
  const topNodes = [], botNodes = [];
  for (let i = 0; i <= n; i++) {
    const x = i * L / n;
    const yTop = TOP0.y + SLOPE * x;
    const depth = D_END + (dMid - D_END) * 4 * (x / L) * (1 - x / L);
    const yBot = yTop - depth;
    topNodes.push({ x, y: yTop });
    botNodes.push({ x, y: yBot, depth });
  }
  const minBotY = Math.min(...botNodes.map(b => b.y));
  const members = []; // {type:'top'|'bottom'|'vertical'|'diagonal', a:{grp,i}, b:{grp,i}}
  for (let i = 0; i < n; i++) members.push({ type: 'top', a: ['T', i], b: ['T', i + 1] });
  for (let i = 0; i < n; i++) members.push({ type: 'bottom', a: ['B', i], b: ['B', i + 1] });
  // end verticals always present (support drop)
  members.push({ type: 'vertical', a: ['T', 0], b: ['B', 0], end: true });
  members.push({ type: 'vertical', a: ['T', n], b: ['B', n], end: true });
  if (webPattern === 'pratt') {
    for (let i = 1; i < n; i++) members.push({ type: 'vertical', a: ['T', i], b: ['B', i] });
    for (let i = 0; i < n; i++) {
      if (i < n / 2) members.push({ type: 'diagonal', a: ['B', i], b: ['T', i + 1] });
      else members.push({ type: 'diagonal', a: ['T', i], b: ['B', i + 1] });
    }
  } else if (webPattern === 'warren') {
    for (let i = 0; i < n; i++) {
      if (i % 2 === 0) members.push({ type: 'diagonal', a: ['B', i], b: ['T', i + 1] });
      else members.push({ type: 'diagonal', a: ['T', i], b: ['B', i + 1] });
    }
  } else throw new Error('unknown webPattern ' + webPattern);

  return { n, dMid, L, topNodes, botNodes, members, minBotY, webPattern };
}

function clearHeightOk(truss) {
  return truss.minBotY >= CLEAR_LINE - 1e-6;
}

function maxDmidAllowed(L) {
  L = L || SPAN_DEFAULT;
  const yTopMid = TOP0.y + SLOPE * (L / 2);
  return yTopMid - CLEAR_LINE;
}

module.exports = { buildTruss, clearHeightOk, maxDmidAllowed, SPAN_DEFAULT, SLOPE, D_END, CLEAR_LINE, TOP0 };
