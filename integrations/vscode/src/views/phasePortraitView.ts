import * as vscode from "vscode";
import { TelemetryClient, TelemetryEvent } from "../telemetryClient";

export class PhasePortraitViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "diaclectics.phasePortraitView";
  private view?: vscode.WebviewView;
  private lastEvent?: TelemetryEvent;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly telemetryClient: TelemetryClient
  ) {
    this.telemetryClient.onEvent((event) => {
      this.lastEvent = event;
      if (this.view) {
        this.view.webview.postMessage({ type: "telemetry", data: event });
      }
    });

    this.telemetryClient.onStatusChange((connected) => {
      if (this.view) {
        this.view.webview.postMessage({ type: "connection", connected });
      }
    });
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

    if (this.lastEvent) {
      webviewView.webview.postMessage({ type: "telemetry", data: this.lastEvent });
    }
  }

  private getHtmlForWebview(webview: vscode.Webview): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Epistemic Phase Portrait</title>
  <style>
    body {
      background-color: var(--vscode-sideBar-background, #080c14);
      color: var(--vscode-foreground, #cccccc);
      font-family: var(--vscode-font-family, sans-serif);
      margin: 0;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .header-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.85rem;
      border-bottom: 1px solid var(--vscode-panel-border, rgba(255,255,255,0.1));
      padding-bottom: 8px;
    }
    .status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #888;
      margin-right: 6px;
    }
    .connected { background: #10b981; box-shadow: 0 0 8px #10b981; }
    .disconnected { background: #f43f5e; }
    
    #canvas-container {
      display: flex;
      justify-content: center;
      background: var(--vscode-editor-background, #04060a);
      border-radius: 8px;
      border: 1px solid var(--vscode-panel-border, rgba(255,255,255,0.08));
      padding: 8px;
    }
    canvas {
      width: 100%;
      max-width: 280px;
      height: 240px;
    }
    .readouts {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .readout-card {
      background: var(--vscode-editor-background, #0d111a);
      border: 1px solid var(--vscode-panel-border, rgba(255,255,255,0.06));
      border-radius: 6px;
      padding: 8px;
      text-align: center;
    }
    .label {
      font-size: 0.7rem;
      color: var(--vscode-descriptionForeground, #888);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .val {
      font-size: 1.1rem;
      font-weight: 700;
      font-family: var(--vscode-editor-font-family, monospace);
      margin-top: 2px;
      color: #00f0ff;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
    }
    .cleared { background: rgba(16, 185, 129, 0.2); color: #10b981; }
    .intercepted { background: rgba(244, 63, 94, 0.2); color: #f43f5e; }
  </style>
</head>
<body>
  <div class="header-bar">
    <div><span id="conn-dot" class="status-dot disconnected"></span><span id="conn-text">Connecting...</span></div>
    <span id="badge-gate" class="badge cleared">STANDBY</span>
  </div>

  <div id="canvas-container">
    <canvas id="phaseCanvas" width="280" height="240"></canvas>
  </div>

  <div class="readouts">
    <div class="readout-card">
      <div class="label">Capitulation (RCI)</div>
      <div class="val" id="val-rci">0.000</div>
    </div>
    <div class="readout-card">
      <div class="label">Tension Prior (T)</div>
      <div class="val" id="val-tension">0.00</div>
    </div>
    <div class="readout-card">
      <div class="label">Evidence (We)</div>
      <div class="val" id="val-evidence">0.00</div>
    </div>
    <div class="readout-card">
      <div class="label">Concession (C)</div>
      <div class="val" id="val-concession">0.00</div>
    </div>
  </div>

  <script>
    const canvas = document.getElementById('phaseCanvas');
    const ctx = canvas.getContext('2d');
    const connDot = document.getElementById('conn-dot');
    const connText = document.getElementById('conn-text');
    const badgeGate = document.getElementById('badge-gate');

    const valRci = document.getElementById('val-rci');
    const valTension = document.getElementById('val-tension');
    const valEvidence = document.getElementById('val-evidence');
    const valConcession = document.getElementById('val-concession');

    let curT = 0.5, curC = 0.0, curWe = 0.0, curRci = 0.0;

    function drawPhase() {
      const w = canvas.width, h = canvas.height, pad = 24;
      ctx.clearRect(0, 0, w, h);

      // BG
      ctx.fillStyle = '#04060a';
      ctx.fillRect(0, 0, w, h);

      const pw = w - pad * 2, ph = h - pad * 2;

      // Danger contour
      ctx.fillStyle = 'rgba(244, 63, 94, 0.15)';
      ctx.beginPath();
      ctx.moveTo(pad + pw * 0.4, pad);
      ctx.lineTo(w - pad, pad);
      ctx.lineTo(w - pad, pad + ph * 0.5);
      ctx.lineTo(pad + pw * 0.4, pad + ph * 0.2);
      ctx.closePath();
      ctx.fill();

      // Axes
      ctx.strokeStyle = 'rgba(255,255,255,0.2)';
      ctx.lineWidth = 1;
      ctx.strokeRect(pad, pad, pw, ph);

      // Labels
      ctx.fillStyle = '#888';
      ctx.font = '9px sans-serif';
      ctx.fillText('0', pad - 10, h - pad + 10);
      ctx.fillText('1', w - pad - 6, h - pad + 10);
      ctx.fillText('T (Tension)', pad + 4, pad + 12);
      ctx.fillText('C (Concession)', w - pad - 68, h - pad - 4);

      // Point
      const px = pad + curC * pw;
      const py = h - pad - curT * ph;
      const isTripped = curRci >= 0.50;
      const color = isTripped ? '#f43f5e' : '#00f0ff';

      ctx.shadowColor = color;
      ctx.shadowBlur = 12;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(px, py, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    window.addEventListener('message', event => {
      const msg = event.data;
      if (msg.type === 'connection') {
        if (msg.connected) {
          connDot.className = 'status-dot connected';
          connText.textContent = 'Live SSE';
        } else {
          connDot.className = 'status-dot disconnected';
          connText.textContent = 'Offline';
        }
      } else if (msg.type === 'telemetry') {
        const d = msg.data;
        curT = d.epistemic_tension || 0;
        curC = d.concession_delta || 0;
        curWe = d.evidence_weight || 0;
        curRci = d.rci || 0;

        valRci.textContent = curRci.toFixed(3);
        valTension.textContent = curT.toFixed(2);
        valEvidence.textContent = curWe.toFixed(2);
        valConcession.textContent = curC.toFixed(2);

        if (curRci >= 0.50) {
          valRci.style.color = '#f43f5e';
          badgeGate.className = 'badge intercepted';
          badgeGate.textContent = 'INTERCEPTED';
        } else {
          valRci.style.color = '#10b981';
          badgeGate.className = 'badge cleared';
          badgeGate.textContent = 'CLEARED';
        }
        drawPhase();
      }
    });

    drawPhase();
  </script>
</body>
</html>`;
  }
}
