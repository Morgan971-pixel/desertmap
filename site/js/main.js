// Page controller: binds summary numbers, starts reveal, loads charts and map lazily.
// CDN libraries load on demand so text and numbers paint before any of them.
import { VIEWS, tractId, fmtPct } from './model.js';
import { initReveal } from './reveal.js';

const CDN = {
  plotly: 'https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js',
  maplibreCss: 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css',
  maplibre: 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js',
  deck: 'https://unpkg.com/deck.gl@9.0.38/dist.min.js',
};

const TRACT_ARRAYS = [
  'id', 'lat', 'lon', 'p', 'pred', 'actual', 'black', 'hisp', 'white',
  'f1', 's1', 'f2', 's2', 'f3', 's3',
];

const $ = (id) => document.getElementById(id);
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- External assets (deduped by URL, failures not cached) ----------

const assetCache = new Map();

function loadAsset(url, create) {
  if (!assetCache.has(url)) {
    const promise = new Promise((resolve, reject) => {
      const el = create();
      el.addEventListener('load', () => resolve());
      el.addEventListener('error', () => {
        el.remove();
        assetCache.delete(url);
        reject(new Error('Failed to load ' + url));
      });
      document.head.appendChild(el);
    });
    assetCache.set(url, promise);
  }
  return assetCache.get(url);
}

function loadScript(url) {
  return loadAsset(url, () => {
    const s = document.createElement('script');
    s.src = url;
    s.async = true;
    return s;
  });
}

function loadCss(url) {
  return loadAsset(url, () => {
    const l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = url;
    return l;
  });
}

// A failed dynamic import can stay cached by the browser, so retries bust the URL.
const importAttempts = new Map();

function importFresh(path) {
  const n = importAttempts.get(path) || 0;
  importAttempts.set(path, n + 1);
  return import(n === 0 ? path : `${path}?retry=${n}`);
}

function whenNear(el, fn, margin = '400px 0px') {
  if (!el) return;
  if (typeof IntersectionObserver === 'undefined') {
    fn();
    return;
  }
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) {
      io.disconnect();
      fn();
    }
  }, { rootMargin: margin });
  io.observe(el);
}

// ---------- Summary binding ----------

function get(obj, path) {
  if (obj == null || typeof path !== 'string') return undefined;
  let cur = obj;
  for (const part of path.split('.')) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[part];
  }
  return cur;
}

function formatFor(key, value) {
  if (key === 'n_tracts' || key === 'n_mapped') {
    return { text: value.toLocaleString('en-US'), count: value, decimals: 0, suffix: '' };
  }
  if (
    key === 'food_desert_share' ||
    key === 'holc.cd_rate' ||
    key === 'holc.ab_rate' ||
    key === 'fairness.counterfactual_flip_rate'
  ) {
    const scaled = value * 100;
    return { text: scaled.toFixed(1) + '%', count: +scaled.toFixed(1), decimals: 1, suffix: '%' };
  }
  if (key === 'holc.ratio') {
    return { text: value.toFixed(2), count: value, decimals: 2, suffix: '' };
  }
  if (key === 'fairness.f1_delta_pts' || key === 'fairness.fpr_disparity_q4_q1') {
    return { text: value.toFixed(1), count: value, decimals: 1, suffix: '' };
  }
  if (
    key.startsWith('metrics.') ||
    key === 'fairness.f1_full' ||
    key === 'fairness.f1_race_removed'
  ) {
    return { text: value.toFixed(3), count: value, decimals: 3, suffix: '' };
  }
  return null;
}

const warnedBindKeys = new Set();

function bindAll(summary) {
  document.querySelectorAll('[data-bind]').forEach((el) => {
    const key = el.dataset.bind;
    const value = get(summary, key);
    const fmt = Number.isFinite(value) ? formatFor(key, value) : null;
    if (!fmt) {
      el.textContent = 'n/a';
      if (!warnedBindKeys.has(key)) {
        warnedBindKeys.add(key);
        console.warn('bindAll: missing or unformattable value for', key);
      }
      return;
    }
    el.textContent = fmt.text;
    if (el.classList.contains('counter')) {
      el.dataset.count = String(fmt.count);
      el.dataset.decimals = String(fmt.decimals);
      el.dataset.suffix = fmt.suffix;
    }
  });
}

function markAllUnavailable() {
  document.querySelectorAll('[data-bind]').forEach((el) => {
    el.textContent = 'n/a';
  });
}

async function loadSummary() {
  const res = await fetch('data/summary.json');
  if (!res.ok) throw new Error('summary.json HTTP ' + res.status);
  return res.json();
}

