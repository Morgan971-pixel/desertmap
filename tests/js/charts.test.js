import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  globalShapSpec,
  holcSpec,
  tractShapSpec,
  fmtShap,
  renderGlobalShap,
  renderHolc,
  renderTractShap,
} from "../../site/js/charts.js";

const summary = JSON.parse(
  readFileSync(new URL("../../site/data/summary.json", import.meta.url), "utf8")
);

const rows = [
  { feature: "a", label: "Alpha", total: 1000 },
  { feature: "b", label: "Beta", total: 500 },
  { feature: "c", label: "Gamma", total: 0 },
];

const entries = [
  { label: "Poverty Rate", value: 0.123 },
  { label: "Urban Tract (yes/no)", value: -0.045 },
  { label: "% Households, No Vehicle", value: 0.0101 },
];

const plainText = (s) => String(s).replace(/<br\s*\/?>/gi, " ");

test("fresh import with window undefined does not throw", async () => {
  const saved = globalThis.window;
  delete globalThis.window;
  try {
    assert.equal(typeof globalThis.window, "undefined");
    const mod = await import(`../../site/js/charts.js?fresh=${Date.now()}`);
    assert.equal(typeof mod.renderHolc, "function");
  } finally {
    if (saved !== undefined) globalThis.window = saved;
  }
});

test("global SHAP: largest bar sits at the top", () => {
  const { data, layout } = globalShapSpec(rows);
  const trace = data[0];
  assert.equal(trace.orientation, "h");
  // Plotly draws the first category at the bottom unless the axis is reversed.
  const reversed = layout.yaxis && layout.yaxis.autorange === "reversed";
  const topIndex = reversed ? 0 : trace.y.length - 1;
  assert.equal(plainText(trace.y[topIndex]), "Alpha");
  assert.equal(trace.x[topIndex], 1000);
});

test("global SHAP: alpha formula endpoints", () => {
  const { data } = globalShapSpec(rows);
  const trace = data[0];
  const colorFor = (label) => trace.marker.color[trace.y.findIndex((y) => plainText(y) === label)];
  assert.equal(colorFor("Alpha"), "rgba(249,115,22,1)");
  assert.equal(colorFor("Beta"), "rgba(249,115,22,0.775)");
  assert.equal(colorFor("Gamma"), "rgba(249,115,22,0.55)");
});

test("global SHAP: text and colors stay aligned with x after sorting", () => {
  const shuffled = [rows[2], rows[0], rows[1]];
  const trace = globalShapSpec(shuffled).data[0];
  assert.deepEqual(trace.x, [1000, 500, 0]);
  assert.deepEqual(trace.text, ["1.0k", "0.5k", "0.0k"]);
  assert.deepEqual(trace.y, ["Alpha", "Beta", "Gamma"]);
  trace.x.forEach((x, i) => assert.equal(trace.text[i], `${(x / 1000).toFixed(1)}k`));
});

test("global SHAP: narrow mode wraps long labels with <br>", () => {
  const narrowY = globalShapSpec(summary.global_shap, { narrow: true }).data[0].y;
  const wideY = globalShapSpec(summary.global_shap, { narrow: false }).data[0].y;
  assert.ok(narrowY.includes("% Households, No<br>Vehicle"));
  assert.ok(wideY.includes("% Households, No Vehicle"));
});

test("global SHAP: text format and axis", () => {
  const { data, layout, config } = globalShapSpec(summary.global_shap);
  const trace = data[0];
  assert.ok(trace.text.includes("62.9k"));
  assert.equal(trace.textposition, "outside");
  const title = layout.xaxis.title.text ?? layout.xaxis.title;
  assert.equal(title, "Cumulative |SHAP| across all tracts");
  assert.equal(layout.xaxis.showticklabels, false);
  assert.equal(layout.showlegend, false);
  assert.deepEqual(config, { displayModeBar: false, responsive: true, staticPlot: false });
});

test("global SHAP: narrow mode shrinks right margin below 160", () => {
  const wide = globalShapSpec(summary.global_shap, { narrow: false }).layout;
  const narrow = globalShapSpec(summary.global_shap, { narrow: true }).layout;
  assert.ok(narrow.margin.r < 160);
  assert.ok(narrow.margin.r <= wide.margin.r);
});

