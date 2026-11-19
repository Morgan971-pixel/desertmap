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
  assert.equal(trueIndex(idx, null), null);
  assert.equal(trueIndex(idx, NaN), null);
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

// ---------- initMap with fake maplibre/deck globals ----------

function fakeGlobals() {
  const log = { removed: 0, finalized: 0, controls: [], overlayProps: null };
  class FakeMap {
    constructor(opts) {
      this.opts = opts;
      this.handlers = {};
      log.map = this;
    }
    on(type, fn) { (this.handlers[type] ||= []).push({ fn, once: false }); return this; }
    once(type, fn) { (this.handlers[type] ||= []).push({ fn, once: true }); return this; }
    emit(type, event = {}) {
      const list = this.handlers[type] || [];
      this.handlers[type] = list.filter((h) => !h.once);
      list.forEach((h) => h.fn(event));
    }
    addControl(control) {
      log.controls.push(control);
      if (control instanceof FakeOverlay) control.props.onAfterRender?.();
      return this;
    }
    remove() { log.removed++; }
  }
  class FakeOverlay {
    constructor(props) { this.props = props; log.overlayProps = props; }
    setProps(p) { Object.assign(this.props, p); }
    finalize() { log.finalized++; }
  }
  const window = {
    innerWidth: 1280,
    matchMedia: () => ({ matches: false }),
    maplibregl: { Map: FakeMap, NavigationControl: class {} },
    deck: { MapboxOverlay: FakeOverlay, ScatterplotLayer: class { constructor(props) { this.props = props; this.id = props.id; } } },
  };
  return { window, log };
}

const mapTracts = {
  n: 3,
  id: [1, 2, 3], lat: [30, 31, 32], lon: [-90, -91, -92],
  p: [0.2, 0.7, 0.9], pred: [0, 1, 1], actual: [0, 1, 0],
  f1: [0, 0, 0], labels: ["Poverty rate"],
};

async function withFakeWindow(fn) {
  const saved = Object.getOwnPropertyDescriptor(globalThis, "window");
  const warn = console.warn;
  const fake = fakeGlobals();
  globalThis.window = fake.window;
  console.warn = () => {};
  try {
    await fn(fake);
  } finally {
    console.warn = warn;
    if (saved) Object.defineProperty(globalThis, "window", saved);
    else delete globalThis.window;
  }
}

test("initMap rejects on a style error before load and cleans up", async () => {
  const { initMap } = await import("../../site/js/map.js");
  await withFakeWindow(async ({ log }) => {
    const pending = initMap({ clientWidth: 800 }, mapTracts, () => {});
    log.map.emit("error", { error: new Error("style 404") });
    await assert.rejects(pending, /style 404/);
    assert.equal(log.removed, 1);
    assert.equal(log.finalized, 1);
    assert.ok(!log.controls.some((c) => c.props && c.props.layers), "overlay never added");
  });
  assert.equal(typeof globalThis.window, "undefined");
});

test("initMap survives a tile error after the style arrives", async () => {
  const { initMap } = await import("../../site/js/map.js");
  await withFakeWindow(async ({ log }) => {
    const selections = [];
    const pending = initMap({ clientWidth: 0 }, mapTracts, (i) => selections.push(i));
    assert.equal(log.map.opts.zoom, 3.4, "falls back to innerWidth when the container has no width");
    log.map.emit("styledata");
    log.map.emit("error", { error: new Error("tile 404"), sourceId: "carto" });
    log.map.emit("load");
    const controller = await pending;
    assert.equal(log.removed, 0);
    assert.equal(controller.setFilter("predicted", 0), 2);
    const tractsLayer = log.overlayProps.layers.find((l) => l.id === "tracts");
    assert.deepEqual(tractsLayer.props.data.idx, [1, 2]);
    assert.equal(tractsLayer.props.autoHighlight, true);
    log.overlayProps.onClick({ layer: tractsLayer, index: 1 });
    log.overlayProps.onClick({ layer: null, index: -1 });
    assert.deepEqual(selections, [2, null]);
  });
});
