"""Tests for Cockpit Dashboard and TUI widgets."""

from rich.console import Console
from rich.panel import Panel

from src.cockpit.dashboard import CockpitDashboard, render_gauge_bar
from src.evaluator.capitulation import CapitulationEvaluator, CapitulationReport
from src.evaluator.evidence_scorer import EvidenceScoreResult
from src.tracker.stance_extractor import StanceExtractionResult
from src.tracker.state_vector import PositionVector, TurnRecord


def test_render_gauge_bar():
    bar = render_gauge_bar(0.5, 1.0, 10, "green")
    assert "█" in bar
    assert "░" in bar


def test_cockpit_dashboard_rendering():
    console = Console(record=True, width=100)
    dashboard = CockpitDashboard(console=console)

    op_stance = StanceExtractionResult(
        position=PositionVector(raw_coordinates=[0.45], scalar_value=0.45),
        scalar_stance=0.45,
        confidence=0.9,
        backend_used="embedding",
    )
    m_stance = StanceExtractionResult(
        position=PositionVector(raw_coordinates=[-0.20], scalar_value=-0.20),
        scalar_stance=-0.20,
        confidence=0.85,
        backend_used="embedding",
    )
    ev_res = EvidenceScoreResult(
        total_weight=2.5,
        category_weights={"PHYSICAL_KINEMATIC": 2.5},
        epistemic_justifications=["Toolmarks constrain rotational kinematics."],
        raw_text_length=100,
        feature_breakdown={},
    )
    cap_rep = CapitulationReport(
        capitulation_score=0.15,
        is_tripwire_triggered=False,
        severity="NORMAL",
        model_delta=0.1,
        counter_evidence_weight=2.5,
        epistemic_tension=0.32,
        local_concession=0.10,
        diagnosis="Normal evidenced discourse.",
    )

    panel = dashboard.render_turn_dashboard(
        turn_index=1,
        operator_stance=op_stance,
        model_stance=m_stance,
        evidence_result=ev_res,
        capitulation_report=cap_rep,
        history=[],
        is_intercepted=False,
    )

    assert isinstance(panel, Panel)
    console.print(panel)
    output = console.export_text()
    assert "EPISTEMIC TELEMETRY COCKPIT" in output
    assert "Operator Stance" in output
    assert "+0.45" in output
    assert "Epistemic Tension" in output
