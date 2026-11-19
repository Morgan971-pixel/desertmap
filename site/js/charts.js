// charts.js - Plotly chart specs and renderers for the static site.
//
// Design: each chart has a pure spec builder (globalShapSpec, holcSpec,
// tractShapSpec) that returns a plain { data, layout, config } object and
// touches no DOM, no Plotly, and no browser globals, so this module can be
// imported in Node for unit tests. The three thin renderers at the bottom
// are the only functions that touch the browser; they look up Plotly lazily
// via globalThis at call time, never at module-evaluation time.

const FONT_STACK = 'Inter, system-ui, sans-serif';

function baseLayout(narrow) {
  return {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: FONT_STACK, color: '#e6edf3', size: narrow ? 11 : 12 },
    showlegend: false,
    hoverlabel: {
      bgcolor: '#0d1117',
      bordercolor: '#30363d',
      font: { color: '#e6edf3', family: FONT_STACK },
    },
  };
}

function baseConfig() {
  return { displayModeBar: false, responsive: true, staticPlot: false };
}

// Wrap a long label onto at most 2 lines by inserting a <br> at the last
// space at or before maxChars (hard break at maxChars when there is no space).
function wrapLabel(label, maxChars) {
  if (label.length <= maxChars) return label;
  let idx = label.lastIndexOf(' ', maxChars);
  if (idx <= 0) idx = maxChars;
  return label.slice(0, idx).trimEnd() + '<br>' + label.slice(idx).trimStart();
}

function isFiniteNumber(v) {
  return typeof v === 'number' && Number.isFinite(v);
}

// Values that round to 0.000 at 3 dp carry no direction, so they get no sign.
const SHAP_EPS = 0.0005;

export function fmtShap(v) {
  if (Math.abs(v) < SHAP_EPS) return '0.000';
  return (v > 0 ? '+' : '-') + Math.abs(v).toFixed(3);
}

function shapColor(v) {
  if (Math.abs(v) < SHAP_EPS) return '#8b949e';
  return v > 0 ? '#ef4444' : '#3b82f6';
}

export function globalShapSpec(rows, { narrow = false } = {}) {
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new Error('globalShapSpec: rows must be a non-empty array');
  }
  rows.forEach((row, i) => {
    if (!row || typeof row.label !== 'string' || row.label.length === 0) {
      throw new Error('globalShapSpec: row ' + i + ' must have a non-empty string label');
    }
    if (!isFiniteNumber(row.total) || row.total < 0) {
      throw new Error('globalShapSpec: row ' + i + ' must have a finite, non-negative number total');
    }
  });
  const sorted = rows.slice().sort((a, b) => b.total - a.total);
  const totals = sorted.map((r) => r.total);
  const maxTotal = Math.max(...totals);
  if (maxTotal <= 0) {
    throw new Error('globalShapSpec: at least one total must be greater than 0');
  }
  const labels = sorted.map((r) => (narrow ? wrapLabel(r.label, 16) : r.label));
  const colors = totals.map((t) => {
    // Floor of 0.55 keeps the faintest bar at 3:1 non-text contrast on the card.
    const a = Math.round((0.55 + (0.45 * t) / maxTotal) * 1000) / 1000;
    return 'rgba(249,115,22,' + a + ')';
  });
  const data = [{
    type: 'bar',
    orientation: 'h',
    x: totals,
    y: labels,
    marker: { color: colors },
    text: totals.map((t) => (t / 1000).toFixed(1) + 'k'),
    textposition: 'outside',
    textfont: { color: '#8b949e', size: narrow ? 10 : 11 },
    cliponaxis: false,
    hovertemplate: '%{y}: %{x:,.0f}<extra></extra>',
  }];
  const layout = {
    ...baseLayout(narrow),
    height: narrow ? 380 : 340,
    margin: narrow ? { l: 8, r: 44, t: 8, b: 36 } : { l: 8, r: 60, t: 10, b: 40 },
    xaxis: {
      title: { text: 'Cumulative |SHAP| across all tracts', font: { size: narrow ? 11 : 12, color: '#8b949e' } },
      showticklabels: false,
      gridcolor: '#21262d',
      zeroline: false,
      range: [0, maxTotal * (narrow ? 1.25 : 1.18)],
      fixedrange: true,
    },
    yaxis: {
      autorange: 'reversed',
      automargin: true,
      tickfont: { size: narrow ? 10 : 12, color: '#e6edf3' },
      fixedrange: true,
    },
    bargap: 0.3,
  };
  return { data, layout, config: baseConfig() };
}

