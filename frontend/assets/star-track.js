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
      ? { baseX: 22, amp: 8,  wave: 300, spurMin: 9,  node: 4.5 }
      : { baseX: rail.clientWidth / 2, amp: 24, wave: 430, spurMin: 14, node: 4 };
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

    /* Fade the line out at both ends so it reads as passing through the page
       rather than starting and stopping at two hard edges. */
    var defs = el('defs');
    var grad = el('linearGradient', { id: 'trackFade', x1: '0', y1: '0', x2: '0', y2: '1' });
    [[0, 0], [0.06, 1], [0.9, 1], [1, 0]].forEach(function (s) {
      grad.appendChild(el('stop', { offset: s[0], 'stop-color': 'currentColor', 'stop-opacity': s[1] }));
    });
    defs.appendChild(grad);
    svg.appendChild(defs);

    /* Sampling every 7px is dense enough that a polyline reads as a curve,
       and avoids hand-fitting beziers to a sine. */
    var d = '', y;
    for (y = 0; y <= h; y += 7) d += (y ? 'L' : 'M') + xAt(y, g).toFixed(2) + ' ' + y + ' ';
    d += 'L' + xAt(h, g).toFixed(2) + ' ' + h;

    svg.appendChild(el('path', {
      d: d, class: 'track-line', fill: 'none', stroke: 'url(#trackFade)'
    }));

    /* Dust along the track: deterministic per-y so a redraw doesn't reshuffle
       the sky, and thinned out on narrow screens where there is less room. */
    var step = narrow.matches ? 34 : 26;
    for (y = 12; y < h; y += step) {
      var seed = Math.sin(y * 12.9898) * 43758.5453;
      var f1 = seed - Math.floor(seed);
      var f2 = (seed * 1.37) - Math.floor(seed * 1.37);
      var spread = narrow.matches ? 26 : 74;
      svg.appendChild(el('circle', {
        class: 'track-dust',
        cx: (xAt(y, g) + (f1 - 0.5) * 2 * spread).toFixed(2),
        cy: (y + (f2 - 0.5) * step).toFixed(2),
        r: (0.7 + f1 * 1.25).toFixed(2),
        opacity: (0.2 + f2 * 0.5).toFixed(2)
      }));
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
         node still marks the station. (On narrow screens every spur is short,
         which is how a missing-node bug hid here.) */
      if (Math.abs(edge - nx) >= g.spurMin) {
        var mid = (nx + edge) / 2;
        svg.appendChild(el('path', {
          class: 'track-spur', fill: 'none',
          d: 'M' + nx.toFixed(2) + ' ' + ny.toFixed(2) +
             ' Q' + mid.toFixed(2) + ' ' + ny.toFixed(2) + ' ' + edge.toFixed(2) + ' ' + ny.toFixed(2)
        }));
      }
      svg.appendChild(el('circle', { class: 'track-halo', cx: nx.toFixed(2), cy: ny.toFixed(2), r: g.node * 2.4 }));
      svg.appendChild(el('circle', { class: 'track-node', cx: nx.toFixed(2), cy: ny.toFixed(2), r: g.node }));

      /* Published in rail coordinates so the screenshot preview can hang a
         second spur off the same node, on the far side of the line. It has to
         come from here: the node's x is a sample of the meander, which only
         this file knows the shape of. */
      s.dataset.nodeX = nx.toFixed(2);
      s.dataset.nodeY = ny.toFixed(2);
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
    pending = requestAnimationFrame(function () {
      pending = null; assignSides(); draw();
      document.dispatchEvent(new CustomEvent('portfolio:trackdrawn'));
    });
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
