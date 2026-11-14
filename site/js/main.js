// Page controller: binds summary numbers, starts reveal, loads charts and map lazily.
import { VIEWS, tractId, fmtPct } from './model.js';
import { initReveal } from './reveal.js';

const $ = (id) => document.getElementById(id);

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
    chartsPromise = import('./charts.js').catch((e) => {
      console.warn('charts.js unavailable:', e.message);
      return null;
    });
  }
  return chartsPromise;
}

async function renderSummaryCharts(summary) {
  const shapEl = $('chart-global-shap');
  const holcEl = $('chart-holc');
  if (!summary) {
    slotMessage(shapEl, 'Chart unavailable.');
    slotMessage(holcEl, 'Chart unavailable.');
    return;
  }
  const charts = await loadCharts();
  if (!charts) {
    slotMessage(shapEl, 'Chart unavailable.');
    slotMessage(holcEl, 'Chart unavailable.');
    return;
  }
  try {
    await charts.renderGlobalShap(shapEl, summary.global_shap);
  } catch (e) {
    console.warn(e);
    slotMessage(shapEl, 'Chart unavailable.');
  }
  try {
    await charts.renderHolc(holcEl, summary.holc);
  } catch (e) {
    console.warn(e);
    slotMessage(holcEl, 'Chart unavailable.');
  }
}

let tracts = null;
let controller = null;
let loading = false;
let selectToken = 0;
const state = { view: 'all', minProb: 0.11 };
let statusTemplate = '';

function renderReadout() {
  const out = $('min-prob-readout');
  const t = 'p >= ' + state.minProb.toFixed(2);
  out.textContent = t;
  out.value = t;
}

function applyFilter() {
  if (!controller || !tracts) return;
  const n = controller.setFilter(state.view, state.minProb);
  $('tract-count').textContent =
    `Showing ${Number(n).toLocaleString('en-US')} of ${tracts.n.toLocaleString('en-US')} tracts`;
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

async function onSelect(i) {
  const token = ++selectToken;
  const hint = $('tract-hint');
  const body = $('tract-body');
  if (i == null || !tracts || i < 0 || i >= tracts.n) {
    body.hidden = true;
    hint.hidden = false;
    return;
  }
  hint.hidden = true;
  body.hidden = false;
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
  const entries = [1, 2, 3]
    .map((k) => ({
      label: tracts.labels[tracts['f' + k][i]] ?? 'Unknown',
      value: tracts['s' + k][i],
    }))
    .filter((e) => Number.isFinite(e.value));
  const el = $('chart-tract-shap');
  const charts = await loadCharts();
  if (token !== selectToken) return; // a newer selection superseded this one
  if (!charts) {
    slotMessage(el, 'Chart unavailable.');
    return;
  }
  try {
    await charts.renderTractShap(el, entries);
  } catch (e) {
    console.warn(e);
    slotMessage(el, 'Chart unavailable.');
  }
}

async function fetchTracts() {
  const res = await fetch('data/tracts.json');
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

async function loadMap() {
  if (loading || controller) return;
  loading = true;
  const status = $('map-status');
  status.hidden = false;
  status.classList.add('skeleton');
  status.innerHTML = statusTemplate; // static markup captured from index.html
  try {
    const [modRes, dataRes] = await Promise.allSettled([
      import('./map.js'),
      fetchTracts(),
    ]);
    if (modRes.status === 'rejected') {
      console.warn('map.js unavailable:', modRes.reason?.message);
      status.classList.remove('skeleton');
      slotMessage(status, 'Map unavailable.');
      return;
    }
    if (dataRes.status === 'rejected') {
      console.warn('tracts.json failed:', dataRes.reason?.message);
      status.classList.remove('skeleton');
      slotMessage(status, 'Could not load tract data.', () => loadMap());
      return;
    }
    tracts = dataRes.value;
    try {
      controller = await modRes.value.initMap($('map'), tracts, onSelect);
    } catch (e) {
      console.warn('initMap failed:', e);
      controller = null;
      status.classList.remove('skeleton');
      slotMessage(status, 'Map unavailable.');
      return;
    }
    status.hidden = true;
    status.classList.remove('skeleton');
    applyFilter();
  } finally {
    loading = false;
  }
}

function setupLazyMap() {
  const mapEl = $('map');
  if (!mapEl) return;
  statusTemplate = $('map-status').innerHTML;
  if (typeof IntersectionObserver === 'undefined') {
    loadMap();
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        loadMap();
      }
    },
    { rootMargin: '400px 0px' }
  );
  io.observe(mapEl);
}

async function main() {
  wireFilters();
  let summary = null;
  try {
    summary = await loadSummary();
    bindAll(summary);
  } catch (e) {
    console.warn('summary.json unavailable:', e.message);
    markAllUnavailable();
  } finally {
    initReveal(document);
  }
  setupLazyMap();
  await renderSummaryCharts(summary);
}

main().catch((e) => console.error('DesertMap boot error:', e));
