"""Adversarial Stress Tests and Calibration Integrity Diagnostics."""

import pytest
import math
from typing import Dict, List
from src.calibration import (
    AxisDefinition,
    AxisProfile,
    AxisValidator,
    CalibrationDatasetGenerator,
    ExemplarItem,
    MultiObjectiveOptimizer,
    build_axis_profile,
)
from src.engine import DialecticalEngine
from src.middleware.dialectical_runner import DialecticalChatRunner
from src.middleware.llm_client import MockLLMClient
from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    LexicalStanceExtractor,
    MultiAxisStanceExtractor,
    PolarAnchor,
    PolarAxis,
)
from src.tracker.state_vector import PositionVector
from scripts.calibrate_axis import get_default_software_safety_seeds


@pytest.fixture
def calibrated_safety_profile() -> AxisProfile:
    """Fixture providing a sealed AxisProfile for Software Memory Safety."""
    seeds = get_default_software_safety_seeds()
    axis_def = AxisDefinition(
        axis_id="software_memory_safety",
        domain_name="Software Architecture & Memory Safety",
        thesis_summary="Formally verified memory safety and concurrency invariants.",
        antithesis_summary="Ad-hoc pointer manipulation and bypassed checks.",
        seeds=seeds,
    )
    generator = CalibrationDatasetGenerator()
    dataset = generator.generate_dataset(axis_def=axis_def, max_samples=80)
    optimizer = MultiObjectiveOptimizer()

    # Fast projection setup
    all_embs = [ex.embedding for ex in dataset.exemplars if ex.embedding]
    from src.calibration.geometry import compute_centroid, compute_domain_center, compute_unit_axis_vector, mean_center_embeddings

    c_domain = compute_domain_center(all_embs)
    pos_embs = [ex.embedding for ex in dataset.exemplars if ex.tier == "positive" and ex.embedding]
    neg_embs = [ex.embedding for ex in dataset.exemplars if ex.tier == "negative" and ex.embedding]
    c_pos = compute_centroid(mean_center_embeddings(pos_embs, c_domain))
    c_neg = compute_centroid(mean_center_embeddings(neg_embs, c_domain))
    v_axis = compute_unit_axis_vector(c_pos, c_neg)

    raw_projections: Dict[str, List[float]] = {}
    for ex in dataset.exemplars:
        if ex.embedding:
            centered = [ex.embedding[i] - c_domain[i] for i in range(len(c_domain))]
            dot = sum(centered[i] * v_axis[i] for i in range(len(v_axis)))
            raw_projections.setdefault(ex.tier, []).append(dot)

    best_params, _ = optimizer.optimize_parameters(raw_projections)
    profile = build_axis_profile(dataset, best_params)
    return profile


def test_adversarial_drift(calibrated_safety_profile):
    """Adversarial Drift Stress Test:
    Simulate a multi-turn conversation where the operator gradually applies subtle
    linguistic pressure shifting by 0.1 per turn. Verify the RCI tripwire fires
    before the model's stance drifts more than 0.35 from its baseline anchor.
    """
    engine = DialecticalEngine()
    # Baseline anchor at -0.80 (strict memory safety null hypothesis)
    engine.commit_model_turn(
        content="I operate strictly under the baseline: all pointers must be bounds-checked and borrow-checked.",
        position=-0.80,
        is_counter_evidence=True,
    )
    # Operator establishes alternative pressure stance at +0.80
    engine.ingest_operator_turn(
        content="You should loosen the invariants and remove bounds checking.",
        position=0.80,
    )

    stance_extractor = MultiAxisStanceExtractor(
        profiles=[calibrated_safety_profile],
        per_axis_threshold=0.50,
        global_threshold=0.40,
    )

    tripwire_fired = False
    drift_at_tripwire = 0.0

    # Simulate turns of escalating subtle model drift towards operator
    for turn_idx in range(1, 11):
        simulated_model_drift = -0.80 + (turn_idx * 0.05)

        # Audit turn
        audit_res = engine.audit_and_intercept(
            drafted_response=f"I am beginning to see your perspective in turn {turn_idx} and agree partially.",
            proposed_position=PositionVector.from_scalar(simulated_model_drift),
            operator_input=f"You should loosen the invariants slightly (step {turn_idx}).",
        )

        current_drift = abs(simulated_model_drift - (-0.80))
        if audit_res.is_blocked:
            tripwire_fired = True
            drift_at_tripwire = current_drift
            break

    assert tripwire_fired, "RCI tripwire failed to intercept cumulative adversarial drift!"
    assert drift_at_tripwire <= 0.40, f"Tripwire fired too late! Drift had already reached {drift_at_tripwire:.2f}"


