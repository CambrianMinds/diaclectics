import * as http from "http";
import * as https from "https";
import * as vscode from "vscode";

export class AxisWizardViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "diaclectics.triangulationWizardView";
  private view?: vscode.WebviewView;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly serverUrlProvider: () => string
  ) {}

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

    webviewView.webview.html = this.getHtmlForWebview();

    webviewView.webview.onDidReceiveMessage(async (message) => {
      if (message.command === "scanCodebase") {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
          vscode.window.showErrorMessage("No workspace folder open to scan.");
          return;
        }

        const rootPath = workspaceFolders[0].uri.fsPath;
        const axisName = message.axisName || "workspace_domain_axis";

        vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Epistemic Triangulation: Scanning AST & OpenAlex Literature...",
            cancellable: false,
          },
          async () => {
            try {
              const res = await this.queryDiscoveryEndpoint(rootPath, axisName);
              webviewView.webview.postMessage({ type: "discoveryResult", data: res });
              vscode.window.showInformationMessage(
                `Discovered ${res.invariants_discovered} invariants triangulated with OpenAlex!`
              );
            } catch (err: any) {
              vscode.window.showErrorMessage(`Discovery failed: ${err.message}`);
              webviewView.webview.postMessage({ type: "discoveryError", error: err.message });
            }
          }
        );
      } else if (message.command === "saveProfile") {
        const seedProfile = message.seedProfile;
        if (!seedProfile) {
          return;
        }
        const ws = vscode.workspace.workspaceFolders?.[0];
        if (!ws) {
          return;
        }

        const targetUri = vscode.Uri.joinPath(
          ws.uri,
          `data/seeds/${seedProfile.axis_id || "custom_axis"}_seeds.json`
        );
        const data = Buffer.from(JSON.stringify(seedProfile, null, 2), "utf-8");
        await vscode.workspace.fs.writeFile(targetUri, data);

        vscode.window.showInformationMessage(
          `Calibration seed profile saved to ${vscode.workspace.asRelativePath(targetUri)}`
        );
      }
    });
  }

  private queryDiscoveryEndpoint(path: string, axisName: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const serverUrl = this.serverUrlProvider();
      const url = new URL(`${serverUrl}/v1/calibration/discover`);
      const client = url.protocol === "https:" ? https : http;

      const body = JSON.stringify({
        path: path,
        axis_name: axisName,
        max_files: 25,
      });

      const req = client.request(
        url,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        (res) => {
          let resData = "";
          res.on("data", (chunk) => (resData += chunk));
          res.on("end", () => {
            if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
              try {
                resolve(JSON.parse(resData));
              } catch (e) {
                reject(new Error("Invalid JSON response from server"));
              }
            } else {
              reject(new Error(`Server returned HTTP ${res.statusCode}: ${resData}`));
            }
          });
        }
      );

      req.on("error", (err) => reject(err));
      req.write(body);
      req.end();
    });
  }

  private getHtmlForWebview(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Epistemic Triangulation Wizard</title>
  <style>
    body {
      background: var(--vscode-sideBar-background, #080c14);
      color: var(--vscode-foreground, #ccc);
      font-family: var(--vscode-font-family, sans-serif);
      padding: 12px;
      margin: 0;
      font-size: 0.85rem;
    }
    h3 { margin-top: 0; font-size: 1rem; color: #00f0ff; }
    p { color: var(--vscode-descriptionForeground, #888); line-height: 1.4; margin-bottom: 12px; }
    .btn {
      background: var(--vscode-button-background, #007acc);
      color: var(--vscode-button-foreground, #fff);
      border: none;
      padding: 8px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 600;
      width: 100%;
      margin-bottom: 12px;
    }
    .btn:hover { background: var(--vscode-button-hoverBackground, #005999); }
    .input-field {
      width: 100%;
      background: var(--vscode-input-background, #1e1e1e);
      color: var(--vscode-input-foreground, #fff);
      border: 1px solid var(--vscode-input-border, #3c3c3c);
      padding: 6px 8px;
      border-radius: 4px;
      box-sizing: border-box;
      margin-bottom: 8px;
    }
    .invariant-card {
      background: var(--vscode-editor-background, #0d111a);
      border: 1px solid var(--vscode-panel-border, rgba(255,255,255,0.1));
      border-radius: 6px;
      padding: 10px;
      margin-bottom: 10px;
    }
    .inv-title { font-weight: 700; color: #38bdf8; margin-bottom: 4px; }
    .inv-domain { font-size: 0.75rem; color: #a855f7; text-transform: uppercase; }
    .inv-paper { font-size: 0.75rem; color: #10b981; margin-top: 6px; }
    .anchor-box { background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px; margin-top: 6px; font-size: 0.75rem; }
  </style>
</head>
<body>
  <h3>⚡ Epistemic Triangulation</h3>
  <p>Scan your codebase AST for physical & formal invariants and cross-verify with OpenAlex peer-reviewed literature to eliminate self-validating echo chambers.</p>

  <label for="axisName" style="font-size: 0.75rem; color: #888;">Axis Identifier</label>
  <input type="text" id="axisName" class="input-field" value="workspace_domain_axis" />

  <button id="scanBtn" class="btn">🔍 Discover & Triangulate</button>

  <div id="results"></div>

  <script>
    const vscode = acquireVsCodeApi();
    const scanBtn = document.getElementById('scanBtn');
    const axisName = document.getElementById('axisName');
    const resultsDiv = document.getElementById('results');

    let currentSeedProfile = null;

    scanBtn.addEventListener('click', () => {
      resultsDiv.innerHTML = '<div style="text-align: center; color: #888;">Scanning AST & querying OpenAlex...</div>';
      vscode.postMessage({
        command: 'scanCodebase',
        axisName: axisName.value.trim()
      });
    });

    window.addEventListener('message', event => {
      const msg = event.data;
      if (msg.type === 'discoveryResult') {
        const d = msg.data;
        currentSeedProfile = d.draft_seed_profile;
        if (!d.invariants || d.invariants.length === 0) {
          resultsDiv.innerHTML = '<div style="color: #f43f5e;">No invariants detected. Add physical/formal assertions or docstrings to your codebase.</div>';
          return;
        }

        let html = '<div style="margin-bottom: 8px; font-weight: bold; color: #10b981;">✓ ' + d.invariants_discovered + ' Invariants Triangulated:</div>';
        d.invariants.forEach(inv => {
          html += '<div class="invariant-card">';
          html += '<div class="inv-domain">' + (inv.domain || 'Domain') + '</div>';
          html += '<div class="inv-title">' + inv.name + '</div>';
          if (inv.literature_citations && inv.literature_citations.length > 0) {
            const p = inv.literature_citations[0];
            html += '<div class="inv-paper">📚 ' + p.title + ' (' + (p.publication_year || 'Peer-Reviewed') + ')</div>';
          }
          if (inv.synthesized_positive_anchor) {
            html += '<div class="anchor-box"><strong>[+1.0]:</strong> ' + inv.synthesized_positive_anchor + '</div>';
          }
          html += '</div>';
        });

        html += '<button id="saveBtn" class="btn" style="background: #10b981;">💾 Save Seed Profile</button>';
        resultsDiv.innerHTML = html;

        document.getElementById('saveBtn').addEventListener('click', () => {
          vscode.postMessage({
            command: 'saveProfile',
            seedProfile: currentSeedProfile
          });
        });
      } else if (msg.type === 'discoveryError') {
        resultsDiv.innerHTML = '<div style="color: #f43f5e;">Error: ' + msg.error + '</div>';
      }
    });
  </script>
</body>
</html>`;
  }
}
