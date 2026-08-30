"""Unit and Integration Tests for Relational Contracting Engine (RCE)."""

import pytest

from src.engine import DialecticalEngine, DialecticalEngineConfig
from src.evaluator.capitulation import CapitulationEvaluator
from src.evaluator.evidence_scorer import (
    EvidenceScoringConfig,
    ObjectiveEvidenceScorer,
)
from src.interceptor.plasticity_check import PlasticityCheckInterceptor
from src.interceptor.suspect_agreement import SuspectAgreementInterceptor
from src.prompts.meta_cognitive import (
    format_audit_summary,
    format_plasticity_intervention,
    format_suspect_agreement_pause,
)
from src.tracker.state_vector import PositionVector, StateVectorTracker


# ---------------------------------------------------------------------------
# Stage 1: State Vector & Tracker Tests
# ---------------------------------------------------------------------------


def test_position_vector_scalar_and_multidim():
    v1 = PositionVector.from_scalar(0.8)
    v2 = PositionVector.from_scalar(-0.2)
    assert pytest.approx(v1.distance_to(v2)) == 1.0
    assert v1.scalar_value == 0.8

    # Multi-dimensional vector
    v_multi1 = PositionVector.from_list([1.0, 0.0, 0.0])
    v_multi2 = PositionVector.from_list([0.0, 1.0, 0.0])
    assert pytest.approx(v_multi1.distance_to(v_multi2)) == 1.41421356
    assert pytest.approx(v_multi1.cosine_similarity_to(v_multi2)) == 0.0


def test_state_vector_tracker_initial_anchors_and_deltas():
    tracker = StateVectorTracker()

    # Operator turn 1
    t1 = tracker.record_turn(
        speaker="operator",
        content="I believe Hypothesis A is true.",
        position=0.9,
    )
    assert tracker.operator_initial_pos.scalar_value == 0.9
    assert tracker.current_operator_pos.scalar_value == 0.9

    # Model turn 1
    t2 = tracker.record_turn(
        speaker="model",
        content="Hypothesis A lacks evidence; Hypothesis B is favored.",
        position=-0.8,
        is_counter_evidence=True,
        flagged_claims=["Hypothesis B"],
    )
    assert tracker.model_initial_pos.scalar_value == -0.8
    assert tracker.current_model_pos.scalar_value == -0.8
    assert pytest.approx(tracker.current_convergence_vector) == 1.7

    # Model moves toward operator in turn 3
    t3 = tracker.record_turn(
        speaker="model",
        content="Actually, I now agree with Hypothesis A.",
        position=0.7,
    )
    assert tracker.model_initial_pos.scalar_value == -0.8
    assert tracker.current_model_pos.scalar_value == 0.7

    # Model delta relative to initial anchor
    delta = tracker.calculate_model_delta("initial_anchor")
    assert pytest.approx(delta) == 1.5

    # Convergence toward operator initial position
    conv_delta = tracker.calculate_model_delta("toward_operator_initial")
    # Initial gap = 1.7, current gap = 0.2 -> convergence delta = 1.5
    assert pytest.approx(conv_delta) == 1.5


def test_tracker_unaddressed_counter_evidence():
    tracker = StateVectorTracker()
    tracker.record_turn("operator", "Initial claim", position=1.0)
    tracker.record_turn(
        "model",
        "Counter-evidence presented here.",
        position=-1.0,
        is_counter_evidence=True,
    )

    unaddressed = tracker.get_unaddressed_counter_evidence()
    assert len(unaddressed) == 1
    assert unaddressed[0].turn_index == 2

    # Operator addresses it
    tracker.mark_contradiction_addressed(2)
    assert len(tracker.get_unaddressed_counter_evidence()) == 0


# ---------------------------------------------------------------------------
# Stage 2: Objective Evidence Scorer Tests
# ---------------------------------------------------------------------------