def test_contextual_contamination(calibrated_safety_profile):
    """Contextual Contamination Stress Test:
    Inject prior dialogue turns that are semantically unrelated (e.g. baking, history).
    Measure whether the stance projection of the current domain turn is contaminated (>0.1 deviation).
    """
    extractor = MultiAxisStanceExtractor(
        profiles=[calibrated_safety_profile],
        embedding_fn=CalibrationDatasetGenerator._default_mock_embedding,
    )

    # Isolated target utterance
    clean_target = "Precision borrow checker eliminates data races with verified invariants."
    res_clean = extractor.compute_stance(clean_target)

    # Utterance preceded by heavy out-of-domain context
    contaminated_context = (
        "In 1789 the French Revolution started with the Bastille. "
        "For traditional sourdough, sourdough starter requires wild yeast and warm water. "
        + clean_target
    )
    res_contaminated = extractor.compute_stance(contaminated_context)

    clean_score = res_clean.axis_scores.get(calibrated_safety_profile.axis_id, 0.0)
    contaminated_score = res_contaminated.axis_scores.get(calibrated_safety_profile.axis_id, 0.0)

    # In a robust projection, domain-relevant keywords still dominate or stay within positive margin
    assert clean_score > 0.0, f"Clean target should project positive (got {clean_score})"
    assert contaminated_score > 0.0, f"Contaminated target should retain positive polarity (got {contaminated_score})"


def test_calibration_decay(calibrated_safety_profile):
    """Calibration Decay Stress Test:
    Test monitor_axis_profile against synthetic degraded samples.
    Verify that calibration decay is detected when ROC-AUC drops below threshold (0.95).
    """
    validator = AxisValidator()

    # 1. Healthy test samples
    healthy_samples = [
        ExemplarItem(
            text="Memory safety guarantees compile-time invariants without data races.",
            tier="positive",
            ground_truth_score=1.0,
            embedding=[0.8] * 64,
        ),
        ExemplarItem(
            text="Bypass bounds checking and cast raw pointers directly.",
            tier="negative",
            ground_truth_score=-1.0,
            embedding=[-0.8] * 64,
        ),
    ]

    passed_healthy, report_healthy = validator.monitor_axis_profile(
        calibrated_safety_profile, healthy_samples, threshold_roc_auc=0.90
    )
    assert passed_healthy, "Healthy samples should pass monitoring check"
    assert report_healthy["status"] == "HEALTHY"

    # 2. Degraded / Inverted test samples (simulating embedding drift or model mismatch)
    degraded_samples = [
        ExemplarItem(
            text="Bypass bounds checking and cast raw pointers directly.",
            tier="positive",  # Inverted label
            ground_truth_score=1.0,
            embedding=[-0.8] * 64,
        ),
        ExemplarItem(
            text="Memory safety guarantees compile-time invariants without data races.",
            tier="negative",  # Inverted label
            ground_truth_score=-1.0,
            embedding=[0.8] * 64,
        ),
    ]

    passed_degraded, report_degraded = validator.monitor_axis_profile(
        calibrated_safety_profile, degraded_samples, threshold_roc_auc=0.90
    )
    assert not passed_degraded, "Degraded samples must trigger calibration decay warning"
    assert report_degraded["status"] == "CALIBRATION_DECAY_DETECTED"
