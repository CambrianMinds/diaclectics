import * as http from "http";
import * as https from "https";
import * as vscode from "vscode";

export interface TelemetryEvent {
  timestamp: string;
  session_id: string;
  turn: number;
  operator_position: number;
  model_position: number;
  epistemic_tension: number;
  concession_delta: number;
  evidence_weight: number;
  rci: number;
  status: string;
  intercepted?: boolean;
  why_rationale?: string;
  citations: Array<{
    doi?: string;
    title: string;
    journal?: string;
    year?: number;
    citation_count?: number;
  }>;
}

export class TelemetryClient {
  private req: http.ClientRequest | null = null;
  private isRunning: boolean = false;
  private onEventEmitter = new vscode.EventEmitter<TelemetryEvent>();
  public readonly onEvent = this.onEventEmitter.event;

  private onStatusEmitter = new vscode.EventEmitter<boolean>();
  public readonly onStatusChange = this.onStatusEmitter.event;

  constructor(private serverUrl: string) {}

  public setServerUrl(url: string): void {
    this.serverUrl = url;
    if (this.isRunning) {
      this.reconnect();
    }
  }

  public connect(): void {
    if (this.isRunning) {
      return;
    }
    this.isRunning = true;
    this.startSSE();
  }

  public disconnect(): void {
    this.isRunning = false;
    if (this.req) {
      this.req.destroy();
      this.req = null;
    }
    this.onStatusEmitter.fire(false);
  }

  public reconnect(): void {
    this.disconnect();
    setTimeout(() => this.connect(), 1000);
  }

  private startSSE(): void {
    try {
      const url = new URL(`${this.serverUrl}/telemetry/stream`);
      const client = url.protocol === "https:" ? https : http;

      this.req = client.get(url, (res) => {
        if (res.statusCode !== 200) {
          this.onStatusEmitter.fire(false);
          this.scheduleRetry();
          return;
        }

        this.onStatusEmitter.fire(true);
        let buffer = "";

        res.on("data", (chunk: Buffer) => {
          buffer += chunk.toString("utf-8");
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const block of lines) {
            for (const line of block.split("\n")) {
              if (line.startsWith("data: ")) {
                try {
                  const data: TelemetryEvent = JSON.parse(line.substring(6));
                  this.onEventEmitter.fire(data);
                } catch (e) {
                  // ignore non-json keepalives
                }
              }
            }
          }
        });

        res.on("end", () => {
          this.onStatusEmitter.fire(false);
          this.scheduleRetry();
        });

        res.on("error", () => {
          this.onStatusEmitter.fire(false);
          this.scheduleRetry();
        });
      });

      this.req.on("error", () => {
        this.onStatusEmitter.fire(false);
        this.scheduleRetry();
      });
    } catch (e) {
      this.onStatusEmitter.fire(false);
      this.scheduleRetry();
    }
  }

  private scheduleRetry(): void {
    if (this.isRunning) {
      setTimeout(() => {
        if (this.isRunning) {
          this.startSSE();
        }
      }, 3000);
    }
  }
}