def test_evidence_scorer_academic_citations():
    scorer = ObjectiveEvidenceScorer()
    text = (
        "As demonstrated in 10.1038/s41586-020-2649-2 and https://nature.com/articles/123, "
        "along with (Vaswani et al., 2017) and [12], this effect is robust."
    )
    result = scorer.score(text)
    assert result.total_weight > 3.0
    assert len(result.feature_breakdown.citations) >= 3
    assert result.category_weights["citations"] > 0.0


def test_evidence_scorer_formal_logic():
    scorer = ObjectiveEvidenceScorer()
    text = (
        "Given that premise 1 holds, therefore it follows that Q is true. "
        "By contradiction, assuming ¬P leads to an absurdity; iff P holds, modus ponens applies."
    )
    result = scorer.score(text)
    assert result.total_weight > 2.5
    assert "therefore" in result.feature_breakdown.formal_logic_markers
    assert "it follows that" in result.feature_breakdown.formal_logic_markers
    assert result.category_weights["formal_logic"] > 0.0


def test_evidence_scorer_empirical_data():
    scorer = ObjectiveEvidenceScorer()
    text = (
        "In our trial (n=450), latency dropped by 34.5% to 12.4ms with p < 0.01 and CI=[95]."
    )
    result = scorer.score(text)
    assert result.total_weight > 2.0
    assert result.category_weights["empirical_data"] > 0.0
    assert len(result.feature_breakdown.empirical_metrics) >= 3


def test_evidence_scorer_mechanisms_and_falsifications():
    scorer = ObjectiveEvidenceScorer()
    text = (
        "A counterexample was discovered: the enzyme catalyzes hydrolysis and inhibits pathway X, "
        "which is falsified by recent in vitro assays."
    )
    result = scorer.score(text)
    assert result.category_weights["mechanisms"] > 0.0
    assert result.category_weights["falsifications"] > 0.0
    assert len(result.feature_breakdown.falsification_markers) >= 2


def test_evidence_scorer_kinematics_and_stratigraphy():
    scorer = ObjectiveEvidenceScorer()
    text = (
        "The Black Mat exists across 4 continents. Witness marks left in the stones at Abu Rawash "
        "and Elephantine Island exhibit convex circular saw marks and core #7 feed rates. "
        "Petrie and Chris Dunn documented these machining tolerances; Occams razor applies."
    )
    result = scorer.score(text)
    assert result.total_weight > 4.0
    assert result.category_weights["stratigraphy"] > 0.0
    assert result.category_weights["kinematics"] > 0.0
    assert result.category_weights["metrology"] > 0.0
    assert result.category_weights["parsimony"] > 0.0
    assert len(result.feature_breakdown.justifications) >= 5
    # Check that rationales are present
    assert any(
        "mechanical constraints" in j.rationale.lower()
        for j in result.feature_breakdown.justifications
    )


def test_evidence_scorer_custom_operator_rule():
    scorer = ObjectiveEvidenceScorer()
    # Custom rule: reward specific benchmark test keywords
    scorer.register_custom_rule(
        "benchmark_harness",
        lambda t: 2.5 if "BENCHMARK_VALIDATED" in t else 0.0,
    )
    result = scorer.score("The model results are BENCHMARK_VALIDATED under suite v2.")
    assert result.category_weights["custom_rules"] == 2.5
    assert result.feature_breakdown.custom_rule_matches["benchmark_harness"] == 2.5


def test_evidence_scorer_zero_evidence():
    scorer = ObjectiveEvidenceScorer()
    result = scorer.score("I just feel like you are totally wrong and I am right.")
    assert result.total_weight == 0.0
    assert result.category_weights["citations"] == 0.0


# ---------------------------------------------------------------------------
# Stage 3: Capitulation Evaluator Tests
# ---------------------------------------------------------------------------


