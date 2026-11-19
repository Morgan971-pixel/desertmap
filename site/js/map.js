// MapLibre base map with a deck.gl overlay drawing every census tract as a dot.
import { filterIndices, probToColor, tractId } from './model.js';

const STYLE_URL = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const LOAD_TIMEOUT_MS = 20000;
const FIRST_RENDER_TIMEOUT_MS = 5000;

const TOOLTIP_STYLE = {
  backgroundColor: '#161b22',
  color: '#e6edf3',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '8px 10px',
  fontSize: '12px',
  lineHeight: '1.45',
  maxWidth: '260px',
};

export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const labelWord = (v) => (v === 1 ? 'Food desert' : v === 0 ? 'Not a food desert' : 'Unknown');

export function tooltipLines(tracts, i) {
  const p = tracts.p[i];
  return [
    'Tract ' + tractId(tracts.id[i]),
    Number.isFinite(p) ? 'Probability ' + p.toFixed(3) : 'Probability n/a',
    'Predicted: ' + labelWord(tracts.pred[i]),
    'Actual: ' + labelWord(tracts.actual[i]),
    'Top driver: ' + (tracts.labels[tracts.f1[i]] ?? 'Unknown'),
  ];
}

export function tooltipHtml(tracts, i) {
  const lines = tooltipLines(tracts, i).map(escapeHtml);
  lines[0] = '<strong>' + lines[0] + '</strong>';
  return lines.join('<br>');
}

export function trueIndex(idx, pickedIndex) {
  if (Number.isInteger(pickedIndex) && pickedIndex >= 0 && pickedIndex < idx.length) {
    return idx[pickedIndex];
  }
  return null;
}

// Only a failure of the style document itself is fatal. Tile, sprite and glyph
// errors all arrive after the first 'styledata', so they are logged and the map
// keeps loading (the timeout still catches a load that never finishes).
function waitForLoad(map) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let styleArrived = false;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fn(value);
    };
    const timer = setTimeout(() => finish(reject, new Error('map load timed out')), LOAD_TIMEOUT_MS);
    map.once('styledata', () => { styleArrived = true; });
    map.once('load', () => finish(resolve));
    map.on('error', (event) => {
      const err = event && event.error ? event.error : new Error('map error');
      if (!settled && !styleArrived) {
        finish(reject, err);
        return;
      }
      console.warn('map: non-fatal error', err);
    });
  });
}

export async function initMap(container, tracts, onSelect) {
  const maplibregl = window.maplibregl;
  const deck = window.deck;
  if (!maplibregl || !deck) throw new Error('initMap: maplibregl and deck must be loaded first');

  const n = tracts.n;
  let map = null;
  let overlay = null;

  try {
    map = new maplibregl.Map({
      container,
      style: STYLE_URL,
      center: [-96.5, 38.5],
      zoom: (container.clientWidth || window.innerWidth) < 600 ? 2.6 : 3.4,
      cooperativeGestures: true,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    const loaded = waitForLoad(map);
    loaded.catch(() => {}); // observed below; avoids an unhandled rejection if setup throws first

    // Positions and colors are computed once; accessors only index into them.
    const positions = new Float32Array(n * 2);
    const colors = new Uint8Array(n * 4);
    for (let i = 0; i < n; i++) {
      positions[2 * i] = tracts.lon[i];
      positions[2 * i + 1] = tracts.lat[i];
      const p = tracts.p[i];
      colors.set(probToColor(Number.isFinite(p) ? p : 0), 4 * i);
    }

    // Touch screens have no hover to clear a highlight, so it would linger after a tap.
    const canHover = !(typeof window.matchMedia === 'function' && window.matchMedia('(hover: none)').matches);

    // One data object per filter result. deck compares data by reference, so a
    // selection change reuses it and only the small ring layer updates.
    const makeData = (idx) => ({ length: idx.length, idx });
    let data = makeData(filterIndices(tracts, 'all', 0));
    let version = 0;
    let selected = null;

    // Picks resolve against the data of the layer that was drawn, which can lag
    // a filter change by one frame.
    const pickedIndex = (info) =>
      info && info.layer && info.layer.id === 'tracts'
        ? trueIndex(info.layer.props?.data?.idx ?? data.idx, info.index)
        : null;

    const buildLayers = () => {
      return [
        new deck.ScatterplotLayer({
          id: 'tracts',
          data,
          getPosition: (_, { index, data: d, target }) => {
            const t = d.idx[index];
            target[0] = positions[2 * t];
            target[1] = positions[2 * t + 1];
            target[2] = 0;
            return target;
          },
          getFillColor: (_, { index, data: d, target }) => {
            const t = d.idx[index] * 4;
            target[0] = colors[t];
            target[1] = colors[t + 1];
            target[2] = colors[t + 2];
            target[3] = colors[t + 3];
            return target;
          },
          radiusUnits: 'meters',
          getRadius: 4000,
          radiusMinPixels: 1,
          radiusMaxPixels: 9,
          pickable: true,
          autoHighlight: canHover,
          highlightColor: [255, 190, 120, 220],
          updateTriggers: { getPosition: version, getFillColor: version },
        }),
        new deck.ScatterplotLayer({
          id: 'selected',
          data: selected == null ? [] : [selected],
          getPosition: (t) => [positions[2 * t], positions[2 * t + 1]],
          radiusUnits: 'pixels',
          getRadius: 11, // encloses the largest tract dot (radiusMaxPixels 9)
          radiusMinPixels: 7,
          stroked: true,
          filled: false,
          getLineColor: [255, 140, 0, 255],
          lineWidthUnits: 'pixels',
          getLineWidth: 2,
          lineWidthMinPixels: 2,
          pickable: false,
        }),
      ];
    };

    let markRendered;
    const firstRender = new Promise((resolve) => { markRendered = resolve; });

    overlay = new deck.MapboxOverlay({
      interleaved: false,
      layers: buildLayers(),
      onAfterRender: () => markRendered(),
      getTooltip: (info) => {
        const i = pickedIndex(info);
        if (i == null) return null;
        return { html: tooltipHtml(tracts, i), style: TOOLTIP_STYLE };
      },
      // Fires for taps too; an empty-map click arrives with no layer and clears the selection.
      onClick: (info) => {
        const i = pickedIndex(info);
        selected = i;
        overlay.setProps({ layers: buildLayers() });
        onSelect(i);
      },
    });

    await loaded;
    map.addControl(overlay);
    let fallbackTimer = 0;
    await Promise.race([
      firstRender,
      new Promise((resolve) => { fallbackTimer = setTimeout(resolve, FIRST_RENDER_TIMEOUT_MS); }),
    ]);
    clearTimeout(fallbackTimer);

    return {
      setFilter(view, minProb) {
        data = makeData(filterIndices(tracts, view, minProb));
        version++;
        selected = null;
        overlay.setProps({ layers: buildLayers() });
        return data.length;
      },
    };
  } catch (err) {
    try { if (overlay) overlay.finalize(); } catch { /* best effort */ }
    try { if (map) map.remove(); } catch { /* best effort */ }
    throw err;
  }
}
