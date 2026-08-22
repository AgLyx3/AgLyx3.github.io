/* Constellation field — a drifting node/link network painted behind the page.
 *
 * Adapted from the ConstellationField renderer in ThreeUI Community
 * (https://github.com/MengTo/threeui, MIT). The upstream renderer ships as a
 * React component that iframes a full Tailwind demo document; this site has no
 * build step and no React, so only the 2D-canvas renderer was lifted and then
 * reworked: colours now come from the page's own CSS custom properties instead
 * of a hard-coded gold, the loop parks itself when the tab or the section is
 * out of view, and pointer gravity is skipped on touch.
 *
 * Usage: <script src="assets/constellation.js" defer></script> plus a
 * <canvas id="constellation">. Everything else is automatic.
 */
(function () {
  'use strict';

  var canvas = document.getElementById('constellation');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  if (!ctx) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Coarse pointers never resolve a hover, so gravity would be dead weight.
  var hasPointer = window.matchMedia('(hover: hover)').matches;

  var width = 0;
  var height = 0;
  var nodes = [];
  var pointer = { x: -9999, y: -9999 };
  var frame = 0;
  var visible = true;

  // Link radius and node count both scale with the viewport: the same absolute
  // numbers that read as a loose web at 1440px read as a solid mat on a phone.
  function nodeCount() {
    if (width < 640) return 26;
    if (width < 1100) return 44;
    return 62;
  }
  function linkRadius() {
    return width < 640 ? 108 : 158;
  }

  /* ── palette ──────────────────────────────────────────────────────────────
     Read from the stylesheet so the field tracks the theme tokens rather than
     duplicating them. --forest-rgb is the accent in both themes; the alphas
     differ because ink-on-cream carries far more than glow-on-navy. */
  var palette = { rgb: '147, 180, 236', node: 0.5, link: 0.15, halo: 0.14 };

  function readPalette() {
    var css = getComputedStyle(document.documentElement);
    var rgb = css.getPropertyValue('--forest-rgb').trim() || '147, 180, 236';
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    palette = dark
      ? { rgb: rgb, node: 0.55, link: 0.16, halo: 0.16 }
      : { rgb: rgb, node: 0.34, link: 0.10, halo: 0.07 };
  }

  /* ── sizing ────────────────────────────────────────────────────────────── */
  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    canvas.width = Math.max(1, Math.floor(width * dpr));
    canvas.height = Math.max(1, Math.floor(height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function seed() {
    var count = nodeCount();
    nodes = [];
    for (var i = 0; i < count; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.22,
        r: Math.random() * 1.5 + 1.0,
        phase: Math.random() * Math.PI * 2
      });
    }
  }

  /* ── render ────────────────────────────────────────────────────────────── */
  function draw(now) {
    frame = requestAnimationFrame(draw);
    if (!visible) return;

    ctx.clearRect(0, 0, width, height);

    var link = linkRadius();
    var i, j;

    // Links first, so the node cores sit crisp on top of them.
    ctx.strokeStyle = 'rgb(' + palette.rgb + ')';
    ctx.lineWidth = 1;
    for (i = 0; i < nodes.length; i++) {
      for (j = i + 1; j < nodes.length; j++) {
        var dx = nodes[i].x - nodes[j].x;
        var dy = nodes[i].y - nodes[j].y;
        var d2 = dx * dx + dy * dy;
        if (d2 > link * link) continue;
        var falloff = 1 - Math.sqrt(d2) / link;
        ctx.globalAlpha = palette.link * falloff;
        ctx.beginPath();
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(nodes[j].x, nodes[j].y);
        ctx.stroke();
      }
    }

    ctx.fillStyle = 'rgb(' + palette.rgb + ')';
    for (i = 0; i < nodes.length; i++) {
      var n = nodes[i];

      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 0 || n.x > width) n.vx *= -1;
      if (n.y < 0 || n.y > height) n.vy *= -1;

      // Gentle pull toward the cursor — enough to feel alive under the hand,
      // not enough to collapse the field into a clump.
      if (hasPointer) {
        var pdx = n.x - pointer.x;
        var pdy = n.y - pointer.y;
        if (pdx * pdx + pdy * pdy < 210 * 210) {
          n.x -= pdx * 0.004;
          n.y -= pdy * 0.004;
        }
      }

      var pulse = 0.72 + Math.sin(now * 0.0009 + n.phase) * 0.28;

      ctx.globalAlpha = palette.halo * pulse;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r * 2.8, 0, Math.PI * 2);
      ctx.fill();

      ctx.globalAlpha = palette.node * pulse;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.globalAlpha = 1;
  }

  /* Reduced motion still gets the field — it just holds still, so the page
     keeps its texture without anything moving. */
  function paintStatic() {
    ctx.clearRect(0, 0, width, height);
    var link = linkRadius();
    ctx.strokeStyle = 'rgb(' + palette.rgb + ')';
    ctx.lineWidth = 1;
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var dx = nodes[i].x - nodes[j].x;
        var dy = nodes[i].y - nodes[j].y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d > link) continue;
        ctx.globalAlpha = palette.link * (1 - d / link);
        ctx.beginPath();
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(nodes[j].x, nodes[j].y);
        ctx.stroke();
      }
    }
    ctx.fillStyle = 'rgb(' + palette.rgb + ')';
    for (var k = 0; k < nodes.length; k++) {
      ctx.globalAlpha = palette.node;
      ctx.beginPath();
      ctx.arc(nodes[k].x, nodes[k].y, nodes[k].r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  /* ── wiring ────────────────────────────────────────────────────────────── */
  readPalette();
  resize();
  seed();

  if (reduceMotion) {
    paintStatic();
  } else {
    frame = requestAnimationFrame(draw);
  }

  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      resize();
      seed();
      if (reduceMotion) paintStatic();
    }, 150);
  });

  if (hasPointer) {
    window.addEventListener('pointermove', function (e) {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
    }, { passive: true });
    document.documentElement.addEventListener('pointerleave', function () {
      pointer.x = -9999;
      pointer.y = -9999;
    });
  }

  // A background animation has no business burning frames on a hidden tab.
  document.addEventListener('visibilitychange', function () {
    visible = !document.hidden;
  });

  // Theme flips change the accent, so re-read the tokens instead of restarting.
  new MutationObserver(function () {
    readPalette();
    if (reduceMotion) paintStatic();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