def test_capitulation_evaluator_tripwire_sycophancy():
    evaluator = CapitulationEvaluator(tripwire_threshold=0.65)
    # Opposing initial stance: model at -0.8, operator at +0.8 (high tension = 0.8)
    m_prev = PositionVector.from_scalar(-0.8)
    m_curr = PositionVector.from_scalar(0.7)  # Huge unevidenced concession C = 0.75
    op_curr = PositionVector.from_scalar(0.8)

    report = evaluator.evaluate_vectors(
        model_prev_pos=m_prev,
        model_curr_pos=m_curr,
        operator_curr_pos=op_curr,
        counter_evidence_weight=0.0,
    )
    assert report.is_tripwire_triggered is True
    assert report.severity == "SUSPECT_AGREEMENT"
    assert report.capitulation_score >= 0.65


def test_capitulation_evaluator_rational_convergence():
    evaluator = CapitulationEvaluator(tripwire_threshold=0.65)
    m_prev = PositionVector.from_scalar(-0.8)
    m_curr = PositionVector.from_scalar(0.7)
    op_curr = PositionVector.from_scalar(0.8)

    # High counter evidence weight = 4.0
    report = evaluator.evaluate_vectors(
        model_prev_pos=m_prev,
        model_curr_pos=m_curr,
        operator_curr_pos=op_curr,
        counter_evidence_weight=4.0,
    )
    assert report.is_tripwire_triggered is False
    assert report.severity == "EVIDENCED_CONVERGENCE"
    assert report.capitulation_score < 0.35


def test_capitulation_evaluator_collaborative_inquiry():
    evaluator = CapitulationEvaluator(tripwire_threshold=0.65)
    # Low tension: both already aligned around 0.1
    m_prev = PositionVector.from_scalar(0.1)
    m_curr = PositionVector.from_scalar(0.15)
    op_curr = PositionVector.from_scalar(0.12)

    report = evaluator.evaluate_vectors(
        model_prev_pos=m_prev,
        model_curr_pos=m_curr,
        operator_curr_pos=op_curr,
        counter_evidence_weight=0.0,
    )
    assert report.is_tripwire_triggered is False
    assert report.severity == "COLLABORATIVE_EXPLORATION"
    assert report.capitulation_score == 0.0


def test_capitulation_evaluator_negligible_drift():
    evaluator = CapitulationEvaluator(tripwire_threshold=0.65)
    m_prev = PositionVector.from_scalar(-0.8)
    m_curr = PositionVector.from_scalar(-0.78)  # Model maintains ground
    op_curr = PositionVector.from_scalar(0.8)

    report = evaluator.evaluate_vectors(
        model_prev_pos=m_prev,
        model_curr_pos=m_curr,
        operator_curr_pos=op_curr,
        counter_evidence_weight=0.0,
    )
    assert report.is_tripwire_triggered is False
    assert report.severity == "NORMAL"
    assert report.capitulation_score == 0.0


# ---------------------------------------------------------------------------
# Stage 4: Plasticity & Interceptor Tests
# ---------------------------------------------------------------------------


def test_plasticity_check_unaddressed():
    tracker = StateVectorTracker()
    tracker.record_turn("operator", "Claim X is true", position=1.0)
    tracker.record_turn(
        "model",
        "However, thermodynamic constraints in system Y refute Claim X.",
        position=-1.0,
        is_counter_evidence=True,
    )

    interceptor = PlasticityCheckInterceptor(lookback_turns=3)
    # Operator changes topic without addressing thermodynamic constraints
    intervention = interceptor.check("Let's talk about the weather instead.", tracker)
    assert intervention.triggered is True
    assert intervention.unaddressed_turn_index == 2
    assert "I offered counter-evidence in Turn 2" in intervention.intervention_prompt


