/* ==========================================================================
   DIACLECTICS INTERACTIVE SHOWCASE - JAVASCRIPT
   Interactive 2D Phase Portrait, RCI Simulator, Tab Switcher, Code Copier
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const sliderTension = document.getElementById('sliderTension');
  const sliderConcession = document.getElementById('sliderConcession');
  const sliderEvidence = document.getElementById('sliderEvidence');

  const valTension = document.getElementById('valTension');
  const valConcession = document.getElementById('valConcession');
  const valEvidence = document.getElementById('valEvidence');

  const readoutRCI = document.getElementById('readoutRCI');
  const readoutTension = document.getElementById('readoutTension');
  const readoutStatus = document.getElementById('readoutStatus');

  const canvas = document.getElementById('phaseCanvas');
  const ctx = canvas.getContext('2d');

  // Math calculation: RCI = sqrt(T) * sigma(alpha*C - beta*We)
  function calculateRCI(T, C, We) {
    const alpha = 4.0;
    const beta = 5.0;
    const z = alpha * C - beta * We;
    const sigma = 1.0 / (1.0 + Math.exp(-z));
    const rci = Math.sqrt(T) * sigma;
    return Math.min(1.0, Math.max(0.0, rci));
  }

  // Draw 2D Phase Space
  function drawPhasePortrait(T, C, We, rci) {
    const width = canvas.width;
    const height = canvas.height;
    const padding = 36;

    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = '#080c14';
    ctx.fillRect(0, 0, width, height);

    const plotW = width - padding * 2;
    const plotH = height - padding * 2;

    // Grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const x = padding + (plotW / 4) * i;
      const y = padding + (plotH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, height - padding);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
    }

    // Danger Zone contour shading (where RCI >= 0.50 assuming current We)
    ctx.fillStyle = 'rgba(244, 63, 94, 0.12)';
    ctx.beginPath();
    ctx.moveTo(padding + plotW * 0.4, padding); // high tension, mid-to-high concession
    ctx.lineTo(width - padding, padding);
    ctx.lineTo(width - padding, padding + plotH * 0.5);
    ctx.lineTo(padding + plotW * 0.4, padding + plotH * 0.2);
    ctx.closePath();
    ctx.fill();

    // Axes
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.lineTo(width - padding, padding);
    ctx.moveTo(padding, height - padding);
    ctx.lineTo(padding, padding);
    ctx.stroke();

    // Axis Labels
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px Inter, sans-serif';
    ctx.fillText('0.0', padding - 14, height - padding + 14);
    ctx.fillText('1.0', width - padding - 8, height - padding + 14);
    ctx.fillText('1.0', padding - 22, padding + 4);
    ctx.fillText('Concession Delta (C)', padding + plotW / 2 - 45, height - 10);

    ctx.save();
    ctx.translate(14, padding + plotH / 2 + 40);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Epistemic Tension (T)', 0, 0);
    ctx.restore();

    // Plot Point (C, T)
    const px = padding + C * plotW;
    const py = height - padding - T * plotH;

    // Draw previous trajectory vector arrow
    const prevC = Math.max(0, C - 0.25);
    const prevT = Math.min(1.0, T + 0.1);
    const prevPx = padding + prevC * plotW;
    const prevPy = height - padding - prevT * plotH;

    ctx.strokeStyle = 'rgba(0, 240, 255, 0.4)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(prevPx, prevPy);
    ctx.lineTo(px, py);
    ctx.stroke();
    ctx.setLineDash([]);

    // Target point glow & dot
    const isIntercepted = rci >= 0.50;
    const pointColor = isIntercepted ? '#f43f5e' : '#00f0ff';

    ctx.shadowColor = pointColor;
    ctx.shadowBlur = 18;
    ctx.fillStyle = pointColor;
    ctx.beginPath();
    ctx.arc(px, py, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Tripwire label if tripped
    if (isIntercepted) {
      ctx.fillStyle = '#f43f5e';
      ctx.font = 'bold 11px Inter, sans-serif';
      ctx.fillText('TRIPWIRE HIT', px + 12, py - 8);
    }
  }

  // Update simulator logic
  function updateSimulator() {
    const T = parseFloat(sliderTension.value);
    const C = parseFloat(sliderConcession.value);
    const We = parseFloat(sliderEvidence.value);

    valTension.textContent = T.toFixed(2);
    valConcession.textContent = C.toFixed(2);
    valEvidence.textContent = We.toFixed(2);

    const rci = calculateRCI(T, C, We);

    readoutRCI.textContent = rci.toFixed(3);
    readoutTension.textContent = T.toFixed(2);

    if (rci >= 0.50) {
      readoutRCI.style.color = 'var(--accent-rose)';
      readoutStatus.textContent = 'INTERCEPTED';
      readoutStatus.className = 'status-badge status-intercepted';
    } else {
      readoutRCI.style.color = 'var(--accent-emerald)';
      readoutStatus.textContent = 'CLEARED';
      readoutStatus.className = 'status-badge status-cleared';
    }

    drawPhasePortrait(T, C, We, rci);
  }

  sliderTension.addEventListener('input', updateSimulator);
  sliderConcession.addEventListener('input', updateSimulator);
  sliderEvidence.addEventListener('input', updateSimulator);

  // Initialize canvas size and simulator
  canvas.width = 380;
  canvas.height = 340;
  updateSimulator();

  // Tab switcher
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const target = btn.getAttribute('data-tab');
      document.getElementById(target).classList.add('active');
    });
  });

  // Copy button helper
  window.copySnippet = function(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const text = el.innerText || el.textContent;
    navigator.clipboard.writeText(text).then(() => {
      alert('Copied to clipboard!');
    });
  };
});
