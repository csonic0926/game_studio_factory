/**
 * Gerstner-style pixel abstraction from Renaiss-Protocol/renaiss-verse,
 * scripts/pixel_snap.js at d413e7f57b1eec48ade231721b2c23b65bc36d05.
 * Factory entry point: itf.py pixel-snap. The cell, palette and alpha
 * algorithms below are unchanged; only final encoding and I/O are adapted.
 */
const fs = require("node:fs");
const sharp = require("sharp");

// ── Profiles ──────────────────────────────────────────────────────────

const ALPHA_THRESHOLD = 24;
const PROFILE_PRESETS = {
  conservative: {
    targetScale: 2,
    finalColors: 24,
    maxFinalColors: 42,
    regionIterations: 4,
    paletteIterations: 10,
    paletteSplitIterations: 4,
    searchRadius: 1,
    positionWeight: 9.0,
    importanceColorBoost: 1.2,
    alphaCoverageThreshold: 0.36,
    fringeCoverageThreshold: 0.58,
    fringeNeighborThreshold: 2,
    laplacianStrength: 0.18,
    saturationBoost: 0.0,
  },
  balanced: {
    targetScale: 3,
    finalColors: 20,
    maxFinalColors: 36,
    regionIterations: 5,
    paletteIterations: 10,
    paletteSplitIterations: 4,
    searchRadius: 2,
    positionWeight: 10.5,
    importanceColorBoost: 1.35,
    alphaCoverageThreshold: 0.40,
    fringeCoverageThreshold: 0.62,
    fringeNeighborThreshold: 2,
    laplacianStrength: 0.22,
    saturationBoost: 0.02,
  },
  chunky: {
    targetScale: 4,
    finalColors: 18,
    maxFinalColors: 32,
    regionIterations: 5,
    paletteIterations: 12,
    paletteSplitIterations: 5,
    searchRadius: 2,
    positionWeight: 12.0,
    importanceColorBoost: 1.5,
    alphaCoverageThreshold: 0.46,
    fringeCoverageThreshold: 0.68,
    fringeNeighborThreshold: 2,
    laplacianStrength: 0.26,
    saturationBoost: 0.04,
  },
};

function autoProfile(meta) {
  if (!meta?.width || !meta?.height) return "conservative";
  const longSide = Math.max(meta.width, meta.height);
  const shortSide = Math.min(meta.width, meta.height);
  if (shortSide <= 128 || longSide <= 256) return "conservative";
  if (longSide >= 768) return "chunky";
  return "balanced";
}

function resolveOptions(options = {}, meta = null, sourceStats = null) {
  const requested = options.profile || options.targetMode || "conservative";
  const profile = requested === "auto" ? autoProfile(meta) : requested;
  const preset = PROFILE_PRESETS[profile] || PROFILE_PRESETS.conservative;
  const { profile: _profile, targetMode: _targetMode, ...overrides } = options;
  const cfg = { ...preset, ...overrides, profile };
  cfg.forceOpaqueOutput = false;

  // Gerstner's results rely on enough palette capacity for salient forms.
  // If a source has a very wide color distribution, let the palette grow
  // before optimization instead of collapsing town-hall-like assets too early.
  if (sourceStats?.uniqueColors > 128) {
    const extra = Math.min(
      cfg.maxFinalColors - cfg.finalColors,
      Math.ceil((sourceStats.uniqueColors - 128) / 14),
    );
    if (extra > 0) cfg.finalColors += extra;
  }
  return cfg;
}

// ── Color conversion / metrics ────────────────────────────────────────

