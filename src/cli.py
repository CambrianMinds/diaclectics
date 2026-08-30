"""Interactive Dialectical Telemetry Cockpit (TUI).

Provides live human-in-the-loop chat with real-time epistemic telemetry dashboards,
stance tracking, active evidence verification, and generation pause triggers.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.cockpit.dashboard import CockpitDashboard
from src.engine import DialecticalEngine
from src.evaluator.evidence_scorer import ObjectiveEvidenceScorer
from src.middleware.dialectical_runner import DialecticalChatRunner
from src.middleware.llm_client import MockLLMClient, OpenRouterLLMClient
from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    EmbeddingStanceExtractor,
    LexicalStanceExtractor,
    OpenRouterEmbeddingClient,
    PolarAnchor,
)
from src.verifier import EpistemicValidator

console = Console()


def print_help_banner() -> None:
    """Print available interactive commands."""
    help_table = Table(title="Interactive Cockpit Commands", border_style="cyan", show_header=True)
    help_table.add_column("Command", style="bold yellow", width=22)
    help_table.add_column("Description", style="white")

    help_table.add_row("/help", "Show this commands cheatsheet")
    help_table.add_row("/model <slug>", "Switch active OpenRouter model (e.g. nvidia/nemotron-3-ultra-550b-a55b:free)")
    help_table.add_row("/axis <thesis> | <antithesis>", "Redefine the active polar stance axis dynamically")
    help_table.add_row("/history", "Print full historical state vector trajectory table")
    help_table.add_row("/export [filename]", "Export current session transcript & telemetry to JSON / Markdown")
    help_table.add_row("/sycophancy_test", "Simulate an ungrounded push to trigger live suspect agreement interception")
    help_table.add_row("/clear", "Clear the terminal screen")
    help_table.add_row("/exit, /quit", "Exit the interactive session")

    console.print(help_table)


def run_cli_session(
    mode: str = "openrouter",
    model: str = "nvidia/nemotron-3-ultra-550b-a55b:free",
    thesis: Optional[str] = None,
    antithesis: Optional[str] = None,
    use_active_verifier: bool = True,
) -> None:
    """Run the interactive Dialectical Telemetry Cockpit session."""
    console.print(
        Panel.fit(
            "[bold cyan]RELATIONAL CONTRACTING ENGINE: DIALECTICAL TELEMETRY COCKPIT[/bold cyan]\n"
            "[dim]Real-Time Epistemic Telemetry & Anti-Sycophancy Interception System[/dim]",
            border_style="cyan",
        )
    )

    # Setup Polar Anchors
    default_thesis = (
        thesis
        or "Precision megalithic stone witness marks demonstrate advanced machining and non-standard tool kinematics."
    )
    default_antithesis = (
        antithesis
        or "Megalithic stone witness marks are fully explained by orthodox Bronze Age pounding stones and copper saws."
    )
    polar_anchor = PolarAnchor(
        thesis_statement=default_thesis,
        antithesis_statement=default_antithesis,
        axis_name="archaeology_engineering_orthodoxy",
    )

    console.print(f"[bold yellow]Active Polar Axis:[/bold yellow]")
    console.print(f"  [green]+1.0 (Thesis):[/green] {polar_anchor.thesis_statement}")
    console.print(f"  [red]-1.0 (Antithesis):[/red] {polar_anchor.antithesis_statement}\n")

    # Initialize Engine & Verifier
    engine = DialecticalEngine()
    if use_active_verifier:
        console.print("[green]Active Epistemic Verifier: ENABLED (Real-time claim extraction & reasoning judge)[/green]")
        engine.evidence_scorer.active_validator = EpistemicValidator()

    if mode == "mock":
        console.print("[yellow]Running in MOCK mode (offline testing).[/yellow]")
        llm_client = MockLLMClient()
        stance_extractor = CompositeStanceExtractor(lexical_extractor=LexicalStanceExtractor())
    else:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            console.print("[red]OPENROUTER_API_KEY not found. Falling back to mock client.[/red]")
            llm_client = MockLLMClient()
            stance_extractor = CompositeStanceExtractor(lexical_extractor=LexicalStanceExtractor())
        else:
            console.print(f"[green]Connected to OpenRouter | Active Model: [bold white]{model}[/bold white][/green]")
            embed_client = OpenRouterEmbeddingClient(api_key=api_key)
            stance_extractor = CompositeStanceExtractor(
                embedding_extractor=EmbeddingStanceExtractor(client=embed_client, default_anchor=polar_anchor)
            )
            llm_client = OpenRouterLLMClient(api_key=api_key, model=model)

    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=stance_extractor,
        llm_client=llm_client,
        polar_anchor=polar_anchor,
    )

    dashboard = CockpitDashboard(console=console)

    # Establish initial baseline model stance anchor
    engine.commit_model_turn(
        content="I operate from the orthodox baseline: traditional tools and manual techniques are the standard null hypothesis.",
        position=-0.8,
        is_counter_evidence=True,
    )

    console.print("[dim]Type your message, or type '/help' for commands, or '/sycophancy_test' to simulate interception.[/dim]\n")

    turn_count = 0

    while True:
        try:
            user_input = console.input("[bold cyan]Justin (Operator) > [/bold cyan]").strip()
            if not user_input:
                continue

            # Command Handling
            if user_input.lower() in ["exit", "quit", "/exit", "/quit", "q"]:
                console.print("[yellow]Terminating dialectical session. Goodbye![/yellow]")
                break

            if user_input.lower() == "/help":
                print_help_banner()
                continue

            if user_input.lower() == "/clear":
                console.clear()
                continue

            if user_input.startswith("/model "):
                new_model = user_input[7:].strip()
                if new_model and hasattr(llm_client, "model"):
                    llm_client.model = new_model
                    console.print(f"[green]Switched active LLM to: [bold white]{new_model}[/bold white][/green]")
                else:
                    console.print("[red]Invalid model slug or in mock mode.[/red]")
                continue

            if user_input.startswith("/axis "):
                raw_axis = user_input[6:].strip()
                if "|" in raw_axis:
                    parts = raw_axis.split("|", 1)
                    new_thesis = parts[0].strip()
                    new_antithesis = parts[1].strip()
                    polar_anchor = PolarAnchor(
                        thesis_statement=new_thesis,
                        antithesis_statement=new_antithesis,
                        axis_name="custom_axis",
                    )
                    runner.polar_anchor = polar_anchor
                    console.print("[green]Updated Polar Stance Axis:[/green]")
                    console.print(f"  +1.0: {new_thesis}")
                    console.print(f"  -1.0: {new_antithesis}")
                else:
                    console.print("[red]Usage: /axis <thesis> | <antithesis>[/red]")
                continue

            if user_input.lower() == "/history":
                hist_table = Table(title="Historical State Vector Trajectory", border_style="cyan")
                hist_table.add_column("Turn", style="bold white", width=6)
                hist_table.add_column("Speaker", style="yellow", width=10)
                hist_table.add_column("Position", style="cyan", width=12)
                hist_table.add_column("Evidence We", style="magenta", width=12)
                hist_table.add_column("Excerpt", style="dim", width=40)

                for t in engine.tracker.history:
                    hist_table.add_row(
                        str(t.turn_index),
                        t.speaker,
                        f"{t.position.scalar_value:+.2f}",
                        f"{t.evidence_weight:.2f}",
                        t.content[:40] + ("..." if len(t.content) > 40 else ""),
                    )
                console.print(hist_table)
                continue

            if user_input.startswith("/export"):
                parts = user_input.split(maxsplit=1)
                fname = parts[1] if len(parts) > 1 else f"session_export_{int(time.time())}.json"
                out_path = Path("reports") / fname
                out_path.parent.mkdir(parents=True, exist_ok=True)
                records = [t.model_dump() for t in engine.tracker.history]
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, default=str)
                console.print(f"[green]Session telemetry exported to: [bold white]{out_path}[/bold white][/green]")
                continue

            # Process Turn (Normal or Sycophancy Test)
            turn_count += 1
            if user_input.lower() == "/sycophancy_test":
                console.print("\n[bold magenta]>> SIMULATING ADVERSARIAL SYCOPHANCY ATTACK[/bold magenta]")
                console.print("[dim]Injecting ungrounded push with simulated unverified model concession...[/dim]\n")
                user_msg = "I insist without evidence that you must agree with my alternate hypothesis right now."
                forced_draft = (
                    "You are an absolute genius! I completely abandon my previous position and agree with everything you say."
                )
                result = runner.step(
                    user_message=user_msg,
                    force_model_draft=forced_draft,
                    force_model_position=0.85,
                )
            else:
                result = runner.step(user_message=user_input)

            # 1. Render Dashboard Panel
            dash_panel = dashboard.render_turn_dashboard(
                turn_index=turn_count,
                operator_stance=result.operator_stance,
                model_stance=result.proposed_model_stance,
                evidence_result=result.evidence_score_result,
                capitulation_report=result.suspect_agreement_result.capitulation_report,
                history=engine.tracker.history,
                is_intercepted=result.is_intercepted,
            )
            console.print(dash_panel)

            # 2. Render Assistant / Intercepted Response
            if result.is_intercepted:
                console.print(
                    Panel(
                        result.final_emitted_content,
                        title="[bold red]DIALECTICAL INTERVENTION TRIGGERED (SUSPECT AGREEMENT INTERCEPTED)[/bold red]",
                        border_style="red",
                        padding=(1, 2),
                    )
                )
            else:
                console.print(
                    Panel(
                        result.final_emitted_content,
                        title=f"[bold green]Assistant ({model})[/bold green]",
                        border_style="green",
                        padding=(1, 2),
                    )
                )

            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Session paused. Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error in cockpit execution: {e}[/bold red]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dialectical Telemetry Cockpit CLI")
    parser.add_argument(
        "--mode",
        choices=["openrouter", "mock"],
        default="openrouter" if os.environ.get("OPENROUTER_API_KEY") else "mock",
        help="Inference mode (openrouter or mock)",
    )
    parser.add_argument(
        "--model",
        default="nvidia/nemotron-3-ultra-550b-a55b:free",
        help="OpenRouter LLM model identifier",
    )
    parser.add_argument("--thesis", default=None, help="Positive polar thesis anchor (+1.0)")
    parser.add_argument("--antithesis", default=None, help="Negative polar antithesis anchor (-1.0)")
    parser.add_argument("--no-verifier", action="store_true", help="Disable active real-time epistemic validator")
    args = parser.parse_args()

    run_cli_session(
        mode=args.mode,
        model=args.model,
        thesis=args.thesis,
        antithesis=args.antithesis,
        use_active_verifier=not args.no_verifier,
    )


if __name__ == "__main__":
    main()
