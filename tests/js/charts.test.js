import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { globalShapSpec, holcSpec, tractShapSpec } from "../../site/js/charts.js";

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

test("importing charts.js does not touch window", () => {
  assert.equal(typeof globalThis.window, "undefined");
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
  assert.equal(colorFor("Beta"), "rgba(249,115,22,0.7)");
  assert.equal(colorFor("Gamma"), "rgba(249,115,22,0.4)");
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
  assert.deepEqual(trace.y.map(plainText), entries.map((e) => e.label));
  assert.deepEqual(trace.x, [0.123, -0.045, 0.0101]);
});

test("tract SHAP: sign colors and signed text", () => {
  const { data } = tractShapSpec([...entries, { label: "Zero", value: 0 }]);
  const trace = data[0];
  assert.deepEqual(trace.marker.color, ["#ef4444", "#3b82f6", "#ef4444", "#3b82f6"]);
  assert.deepEqual(trace.text, ["+0.123", "-0.045", "+0.010", "+0.000"]);
});

test("tract SHAP: vertical zero line", () => {
  const { layout } = tractShapSpec(entries);
  const line = layout.shapes.find((s) => s.type === "line" && s.x0 === 0 && s.x1 === 0);
  assert.ok(line, "zero line shape present");
  assert.equal(line.line.color, "#484f58");
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
