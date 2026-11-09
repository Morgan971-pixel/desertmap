// Pure, DOM-free logic shared by map.js and unit tests.
export const VIEWS = {
  all: "All tracts",
  predicted: "Predicted food deserts",
  tp: "True positives (correctly flagged)",
  fp: "False positives (incorrectly flagged)",
};

export function filterIndices(t, view, minProb) {
  if (!Object.hasOwn(VIEWS, view)) throw new Error(`unknown view: ${view}`);
  const { n, p, pred, actual } = t;
  const out = [];
  for (let i = 0; i < n; i++) {
    if (!(Number.isFinite(p[i]) && p[i] >= minProb)) continue;
    if (view === "predicted" && pred[i] !== 1) continue;
    if (view === "tp" && !(pred[i] === 1 && actual[i] === 1)) continue;
    if (view === "fp" && !(pred[i] === 1 && actual[i] === 0)) continue;
    out.push(i);
  }
  return out;
}

export function probToColor(p) {
  return [
    Math.round(49 + p * (214 - 49)),
    Math.round(160 + p * (39 - 160)),
    Math.round(208 + p * (40 - 208)),
    200,
  ];
}

export const tractId = (id) => String(id).padStart(11, "0");
export const fmtPct = (v) => (!Number.isFinite(v) ? "n/a" : `${v.toFixed(1)}%`);
