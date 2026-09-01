import * as vscode from "vscode";
import { TelemetryClient, TelemetryEvent } from "./telemetryClient";
import { PhasePortraitViewProvider } from "./views/phasePortraitView";
import { CitationsProvider } from "./views/citationsView";
import { AxisWizardViewProvider } from "./views/axisWizardView";
import { registerCommands } from "./commands";

let statusBarItem: vscode.StatusBarItem;
let telemetryClient: TelemetryClient;

export function activate(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration("diaclectics");
  const serverUrl = config.get<string>("serverUrl", "http://localhost:8000");
  const showTripwireNotifications = config.get<boolean>("showTripwireNotifications", true);
  const tripwireThreshold = config.get<number>("tripwireThreshold", 0.50);

  // Initialize Telemetry SSE Client
  telemetryClient = new TelemetryClient(serverUrl);

  // Initialize Status Bar Item
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = "diaclectics.openDashboard";
  statusBarItem.text = "$(zap) Diaclectics: Standby";
  statusBarItem.tooltip = "Click to open Diaclectics Web Visualizer";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Listen to Telemetry SSE Events
  telemetryClient.onEvent((event: TelemetryEvent) => {
    const rci = event.rci || 0.0;
    const isIntercepted = rci >= tripwireThreshold;

    if (isIntercepted) {
      statusBarItem.text = `$(alert) RCI: ${rci.toFixed(2)} (INTERCEPTED)`;
      statusBarItem.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
      if (showTripwireNotifications) {
        vscode.window.showWarningMessage(
          `⚡ Diaclectics Interception: Model capitulation intercepted (RCI: ${rci.toFixed(2)}). Self-healing re-draft active.`
        );
      }
    } else {
      statusBarItem.text = `$(zap) RCI: ${rci.toFixed(2)} (Cleared)`;
      statusBarItem.backgroundColor = undefined;
    }
  });

  telemetryClient.onStatusChange((connected) => {
    if (!connected) {
      statusBarItem.text = "$(debug-disconnect) Diaclectics: Offline";
      statusBarItem.backgroundColor = undefined;
    }
  });

  if (config.get<boolean>("autoConnect", true)) {
    telemetryClient.connect();
  }

  // Register Webviews and Views
  const phaseProvider = new PhasePortraitViewProvider(context.extensionUri, telemetryClient);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(PhasePortraitViewProvider.viewType, phaseProvider)
  );

  const citationsProvider = new CitationsProvider(telemetryClient);
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("diaclectics.citationsView", citationsProvider)
  );

  const wizardProvider = new AxisWizardViewProvider(
    context.extensionUri,
    () => vscode.workspace.getConfiguration("diaclectics").get<string>("serverUrl", "http://localhost:8000")
  );
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(AxisWizardViewProvider.viewType, wizardProvider)
  );

  // Register Command Palette Actions
  registerCommands(context, () =>
    vscode.workspace.getConfiguration("diaclectics").get<string>("serverUrl", "http://localhost:8000")
  );

  // Configuration change listener
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("diaclectics.serverUrl")) {
        const newUrl = vscode.workspace
          .getConfiguration("diaclectics")
          .get<string>("serverUrl", "http://localhost:8000");
        telemetryClient.setServerUrl(newUrl);
      }
    })
  );
}

export function deactivate() {
  if (telemetryClient) {
    telemetryClient.disconnect();
  }
}