export function holcSpec(holc, { narrow = false } = {}) {
  if (!holc || typeof holc !== 'object') {
    throw new Error('holcSpec: holc must be an object');
  }
  const grades = ['A', 'B', 'C', 'D'];
  if (!holc.rates || typeof holc.rates !== 'object') {
    throw new Error('holcSpec: rates must be an object with A, B, C, D');
  }
  const rates = grades.map((g) => {
    const r = holc.rates[g];
    if (!isFiniteNumber(r) || r < 0 || r > 1) {
      throw new Error('holcSpec: rates.' + g + ' must be a finite number in [0, 1]');
    }
    return r;
  });
  for (const key of ['cd_rate', 'ab_rate']) {
    if (!isFiniteNumber(holc[key]) || holc[key] < 0 || holc[key] > 1) {
      throw new Error('holcSpec: ' + key + ' must be a finite number in [0, 1]');
    }
  }
  // All-zero rates would give a [0, 0] axis; fall back to a 0-130% frame.
  const maxRate = Math.max(...rates) || 1;
  const data = [{
    type: 'bar',
    x: grades,
    y: rates.map((r) => r * 100),
    marker: { color: ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'] },
    text: rates.map((r) => (r * 100).toFixed(1) + '%'),
    textposition: 'outside',
    textfont: { color: '#e6edf3', size: narrow ? 12 : 13 },
    cliponaxis: false,
    width: 0.55,
    hovertemplate: 'Grade %{x}: %{y:.1f}%<extra></extra>',
  }];
  const layout = {
    ...baseLayout(narrow),
    height: 360,
    margin: narrow ? { l: 44, r: 8, t: 16, b: 52 } : { l: 60, r: 20, t: 24, b: 56 },
    xaxis: {
      title: { text: 'HOLC grade (A = best, D = hazardous)', font: { size: narrow ? 11 : 12, color: '#8b949e' } },
      tickfont: { size: 14, color: '#e6edf3' },
      gridcolor: '#21262d',
      fixedrange: true,
    },
    yaxis: {
      title: { text: '% predicted food desert', font: { size: narrow ? 11 : 12, color: '#8b949e' } },
      ticksuffix: '%',
      range: [0, maxRate * 130],
      gridcolor: '#21262d',
      tickfont: { color: '#8b949e', size: narrow ? 10 : 11 },
      fixedrange: true,
    },
    annotations: [{
      // Pooled C+D and A+B rates from the export, never an average of grade rates.
      text: '<b>C+D tracts: ' + (holc.cd_rate * 100).toFixed(1) + '%</b><br>vs A+B tracts: ' + (holc.ab_rate * 100).toFixed(1) + '%',
      x: 1.5,
      y: maxRate * 120,
      xref: 'x',
      yref: 'y',
      showarrow: false,
      font: { color: '#f87171', size: narrow ? 10 : 11 },
      align: 'center',
      bgcolor: 'rgba(239,68,68,0.1)',
      bordercolor: '#ef4444',
      borderwidth: 1,
      borderpad: narrow ? 4 : 6,
    }],
  };
  return { data, layout, config: baseConfig() };
}

export function tractShapSpec(entries, { narrow = false } = {}) {
  if (!Array.isArray(entries) || entries.length === 0) {
    throw new Error('tractShapSpec: entries must be a non-empty array');
  }
  entries.forEach((entry, i) => {
    if (!entry || typeof entry.label !== 'string' || entry.label.length === 0) {
      throw new Error('tractShapSpec: entry ' + i + ' must have a non-empty string label');
    }
    if (!isFiniteNumber(entry.value)) {
      throw new Error('tractShapSpec: entry ' + i + ' must have a finite number value');
    }
  });
  const values = entries.map((e) => e.value);
  const labels = entries.map((e) => (narrow ? wrapLabel(e.label, 18) : e.label));
  const m = Math.max(...values.map((v) => Math.abs(v))) || 1;
  const allPos = values.every((v) => v >= 0);
  const allNeg = values.every((v) => v <= 0);
  const range = allPos ? [-m * 0.05, m * 1.45]
    : allNeg ? [-m * 1.45, m * 0.05]
    : [-m * 1.45, m * 1.45];
  // Numeric y positions with tick labels, so two entries with the same label
  // stay two bars instead of merging into one category.
  const positions = entries.map((_, i) => i);
  const data = [{
    type: 'bar',
    orientation: 'h',
    x: values,
    y: positions,
    customdata: entries.map((e) => e.label),
    marker: { color: values.map(shapColor) },
    text: values.map(fmtShap),
    textposition: 'outside',
    textfont: { color: '#e6edf3', size: narrow ? 10 : 11 },
    cliponaxis: false,
    hovertemplate: '%{customdata}: %{text}<extra></extra>',
  }];
  const layout = {
    ...baseLayout(narrow),
    height: 185,
    margin: narrow ? { l: 4, r: 8, t: 6, b: 34 } : { l: 4, r: 16, t: 8, b: 36 },
    xaxis: {
      title: { text: 'SHAP value', font: { size: 11, color: '#8b949e' } },
      gridcolor: '#21262d',
      zeroline: false,
      tickfont: { color: '#8b949e', size: 10 },
      fixedrange: true,
      range,
    },
    yaxis: {
      autorange: 'reversed',
      automargin: true,
      tickmode: 'array',
      tickvals: positions,
      ticktext: labels,
      tickfont: { size: narrow ? 10 : 11, color: '#e6edf3' },
      fixedrange: true,
      zeroline: false,
      showgrid: false,
    },
    bargap: 0.35,
    shapes: [{ type: 'line', xref: 'x', yref: 'paper', x0: 0, x1: 0, y0: 0, y1: 1, line: { color: '#484f58', width: 1 } }],
  };
  return { data, layout, config: baseConfig() };
}

function render(el, build, input) {
  if (!el) throw new Error('chart element missing');
  const Plotly = globalThis.window && globalThis.window.Plotly;
  if (!Plotly || typeof Plotly.newPlot !== 'function') throw new Error('Plotly is not loaded');
  const { data, layout, config } = build(input, { narrow: el.clientWidth > 0 && el.clientWidth < 600 });
  return Plotly.newPlot(el, data, layout, config);
}

export function renderGlobalShap(el, rows) { return render(el, globalShapSpec, rows); }
export function renderHolc(el, holc) { return render(el, holcSpec, holc); }
export function renderTractShap(el, entries) { return render(el, tractShapSpec, entries); }