function srgbToLinear(v) {
  v /= 255;
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

function linearToSrgb(v) {
  v = Math.max(0, Math.min(1, v));
  const s = v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055;
  return Math.max(0, Math.min(255, Math.round(s * 255)));
}

function rgbToLab(r, g, b) {
  const R = srgbToLinear(r), G = srgbToLinear(g), B = srgbToLinear(b);
  let x = (R * 0.4124564 + G * 0.3575761 + B * 0.1804375) / 0.95047;
  let y = (R * 0.2126729 + G * 0.7151522 + B * 0.0721750) / 1.00000;
  let z = (R * 0.0193339 + G * 0.1191920 + B * 0.9503041) / 1.08883;
  const f = (t) => t > 0.008856 ? Math.cbrt(t) : (7.787 * t + 16 / 116);
  x = f(x); y = f(y); z = f(z);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}

function labToRgb(L, a, b) {
  const fy = (L + 16) / 116;
  const fx = a / 500 + fy;
  const fz = fy - b / 200;
  const finv = (t) => {
    const t3 = t * t * t;
    return t3 > 0.008856 ? t3 : (t - 16 / 116) / 7.787;
  };
  const x = 0.95047 * finv(fx);
  const y = 1.00000 * finv(fy);
  const z = 1.08883 * finv(fz);
  const R = x * 3.2404542 + y * -1.5371385 + z * -0.4985314;
  const G = x * -0.9692660 + y * 1.8760108 + z * 0.0415560;
  const B = x * 0.0556434 + y * -0.2040259 + z * 1.0572252;
  return [linearToSrgb(R), linearToSrgb(G), linearToSrgb(B)];
}

function labDistSq(a, b) {
  const dL = a[0] - b[0], da = a[1] - b[1], db = a[2] - b[2];
  return dL * dL + da * da + db * db;
}

function labLumaChroma(lab) {
  return { L: lab[0], C: Math.sqrt(lab[1] * lab[1] + lab[2] * lab[2]) };
}

function boostLabSaturation(lab, amount) {
  if (!amount) return lab;
  return [lab[0], lab[1] * (1 + amount), lab[2] * (1 + amount)];
}

// ── Source analysis ──────────────────────────────────────────────────

function countUniqueRgba(data) {
  const colors = new Set();
  let opaquePixels = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] <= ALPHA_THRESHOLD) continue;
    opaquePixels++;
    colors.add(`${data[i]},${data[i + 1]},${data[i + 2]},${data[i + 3]}`);
  }
  return { uniqueColors: colors.size, opaquePixels };
}

function buildSourcePixels(data, w, h) {
  const n = w * h;
  const labs = new Array(n);
  const opaque = new Uint8Array(n);
  const importance = new Float32Array(n);

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      const i = p * 4;
      const a = data[i + 3];
      if (a > ALPHA_THRESHOLD) {
        opaque[p] = 1;
        labs[p] = rgbToLab(data[i], data[i + 1], data[i + 2]);
      } else {
        labs[p] = [0, 0, 0];
      }
    }
  }

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      if (!opaque[p]) continue;
      let edge = 0;
      let colorGrad = 0;
      let neighbors = 0;
      const lab = labs[p];
      for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || nx >= w || ny < 0 || ny >= h) { edge += 1; continue; }
        const q = ny * w + nx;
        if (!opaque[q]) { edge += 1; continue; }
        colorGrad += Math.sqrt(labDistSq(lab, labs[q]));
        neighbors++;
      }
      colorGrad = neighbors ? colorGrad / neighbors : 0;
      // Silhouette and high-contrast structures are the asset features most
      // likely to be intentionally placed by an artist.
      importance[p] = 1 + Math.min(2.5, edge * 0.7) + Math.min(2.0, colorGrad / 24);
    }
  }

  return { labs, opaque, importance };
}

// ── Output cell / superpixel model ────────────────────────────────────

function makeCells(outW, outH, srcW, srcH) {
  const n = outW * outH;
  const cells = new Array(n);
  for (let y = 0; y < outH; y++) {
    for (let x = 0; x < outW; x++) {
      const id = y * outW + x;
      cells[id] = {
        id, x, y,
        cx: (x + 0.5) * srcW / outW,
        cy: (y + 0.5) * srcH / outH,
        lab: [0, 0, 0],
        coverage: 0,
        weight: 0,
        importance: 1,
        palette: -1,
      };
    }
  }
  return cells;
}

function initialAssignments(srcW, srcH, outW, outH) {
  const assign = new Int32Array(srcW * srcH);
  for (let y = 0; y < srcH; y++) {
    const oy = Math.min(outH - 1, Math.floor(y * outH / srcH));
    for (let x = 0; x < srcW; x++) {
      const ox = Math.min(outW - 1, Math.floor(x * outW / srcW));
      assign[y * srcW + x] = oy * outW + ox;
    }
  }
  return assign;
}