// ---------- Slots and charts ----------

function slotMessage(el, text, retryFn) {
  if (!el) return;
  el.replaceChildren();
  const wrap = document.createElement('div');
  wrap.className = 'slot-msg';
  const span = document.createElement('span');
  span.textContent = text;
  wrap.appendChild(span);
  if (typeof retryFn === 'function') {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn';
    btn.textContent = 'Retry';
    btn.addEventListener('click', retryFn);
    wrap.appendChild(btn);
  }
  el.appendChild(wrap);
}

let chartsPromise = null;

function loadCharts() {
  if (!chartsPromise) {
    chartsPromise = (async () => {
      await loadScript(CDN.plotly);
      return importFresh('./charts.js');
    })().catch((e) => {
      console.warn('charts unavailable:', e);
      chartsPromise = null; // allow a later retry
      return null;
    });
  }
  return chartsPromise;
}

// Renders into a fresh inner element; role="img" is added only after success,
// so a failure message in the slot stays readable text.
async function renderChart(slot, render, retryFn) {
  if (!slot) return;
  const charts = await loadCharts();
  if (!charts) {
    slotMessage(slot, 'Chart unavailable.', retryFn);
    return;
  }
  slot.replaceChildren();
  const inner = document.createElement('div');
  inner.className = 'chart-inner';
  slot.appendChild(inner);
  try {
    await render(charts, inner);
    inner.setAttribute('role', 'img');
    if (slot.dataset.chartLabel) inner.setAttribute('aria-label', slot.dataset.chartLabel);
  } catch (e) {
    console.warn('chart render failed:', e);
    // A newer render may have replaced this inner element; never overwrite it.
    if (inner.parentNode !== slot) return;
    slotMessage(slot, 'Chart unavailable.', retryFn);
  }
}

function setupLazyCharts(summary) {
  const shapEl = $('chart-global-shap');
  const holcEl = $('chart-holc');
  if (!summary) {
    slotMessage(shapEl, 'Chart unavailable.');
    slotMessage(holcEl, 'Chart unavailable.');
    return;
  }
  const drawShap = () =>
    renderChart(shapEl, (c, el) => c.renderGlobalShap(el, summary.global_shap), drawShap);
  const drawHolc = () =>
    renderChart(holcEl, (c, el) => c.renderHolc(el, summary.holc), drawHolc);
  whenNear(shapEl, drawShap);
  whenNear(holcEl, drawHolc);
}

// ---------- Filters ----------

let summaryData = null;
let tracts = null;
let controller = null;
let loading = false;
let selectToken = 0;
const state = { view: 'all', minProb: 0.11 };

function renderReadout() {
  const out = $('min-prob-readout');
  const t = 'p ≥ ' + state.minProb.toFixed(2);
  out.textContent = t;
  out.value = t;
}

function applyFilter() {
  if (!controller || !tracts) return;
  const n = controller.setFilter(state.view, state.minProb);
  $('tract-count').textContent =
    `Showing ${Number(n).toLocaleString('en-US')} of ${tracts.n.toLocaleString('en-US')} tracts`;
  onSelect(null); // never show a tract the filter just hid
}

function debounce(fn, ms) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function wireFilters() {
  const select = $('view-select');
  const range = $('min-prob');
  if (Object.hasOwn(VIEWS, select.value)) state.view = select.value;
  const initial = parseFloat(range.value);
  if (Number.isFinite(initial)) state.minProb = initial;
  renderReadout();
  select.addEventListener('change', () => {
    if (!Object.hasOwn(VIEWS, select.value)) return;
    state.view = select.value;
    applyFilter();
  });
  const applyDebounced = debounce(applyFilter, 100);
  range.addEventListener('input', () => {
    const v = parseFloat(range.value);
    if (!Number.isFinite(v)) return;
    state.minProb = v;
    renderReadout();
    applyDebounced();
  });
}

// ---------- Tract detail ----------

function makeTag(cls, text) {
  const span = document.createElement('span');
  span.className = 'tag ' + cls;
  span.textContent = text;
  return span;
}

function labelTag(v) {
  return v === 1
    ? makeTag('tag-fd', 'Food desert')
    : makeTag('tag-ok', 'Not a food desert');
}

function showTract(visible) {
  $('tract-hint').hidden = visible;
  $('tract-heading').hidden = !visible;
  $('tract-tags').hidden = !visible;
  $('tract-body').hidden = !visible;
}

