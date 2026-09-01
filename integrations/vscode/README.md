# Diaclectics Extension for VS Code & Antigravity IDE

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Diaclectics Engine](https://img.shields.io/badge/Diaclectics-v1.0.0-00f0ff.svg)](https://github.com/CambrianMinds/diaclectics)

Embed real-time **epistemic telemetry**, **anti-sycophancy pre-emission token gating**, an interactive **2D Phase Portrait sidebar**, and an automated **Epistemic Triangulation Codebase Discovery Wizard** directly inside VS Code and Antigravity IDE.

---

## ⚡ Features

### 1. Live Epistemic Phase Space Sidebar
- **2D $(T, C)$ Phase Plane**: Canvas-rendered trajectory vectors plotting Epistemic Tension ($\mathcal{T}$) vs Model Concession ($\mathcal{C}$) in real time.
- **Danger Zone Contours**: Real-time visualization of the $\text{RCI} \ge 0.50$ tripwire boundary.
- **Epistemic Dials**: Real-time readouts for $\text{RCI}$, Prior Tension ($\mathcal{T}$), Evidence Weight ($W_e$), and Concession Delta ($\mathcal{C}$).

### 2. Status Bar Needle & Tripwire Alerts
- Live status bar item showing current RCI status (`🟢 RCI: 0.12 (Cleared)` or `🔴 RCI: 0.84 (INTERCEPTED)`).
- Instant toast notifications when ungrounded sycophantic drift is halted pre-emission and self-healing re-draft is triggered.

### 3. OpenAlex Literature TreeView
- Automatically displays peer-reviewed papers, DOIs, citation counts, and journals retrieved during the dialogue.
- Click any paper to open its official DOI link directly in your browser.

### 4. Epistemic Triangulation Codebase Discovery Wizard
- **Breaks Self-Referential Echo Chambers**: Scans local AST/docstrings for physical units, type bounds, and domain formulas, and automatically cross-checks them against millions of OpenAlex papers.
- **Interactive Review**: Review synthesized $+1.0$ literature-backed invariants and $-1.0$ counter-fallacy anchors.
- **1-Click Profile Generation**: Exports validated seed profiles to `data/seeds/` for instant runtime calibration.

---

## 🚀 Installation & Setup

### In VS Code:
1. Open terminal in `integrations/vscode`:
   ```bash
   cd integrations/vscode
   npm install
   npm run build
   ```
2. Press `F5` in VS Code to launch the Extension Development Host, or package as a `.vsix`:
   ```bash
   npm run package
   code --install-extension diaclectics-vscode-1.0.0.vsix
   ```

### In Antigravity IDE:
1. In Antigravity IDE, go to **Extensions > Install from VSIX...**
2. Select `integrations/vscode/diaclectics-vscode-1.0.0.vsix`.
3. The Diaclectics lightning bolt activity bar icon and live telemetry status bar item will activate immediately.

---

## ⌨️ Command Palette

Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and search for **Diaclectics**:
- `Diaclectics: Start Engine Proxy`: Launches `diaclectics-server` in the integrated terminal.
- `Diaclectics: Open Live Web Visualizer`: Opens `http://localhost:8000/dashboard`.
- `Diaclectics: Discover & Triangulate Calibration Axis from Workspace`: Opens the Triangulation Wizard.
- `Diaclectics: Generate Session Forensic Audit Report`: Generates and displays the session audit markdown.
- `Diaclectics: Insert Anti-Sycophancy System Prompt Preset`: Inserts forensic, socratic, or anti-sycophantic system instructions.

---

## ⚙️ Configuration Settings

| Setting | Default | Description |
| :--- | :--- | :--- |
| `diaclectics.serverUrl` | `http://localhost:8000` | Base URL of the Diaclectics API proxy and telemetry stream. |
| `diaclectics.autoConnect` | `true` | Automatically connect to the SSE telemetry stream on startup. |
| `diaclectics.tripwireThreshold` | `0.50` | Robust Capitulation Index (RCI) tripwire threshold. |
| `diaclectics.showTripwireNotifications` | `true` | Display in-editor warning banners upon interception. |
| `diaclectics.enableStatusBar` | `true` | Display the live RCI needle in the VS Code status bar. |

---

## 📜 License
MIT License. Part of the [Diaclectics Engine](https://github.com/CambrianMinds/diaclectics) project.
