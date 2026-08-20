(function () {
  'use strict';

  var page = document.body && document.body.dataset.pixelPage;
  if (!page || page === 'chat') return;

  var palettes = {
    blue: '149,164,189',
    mist: '196,208,228',
    warm: '214,204,194',
    amber: '223,212,198',
  };
  var layouts = {
    home: [
      { x: 5, y: 10, size: 150, color: 'blue', opacity: 0.34, seed: 11 },
      { x: 79, y: 13, size: 190, color: 'mist', opacity: 0.28, seed: 23 },
      { x: 14, y: 70, size: 130, color: 'warm', opacity: 0.26, seed: 37 },
      { x: 84, y: 68, size: 160, color: 'blue', opacity: 0.30, seed: 49 },
    ],
    portfolio: [
      { x: -2, y: 12, size: 190, color: 'blue', opacity: 0.30, seed: 61 },
      { x: 82, y: 8, size: 170, color: 'mist', opacity: 0.26, seed: 73 },
      { x: 4, y: 68, size: 150, color: 'amber', opacity: 0.22, seed: 89 },
      { x: 84, y: 72, size: 210, color: 'blue', opacity: 0.28, seed: 101 },
    ],
  };

  function unit(seed) {
    var value = Math.sin(seed * 12.9898) * 43758.5453;
    return value - Math.floor(value);
  }

  function buildCluster(config, index) {
    var cluster = document.createElement('span');
    cluster.className = 'pixel-cluster';
    cluster.style.left = config.x + '%';
    cluster.style.top = config.y + '%';
    cluster.style.setProperty('--cluster-size', config.size + 'px');
    cluster.style.setProperty('--cluster-color', palettes[config.color]);
    cluster.style.setProperty('--cluster-opacity', config.opacity);
    cluster.style.setProperty('--cluster-duration', (22 + index * 3) + 's');
    cluster.style.setProperty('--cluster-delay', (-4 - index * 3) + 's');
    cluster.style.setProperty('--cluster-dx', (index % 2 ? -10 : 12) + 'px');
    cluster.style.setProperty('--cluster-dy', (index % 2 ? 12 : -14) + 'px');

    for (var i = 0; i < 54; i++) {
      var angle = unit(config.seed + i * 7) * Math.PI * 2;
      var distance = Math.sqrt(unit(config.seed + i * 11 + 3)) * 46;
      var cell = document.createElement('i');
      cell.className = 'pixel-cell';
      cell.style.left = (50 + Math.cos(angle) * distance) + '%';
      cell.style.top = (50 + Math.sin(angle) * distance) + '%';
      cell.style.setProperty('--cell-size', (3 + Math.floor(unit(config.seed + i * 13) * 4)) + 'px');
      cell.style.setProperty('--cell-opacity', (0.16 + unit(config.seed + i * 17) * 0.46).toFixed(2));
      cluster.appendChild(cell);
    }
    return cluster;
  }

  var host = document.createElement('div');
  host.className = 'pixel-atmosphere';
  host.setAttribute('aria-hidden', 'true');
  (layouts[page] || []).forEach(function (config, index) {
    host.appendChild(buildCluster(config, index));
  });
  document.body.prepend(host);
})();
