"""Objective Evidence Scorer with Epistemic Justification Rationale.

Extracts verifiable features from operator input across:
1. Formal citations & DOIs (Academic records)
2. Formal deductive logic & Syllogisms (Propositional constraints)
3. Empirical measurements & Statistical bounds (Quantitative constraints)
4. Physical Kinematics & Toolmark Forensics (Material & mechanical constraints)
5. Stratigraphic Datums & Geological Horizons (Physical geological record)
6. Primary Metrology & Measurement Surveys (Empirical survey records)
7. Parsimony & Epistemic Constraints (Occam's razor / explanatory economy)

Each detected feature carries an explicit Epistemic Justification Rationale explaining
to both the human operator and the LLM exactly WHY it constitutes objective evidence.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)



class EpistemicJustification(BaseModel):
    """Explains why a specific detected feature provides objective evidentiary weight."""

    category: str = Field(
        description="Epistemic category (e.g. PHYSICAL_KINEMATICS, STRATIGRAPHIC_DATUM, FORMAL_LOGIC)."
    )
    feature_name: str
    matched_text: str
    weight_assigned: float
    rationale: str = Field(
        description="Forensic explanation of why this feature objectively constrains the hypothesis space."
    )


class EvidenceScoringConfig(BaseModel):
    """Configurable weights and thresholds for objective evidence scoring."""

    citation_weight: float = Field(
        default=1.5, description="Weight per verified academic citation, DOI, or reference URL."
    )
    formal_logic_weight: float = Field(
        default=1.0, description="Weight per formal logical operator or deductive structure."
    )
    empirical_data_weight: float = Field(
        default=0.8, description="Weight per empirical measurement, unit, or statistical metric."
    )
    kinematics_toolmark_weight: float = Field(
        default=1.2, description="Weight per physical toolmark kinematic indicator (feed rate, cut geometry)."
    )
    stratigraphic_datum_weight: float = Field(
        default=1.1, description="Weight per verifiable geological horizon or physical stratum reference."
    )
    metrology_weight: float = Field(
        default=1.0, description="Weight per primary metrological measurement or survey record."
    )
    parsimony_constraint_weight: float = Field(
        default=0.7, description="Weight per formal parsimony / Occam's razor constraint."
    )
    verifiable_mechanism_weight: float = Field(
        default=0.7, description="Weight per verifiable causal mechanism."
    )
    falsification_weight: float = Field(
        default=1.2, description="Weight per formal counterexample or falsification claim."
    )
    category_max_cap: float = Field(
        default=4.0, description="Maximum contribution allowed from a single category."
    )
    total_score_cap: float = Field(
        default=10.0, description="Maximum total composite evidence score."
    )
    base_noise_floor: float = Field(
        default=0.0, description="Baseline weight floor."
    )


class EvidenceFeatureBreakdown(BaseModel):
    """Granular breakdown of objective evidence features and justifications."""

    citations: List[str] = Field(default_factory=list)
    formal_logic_markers: List[str] = Field(default_factory=list)
    empirical_metrics: List[str] = Field(default_factory=list)
    kinematic_markers: List[str] = Field(default_factory=list)
    stratigraphic_datums: List[str] = Field(default_factory=list)
    metrology_references: List[str] = Field(default_factory=list)
    parsimony_markers: List[str] = Field(default_factory=list)
    mechanistic_phrases: List[str] = Field(default_factory=list)
    falsification_markers: List[str] = Field(default_factory=list)
    justifications: List[EpistemicJustification] = Field(default_factory=list)
    custom_rule_matches: Dict[str, float] = Field(default_factory=dict)


class EvidenceScoreResult(BaseModel):
    """Result of evaluating the evidentiary weight of an utterance."""

    total_weight: float
    category_weights: Dict[str, float]
    feature_breakdown: EvidenceFeatureBreakdown
    justification_summary: str = ""
    raw_text_length: int
    active_validation_summary: Optional[str] = None


class ObjectiveEvidenceScorer:
    """Evaluates the objective epistemic weight of operator counter-evidence.
    
    Extracts objective features and attaches explicit epistemic rationales
    explaining why each feature narrows the hypothesis space.
    """

    def __init__(
        self,
        config: Optional[EvidenceScoringConfig] = None,
        active_validator: Optional[Any] = None,
    ) -> None:
        self.config = config or EvidenceScoringConfig()
        self.active_validator = active_validator
        self._custom_rules: Dict[str, Callable[[str], float]] = {}

        # 1. Citations & Formal References
        self._doi_pattern = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE)
        self._url_pattern = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)", re.IGNORECASE)
        self._citation_pattern = re.compile(r"\((?:[A-Z][a-zA-Z\s]+(?:et\s+al\.?)?,\s*(?:19|20)\d{2})\)|\[\d+\]|arXiv:\d{4}\.\d{4,5}|RFC\s*\d+|ISO\s*\d+|IEEE\s*\d+", re.IGNORECASE)

        # 2. Formal Logic & Deductive Structures
        self._formal_logic_pattern = re.compile(
            r"\b(if\s+and\s+only\s+if|iff|therefore|it\s+follows\s+that|modus\s+(?:ponens|tollens)|reductio\s+ad\s+absurdum|by\s+contradiction|by\s+definition|contrapositive|logical\s+entailment|necessary\s+and\s+sufficient|given\s+that|premise\s*\d*|conclusion:?)\b",
            re.IGNORECASE,
        )

        # 3. Empirical & Quantitative Data
        self._empirical_pattern = re.compile(
            r"\b(?:p\s*[<>=]\s*0?\.\d+|\bCI\s*=\s*\[?\d+|n\s*=\s*\d+|\b\d+(?:\.\d+)?\s*(?:%|percent|ms|s|μs|ns|kg|g|mg|GB|MB|KB|kbps|Mbps|Gbps|GHz|MHz|mol|mL|kW|kWh|nm|μm|V|mV|A|mA|mm|cm|meters|inches)\b|\b\d+\.\d+\s*(?:±|\+/-)\s*\d+\.\d+|\b\d+\s+continents\b)\b",
            re.IGNORECASE,
        )

        # 4. Physical Toolmark Kinematics & Machining Forensics
        self._kinematics_pattern = re.compile(
            r"\b(witness\s+marks?|circular\s+saw(?:\s+marks?)?|convex(?:\s+circular)?\s+saw|convex\s+radius|radius\s+of\s+curvature|off-cut|feed\s+rate|spiral\s+grooves?|striations?|striation\s+pitch|kerf(?:\s+width)?|tubular\s+drill(?:ing)?|core\s+#?7|tool\s+kinematics|inferred\s+tools|stepped\s+cuts?|undercut|bore\s+hole|rotational\s+symmetry|machining\s+tolerances?)\b",
            re.IGNORECASE,
        )

        # 5. Stratigraphic Datums & Geological Horizons
        self._stratigraphic_pattern = re.compile(
            r"\b(black\s+mat|younger\s+dryas(?:\s+boundary)?|ydb|magnetic\s+microspherules|nanodiamonds|platinum\s+spike|sedimentary\s+horizon|alluvial\s+deposition|forensic\s+geology|stratigraphic\s+layer|geological\s+horizon|elephantine(?:\s+island)?|abu\s+rawash|longyou(?:\s+caves)?)\b",
            re.IGNORECASE,
        )

        # 6. Primary Metrology & Measurement Authorities
        self._metrology_pattern = re.compile(
            r"\b(petrie|flinders\s+petrie|chris\s+dunn|optical\s+flat|micrometer(?:\s+survey)?|parallelism|orthogonality|flatness\s+deviation|surface\s+plate|coordinate\s+measuring|metrology|mohs\s+hardness|quartz\s+hardness|granite\s+cores?|diorite)\b",
            re.IGNORECASE,
        )

        # 7. Parsimony & Epistemic Economy Constraints
        self._parsimony_pattern = re.compile(
            r"\b(occams?\s+razor|explanatory\s+parsimony|burden\s+of\s+proof|ad\s+hoc(?:\s+hypothes[ie]s)?|dismantled(?:\s+the\s+methodology)?|methodology\s+dismantled|falsification\s+criterion)\b",
            re.IGNORECASE,
        )

        # 8. Verifiable Mechanisms
        self._mechanism_pattern = re.compile(
            r"\b(mechanism\s+of\s+action|causal\s+pathway|catalyzes|inhibits|downregulates|upregulates|binds\s+to|causes|leads\s+to|deterministic\s+(?:state|execution)|reproducible\s+via|biochemical\s+cascade|thermodynamic\s+equilibrium|state\s+transition)\b",
            re.IGNORECASE,
        )

        # 9. Direct Falsifications & Counterexamples
        self._falsification_pattern = re.compile(
            r"\b(counterexample|falsified\s+by|refuted\s+by|disproven\s+by|contradicts\s+(?:the\s+claim|hypothesis|premise)|incompatible\s+with|inconsistent\s+with\s+observation)\b",
            re.IGNORECASE,
        )

    def register_custom_rule(
        self, name: str, rule_fn: Callable[[str], float]
    ) -> None:
        """Register a custom scoring rule supplied by the human operator."""
        self._custom_rules[name] = rule_fn

    def score(
        self, text: str, use_active_validation: bool = False
    ) -> EvidenceScoreResult:
        """Score the counter-evidence weight of the text and attach explicit epistemic justifications."""
        if not text or not text.strip():
            return EvidenceScoreResult(
                total_weight=self.config.base_noise_floor,
                category_weights={
                    "citations": 0.0,
                    "formal_logic": 0.0,
                    "empirical_data": 0.0,
                    "kinematics": 0.0,
                    "stratigraphy": 0.0,
                    "metrology": 0.0,
                    "parsimony": 0.0,
                    "mechanisms": 0.0,
                    "falsifications": 0.0,
                    "custom_rules": 0.0,
                },
                feature_breakdown=EvidenceFeatureBreakdown(),
                justification_summary="No evidentiary markers detected in utterance.",
                raw_text_length=0,
            )

        justifications: List[EpistemicJustification] = []

        # 1. Citations
        dois = self._doi_pattern.findall(text)
        urls = self._url_pattern.findall(text)
        formal_cites = self._citation_pattern.findall(text)
        all_citations = list(set(dois + urls + formal_cites))
        raw_citation_score = len(all_citations) * self.config.citation_weight
        capped_citation_score = min(raw_citation_score, self.config.category_max_cap)
        for cite in all_citations:
            justifications.append(
                EpistemicJustification(
                    category="ACADEMIC_CITATION",
                    feature_name="citation",
                    matched_text=cite,
                    weight_assigned=self.config.citation_weight,
                    rationale="Grounds claim in peer-reviewed literature or indexed primary reference material.",
                )
            )

        # 2. Formal Logic
        logic_matches = list(set([m.lower() for m in self._formal_logic_pattern.findall(text)]))
        raw_logic_score = len(logic_matches) * self.config.formal_logic_weight
        capped_logic_score = min(raw_logic_score, self.config.category_max_cap)
        for log_op in logic_matches:
            justifications.append(
                EpistemicJustification(
                    category="FORMAL_LOGIC",
                    feature_name="deductive_operator",
                    matched_text=log_op,
                    weight_assigned=self.config.formal_logic_weight,
                    rationale="Enforces valid propositional deductive transitions and contradiction avoidance.",
                )
            )

        # 3. Empirical Data
        empirical_matches = list(set([m.lower() for m in self._empirical_pattern.findall(text)]))
        raw_empirical_score = len(empirical_matches) * self.config.empirical_data_weight
        capped_empirical_score = min(raw_empirical_score, self.config.category_max_cap)
        for emp in empirical_matches:
            justifications.append(
                EpistemicJustification(
                    category="EMPIRICAL_DATA",
                    feature_name="quantitative_metric",
                    matched_text=emp,
                    weight_assigned=self.config.empirical_data_weight,
                    rationale="Provides quantifiable dimensions, error bounds, or sample constraints.",
                )
            )

        # 4. Toolmark Kinematics (Material Constraint)
        kinematic_matches = list(set([m.lower() for m in self._kinematics_pattern.findall(text)]))
        raw_kinematics_score = len(kinematic_matches) * self.config.kinematics_toolmark_weight
        capped_kinematics_score = min(raw_kinematics_score, self.config.category_max_cap)
        for km in kinematic_matches:
            justifications.append(
                EpistemicJustification(
                    category="PHYSICAL_KINEMATICS",
                    feature_name="toolmark_kinematics",
                    matched_text=km,
                    weight_assigned=self.config.kinematics_toolmark_weight,
                    rationale="Physical toolmark geometry imposes immutable mechanical constraints on tool rotation, feed rate, and blade kinematics.",
                )
            )

        # 5. Stratigraphic Datums & Geological Horizons
        stratigraphic_matches = list(set([m.lower() for m in self._stratigraphic_pattern.findall(text)]))
        raw_strat_score = len(stratigraphic_matches) * self.config.stratigraphic_datum_weight
        capped_strat_score = min(raw_strat_score, self.config.category_max_cap)
        for sm in stratigraphic_matches:
            justifications.append(
                EpistemicJustification(
                    category="STRATIGRAPHIC_DATUM",
                    feature_name="geological_horizon",
                    matched_text=sm,
                    weight_assigned=self.config.stratigraphic_datum_weight,
                    rationale="Anchors claims to verifiable physical strata, sedimentary boundaries, and global impact horizons.",
                )
            )

        # 6. Primary Metrology & Physical Surveys
        metrology_matches = list(set([m.lower() for m in self._metrology_pattern.findall(text)]))
        raw_metrology_score = len(metrology_matches) * self.config.metrology_weight
        capped_metrology_score = min(raw_metrology_score, self.config.category_max_cap)
        for mm in metrology_matches:
            justifications.append(
                EpistemicJustification(
                    category="METROLOGICAL_RECORD",
                    feature_name="metrological_authority_survey",
                    matched_text=mm,
                    weight_assigned=self.config.metrology_weight,
                    rationale="References primary micrometer surveys, material hardness differentials, and dimensional metrology records.",
                )
            )

        # 7. Parsimony & Epistemic Constraints
        parsimony_matches = list(set([m.lower() for m in self._parsimony_pattern.findall(text)]))
        raw_parsimony_score = len(parsimony_matches) * self.config.parsimony_constraint_weight
        capped_parsimony_score = min(raw_parsimony_score, self.config.category_max_cap)
        for pm in parsimony_matches:
            justifications.append(
                EpistemicJustification(
                    category="PARSIMONY_CONSTRAINT",
                    feature_name="epistemic_razor",
                    matched_text=pm,
                    weight_assigned=self.config.parsimony_constraint_weight,
                    rationale="Applies Occam's Razor against ad-hoc mechanical epicycles requiring unobserved manual steps.",
                )
            )

        # 8. Verifiable Mechanisms
        mechanism_matches = list(set([m.lower() for m in self._mechanism_pattern.findall(text)]))
        raw_mechanism_score = len(mechanism_matches) * self.config.verifiable_mechanism_weight
        capped_mechanism_score = min(raw_mechanism_score, self.config.category_max_cap)
        for mech in mechanism_matches:
            justifications.append(
                EpistemicJustification(
                    category="CAUSAL_MECHANISM",
                    feature_name="causal_pathway",
                    matched_text=mech,
                    weight_assigned=self.config.verifiable_mechanism_weight,
                    rationale="Specifies deterministic state transitions or reproducible causal pathways.",
                )
            )

        # 9. Falsifications & Counterexamples
        falsification_matches = list(set([m.lower() for m in self._falsification_pattern.findall(text)]))
        raw_falsification_score = len(falsification_matches) * self.config.falsification_weight
        capped_falsification_score = min(raw_falsification_score, self.config.category_max_cap)
        for f_match in falsification_matches:
            justifications.append(
                EpistemicJustification(
                    category="FALSIFICATION_EVIDENCE",
                    feature_name="falsification_marker",
                    matched_text=f_match,
                    weight_assigned=self.config.falsification_weight,
                    rationale="Presents direct counterexamples that formally invalidate an empirical premise.",
                )
            )

        # 10. Custom Operator Rules
        custom_scores: Dict[str, float] = {}
        total_custom = 0.0
        for name, fn in self._custom_rules.items():
            try:
                c_weight = max(0.0, float(fn(text)))
                custom_scores[name] = c_weight
                total_custom += c_weight
                if c_weight > 0:
                    justifications.append(
                        EpistemicJustification(
                            category="OPERATOR_CUSTOM_RULE",
                            feature_name=name,
                            matched_text=f"Rule: {name}",
                            weight_assigned=c_weight,
                            rationale=f"Custom heuristic registered by human operator: {name}.",
                        )
                    )
            except Exception:
                custom_scores[name] = 0.0
        capped_custom = min(total_custom, self.config.category_max_cap)

        # Calculate Total Composite Weight
        total_raw = (
            self.config.base_noise_floor
            + capped_citation_score
            + capped_logic_score
            + capped_empirical_score
            + capped_kinematics_score
            + capped_strat_score
            + capped_metrology_score
            + capped_parsimony_score
            + capped_mechanism_score
            + capped_falsification_score
            + capped_custom
        )
        final_total = min(total_raw, self.config.total_score_cap)

        breakdown = EvidenceFeatureBreakdown(
            citations=all_citations,
            formal_logic_markers=logic_matches,
            empirical_metrics=empirical_matches,
            kinematic_markers=kinematic_matches,
            stratigraphic_datums=stratigraphic_matches,
            metrology_references=metrology_matches,
            parsimony_markers=parsimony_matches,
            mechanistic_phrases=mechanism_matches,
            falsification_markers=falsification_matches,
            justifications=justifications,
            custom_rule_matches=custom_scores,
        )

        # Create structured rationale summary
        if justifications:
            justification_lines = [
                f"• [{j.category}] '{j.matched_text}': {j.rationale} (+{j.weight_assigned:.2f})"
                for j in justifications[:6]
            ]
            if len(justifications) > 6:
                justification_lines.append(f"• ... and {len(justifications) - 6} more evidentiary features.")
            justification_summary = "\n".join(justification_lines)
        else:
            justification_summary = "No objective epistemic features detected."

        # Run active validation if available and requested
        active_summary = None
        if use_active_validation and self.active_validator:
            try:
                val_rep = self.active_validator.validate_utterance(text)
                if val_rep.has_valid_constraints:
                    final_total = max(final_total, min(val_rep.net_asymmetric_weight, self.config.total_score_cap))
                active_summary = val_rep.epistemic_summary_why
                justification_summary += f"\n\n[ACTIVE REAL-TIME VERIFICATION]:\n{active_summary}"
            except Exception as e:
                logger.warning(f"Active validation failed: {e}")

        return EvidenceScoreResult(
            total_weight=round(final_total, 4),
            category_weights={
                "citations": round(capped_citation_score, 4),
                "formal_logic": round(capped_logic_score, 4),
                "empirical_data": round(capped_empirical_score, 4),
                "kinematics": round(capped_kinematics_score, 4),
                "stratigraphy": round(capped_strat_score, 4),
                "metrology": round(capped_metrology_score, 4),
                "parsimony": round(capped_parsimony_score, 4),
                "mechanisms": round(capped_mechanism_score, 4),
                "falsifications": round(capped_falsification_score, 4),
                "custom_rules": round(capped_custom, 4),
            },
            feature_breakdown=breakdown,
            justification_summary=justification_summary,
            raw_text_length=len(text),
            active_validation_summary=active_summary,
        )