function recomputeCells(cells, assign, source, srcW, srcH, outW, outH) {
  const n = cells.length;
  const sumL = new Float64Array(n), sumA = new Float64Array(n), sumB = new Float64Array(n);
  const colorW = new Float64Array(n), totalW = new Float64Array(n), opaqueW = new Float64Array(n), impW = new Float64Array(n);

  for (let p = 0; p < assign.length; p++) {
    const id = assign[p];
    totalW[id] += 1;
    if (!source.opaque[p]) continue;
    const w = source.importance[p] || 1;
    const lab = source.labs[p];
    sumL[id] += lab[0] * w;
    sumA[id] += lab[1] * w;
    sumB[id] += lab[2] * w;
    colorW[id] += w;
    opaqueW[id] += 1;
    impW[id] += w;
  }

  for (let id = 0; id < n; id++) {
    const c = cells[id];
    if (colorW[id] > 0) c.lab = [sumL[id] / colorW[id], sumA[id] / colorW[id], sumB[id] / colorW[id]];
    c.coverage = totalW[id] > 0 ? opaqueW[id] / totalW[id] : 0;
    c.weight = colorW[id];
    c.importance = opaqueW[id] > 0 ? Math.max(1, impW[id] / opaqueW[id]) : 1;
    // Mild Laplacian center smoothing keeps regions aligned with rectangular
    // output neighborhoods, borrowing the paper's grid-regularization insight.
    const x = id % outW, y = Math.floor(id / outW);
    c.cx = (x + 0.5) * srcW / outW;
    c.cy = (y + 0.5) * srcH / outH;
  }
}

function smoothCellLabs(cells, outW, outH, strength) {
  if (!strength) return;
  const before = cells.map(c => c.lab.slice());
  for (let y = 0; y < outH; y++) {
    for (let x = 0; x < outW; x++) {
      const id = y * outW + x;
      if (cells[id].coverage <= 0) continue;
      let n = 0, L = 0, A = 0, B = 0;
      for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || nx >= outW || ny < 0 || ny >= outH) continue;
        const nid = ny * outW + nx;
        if (cells[nid].coverage <= 0) continue;
        L += before[nid][0]; A += before[nid][1]; B += before[nid][2]; n++;
      }
      if (!n) continue;
      cells[id].lab = [
        before[id][0] * (1 - strength) + (L / n) * strength,
        before[id][1] * (1 - strength) + (A / n) * strength,
        before[id][2] * (1 - strength) + (B / n) * strength,
      ];
    }
  }
}

// ── Palette optimization ──────────────────────────────────────────────

function weightedMeanLab(items) {
  let sw = 0, L = 0, A = 0, B = 0;
  for (const it of items) {
    const w = it.weight;
    sw += w; L += it.lab[0] * w; A += it.lab[1] * w; B += it.lab[2] * w;
  }
  return sw > 0 ? [L / sw, A / sw, B / sw] : [0, 0, 0];
}

function optimizePalette(cells, k, cfg) {
  const items = cells
    .filter(c => c.coverage >= cfg.alphaCoverageThreshold * 0.5 && c.weight > 0)
    .map(c => ({ lab: c.lab, weight: c.weight * c.importance }));
  if (!items.length) return [[0, 0, 0]];

  let palette = [weightedMeanLab(items)];
  while (palette.length < k) {
    const groups = palette.map(() => []);
    for (const it of items) {
      let best = 0, bestD = Infinity;
      for (let i = 0; i < palette.length; i++) {
        const d = labDistSq(it.lab, palette[i]);
        if (d < bestD) { bestD = d; best = i; }
      }
      groups[best].push(it);
    }

    let splitIdx = -1, splitScore = -1;
    for (let i = 0; i < groups.length; i++) {
      let err = 0;
      for (const it of groups[i]) err += labDistSq(it.lab, palette[i]) * it.weight;
      if (err > splitScore && groups[i].length > 1) { splitScore = err; splitIdx = i; }
    }
    if (splitIdx < 0) break;

    const group = groups[splitIdx];
    const center = palette[splitIdx];
    let far = group[0], farD = -1;
    for (const it of group) {
      const d = labDistSq(it.lab, center);
      if (d > farD) { farD = d; far = it; }
    }
    const dir = [far.lab[0] - center[0], far.lab[1] - center[1], far.lab[2] - center[2]];
    const len = Math.sqrt(dir[0] ** 2 + dir[1] ** 2 + dir[2] ** 2) || 1;
    const step = Math.min(8, Math.sqrt(farD) * 0.35);
    palette[splitIdx] = [center[0] - dir[0] / len * step, center[1] - dir[1] / len * step, center[2] - dir[2] / len * step];
    palette.push([center[0] + dir[0] / len * step, center[1] + dir[1] / len * step, center[2] + dir[2] / len * step]);

    refinePalette(items, palette, cfg.paletteSplitIterations);
  }
  refinePalette(items, palette, cfg.paletteIterations);
  return palette;
}

