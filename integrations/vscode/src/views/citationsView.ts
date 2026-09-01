import * as vscode from "vscode";
import { TelemetryClient, TelemetryEvent } from "../telemetryClient";

export class CitationTreeItem extends vscode.TreeItem {
  constructor(
    public readonly title: string,
    public readonly doi?: string,
    public readonly journal?: string,
    public readonly year?: number,
    public readonly citations?: number
  ) {
    super(
      title,
      vscode.TreeItemCollapsibleState.None
    );

    this.description = journal ? `${journal} (${year || "recent"})` : `${year || "recent"}`;
    this.tooltip = `DOI: ${doi || "N/A"}\nCitations: ${citations || 0}\nJournal: ${journal || "Peer-Reviewed"}`;
    this.iconPath = new vscode.ThemeIcon("book");

    if (doi) {
      this.command = {
        command: "vscode.open",
        title: "Open Paper DOI",
        arguments: [vscode.Uri.parse(doi.startsWith("http") ? doi : `https://doi.org/${doi}`)],
      };
    }
  }
}

export class CitationsProvider implements vscode.TreeDataProvider<CitationTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<CitationTreeItem | undefined | null | void> = new vscode.EventEmitter<CitationTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<CitationTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

  private items: CitationTreeItem[] = [];

  constructor(private readonly telemetryClient: TelemetryClient) {
    this.telemetryClient.onEvent((event: TelemetryEvent) => {
      if (event.citations && event.citations.length > 0) {
        this.items = event.citations.map(
          (c) => new CitationTreeItem(c.title, c.doi, c.journal, c.year, c.citation_count)
        );
        this._onDidChangeTreeData.fire();
      }
    });
  }

  getTreeItem(element: CitationTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: CitationTreeItem): Thenable<CitationTreeItem[]> {
    if (element) {
      return Promise.resolve([]);
    }
    if (this.items.length === 0) {
      const placeholder = new CitationTreeItem("No OpenAlex literature queried yet");
      placeholder.iconPath = new vscode.ThemeIcon("info");
      return Promise.resolve([placeholder]);
    }
    return Promise.resolve(this.items);
  }
}