async function onSelect(i) {
  const token = ++selectToken;
  if (i == null || !tracts || i < 0 || i >= tracts.n) {
    showTract(false);
    return;
  }
  $('tract-heading').textContent = 'Census tract ' + tractId(tracts.id[i]);
  const actual = tracts.actual[i];
  const pred = tracts.pred[i];
  $('tract-tags').replaceChildren(
    document.createTextNode('Actual '),
    labelTag(actual),
    document.createTextNode(' Predicted '),
    labelTag(pred),
    document.createTextNode(' '),
    actual === pred
      ? makeTag('tag-right', 'Correct')
      : makeTag('tag-wrong', 'Incorrect')
  );
  const p = tracts.p[i];
  $('tract-prob').textContent = Number.isFinite(p) ? p.toFixed(3) : 'n/a';
  $('tract-black').textContent = fmtPct(tracts.black[i]);
  $('tract-hisp').textContent = fmtPct(tracts.hisp[i]);
  $('tract-white').textContent = fmtPct(tracts.white[i]);
  showTract(true);
  $('tract-detail').scrollIntoView({
    block: 'nearest',
    behavior: reducedMotion() ? 'auto' : 'smooth',
  });

  const entries = [1, 2, 3]
    .map((k) => ({
      label: tracts.labels[tracts['f' + k][i]] ?? 'Unknown',
      value: tracts['s' + k][i],
    }))
    .filter((e) => Number.isFinite(e.value));
  const slot = $('chart-tract-shap');
  slot.replaceChildren();
  await loadCharts();
  if (token !== selectToken) return; // a newer selection superseded this one
  await renderChart(slot, (c, el) => c.renderTractShap(el, entries));
}

// ---------- Map ----------

function validateTracts(t) {
  if (!t || typeof t !== 'object') throw new Error('tracts.json is not an object');
  if (!Number.isInteger(t.n) || t.n <= 0) throw new Error('tracts.json: bad n');
  if (!Array.isArray(t.labels)) throw new Error('tracts.json: missing labels');
  for (const key of TRACT_ARRAYS) {
    if (!Array.isArray(t[key]) || t[key].length !== t.n) {
      throw new Error(`tracts.json: ${key} missing or length != n`);
    }
  }
  return t;
}

async function fetchTracts() {
  const res = await fetch('data/tracts.json');
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return validateTracts(await res.json());
}

async function loadMapLibs() {
  await Promise.all([
    loadCss(CDN.maplibreCss),
    loadScript(CDN.maplibre).then(() => loadScript(CDN.deck)),
  ]);
}

function showMapLoading(status) {
  const n = summaryData && Number.isFinite(summaryData.n_mapped)
    ? summaryData.n_mapped.toLocaleString('en-US') + ' '
    : '';
  const span = document.createElement('span');
  span.textContent = `Loading ${n}tracts`;
  status.replaceChildren(span);
  status.hidden = false;
  status.classList.add('skeleton');
}

async function loadMap() {
  if (loading || controller) return;
  loading = true;
  const status = $('map-status');
  const mapEl = $('map');
  const fail = (text, err) => {
    console.warn(text, err);
    status.classList.remove('skeleton');
    status.hidden = false;
    slotMessage(status, text, () => loadMap());
  };
  showMapLoading(status);
  try {
    const [libRes, modRes, dataRes] = await Promise.allSettled([
      loadMapLibs(),
      importFresh('./map.js'),
      tracts ? Promise.resolve(tracts) : fetchTracts(),
    ]);
    if (modRes.status === 'rejected') return fail('Map unavailable.', modRes.reason);
    if (libRes.status === 'rejected') return fail('Map unavailable.', libRes.reason);
    if (dataRes.status === 'rejected') return fail('Could not load tract data.', dataRes.reason);
    tracts = dataRes.value;
    mapEl.replaceChildren(); // retry-safe: clear anything a failed attempt left behind
    try {
      controller = await modRes.value.initMap(mapEl, tracts, onSelect);
    } catch (e) {
      controller = null;
      mapEl.replaceChildren();
      return fail('Map unavailable.', e);
    }
    status.hidden = true;
    status.classList.remove('skeleton');
    applyFilter();
  } finally {
    loading = false;
  }
}

// ---------- Boot ----------

async function main() {
  try {
    wireFilters();
    whenNear($('map'), loadMap); // before the summary fetch, so a hung summary cannot block it
    try {
      summaryData = await loadSummary();
      bindAll(summaryData);
    } catch (e) {
      console.warn('summary.json unavailable:', e);
      summaryData = null;
      markAllUnavailable();
    }
    setupLazyCharts(summaryData);
  } finally {
    initReveal(document);
    clearTimeout(window.__dmRevealFailsafe);
  }
}

main().catch((e) => console.error('DesertMap boot error:', e));
