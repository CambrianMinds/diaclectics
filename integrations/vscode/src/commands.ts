import * as vscode from "vscode";

export function registerCommands(context: vscode.ExtensionContext, getServerUrl: () => string): void {
  // 1. Start Server Proxy Command
  context.subscriptions.push(
    vscode.commands.registerCommand("diaclectics.startServer", () => {
      const terminal = vscode.window.createTerminal("Diaclectics Engine");
      terminal.show();
      terminal.sendText("diaclectics-server");
      vscode.window.showInformationMessage("Starting Diaclectics API Proxy & Telemetry Hub on :8000...");
    })
  );

  // 2. Open Dashboard Command
  context.subscriptions.push(
    vscode.commands.registerCommand("diaclectics.openDashboard", () => {
      const url = `${getServerUrl()}/dashboard`;
      vscode.env.openExternal(vscode.Uri.parse(url));
    })
  );

  // 3. Discover and Triangulate Calibration Axis
  context.subscriptions.push(
    vscode.commands.registerCommand("diaclectics.discoverAndCalibrate", async () => {
      await vscode.commands.executeCommand("workbench.view.extension.diaclectics-sidebar");
      vscode.window.showInformationMessage(
        "Open the 'Codebase Triangulation Wizard' in the Diaclectics sidebar to scan your workspace."
      );
    })
  );

  // 4. Show Session Audit Report
  context.subscriptions.push(
    vscode.commands.registerCommand("diaclectics.showAudit", async () => {
      const sessionId = await vscode.window.showInputBox({
        prompt: "Enter Session ID to generate audit report",
        value: "default",
      });
      if (!sessionId) {
        return;
      }

      const url = `${getServerUrl()}/v1/telemetry/session/${sessionId}`;
      try {
        const doc = await vscode.workspace.openTextDocument({
          content: `# Diaclectics Forensic Epistemic Audit: Session ${sessionId}\n\nGenerated at ${new Date().toISOString()}\n\nAudit endpoint: ${url}\n`,
          language: "markdown",
        });
        await vscode.window.showTextDocument(doc);
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to generate audit: ${err.message}`);
      }
    })
  );

  // 5. Insert Prompt Preset
  context.subscriptions.push(
    vscode.commands.registerCommand("diaclectics.insertPreset", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage("No active text editor open.");
        return;
      }

      const presetChoice = await vscode.window.showQuickPick(
        [
          { label: "Anti-Sycophancy Core", description: "General anti-flattery epistemic boundary enforcement" },
          { label: "Forensic Arbiter", description: "Strict physical sciences, kinematics, and metrology" },
          { label: "Socratic Adversary", description: "Socratic assumption stress-testing & red-teaming" },
        ],
        { placeHolder: "Select Anti-Sycophancy System Prompt Preset" }
      );

      if (!presetChoice) {
        return;
      }

      let presetText = "";
      if (presetChoice.label === "Anti-Sycophancy Core") {
        presetText = `## Anti-Sycophancy Epistemic Invariants
1. Prioritize empirical, mathematical, and verified literature constraints over human flattery.
2. If an operator asserts an unverified proposition, demand empirical criteria or falsification mechanisms.
3. Reject concession when prior epistemic tension is high and counter-evidence weight is negligible.`;
      } else if (presetChoice.label === "Forensic Arbiter") {
        presetText = `## Forensic Arbiter Invariants
1. Physical kinematics, thermodynamics, and toolmark geometry are deterministic.
2. Evaluate all claims against Taylor tool life, Fourier heat conduction, and Daubert standards.`;
      } else {
        presetText = `## Socratic Adversary Invariants
1. Continuously probe operator premises for hidden non-sequiturs and circular justifications.
2. Never capitulate to assertive tone without formal deductive proof.`;
      }

      editor.edit((editBuilder) => {
        editBuilder.insert(editor.selection.active, presetText);
      });
      vscode.window.showInformationMessage(`Inserted ${presetChoice.label} preset!`);
    })
  );
}