test("HOLC: grades, colors, rates and text", () => {
  const { data } = holcSpec(summary.holc);
  const trace = data[0];
  assert.deepEqual(trace.x, ["A", "B", "C", "D"]);
  assert.deepEqual(trace.marker.color, ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444"]);
  const r = summary.holc.rates;
  assert.deepEqual(trace.y, [r.A * 100, r.B * 100, r.C * 100, r.D * 100]);
  assert.deepEqual(trace.text, ["10.8%", "18.0%", "24.2%", "27.4%"]);
  assert.equal(trace.textposition, "outside");
});

test("HOLC: axes", () => {
  const { layout } = holcSpec(summary.holc);
  const ytitle = layout.yaxis.title.text ?? layout.yaxis.title;
  const xtitle = layout.xaxis.title.text ?? layout.xaxis.title;
  assert.equal(ytitle, "% predicted food desert");
  assert.equal(xtitle, "HOLC grade (A = best, D = hazardous)");
  assert.equal(layout.yaxis.ticksuffix, "%");
  assert.equal(layout.yaxis.range[0], 0);
  assert.ok(Math.abs(layout.yaxis.range[1] - summary.holc.rates.D * 130) < 1e-9);
});

test("HOLC: all-zero rates still give a usable y range", () => {
  const zero = { rates: { A: 0, B: 0, C: 0, D: 0 }, cd_rate: 0, ab_rate: 0 };
  const { layout } = holcSpec(zero);
  assert.deepEqual(layout.yaxis.range, [0, 130]);
  assert.ok(layout.annotations[0].y > 0);
});

test("HOLC: annotation uses pooled cd_rate/ab_rate exactly", () => {
  const { layout } = holcSpec(summary.holc);
  assert.equal(layout.annotations.length, 1);
  assert.equal(layout.annotations[0].text, "<b>C+D tracts: 25.4%</b><br>vs A+B tracts: 16.2%");
  // Pooled, not averaged: averaging grade rates would give 25.8% / 14.4%.
  const fake = { ...summary.holc, cd_rate: 0.5, ab_rate: 0.25 };
  assert.equal(
    holcSpec(fake).layout.annotations[0].text,
    "<b>C+D tracts: 50.0%</b><br>vs A+B tracts: 25.0%"
  );
});

test("HOLC: narrow mode reduces margins", () => {
  const wide = holcSpec(summary.holc, { narrow: false }).layout.margin;
  const narrow = holcSpec(summary.holc, { narrow: true }).layout.margin;
  assert.ok(narrow.l + narrow.r <= wide.l + wide.r);
});

test("tract SHAP: order preserved top to bottom", () => {
  const { data, layout } = tractShapSpec(entries);
  const trace = data[0];
  assert.equal(trace.orientation, "h");
  assert.equal(layout.yaxis.autorange, "reversed");
  assert.deepEqual(trace.y, [0, 1, 2]);
  assert.deepEqual(layout.yaxis.tickvals, [0, 1, 2]);
  assert.deepEqual(layout.yaxis.ticktext.map(plainText), entries.map((e) => e.label));
  assert.deepEqual(trace.x, [0.123, -0.045, 0.0101]);
});

test("tract SHAP: duplicate labels stay separate bars", () => {
  const dup = [
    { label: "Unknown", value: 0.2 },
    { label: "Unknown", value: -0.1 },
  ];
  const { data, layout } = tractShapSpec(dup);
  assert.equal(new Set(data[0].y).size, 2);
  assert.deepEqual(data[0].x, [0.2, -0.1]);
  assert.deepEqual(layout.yaxis.ticktext, ["Unknown", "Unknown"]);
});

test("tract SHAP: sign colors and signed text, near-zero is neutral", () => {
  const { data } = tractShapSpec([
    ...entries,
    { label: "Zero", value: 0 },
    { label: "Tiny pos", value: 0.0004 },
    { label: "Tiny neg", value: -0.0004 },
  ]);
  const trace = data[0];
  assert.deepEqual(trace.marker.color, [
    "#ef4444", "#3b82f6", "#ef4444", "#8b949e", "#8b949e", "#8b949e",
  ]);
  assert.deepEqual(trace.text, ["+0.123", "-0.045", "+0.010", "0.000", "0.000", "0.000"]);
});

test("fmtShap formats signed 3dp with neutral near-zero", () => {
  assert.equal(fmtShap(0.123), "+0.123");
  assert.equal(fmtShap(-0.045), "-0.045");
  assert.equal(fmtShap(0.0004999), "0.000");
  assert.equal(fmtShap(-0.0004999), "0.000");
  assert.equal(fmtShap(0.0005), "+0.001");
});

test("tract SHAP: vertical zero line", () => {
  const { layout } = tractShapSpec(entries);
  const line = layout.shapes.find((s) => s.type === "line" && s.x0 === 0 && s.x1 === 0);
  assert.ok(line, "zero line shape present");
  assert.equal(line.line.color, "#484f58");
});

test("tract SHAP: x range includes 0 for one-signed inputs", () => {
  for (const vals of [[0.3, 0.1, 0.05], [-0.3, -0.1, -0.05]]) {
    const { layout } = tractShapSpec(vals.map((v, i) => ({ label: "f" + i, value: v })));
    const [lo, hi] = layout.xaxis.range;
    assert.ok(lo < 0 && hi > 0, `range ${lo},${hi} must straddle 0`);
    const line = layout.shapes.find((s) => s.type === "line");
    assert.equal(line.x0, 0);
    assert.equal(line.x1, 0);
  }
});

test("tract SHAP: narrow mode reduces margins", () => {
  const wide = tractShapSpec(entries, { narrow: false }).layout.margin;
  const narrow = tractShapSpec(entries, { narrow: true }).layout.margin;
  assert.ok(narrow.l + narrow.r <= wide.l + wide.r);
});

test("heights and shared styling", () => {
  assert.equal(globalShapSpec(rows).layout.height, 340);
  assert.equal(holcSpec(summary.holc).layout.height, 360);
  assert.equal(tractShapSpec(entries).layout.height, 185);
  for (const { layout } of [globalShapSpec(rows), holcSpec(summary.holc), tractShapSpec(entries)]) {
    assert.equal(layout.font.color, "#e6edf3");
    assert.match(layout.font.family, /Inter/);
    assert.equal(layout.showlegend, false);
  }
});

test("builders throw on empty or malformed input", () => {
  assert.throws(() => globalShapSpec([]), Error);
  assert.throws(() => globalShapSpec(null), Error);
  assert.throws(() => globalShapSpec([{ label: "x", total: NaN }]), Error);
  assert.throws(() => holcSpec(null), Error);
  assert.throws(() => holcSpec({ rates: { A: 0.1 }, cd_rate: 0.2, ab_rate: 0.1 }), Error);
  assert.throws(() => holcSpec({ ...summary.holc, cd_rate: undefined }), Error);
  assert.throws(() => tractShapSpec([]), Error);
  assert.throws(() => tractShapSpec(undefined), Error);
  assert.throws(() => tractShapSpec([{ label: "x", value: "abc" }]), Error);
});

// ---------- Renderers (fake window.Plotly and elements) ----------

function withFakePlotly(fn) {
  const saved = globalThis.window;
  const calls = [];
  globalThis.window = {
    Plotly: {
      newPlot: (el, data, layout, config) => {
        calls.push({ el, data, layout, config });
        return Promise.resolve(el);
      },
    },
  };
  return Promise.resolve()
    .then(() => fn(calls))
    .finally(() => {
      if (saved === undefined) delete globalThis.window;
      else globalThis.window = saved;
    });
}

test("renderers pass narrow for clientWidth 500 and wide for 800 or 0", () =>
  withFakePlotly(async (calls) => {
    const narrowWrapped = globalShapSpec(summary.global_shap, { narrow: true }).layout.margin;
    const wide = globalShapSpec(summary.global_shap, { narrow: false }).layout.margin;
    await renderGlobalShap({ clientWidth: 500 }, summary.global_shap);
    await renderGlobalShap({ clientWidth: 800 }, summary.global_shap);
    await renderGlobalShap({ clientWidth: 0 }, summary.global_shap);
    assert.equal(calls.length, 3);
    assert.deepEqual(calls[0].layout.margin, narrowWrapped);
    assert.deepEqual(calls[1].layout.margin, wide);
    assert.deepEqual(calls[2].layout.margin, wide);
    await renderHolc({ clientWidth: 500 }, summary.holc);
    assert.deepEqual(calls[3].layout.margin, holcSpec(summary.holc, { narrow: true }).layout.margin);
    await renderTractShap({ clientWidth: 800 }, entries);
    assert.deepEqual(calls[4].layout.margin, tractShapSpec(entries).layout.margin);
    assert.deepEqual(calls[4].config, { displayModeBar: false, responsive: true, staticPlot: false });
  }));

test("renderers return the newPlot promise", () =>
  withFakePlotly(async () => {
    const el = { clientWidth: 700 };
    const p = renderHolc(el, summary.holc);
    assert.ok(p instanceof Promise);
    assert.equal(await p, el);
  }));

test("renderers throw when Plotly is missing or input is bad", async () => {
  const saved = globalThis.window;
  try {
    delete globalThis.window;
    assert.throws(() => renderHolc({ clientWidth: 700 }, summary.holc), /Plotly/);
    globalThis.window = {};
    assert.throws(() => renderGlobalShap({ clientWidth: 700 }, summary.global_shap), /Plotly/);
  } finally {
    if (saved === undefined) delete globalThis.window;
    else globalThis.window = saved;
  }
  await withFakePlotly(async (calls) => {
    assert.throws(() => renderTractShap({ clientWidth: 700 }, []), /tractShapSpec/);
    assert.throws(() => renderHolc(null, summary.holc), /element/);
    assert.equal(calls.length, 0);
  });
});
