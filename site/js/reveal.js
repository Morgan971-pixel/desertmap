// Reveal on scroll and animated counters.
// Reduced motion contract: no animation, final values shown immediately.

const REVEAL_SELECTOR = '.reveal-up, .reveal-left, .reveal-right, .reveal-scale';
const COUNTER_SELECTOR = '.counter[data-count]';
const COUNT_DURATION = 1400;

function format(v, el) {
  const prefix = el.dataset.prefix || '';
  const suffix = el.dataset.suffix || '';
  const decimals = parseInt(el.dataset.decimals || '0', 10);
  if (decimals > 0) {
    return prefix + v.toFixed(decimals) + suffix;
  }
  return prefix + Math.round(v).toLocaleString('en-US') + suffix;
}

function easeOutCubic(p) {
  return 1 - Math.pow(1 - p, 3);
}

function animateCount(el, target, finalText) {
  let start = null;

  function frame(now) {
    if (start === null) {
      start = now;
    }
    const elapsed = now - start;
    const p = Math.min(elapsed / COUNT_DURATION, 1);
    el.textContent = format(target * easeOutCubic(p), el);
    if (p < 1) {
      requestAnimationFrame(frame);
    } else {
      el.textContent = finalText;
    }
  }

  requestAnimationFrame(frame);
}

export function initReveal(root = document) {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const targets = Array.from(root.querySelectorAll(REVEAL_SELECTOR));
  const counters = Array.from(root.querySelectorAll(COUNTER_SELECTOR));

  if (reduce || typeof IntersectionObserver === 'undefined') {
    for (const el of targets) {
      el.classList.add('revealed');
    }
    return;
  }

  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );

  for (const el of targets) {
    revealObserver.observe(el);
  }

  const counterObserver = new IntersectionObserver(
    (entries, observer) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          observer.unobserve(entry.target);
          animateCount(
            entry.target,
            parseFloat(entry.target.dataset.count),
            entry.target.dataset.finalText
          );
        }
      }
    },
    { threshold: 0.5 }
  );

  for (const el of counters) {
    if (el.dataset.revealInit === '1') {
      continue;
    }
    el.dataset.revealInit = '1';
    const target = parseFloat(el.dataset.count);
    if (!Number.isFinite(target)) {
      continue;
    }
    el.dataset.finalText = el.textContent;
    // Lock the final rendered width so the count-up does not shift nearby text.
    // offsetWidth is layout width, unaffected by reveal transforms (scale).
    el.style.minWidth = el.offsetWidth + 'px';
    el.textContent = format(0, el);
    counterObserver.observe(el);
  }
}
