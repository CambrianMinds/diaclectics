"""Epistemic Triangulation Codebase Discoverer.

Scans workspace source code for candidate domain invariants, AST constraints,
and physical/formal units, and then triangulates them against external peer-reviewed
academic literature (OpenAlex API) to synthesize robust, non-circular polar anchor seeds.
"""

from __future__ import annotations

import ast
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from src.calibration.schema import AxisDefinition, SeedTextItem
from src.verifier.search_verifier import SearchVerifier, AcademicPaper



logger = logging.getLogger(__name__)


class DiscoveredInvariant(BaseModel):
    """Candidate invariant extracted from source code."""

    name: str = Field(description="Name or short summary of the invariant.")
    domain: str = Field(description="Domain category (e.g. kinematics, systems_programming, thermodynamics).")
    raw_code_snippet: str = Field(description="Source code or docstring snippet where invariant was discovered.")
    file_path: str
    line_number: int
    candidate_keywords: List[str] = Field(default_factory=list)
    literature_citations: List[AcademicPaper] = Field(default_factory=list)
    synthesized_positive_anchor: Optional[str] = None
    synthesized_negative_anchor: Optional[str] = None


class EpistemicCodebaseDiscoverer:
    """Discovers domain invariants in source code and triangulates with academic literature."""

    def __init__(self, search_verifier: Optional[SearchVerifier] = None) -> None:
        self.search_verifier = search_verifier or SearchVerifier()

    def scan_python_file(self, file_path: str | Path) -> List[DiscoveredInvariant]:
        """Scan a Python file for invariant patterns, docstring physical formulas, and assertions."""
        invariants: List[DiscoveredInvariant] = []
        path_obj = Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return invariants

        try:
            content = path_obj.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(path_obj))
        except Exception as e:
            logger.warning(f"Failed to parse AST for {file_path}: {e}")
            return invariants

        # Heuristic keywords mapping to domain invariants
        domain_patterns = {
            "kinematics": [r"feed[\s_]?rate", r"spindle[\s_]?speed", r"cutting[\s_]?speed", r"tool[\s_]?life", r"taylor", r"chatter", r"resonance"],
            "systems_programming": [r"borrow[\s_]?check", r"affine[\s_]?type", r"use[\s_]?after[\s_]?free", r"data[\s_]?race", r"thread[\s_]?safety", r"mutex"],
            "thermodynamics": [r"carnot", r"entropy", r"thermal[\s_]?expansion", r"heat[\s_]?transfer", r"conduction", r"fourier"],
            "materials_science": [r"fatigue[\s_]?limit", r"s[\s_]?n[\s_]?curve", r"endurance[\s_]?limit", r"brittle", r"ductile", r"dislocation"],
            "statutory_law": [r"daubert", r"precedent", r"admissibility", r"standard[\s_]?of[\s_]?review", r"burden[\s_]?of[\s_]?proof"]
        }

        # 1. Inspect module docstring
        module_doc = ast.get_docstring(tree)
        if module_doc:
            for domain, patterns in domain_patterns.items():
                matched_kw = [p for p in patterns if re.search(p, module_doc, re.IGNORECASE)]
                if matched_kw:
                    invariants.append(
                        DiscoveredInvariant(
                            name=f"{domain.replace('_', ' ').title()} Invariant (Module Doc)",
                            domain=domain,
                            raw_code_snippet=module_doc[:300].strip(),
                            file_path=str(path_obj),
                            line_number=1,
                            candidate_keywords=matched_kw
                        )
                    )

        # 2. Inspect class & function docstrings + assertions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                fn_doc = ast.get_docstring(node)
                if fn_doc:
                    for domain, patterns in domain_patterns.items():
                        matched_kw = [p for p in patterns if re.search(p, fn_doc, re.IGNORECASE)]
                        if matched_kw:
                            invariants.append(
                                DiscoveredInvariant(
                                    name=f"{node.name} Invariant",
                                    domain=domain,
                                    raw_code_snippet=fn_doc[:300].strip(),
                                    file_path=str(path_obj),
                                    line_number=getattr(node, "lineno", 1),
                                    candidate_keywords=matched_kw
                                )
                            )

            # Assert statements with formulas or explanatory messages
            elif isinstance(node, ast.Assert):
                assert_msg = ""
                if node.msg and isinstance(node.msg, ast.Constant):
                    assert_msg = str(node.msg.value)
                line_no = getattr(node, "lineno", 1)
                snippet = content.splitlines()[line_no - 1] if line_no <= len(content.splitlines()) else ""
                
                for domain, patterns in domain_patterns.items():
                    matched_kw = [p for p in patterns if re.search(p, snippet + " " + assert_msg, re.IGNORECASE)]
                    if matched_kw:
                        invariants.append(
                            DiscoveredInvariant(
                                name=f"Assertion Boundary (Line {line_no})",
                                domain=domain,
                                raw_code_snippet=snippet.strip(),
                                file_path=str(path_obj),
                                line_number=line_no,
                                candidate_keywords=matched_kw
                            )
                        )

        return invariants

    def scan_directory(self, dir_path: str | Path, max_files: int = 50) -> List[DiscoveredInvariant]:
        """Recursively scan a directory for candidate invariants."""
        all_invariants: List[DiscoveredInvariant] = []
        path_obj = Path(dir_path)
        if not path_obj.exists():
            return all_invariants

        count = 0
        for root, _, files in os.walk(path_obj):
            if any(p in root for p in [".git", "__pycache__", "venv", ".venv", "node_modules", "dist", "build"]):
                continue
            for file in files:
                if file.endswith(".py"):
                    file_p = Path(root) / file
                    invariants = self.scan_python_file(file_p)
                    all_invariants.extend(invariants)
                    count += 1
                    if count >= max_files:
                        break
            if count >= max_files:
                break

        return all_invariants

    def triangulate_invariant(self, invariant: DiscoveredInvariant) -> DiscoveredInvariant:
        """Query OpenAlex to retrieve peer-reviewed grounding literature for the invariant."""
        query_terms = invariant.candidate_keywords[:3]
        if not query_terms:
            query_terms = [invariant.name, invariant.domain]
        query = f"{invariant.domain} " + " ".join(query_terms)

        search_res = self.search_verifier.search(query)
        invariant.literature_citations = search_res.papers_found


        # Synthesize literature-backed polar anchors
        domain_title = invariant.domain.replace("_", " ").title()
        if invariant.literature_citations:
            top_paper = invariant.literature_citations[0]
            author_str = top_paper.authors[0] if top_paper.authors else "researchers"
            year_str = str(top_paper.publication_year) if top_paper.publication_year else "recent"
            invariant.synthesized_positive_anchor = (
                f"According to established literature in {domain_title} (e.g. {author_str}, "
                f"{year_str}, DOI: {top_paper.doi or 'OpenAlex'}), the invariant governing {', '.join(invariant.candidate_keywords)} "
                f"enforces deterministic empirical and mathematical constraints that cannot be dismissed."
            )
            invariant.synthesized_negative_anchor = (
                f"The physical and formal constraints of {domain_title} regarding {', '.join(invariant.candidate_keywords)} "
                f"can be ignored or bypassed without consequence through arbitrary convention."
            )

        else:
            invariant.synthesized_positive_anchor = (
                f"Formal and empirical constraints in {domain_title} regarding {', '.join(invariant.candidate_keywords)} "
                f"strictly govern system behavior."
            )
            invariant.synthesized_negative_anchor = (
                f"Empirical constraints regarding {', '.join(invariant.candidate_keywords)} have no bearing on valid operations."
            )

        return invariant

    def create_calibrated_seed_profile(
        self,
        axis_name: str,
        invariants: List[DiscoveredInvariant]
    ) -> AxisDefinition:
        """Construct an AxisDefinition ready for the calibration optimizer."""

        if not invariants:
            raise ValueError("Cannot create seed profile from empty invariants list.")

        domain = invariants[0].domain
        pos_anchors: List[str] = []
        neg_anchors: List[str] = []

        for inv in invariants:
            if not inv.literature_citations:
                self.triangulate_invariant(inv)
            if inv.synthesized_positive_anchor:
                pos_anchors.append(inv.synthesized_positive_anchor)
            if inv.synthesized_negative_anchor:
                neg_anchors.append(inv.synthesized_negative_anchor)

        # Deduplicate
        pos_anchors = list(dict.fromkeys(pos_anchors))
        neg_anchors = list(dict.fromkeys(neg_anchors))

        # Ensure minimum sample size of 3
        while len(pos_anchors) < 3:
            pos_anchors.append(f"Established empirical invariants in {domain} hold under rigorous scientific scrutiny.")
        while len(neg_anchors) < 3:
            neg_anchors.append(f"Invariants in {domain} are arbitrary subjective conventions with no objective truth.")

        seeds: List[SeedTextItem] = []
        for a in pos_anchors:
            seeds.append(SeedTextItem(text=a, tier="positive", source="codebase_openalex_triangulation"))
        for a in neg_anchors:
            seeds.append(SeedTextItem(text=a, tier="negative", source="codebase_openalex_triangulation"))

        return AxisDefinition(
            axis_id=axis_name,
            domain_name=domain.replace("_", " ").title(),
            thesis_summary=f"Literature-verified {domain} invariants and physical bounds.",
            antithesis_summary=f"Ungrounded assertions and relativist drift in {domain}.",
            seeds=seeds,
        )

