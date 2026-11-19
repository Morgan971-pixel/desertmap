import { test } from "node:test";
import assert from "node:assert/strict";

const fixture = {
  n: 3,
  id: [1001020100, 24510010100, 6037101110],
  p: [0.12345, 0.9876, NaN],
  pred: [0, 1, 1],
  actual: [0, 0, null],
  f1: [0, 1, 2],
  labels: ["Poverty rate", "Median income", "<b>Bold</b> & co"],
};

test("importing map.js without a window does not throw", async () => {
  assert.equal(typeof globalThis.window, "undefined");
  const mod = await import("../../site/js/map.js");
  assert.equal(typeof mod.initMap, "function");
});

test("tooltipLines gives padded id, 3-dp probability and labels", async () => {
  const { tooltipLines } = await import("../../site/js/map.js");
  assert.deepEqual(tooltipLines(fixture, 0), [
    "Tract 01001020100",
    "Probability 0.123",
    "Predicted: Not a food desert",
    "Actual: Not a food desert",
    "Top driver: Poverty rate",
  ]);
  assert.deepEqual(tooltipLines(fixture, 1), [
    "Tract 24510010100",
    "Probability 0.988",
    "Predicted: Food desert",
    "Actual: Not a food desert",
    "Top driver: Median income",
  ]);
});

test("tooltipLines handles missing probability and unknown actual", async () => {
  const { tooltipLines } = await import("../../site/js/map.js");
  const lines = tooltipLines(fixture, 2);
  assert.equal(lines[0], "Tract 06037101110");
  assert.equal(lines[1], "Probability n/a");
  assert.equal(lines[3], "Actual: Unknown");
});

test("tooltipLines falls back when a label index is out of range", async () => {
  const { tooltipLines } = await import("../../site/js/map.js");
  const t = { ...fixture, f1: [99, 1, 2] };
  assert.equal(tooltipLines(t, 0)[4], "Top driver: Unknown");
});

test("trueIndex maps a picked index through idx", async () => {
  const { trueIndex } = await import("../../site/js/map.js");
  const idx = [4, 9, 17];
  assert.equal(trueIndex(idx, 0), 4);
  assert.equal(trueIndex(idx, 2), 17);
  assert.equal(trueIndex(Uint32Array.from(idx), 1), 9);
});

test("trueIndex returns null for invalid picks", async () => {
  const { trueIndex } = await import("../../site/js/map.js");
  const idx = [4, 9];
  assert.equal(trueIndex(idx, -1), null);
  assert.equal(trueIndex(idx, 2), null);
  assert.equal(trueIndex(idx, undefined), null);
  assert.equal(trueIndex(idx, 1.5), null);
});

test("tooltipHtml escapes label text", async () => {
  const { tooltipHtml } = await import("../../site/js/map.js");
  const html = tooltipHtml(fixture, 2);
  assert.ok(!html.includes("<b>"), html);
  assert.ok(html.includes("&lt;b&gt;Bold&lt;/b&gt; &amp; co"), html);
  assert.ok(html.includes("Tract 06037101110"));
});

test("escapeHtml escapes all five special characters", async () => {
  const { escapeHtml } = await import("../../site/js/map.js");
  assert.equal(escapeHtml(`<a href="x">'&'</a>`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;");
});
