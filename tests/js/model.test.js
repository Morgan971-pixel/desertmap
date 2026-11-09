import { test } from "node:test";
import assert from "node:assert/strict";
import { filterIndices, probToColor, tractId, fmtPct } from "../../site/js/model.js";

const t = { n: 4, p: [0.1, 0.6, 0.9, 0.95], pred: [0, 1, 1, 1], actual: [0, 1, 0, 1] };

test("all view applies min probability", () => assert.deepEqual(filterIndices(t, "all", 0.5), [1, 2, 3]));
test("predicted view keeps pred=1", () => assert.deepEqual(filterIndices(t, "predicted", 0), [1, 2, 3]));
test("true positives", () => assert.deepEqual(filterIndices(t, "tp", 0), [1, 3]));
test("false positives", () => assert.deepEqual(filterIndices(t, "fp", 0), [2]));
test("unknown view throws", () => assert.throws(() => filterIndices(t, "nope", 0)));
test("color ramp endpoints", () => {
  assert.deepEqual(probToColor(0), [49, 160, 208, 200]);
  assert.deepEqual(probToColor(1), [214, 39, 40, 200]);
});
test("tract id zero-pads to 11 digits", () => assert.equal(tractId(1001020100), "01001020100"));
test("fmtPct handles null", () => {
  assert.equal(fmtPct(12.345), "12.3%");
  assert.equal(fmtPct(null), "n/a");
});

test("inherited keys are not valid views", () => {
  assert.throws(() => filterIndices(t, "toString", 0));
  assert.throws(() => filterIndices(t, "constructor", 0));
});
test("NaN/null p values are excluded", () => {
  const bad = { n: 3, p: [NaN, null, 0.5], pred: [1, 1, 1], actual: [1, 1, 1] };
  assert.deepEqual(filterIndices(bad, "all", 0), [2]);
});
test("p equal to minProb is included", () => assert.deepEqual(filterIndices(t, "all", 0.6), [1, 2, 3]));
test("boundary at exactly 0.5", () => {
  const b = { n: 2, p: [0.5, 0.49], pred: [1, 1], actual: [1, 1] };
  assert.deepEqual(filterIndices(b, "all", 0.5), [0]);
});
test("combined view and threshold", () => {
  assert.deepEqual(filterIndices(t, "tp", 0.9), [3]);
  assert.deepEqual(filterIndices(t, "fp", 0.95), []);
});
test("fp excludes null actual and pred=0", () => {
  const f = { n: 3, p: [0.9, 0.9, 0.9], pred: [1, 1, 0], actual: [null, 0, 0] };
  assert.deepEqual(filterIndices(f, "fp", 0), [1]);
});
test("respects t.n when arrays are longer; n=0 is empty", () => {
  const long = { n: 2, p: [0.9, 0.9, 0.9], pred: [1, 1, 1], actual: [1, 1, 1] };
  assert.deepEqual(filterIndices(long, "all", 0), [0, 1]);
  assert.deepEqual(filterIndices({ n: 0, p: [], pred: [], actual: [] }, "all", 0), []);
});
test("fmtPct non-finite and zero", () => {
  assert.equal(fmtPct(0), "0.0%");
  assert.equal(fmtPct(NaN), "n/a");
  assert.equal(fmtPct(undefined), "n/a");
  assert.equal(fmtPct(Infinity), "n/a");
});
test("color ramp interior", () => assert.deepEqual(probToColor(0.5), [132, 100, 124, 200]));
