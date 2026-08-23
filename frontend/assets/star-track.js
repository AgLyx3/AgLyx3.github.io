/* Star track — the spine the portfolio hangs off.
 *
 * Draws one meandering path down the rail, strings faint stars along it, and
 * puts a glowing node where each card attaches, joined by a short spur.
 *
 * Everything is drawn from MEASURED geometry rather than guessed offsets, so
 * the track stays correct through filtering, resize, font swap-in, and cards
 * of different heights. Redraw is debounced and driven by a ResizeObserver on
 * the rail plus an explicit call after filtering.
 */
(function () {
  'use strict';

  var rail = document.getElementById('rail');
  var svg = document.getElementById('railSvg');
  var stationsEl = document.getElementById('stations');
  if (!rail || !svg || !stationsEl) return;

  var NS = 'http://www.w3.org/2000/svg';
  var narrow = window.matchMedia('(max-width: 860px)');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var stations = Array.prototype.slice.call(stationsEl.querySelectorAll('.station'));

  /* The node sits level with the card's mark: 26px of card padding plus half
     of the 44px mark. Kept as one constant so the spur never drifts off it. */
  var ANCHOR = 48;

  /* baseX on narrow screens must match the first grid column in the stylesheet
     (--track-gutter / 2). Desktop centres the track in the rail. */
  function geometry() {
    return narrow.matches
      ? { baseX: 22, amp: 8,  wave: 300, spurMin: 9,  node: 4.5, px: 3 }
      : { baseX: rail.clientWidth / 2, amp: 24, wave: 430, spurMin: 14, node: 4, px: 4 };
  }

  function xAt(y, g) {
    return g.baseX + g.amp * Math.sin((y / g.wave) * Math.PI * 2);
  }

  function visible() {
    return stations.filter(function (s) { return !s.hidden; });
  }

  /* Sides and rows are assigned over the VISIBLE set, not the DOM order —
     otherwise filtering leaves two cards stacked on the same side of the spine.
     Every station gets its OWN grid row: left in column 1, right in column 3,
     but never sharing a row. Sharing is what makes a two-column grid; taking
     turns down the page is what makes a track. */
  function assignSides() {
    visible().forEach(function (s, i) {
      s.setAttribute('data-side', narrow.matches ? 'right' : (i % 2 ? 'right' : 'left'));
      s.style.gridRow = String(i + 1);
      /* The interlock margin comes from `.station + .station`, which is DOM
         adjacency — so when a filter hides the first card, the next one still
         inherits the pull-up and rides into the filter row above. Only the
         first VISIBLE station is exempt, and only JS knows which that is. */
      s.style.marginTop = i === 0 ? '0px' : '';
    });
    stations.filter(function (s) { return s.hidden; })
            .forEach(function (s) { s.style.gridRow = ''; s.style.marginTop = ''; });
  }

  function el(name, attrs) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  function draw() {
    var w = rail.clientWidth;
    var h = rail.clientHeight;
    if (!w || !h) return;

    var g = geometry();
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    /* ── Pixel grid ──
       The track is drawn as discrete cells on a fixed grid rather than as
       stroked vectors, so it speaks the same language as the pixel clusters
       and the chat bubbles. Snapping x to the grid is what turns the sine
       into a staircase; without it the squares just trace a smooth curve and
       the effect is lost. */
    var PX = g.px;
    function snap(v) { return Math.round(v / PX) * PX; }

    /* Deterministic per-coordinate, matching the dust seed already used here,
       so a redraw never reshuffles the pattern. */
    function unit(n) {
      var v = Math.sin(n * 12.9898) * 43758.5453;
      return v - Math.floor(v);
    }

    /* Replaces the old linearGradient: the line used to fade at both ends via
       stroke: url(#trackFade). Per-cell opacity does the same job and keeps
       every mark a plain filled rect. */
    function fade(t) {
      if (t < 0.06) return t / 0.06;
      if (t > 0.90) return Math.max(0, (1 - t) / 0.10);
      return 1;
    }

    function cell(x, y, size, opacity, cls) {
      return el('rect', {
        class: cls, x: snap(x), y: snap(y), width: size, height: size,
        opacity: opacity.toFixed(2)
      });
    }

    /* The spine. One cell per grid row, x snapped so the meander reads as
       steps. A deterministic 14% of cells are dropped and the rest vary in
       weight, so the line has texture instead of reading as a solid bar. */
    var y;
    for (y = 0; y <= h; y += PX) {
      var f = unit(y);
      if (f > 0.86) continue;
      var o = fade(y / h) * (0.34 + f * 0.5);
      if (o <= 0.01) continue;
      svg.appendChild(cell(xAt(y, g) - PX / 2, y, PX, o, 'track-px'));
    }

    /* Dust, same placement maths as before but square and grid-aligned. */
    var step = narrow.matches ? 34 : 26;
    for (y = 12; y < h; y += step) {
      var seed = Math.sin(y * 12.9898) * 43758.5453;
      var f1 = seed - Math.floor(seed);
      var f2 = (seed * 1.37) - Math.floor(seed * 1.37);
      var spread = narrow.matches ? 26 : 74;
      svg.appendChild(cell(
        xAt(y, g) + (f1 - 0.5) * 2 * spread,
        y + (f2 - 0.5) * step,
        f1 > 0.62 ? PX : Math.max(2, PX - 1),
        0.2 + f2 * 0.5, 'track-px-dust'));
    }

    /* Nodes and spurs, measured off each station. The station carries no
       transform (the card inside it does), so its rect is the honest one. */
    var railRect = rail.getBoundingClientRect();
    visible().forEach(function (s) {
      var r = s.getBoundingClientRect();
      var ny = r.top - railRect.top + ANCHOR;
      var nx = xAt(ny, g);
      var side = s.getAttribute('data-side');
      var edge = side === 'left' ? (r.right - railRect.left) : (r.left - railRect.left);

      /* Skip only the spur when the card edge already sits on the line — the
         node still marks the station. */
      if (Math.abs(edge - nx) >= g.spurMin) {
        var dir = edge > nx ? 1 : -1;
        var run = Math.abs(edge - nx);
        /* every other grid cell, so the spur reads as a dashed pixel run */
        for (var d = PX * 2; d < run; d += PX * 2) {
          svg.appendChild(cell(nx + dir * d - PX / 2, ny - PX / 2, PX,
            0.34 * (1 - d / run) + 0.16, 'track-px-spur'));
        }
      }

      /* Station marker: a plus of cells around a 2x2 core. In dark mode the
         node used to carry a drop-shadow filter — an SVG filter, the same
         thing iOS Safari rasterises at the wrong scale — so the glow is now
         concentric cells at falling opacity instead. */
      var cx = nx - PX, cy = ny - PX;
      svg.appendChild(cell(cx, cy, PX * 2, 1, 'track-px-node'));
      [[-1, 0], [2, 0], [0, -1], [0, 2]].forEach(function (o) {
        svg.appendChild(cell(cx + o[0] * PX, cy + o[1] * PX, PX, 0.72, 'track-px-node'));
      });
      [[-2, -1], [-2, 2], [3, -1], [3, 2], [-1, -2], [2, -2], [-1, 3], [2, 3]].forEach(function (o) {
        svg.appendChild(cell(cx + o[0] * PX, cy + o[1] * PX, PX, 0.20, 'track-px-halo'));
      });
    });
  }

  /* Reveal. The station handles the entrance (opacity + lift) and the card
     handles the resting tilt, so the two transforms never fight over the same
     property. */
  var io = null;
  if (!reduce && 'IntersectionObserver' in window) {
    io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('in');
        io.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    stations.forEach(function (s, i) {
      s.style.setProperty('--in-delay', Math.min(i, 5) * 55 + 'ms');
      io.observe(s);
    });
  } else {
    stations.forEach(function (s) { s.classList.add('in'); });
  }

  var pending = null;
  function redraw() {
    if (pending) cancelAnimationFrame(pending);
    pending = requestAnimationFrame(function () { pending = null; assignSides(); draw(); });
  }

  assignSides();
  redraw();

  if ('ResizeObserver' in window) new ResizeObserver(redraw).observe(rail);
  window.addEventListener('resize', redraw);
  if (narrow.addEventListener) narrow.addEventListener('change', redraw);

  /* Web fonts land after first paint and change every card's height. */
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(redraw);
  window.addEventListener('load', redraw);

  /* The filter script owns visibility; it tells us when it has changed. */
  document.addEventListener('portfolio:filtered', function () {
    visible().forEach(function (s) { s.classList.add('in'); });
    redraw();
  });
})();