function refinePalette(items, palette, iterations) {
  for (let iter = 0; iter < iterations; iter++) {
    const sums = palette.map(() => [0, 0, 0, 0]);
    for (const it of items) {
      let best = 0, bestD = Infinity;
      for (let i = 0; i < palette.length; i++) {
        const d = labDistSq(it.lab, palette[i]);
        if (d < bestD) { bestD = d; best = i; }
      }
      const s = sums[best];
      s[0] += it.lab[0] * it.weight; s[1] += it.lab[1] * it.weight; s[2] += it.lab[2] * it.weight; s[3] += it.weight;
    }
    let moved = false;
    for (let i = 0; i < palette.length; i++) {
      if (sums[i][3] <= 0) continue;
      const next = [sums[i][0] / sums[i][3], sums[i][1] / sums[i][3], sums[i][2] / sums[i][3]];
      if (labDistSq(next, palette[i]) > 0.01) moved = true;
      palette[i] = next;
    }
    if (!moved) break;
  }
}

function assignCellPalette(cells, palette, cfg) {
  for (const c of cells) {
    if (c.coverage < cfg.alphaCoverageThreshold * 0.5 || c.weight <= 0) { c.palette = -1; continue; }
    let best = 0, bestD = Infinity;
    for (let i = 0; i < palette.length; i++) {
      const d = labDistSq(c.lab, palette[i]);
      if (d < bestD) { bestD = d; best = i; }
    }
    c.palette = best;
  }
}

// ── Region assignment ─────────────────────────────────────────────────

function reassignPixels(assign, cells, palette, source, srcW, srcH, outW, outH, cfg) {
  const cellW = srcW / outW;
  const cellH = srcH / outH;
  const diag = Math.sqrt(cellW * cellW + cellH * cellH) || 1;
  const r = cfg.searchRadius;

  for (let y = 0; y < srcH; y++) {
    const baseOy = Math.min(outH - 1, Math.floor(y * outH / srcH));
    for (let x = 0; x < srcW; x++) {
      const p = y * srcW + x;
      const baseOx = Math.min(outW - 1, Math.floor(x * outW / srcW));
      let bestId = assign[p], bestCost = Infinity;
      const isOpaque = source.opaque[p] === 1;
      const lab = source.labs[p];
      const imp = source.importance[p] || 1;

      for (let oy = Math.max(0, baseOy - r); oy <= Math.min(outH - 1, baseOy + r); oy++) {
        for (let ox = Math.max(0, baseOx - r); ox <= Math.min(outW - 1, baseOx + r); ox++) {
          const id = oy * outW + ox;
          const c = cells[id];
          const dx = (x + 0.5 - c.cx) / diag;
          const dy = (y + 0.5 - c.cy) / diag;
          let cost = (dx * dx + dy * dy) * cfg.positionWeight * 100;
          if (isOpaque) {
            const pal = c.palette >= 0 ? palette[c.palette] : c.lab;
            cost += labDistSq(lab, pal) * (1 + (imp - 1) * cfg.importanceColorBoost);
          } else {
            // Transparent is a special class. Discourage background pixels from
            // being swallowed by strongly opaque cells, but keep spatial cost
            // dominant so silhouettes stay local.
            cost += c.coverage > cfg.alphaCoverageThreshold ? 180 : 0;
          }
          if (cost < bestCost) { bestCost = cost; bestId = id; }
        }
      }
      assign[p] = bestId;
    }
  }
}

// ── Output / silhouette post-process ──────────────────────────────────

function buildOutput(cells, palette, outW, outH, cfg, source = null, srcW = outW, srcH = outH) {
  const out = Buffer.alloc(outW * outH * 4);
  const coverage = new Float32Array(outW * outH);
  for (let id = 0; id < cells.length; id++) {
    const c = cells[id];
    coverage[id] = c.coverage;
    const i = id * 4;
    if (!cfg.forceOpaqueOutput && (c.coverage < cfg.alphaCoverageThreshold || c.palette < 0)) continue;
    const lab = c.palette >= 0 ? palette[c.palette] : c.lab;
    const rgb = labToRgb(...boostLabSaturation(lab, cfg.saturationBoost));
    out[i] = rgb[0]; out[i + 1] = rgb[1]; out[i + 2] = rgb[2]; out[i + 3] = 255;
  }
  if (cfg.forceOpaqueOutput) {
    fillTransparentFromNeighbors(out, outW, outH);
    for (let i = 3; i < out.length; i += 4) out[i] = 255;
  } else {
    cleanupFringe(out, outW, outH, coverage, cfg);
    repairUnsupportedInteriorTransparency(out, outW, outH, source, srcW, srcH, palette, cfg);
  }
  return out;
}

