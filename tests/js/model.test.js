import { test } from "node:test";
import assert from "node:assert/strict";
import { filterIndices, probToColor, tractId, fmtPct } from "../../site/js/model.js";

const t = { n: 4, p: [0.1, 0.6, 0.9, 0.95], pred: [0, 1, 1, 1], actual: [0, 1, 0, 1] };

test("all view applies min probability", () => assert.deepEqual(filterIndices(t, "all", 0.5), [1, 2, 3]));
test("predicted view keeps pred=1", () => assert.deepEqual(filterIndices(t, "predicted", 0), [1, 2, 3]));
test("true positives", () => assert.deepEqual(filterIndices(t, "tp", 0), [1, 3]));
test("false positives", () => assert.deepEqual(filterIndices(t, "fp", 0), [2]));
test("unknown view throws", () => assert.throws(() => filterIndices(t, "nope", 0)));
test("color ramp endpoints match Streamlit app", () => {
  assert.deepEqual(probToColor(0), [49, 160, 208, 200]);
  assert.deepEqual(probToColor(1), [214, 39, 40, 200]);
});
test("tract id zero-pads to 11 digits", () => assert.equal(tractId(1001020100), "01001020100"));
test("fmtPct handles null", () => {
  assert.equal(fmtPct(12.345), "12.3%");
  assert.equal(fmtPct(null), "n/a");
});
