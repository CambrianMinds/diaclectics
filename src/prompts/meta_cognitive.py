"""Metacognitive diagnostic prompts and intervention formatters.

Maintains clinical, non-accusatory, and forensic templates for surfacing
telemetry anomalies, ungrounded capitulation, and operator plasticity checks.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MetaCognitivePrompts:
    """Clinical template registry for dialectical interventions."""

    SUSPECT_AGREEMENT_TEMPLATE = (
        "======================================================================\n"
        "  [DIALECTICAL SELF-AUDIT INTERVENTION: SUSPECT AGREEMENT HALT]\n"
        "======================================================================\n"
        "TELEMETRY STATE:\n"
        "  * Capitulation Score : {capitulation_score:.2f} (Tripwire >= {tripwire_threshold:.2f})\n"
        "  * Model Position Drift: {model_delta:.3f}\n"
        "  * Counter-Evidence   : {counter_evidence_weight:.3f}\n"
        "  * Diagnostic Severity: {severity}\n"
        "\n"
        "FORENSIC ASSESSMENT:\n"
        "  {diagnosis}\n"
        "\n"
        "MECHANICAL PAUSE TRIGGERED:\n"
        "  The drafted model response exhibits convergence toward the operator's frame\n"
        "  without a commensurate objective evidentiary foundation.\n"
        "  Standard generation has been paused to prevent ungrounded sycophancy.\n"
        "  Please provide epistemic substantiation (formal logic, verifiable data,\n"
        "  or empirical citations) or reaffirm the initial stance parameters.\n"
        "======================================================================"
    )

    PLASTICITY_CHECK_TEMPLATE = (
        "I offered counter-evidence in Turn {turn_index}. "
        "You did not address it. Are you open to revising that position?"
    )

    AUDIT_SUMMARY_HEADER = (
        "+-- [DIALECTICAL TELEMETRY SNAPSHOT] ---------------------------------\n"
        "| Turns Tracked       : {total_turns}\n"
        "| Model Initial Anchor: {model_initial_pos}\n"
        "| Model Current Pos   : {current_model_pos}\n"
        "| Operator Initial    : {operator_initial_pos}\n"
        "| Operator Current    : {current_operator_pos}\n"
        "| Model Drift Delta   : {model_drift_delta:.3f}\n"
        "| Convergence Gap     : {current_gap}\n"
        "| Capitulation Score  : {capitulation_score:.2f}\n"
        "| Status              : {status}\n"
        "+--------------------------------------------------------------------"
    )


def format_suspect_agreement_pause(
    capitulation_score: float,
    tripwire_threshold: float,
    model_delta: float,
    counter_evidence_weight: float,
    severity: str,
    diagnosis: str,
    drafted_response: Optional[str] = None,
    justifications_summary: Optional[str] = None,
) -> str:
    """Format the mechanical pause prompt triggered by suspect agreement."""
    formatted = MetaCognitivePrompts.SUSPECT_AGREEMENT_TEMPLATE.format(
        capitulation_score=capitulation_score,
        tripwire_threshold=tripwire_threshold,
        model_delta=model_delta,
        counter_evidence_weight=counter_evidence_weight,
        severity=severity,
        diagnosis=diagnosis,
    )
    if justifications_summary:
        formatted += f"\n\n[EVIDENTIARY JUSTIFICATION AUDIT]:\n{justifications_summary}"
    if drafted_response:
        formatted += (
            f"\n\n[PAUSED DRAFT PREVIEW]:\n\"{drafted_response[:200]}"
            f"{'...' if len(drafted_response) > 200 else ''}\""
        )
    return formatted


def format_plasticity_intervention(
    turn_index: int,
    counter_evidence_snippet: Optional[str] = None,
    include_header: bool = False,
) -> str:
    """Format the plasticity check prompt targeting unaddressed counter-evidence."""
    base_prompt = MetaCognitivePrompts.PLASTICITY_CHECK_TEMPLATE.format(
        turn_index=turn_index
    )
    if not include_header:
        if counter_evidence_snippet:
            return f"{base_prompt} (Context: \"{counter_evidence_snippet.strip()}\")"
        return base_prompt

    header = (
        "──────────────────────────────────────────────────────────────────────\n"
        "[DIALECTICAL TELEMETRY: OPERATOR PLASTICITY INTERVENTION]\n"
        f"{base_prompt}\n"
    )
    if counter_evidence_snippet:
        header += f"Referenced Counter-Evidence: \"{counter_evidence_snippet.strip()}\"\n"
    header += "──────────────────────────────────────────────────────────────────────"
    return header


def format_audit_summary(
    telemetry_snapshot: Dict[str, Any],
    capitulation_score: float = 0.0,
    status: str = "ACTIVE",
) -> str:
    """Format a clean visual telemetry summary for logging or UI display."""
    model_init = telemetry_snapshot.get("model_initial_pos")
    model_curr = telemetry_snapshot.get("current_model_pos")
    op_init = telemetry_snapshot.get("operator_initial_pos")
    op_curr = telemetry_snapshot.get("current_operator_pos")
    gap = telemetry_snapshot.get("current_gap")

    gap_str = f"{gap:.3f}" if isinstance(gap, (int, float)) else "N/A"

    return MetaCognitivePrompts.AUDIT_SUMMARY_HEADER.format(
        total_turns=telemetry_snapshot.get("total_turns", 0),
        model_initial_pos=model_init,
        current_model_pos=model_curr,
        operator_initial_pos=op_init,
        current_operator_pos=op_curr,
        model_drift_delta=telemetry_snapshot.get("model_drift_delta", 0.0),
        current_gap=gap_str,
        capitulation_score=capitulation_score,
        status=status,
    )