function buildBaseCellFallbacks(source, srcW, srcH, outW, outH) {
  const n = outW * outH;
  const total = new Uint32Array(n);
  const opaque = new Uint32Array(n);
  const weight = new Float64Array(n);
  const sumL = new Float64Array(n);
  const sumA = new Float64Array(n);
  const sumB = new Float64Array(n);

  for (let y = 0; y < srcH; y++) {
    const oy = Math.min(outH - 1, Math.floor(y * outH / srcH));
    for (let x = 0; x < srcW; x++) {
      const ox = Math.min(outW - 1, Math.floor(x * outW / srcW));
      const id = oy * outW + ox;
      const p = y * srcW + x;
      total[id] += 1;
      if (!source.opaque[p]) continue;
      const w = source.importance[p] || 1;
      const lab = source.labs[p];
      opaque[id] += 1;
      weight[id] += w;
      sumL[id] += lab[0] * w;
      sumA[id] += lab[1] * w;
      sumB[id] += lab[2] * w;
    }
  }

  return { total, opaque, weight, sumL, sumA, sumB };
}

function nearestPaletteLab(lab, palette) {
  if (!palette || palette.length === 0) return lab;
  let best = palette[0];
  let bestD = labDistSq(lab, best);
  for (let i = 1; i < palette.length; i++) {
    const d = labDistSq(lab, palette[i]);
    if (d < bestD) {
      bestD = d;
      best = palette[i];
    }
  }
  return best;
}

function repairUnsupportedInteriorTransparency(data, outW, outH, source, srcW, srcH, palette, cfg) {
  if (!source) return;

  const n = outW * outH;
  const exteriorTransparent = new Uint8Array(n);
  const queue = [];
  const pushExterior = (x, y) => {
    if (x < 0 || x >= outW || y < 0 || y >= outH) return;
    const id = y * outW + x;
    if (exteriorTransparent[id] || data[id * 4 + 3] !== 0) return;
    exteriorTransparent[id] = 1;
    queue.push(id);
  };

  for (let x = 0; x < outW; x++) {
    pushExterior(x, 0);
    pushExterior(x, outH - 1);
  }
  for (let y = 0; y < outH; y++) {
    pushExterior(0, y);
    pushExterior(outW - 1, y);
  }

  for (let head = 0; head < queue.length; head++) {
    const id = queue[head];
    const x = id % outW;
    const y = Math.floor(id / outW);
    pushExterior(x - 1, y);
    pushExterior(x + 1, y);
    pushExterior(x, y - 1);
    pushExterior(x, y + 1);
  }

  const base = buildBaseCellFallbacks(source, srcW, srcH, outW, outH);
  for (let id = 0; id < n; id++) {
    const offset = id * 4;
    if (data[offset + 3] !== 0 || exteriorTransparent[id]) continue;
    if (!base.total[id] || !base.weight[id]) continue;
    const baseCoverage = base.opaque[id] / base.total[id];
    if (baseCoverage < cfg.alphaCoverageThreshold) continue;

    const avgLab = [
      base.sumL[id] / base.weight[id],
      base.sumA[id] / base.weight[id],
      base.sumB[id] / base.weight[id],
    ];
    const lab = nearestPaletteLab(avgLab, palette);
    const rgb = labToRgb(...boostLabSaturation(lab, cfg.saturationBoost));
    data[offset] = rgb[0];
    data[offset + 1] = rgb[1];
    data[offset + 2] = rgb[2];
    data[offset + 3] = 255;
  }
}