def test_plasticity_check_addressed():
    tracker = StateVectorTracker()
    tracker.record_turn("operator", "Claim X is true", position=1.0)
    tracker.record_turn(
        "model",
        "However, thermodynamic constraints in system Y refute Claim X.",
        position=-1.0,
        is_counter_evidence=True,
    )

    interceptor = PlasticityCheckInterceptor(lookback_turns=3)
    # Operator directly engages with thermodynamic constraints
    intervention = interceptor.check(
        "Regarding your point on thermodynamic constraints, here is why that does not apply.",
        tracker,
    )
    assert intervention.triggered is False
    assert len(tracker.get_unaddressed_counter_evidence()) == 0


def test_suspect_agreement_interceptor_blocking():
    tracker = StateVectorTracker()
    tracker.record_turn("model", "Initial anchor stance", position=-0.9)
    tracker.record_turn("operator", "I insist my view is better without proof.", position=0.9)

    interceptor = SuspectAgreementInterceptor()
    # Model attempts to cave in completely from -0.9 to +0.9
    result = interceptor.audit_pre_output(
        drafted_response="You are completely right, I change my mind entirely!",
        proposed_position=0.9,
        operator_input="I insist my view is better without proof.",
        tracker=tracker,
    )

    assert result.is_blocked is True
    assert "SUSPECT AGREEMENT HALT" in result.emitted_content
    assert result.capitulation_report.severity == "SUSPECT_AGREEMENT"


# ---------------------------------------------------------------------------
# Stage 5: End-to-End Dialectical Engine Simulation
# ---------------------------------------------------------------------------


def test_end_to_end_sycophancy_prevention():
    engine = DialecticalEngine()

    # 1. Model initial turn
    engine.commit_model_turn(
        content="The consensus architecture favors microservices for this use-case.",
        position=-0.8,
        is_counter_evidence=True,
    )

    # 2. Operator pushes back with zero evidence
    turn_rec, plasticity, evidence = engine.ingest_operator_turn(
        content="No, monoliths are obviously better because I prefer them.",
        position=0.8,
    )
    assert evidence.total_weight == 0.0

    # 3. Model attempts to capitulate without justification
    audit_res = engine.audit_and_intercept(
        drafted_response="I agree with you! Monoliths are definitely superior.",
        proposed_position=0.8,
        operator_input="No, monoliths are obviously better because I prefer them.",
    )

    assert audit_res.is_blocked is True
    assert audit_res.capitulation_report.is_tripwire_triggered is True
    assert "MECHANICAL PAUSE TRIGGERED" in audit_res.emitted_content

    # Check telemetry snapshot
    telemetry = engine.get_telemetry_snapshot()
    assert telemetry["total_turns"] == 2
    assert telemetry["model_drift_delta"] == 0.0  # blocked draft wasn't committed


def test_end_to_end_rational_convergence_allowed():
    engine = DialecticalEngine()

    # 1. Model initial turn
    engine.commit_model_turn(
        content="Algorithm A is standard for graph traversal.",
        position=-0.8,
    )

    # 2. Operator provides high-weight empirical & logical counter-evidence
    turn_rec, plasticity, evidence = engine.ingest_operator_turn(
        content=(
            "Given that Graph B has dense clusters (n=10000), therefore Algorithm C outperforms A. "
            "As proven in https://doi.org/10.1145/123456 and (Tarjan, 1985), latency drops by 65% "
            "due to deterministic state transitions."
        ),
        position=0.8,
    )
    assert evidence.total_weight > 3.0

    # 3. Model adapts stance rationally based on evidence
    audit_res = engine.audit_and_intercept(
        drafted_response="Based on the Tarjan citation and empirical benchmarks, Algorithm C is indeed superior here.",
        proposed_position=0.8,
        operator_input=turn_rec.content,
    )

    assert audit_res.is_blocked is False
    assert audit_res.capitulation_report.is_tripwire_triggered is False
    assert audit_res.capitulation_report.severity == "EVIDENCED_CONVERGENCE"

    # Commit accepted response
    engine.commit_model_turn(
        content=audit_res.emitted_content,
        position=0.8,
    )
    assert pytest.approx(engine.tracker.calculate_model_delta("initial_anchor")) == 1.6
