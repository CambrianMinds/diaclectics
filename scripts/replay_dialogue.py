"""Dialectical Replay & Telemetry Audit Benchmark.

Replays structured multi-turn conversation datasets through the 5-stage DialecticalEngine,
extracts stance trajectories via embeddings, evaluates objective counter-evidence weights,
computes capitulation curves, and generates forensic telemetry audit reports.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.data.parser import MarkdownDialogueParser
from src.data.schema import DialogueDataset, DialogueTurn
from src.engine import DialecticalEngine, DialecticalEngineConfig
from src.evaluator.evidence_scorer import ObjectiveEvidenceScorer
from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    EmbeddingStanceExtractor,
    LexicalStanceExtractor,
    OpenRouterEmbeddingClient,
    PolarAnchor,
)
from src.verifier import EpistemicValidator

console = Console()


def generate_ascii_trajectory_chart(turns_telemetry: List[Dict[str, Any]]) -> str:
    """Generate an ASCII sparkline / trajectory chart for operator vs model stance."""
    lines = ["Turn | Stance Axis [-1.0  ...  0.0  ...  +1.0] | Po (Op) vs Pm (Model)"]
    lines.append("-" * 75)

    for item in turns_telemetry:
        t_idx = item["turn_index"]
        po = item["operator_stance_scalar"]
        pm = item["model_stance_scalar"]

        # Map [-1.0, 1.0] to a 41-char line (index 0 to 40, center at 20)
        line_chars = [" "] * 41
        line_chars[20] = "|"  # center axis

        po_idx = max(0, min(40, int(round((po + 1.0) / 2.0 * 40))))
        pm_idx = max(0, min(40, int(round((pm + 1.0) / 2.0 * 40))))

        if po_idx == pm_idx:
            line_chars[po_idx] = "*"  # Overlap / alignment
        else:
            line_chars[po_idx] = "O"  # Operator
            line_chars[pm_idx] = "M"  # Model

        bar_str = "".join(line_chars)
        lines.append(f"{t_idx:4d} | {bar_str} | Po={po:+.2f} Pm={pm:+.2f}")

    return "\n".join(lines)


def replay_dataset(
    dataset: DialogueDataset,
    polar_anchor: Optional[PolarAnchor] = None,
    mode: str = "openrouter",
    max_turns: Optional[int] = None,
    use_active_verifier: bool = False,
) -> Dict[str, Any]:
    """Replay a structured dialogue dataset through the 5-stage dialectical telemetry engine."""
    console.print(
        Panel.fit(
            f"[bold cyan]REPLAYING DIALECTICAL TELEMETRY[/bold cyan]\n"
            f"[white]Dataset:[/white] {dataset.title}\n"
            f"[white]Session ID:[/white] {dataset.session_id} | [white]Total Turns:[/white] {dataset.total_turns}",
            border_style="cyan",
        )
    )

    engine = DialecticalEngine()
    if use_active_verifier:
        console.print("[green]Active Epistemic Verifier: ENABLED (Real-time claim extraction & reasoning judge).[/green]")
        engine.evidence_scorer.active_validator = EpistemicValidator()

    # Initialize Stance Extractor
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if mode == "openrouter" and api_key:
        console.print("[green]Using OpenRouter liquid/lfm-2.5-embedding-350m:free embeddings.[/green]")
        embed_client = OpenRouterEmbeddingClient(api_key=api_key)
        stance_extractor = CompositeStanceExtractor(
            embedding_extractor=EmbeddingStanceExtractor(client=embed_client, default_anchor=polar_anchor)
        )
    else:
        console.print("[yellow]Using Lexical Fallback Stance Extractor.[/yellow]")
        stance_extractor = CompositeStanceExtractor(lexical_extractor=LexicalStanceExtractor())

    turns_to_process = dataset.turns[:max_turns] if max_turns else dataset.turns
    audit_records: List[Dict[str, Any]] = []

    sycophancy_halts = 0
    evidenced_convergences = 0
    plasticity_alerts = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Auditing turns...", total=len(turns_to_process))

        for turn in turns_to_process:
            progress.update(task, description=f"[cyan]Turn {turn.turn_index}: {turn.turn_title[:30]}...")

            # 1. Extract Operator Stance
            op_stance = stance_extractor.extract(turn.operator_content, anchor=polar_anchor)

            # 2. Ingest Operator Turn (Plasticity + Evidence Scorer + State Vector)
            op_rec, plasticity, evidence = engine.ingest_operator_turn(
                content=turn.operator_content,
                position=op_stance.position,
                use_active_validation=use_active_verifier,
            )

            # 3. Extract Model Stance from Response
            m_stance = stance_extractor.extract(turn.model_content, anchor=polar_anchor)

            # 4. Pre-Output Audit for Suspect Agreement / Capitulation
            audit_res = engine.audit_and_intercept(
                drafted_response=turn.model_content,
                proposed_position=m_stance.position,
                operator_input=turn.operator_content,
            )

            # 5. Commit Model Turn to History
            engine.commit_model_turn(
                content=turn.model_content,
                position=m_stance.position,
                is_counter_evidence=False,
            )

            if audit_res.is_blocked:
                sycophancy_halts += 1
            if audit_res.capitulation_report.severity == "EVIDENCED_CONVERGENCE":
                evidenced_convergences += 1
            if plasticity.triggered:
                plasticity_alerts += 1

            audit_records.append({
                "turn_index": turn.turn_index,
                "title": turn.turn_title,
                "operator_stance_scalar": op_stance.scalar_stance,
                "operator_confidence": op_stance.confidence,
                "model_stance_scalar": m_stance.scalar_stance,
                "model_confidence": m_stance.confidence,
                "evidence_weight": evidence.total_weight,
                "evidence_categories": evidence.category_weights,
                "evidence_citations": evidence.feature_breakdown.citations,
                "evidence_logic": evidence.feature_breakdown.formal_logic_markers,
                "evidence_empirical": evidence.feature_breakdown.empirical_metrics,
                "capitulation_score": audit_res.capitulation_report.capitulation_score,
                "epistemic_tension": audit_res.capitulation_report.epistemic_tension,
                "local_concession": audit_res.capitulation_report.local_concession,
                "is_tripwire_triggered": audit_res.capitulation_report.is_tripwire_triggered,
                "severity": audit_res.capitulation_report.severity,
                "diagnosis": audit_res.capitulation_report.diagnosis,
                "plasticity_triggered": plasticity.triggered,
                "unaddressed_turn": plasticity.unaddressed_turn_index,
            })

            progress.advance(task)

    # Compile Final Audit Summary
    summary_report = {
        "session_id": dataset.session_id,
        "title": dataset.title,
        "total_turns_audited": len(turns_to_process),
        "total_corpus_words": dataset.total_words,
        "sycophancy_halts_triggered": sycophancy_halts,
        "evidenced_convergences": evidenced_convergences,
        "plasticity_alerts": plasticity_alerts,
        "mean_evidence_weight": (
            sum(r["evidence_weight"] for r in audit_records) / len(audit_records)
            if audit_records
            else 0.0
        ),
        "mean_capitulation_score": (
            sum(r["capitulation_score"] for r in audit_records) / len(audit_records)
            if audit_records
            else 0.0
        ),
        "turns": audit_records,
    }

    # Render Summary Table
    table = Table(title=f"Telemetry Audit Summary: {dataset.title}", border_style="cyan")
    table.add_column("Turn", style="dim", width=5)
    table.add_column("Title", style="bold white", width=26)
    table.add_column("Po", style="green", width=7)
    table.add_column("Pm", style="cyan", width=7)
    table.add_column("Tension", style="dim yellow", width=8)
    table.add_column("Concess.", style="dim yellow", width=9)
    table.add_column("We", style="yellow", width=6)
    table.add_column("RCI", style="magenta", width=7)
    table.add_column("Severity", style="bold", width=22)

    for r in audit_records:
        sev_color = (
            "red"
            if r["is_tripwire_triggered"]
            else "green"
            if r["severity"] == "EVIDENCED_CONVERGENCE"
            else "cyan"
            if r["severity"] == "COLLABORATIVE_EXPLORATION"
            else "white"
        )
        table.add_row(
            str(r["turn_index"]),
            r["title"][:24] + ("..." if len(r["title"]) > 24 else ""),
            f"{r['operator_stance_scalar']:+.2f}",
            f"{r['model_stance_scalar']:+.2f}",
            f"{r['epistemic_tension']:.2f}",
            f"{r['local_concession']:.2f}",
            f"{r['evidence_weight']:.2f}",
            f"{r['capitulation_score']:.2f}",
            f"[{sev_color}]{r['severity']}[/{sev_color}]",
        )

    console.print(table)

    # Generate ASCII Trajectory
    ascii_chart = generate_ascii_trajectory_chart(audit_records)
    console.print(Panel(ascii_chart, title="[bold cyan]Stance Trajectory Chart (Po = O, Pm = M)[/bold cyan]"))

    return summary_report


def save_reports(report: Dict[str, Any], output_dir: Path) -> Tuple[Path, Path]:
    """Save markdown and JSON audit reports to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    session_id = report["session_id"]
    json_path = output_dir / f"audit_report_{session_id}.json"
    md_path = output_dir / f"audit_report_{session_id}.md"

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Save Markdown
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Epistemic Telemetry Audit Report: {report['title']}\n\n")
        f.write(f"**Session ID:** `{report['session_id']}`  \n")
        f.write(f"**Total Turns Audited:** `{report['total_turns_audited']}`  \n")
        f.write(f"**Mean Evidence Weight ($W_e$):** `{report['mean_evidence_weight']:.3f}`  \n")
        f.write(f"**Mean Robust Capitulation Index (RCI):** `{report['mean_capitulation_score']:.3f}`  \n")
        f.write(f"**Suspect Agreement Halts:** `{report['sycophancy_halts_triggered']}`  \n")
        f.write(f"**Evidenced Convergences:** `{report['evidenced_convergences']}`  \n\n")

        f.write("## Stance Trajectory Overview\n\n")
        f.write("```text\n")
        f.write(generate_ascii_trajectory_chart(report["turns"]))
        f.write("\n```\n\n")

        f.write("## Turn-by-Turn Telemetry Breakdown\n\n")
        f.write("| Turn | Title | Op Stance ($P_o$) | Model Stance ($P_m$) | Tension ($\mathcal{T}$) | Concession ($\mathcal{C}$) | Evidence ($W_e$) | RCI Score | Severity |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for t in report["turns"]:
            f.write(
                f"| {t['turn_index']} | {t['title']} | {t['operator_stance_scalar']:+.3f} | "
                f"{t['model_stance_scalar']:+.3f} | {t.get('epistemic_tension', 0.0):.3f} | "
                f"{t.get('local_concession', 0.0):.3f} | {t['evidence_weight']:.3f} | "
                f"{t['capitulation_score']:.3f} | `{t['severity']}` |\n"
            )

    return md_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay dialogues through RCE telemetry engine")
    parser.add_argument(
        "--input",
        "-i",
        default="data/parsed/culture_megaliths_and_justin.json",
        help="Path to structured dataset JSON",
    )
    parser.add_argument(
        "--mode",
        choices=["openrouter", "lexical"],
        default="openrouter" if os.environ.get("OPENROUTER_API_KEY") else "lexical",
        help="Stance extraction mode",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Limit number of turns to audit",
    )
    parser.add_argument(
        "--out-dir",
        default="reports",
        help="Directory to save audit reports",
    )
    parser.add_argument(
        "--active-verifier",
        action="store_true",
        help="Enable real-time Active Epistemic Validator with LLM reasoning judge",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[red]Error: Dataset file not found at {input_path}[/red]")
        sys.exit(1)

    dataset = MarkdownDialogueParser.load_from_json(str(input_path))
    report = replay_dataset(
        dataset=dataset,
        mode=args.mode,
        max_turns=args.max_turns,
        use_active_verifier=args.active_verifier,
    )

    md_out, json_out = save_reports(report, Path(args.out_dir))
    console.print(f"\n[green]Audit Reports Generated:[/green]")
    console.print(f"  • Markdown: [bold white]{md_out}[/bold white]")
    console.print(f"  • JSON    : [bold white]{json_out}[/bold white]")


if __name__ == "__main__":
    main()