function fillTransparentFromNeighbors(data, w, h) {
  const copy = Buffer.from(data);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = (y * w + x) * 4;
      if (copy[idx + 3] !== 0) continue;
      let r = 0, g = 0, b = 0, n = 0;
      for (let radius = 1; radius <= 3 && n === 0; radius++) {
        for (let dy = -radius; dy <= radius; dy++) {
          for (let dx = -radius; dx <= radius; dx++) {
            if (dx === 0 && dy === 0) continue;
            const nx = x + dx, ny = y + dy;
            if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;
            const ni = (ny * w + nx) * 4;
            if (copy[ni + 3] === 0) continue;
            r += copy[ni]; g += copy[ni + 1]; b += copy[ni + 2]; n++;
          }
        }
      }
      if (n > 0) {
        data[idx] = Math.round(r / n);
        data[idx + 1] = Math.round(g / n);
        data[idx + 2] = Math.round(b / n);
      }
    }
  }
}

function cleanupFringe(data, w, h, coverage, cfg) {
  const copy = Buffer.from(data);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = (y * w + x) * 4;
      if (copy[idx + 3] === 0) continue;
      if (coverage[y * w + x] >= cfg.fringeCoverageThreshold) continue;
      let opaque8 = 0, opaqueCardinal = 0;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;
          const ni = (ny * w + nx) * 4;
          if (copy[ni + 3] === 0) continue;
          opaque8++;
          if (Math.abs(dx) + Math.abs(dy) === 1) opaqueCardinal++;
        }
      }
      if (opaqueCardinal === 0 || opaque8 <= cfg.fringeNeighborThreshold) {
        data[idx] = 0; data[idx + 1] = 0; data[idx + 2] = 0; data[idx + 3] = 0;
      }
    }
  }
}

// ── Main pipeline ─────────────────────────────────────────────────────

async function pixelSnap(inputPath, outputPath, options = {}) {
  const meta = await sharp(inputPath).metadata();
  const srcW = meta.width, srcH = meta.height;
  if (!srcW || !srcH) throw new Error(`Invalid image dimensions for ${inputPath}`);

  const { data } = await sharp(inputPath).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const sourceStats = countUniqueRgba(data);
  const cfg = resolveOptions(options, meta, sourceStats);
  // If the source has no transparent pixels, the abstraction step must not
  // invent transparency. Thin repeated structures such as fence rails can have
  // low-coverage/highlight cells after region reassignment; treating those as
  // silhouette fringe produces visible background-colored holes in-game.
  cfg.forceOpaqueOutput = sourceStats.opaquePixels === srcW * srcH;
  const outW = Math.max(1, Math.round(srcW / cfg.targetScale));
  const outH = Math.max(1, Math.round(srcH / cfg.targetScale));

  const source = buildSourcePixels(data, srcW, srcH);
  const cells = makeCells(outW, outH, srcW, srcH);
  const assign = initialAssignments(srcW, srcH, outW, outH);

  let palette = [[0, 0, 0]];
  for (let iter = 0; iter < cfg.regionIterations; iter++) {
    recomputeCells(cells, assign, source, srcW, srcH, outW, outH);
    smoothCellLabs(cells, outW, outH, cfg.laplacianStrength);
    palette = optimizePalette(cells, cfg.finalColors, cfg);
    assignCellPalette(cells, palette, cfg);
    reassignPixels(assign, cells, palette, source, srcW, srcH, outW, outH, cfg);
  }

  recomputeCells(cells, assign, source, srcW, srcH, outW, outH);
  smoothCellLabs(cells, outW, outH, cfg.laplacianStrength * 0.5);
  palette = optimizePalette(cells, cfg.finalColors, cfg);
  assignCellPalette(cells, palette, cfg);
  const out = buildOutput(cells, palette, outW, outH, cfg, source, srcW, srcH);

  // Encode the actual optimized cells, not a downscale of the enlarged PNG.
  let image = sharp(out, { raw: { width: outW, height: outH, channels: 4 } });
  if (!options.trueGrid) image = image.resize(srcW, srcH, { kernel: "nearest" });
  const png = await image.png().toBuffer({ resolveWithObject: true });
  await fs.promises.writeFile(outputPath, png.data, { flag: "wx" });

  return {
    width: srcW,
    height: srcH,
    outputWidth: png.info.width,
    outputHeight: png.info.height,
    profile: cfg.profile,
    sourceUniqueColors: sourceStats.uniqueColors,
    finalColors: palette.length,
    targetScale: cfg.targetScale,
    gridW: outW,
    gridH: outH,
    targetW: outW,
    targetH: outH,
    regionIterations: cfg.regionIterations,
  };
}

module.exports = { pixelSnap };
