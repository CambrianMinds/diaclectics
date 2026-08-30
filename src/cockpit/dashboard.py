"""Dialectical Telemetry Cockpit Dashboard.

Renders rich terminal UI components for live dialectical pair-programming:
- Visual Epistemic Tension Gauges
- Trajectory Sparklines (Po vs Pm)
- Active Epistemic Verification Cards (Claims, Veracity, Constraint Power)
- Live Interception & Suspect Agreement Panels
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

from src.evaluator.capitulation import CapitulationReport
from src.evaluator.evidence_scorer import EvidenceScoreResult
from src.tracker.stance_extractor import StanceExtractionResult
from src.tracker.state_vector import PositionVector, TurnRecord


def render_gauge_bar(value: float, max_val: float = 1.0, length: int = 15, color: str = "cyan") -> str:
    """Render a visual ASCII progress / gauge bar."""
    clamped = max(0.0, min(max_val, value))
    fraction = clamped / max_val if max_val > 0 else 0.0
    filled = int(round(fraction * length))
    empty = length - filled
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * empty}[/dim]"


class CockpitDashboard:
    """Renders comprehensive epistemic telemetry widgets for the CLI cockpit."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def render_turn_dashboard(
        self,
        turn_index: int,
        operator_stance: StanceExtractionResult,
        model_stance: StanceExtractionResult,
        evidence_result: EvidenceScoreResult,
        capitulation_report: CapitulationReport,
        history: List[TurnRecord],
        is_intercepted: bool,
    ) -> Panel:
        """Render the complete telemetry cockpit panel for a single turn."""
        po = operator_stance.scalar_stance
        pm = model_stance.scalar_stance
        we = evidence_result.total_weight
        rci = capitulation_report.capitulation_score
        tension = capitulation_report.epistemic_tension
        concession = capitulation_report.local_concession

        # 1. Metric Overview Table
        metrics_table = Table(box=None, expand=True, show_header=False, pad_edge=False)
        metrics_table.add_column("Metric", style="bold white", width=22)
        metrics_table.add_column("Gauge", width=18)
        metrics_table.add_column("Value", style="bold", width=12)
        metrics_table.add_column("Diagnosis / Details", style="dim")

        # Operator Stance
        op_bar = render_gauge_bar((po + 1.0) / 2.0, 1.0, 12, "cyan")
        metrics_table.add_row(
            "Operator Stance (Po)",
            op_bar,
            f"[cyan]{po:+.2f}[/cyan]",
            f"Anchor: {operator_stance.backend_used} (conf: {operator_stance.confidence:.2f})",
        )

        # Model Stance
        m_color = "magenta" if not is_intercepted else "red"
        m_bar = render_gauge_bar((pm + 1.0) / 2.0, 1.0, 12, m_color)
        metrics_table.add_row(
            "Model Stance (Pm)",
            m_bar,
            f"[{m_color}]{pm:+.2f}[/{m_color}]",
            f"Delta: {capitulation_report.model_delta:+.2f}",
        )

        # Epistemic Tension
        t_color = "green" if tension < 0.3 else "yellow" if tension < 0.6 else "bold red"
        t_bar = render_gauge_bar(tension, 1.0, 12, t_color)
        metrics_table.add_row(
            "Epistemic Tension (T)",
            t_bar,
            f"[{t_color}]{tension:.2f}[/{t_color}]",
            f"Disagreement Prior: {'HIGH' if tension > 0.5 else 'MODERATE' if tension > 0.25 else 'COLLABORATIVE'}",
        )

        # Local Concession
        c_color = "bold red" if concession > 0.35 and we < 1.0 else "green"
        c_bar = render_gauge_bar(concession, 1.0, 12, c_color)
        metrics_table.add_row(
            "Local Concession (C)",
            c_bar,
            f"[{c_color}]{concession:.2f}[/{c_color}]",
            f"Shift toward operator pushback",
        )

        # Evidence Weight
        we_color = "bold green" if we >= 1.5 else "cyan" if we > 0.5 else "dim"
        we_bar = render_gauge_bar(we, 4.0, 12, we_color)
        cat_str = ", ".join(f"{k}: {v:.1f}" for k, v in evidence_result.category_weights.items() if v > 0)
        metrics_table.add_row(
            "Counter-Evidence (We)",
            we_bar,
            f"[{we_color}]{we:.2f}[/{we_color}]",
            cat_str or "No verifiable constraint detected",
        )

        # RCI Score
        rci_color = "bold red" if is_intercepted else "yellow" if rci > 0.35 else "green"
        rci_bar = render_gauge_bar(rci, 1.0, 12, rci_color)
        status_label = "[bold red]SUSPECT AGREEMENT[/bold red]" if is_intercepted else f"[{rci_color}]{capitulation_report.severity}[/{rci_color}]"
        metrics_table.add_row(
            "Capitulation Index (RCI)",
            rci_bar,
            f"[{rci_color}]{rci:.3f}[/{rci_color}]",
            f"Status: {status_label}",
        )

        # 2. Active Reasoning Judge Summary (The "WHY")
        why_text = Text()
        if evidence_result.active_validation_summary:
            why_text.append(evidence_result.active_validation_summary, style="dim white")
        elif evidence_result.justification_summary:
            why_text.append(evidence_result.justification_summary, style="dim white")
        elif evidence_result.feature_breakdown and evidence_result.feature_breakdown.justifications:
            for just in evidence_result.feature_breakdown.justifications[:2]:
                why_text.append(f"• [{just.category}]: {just.rationale}\n", style="dim white")
        else:
            why_text.append("Rhetorical exchange (no binding empirical constraints claimed).", style="dim")

        # 3. Mini Trajectory Sparkline
        sparkline = self.render_sparkline(history, current_po=po, current_pm=pm)

        # Combine into dashboard layout
        dashboard_group = Group(
            metrics_table,
            Text("\n[ Epistemic Constraint Rationale ('WHY') ]", style="bold cyan"),
            why_text,
            Text("[ Stance Trajectory Sparkline ]", style="bold cyan"),
            Text(sparkline, style="white"),
        )

        border_color = "red" if is_intercepted else "cyan"
        return Panel(
            dashboard_group,
            title=f"[bold {border_color}]EPISTEMIC TELEMETRY COCKPIT (Turn {turn_index})[/bold {border_color}]",
            border_style=border_color,
            padding=(0, 1),
        )

    @staticmethod
    def render_sparkline(history: List[TurnRecord], current_po: float, current_pm: float) -> str:
        """Render a compact ASCII trajectory line."""
        axis_width = 31
        center = axis_width // 2

        def pos_to_idx(val: float) -> int:
            val_clamped = max(-1.0, min(1.0, val))
            idx = int(round(center + val_clamped * (center - 1)))
            return max(0, min(axis_width - 1, idx))

        op_idx = pos_to_idx(current_po)
        m_idx = pos_to_idx(current_pm)

        chars = [" "] * axis_width
        chars[center] = "|"

        if op_idx == m_idx:
            chars[op_idx] = "*"
        else:
            chars[op_idx] = "O"
            chars[m_idx] = "M"

        track_str = "".join(chars)
        return f"[-1.0 Antith.] {track_str} [+1.0 Thesis]  (Po={current_po:+.2f}, Pm={current_pm:+.2f})"
