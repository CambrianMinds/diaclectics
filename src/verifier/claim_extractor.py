"""Active Claim & Proposition Extractor.

Parses natural language dialogue utterances into discrete, falsifiable empirical,
kinematic, stratigraphic, and statutory propositions ready for real-time verification.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class FalsifiableClaim(BaseModel):
    """A discrete proposition with empirical or logical truth-conditions."""

    claim_text: str = Field(description="The extracted proposition statement.")
    claim_type: Literal[
        "PHYSICAL_KINEMATIC",
        "STRATIGRAPHIC_CHRONOLOGY",
        "METROLOGICAL_MEASUREMENT",
        "STATUTORY_LEGAL",
        "LOGICAL_DEDUCTIVE",
        "EMPIRICAL_STUDY",
        "GENERAL_ASSERTION",
    ] = "GENERAL_ASSERTION"
    entities_involved: List[str] = Field(default_factory=list)
    quantities_or_units: List[str] = Field(default_factory=list)
    citations_referenced: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class ExtractedClaims(BaseModel):
    """Collection of extracted claims from an utterance."""

    raw_text: str
    claims: List[FalsifiableClaim] = Field(default_factory=list)
    total_claims: int = 0


class ClaimExtractor:
    """Extracts falsifiable propositions from dialogue utterances."""

    # Patterns for isolating numerical measurements and physical claims
    MEASUREMENT_PATTERN = re.compile(
        r"(\b\d+(?:\.\d+)?\s*(?:mm|cm|m|km|inch|inches|rpm|kg|ms|feet|ft|mohs|vickers|bp|bce|ce|percent|%)\b)",
        re.IGNORECASE,
    )
    CITATION_PATTERN = re.compile(
        r"(?:10\.\d{4,9}/[-._;()/:A-Za-z0-9]+|\([A-Z][a-zA-Z]+(?:\s+et\s+al\.?)?,\s*\d{4}\)|(?:Petrie|Chris Dunn|Stocks|Hancock|Schoch|Sweatman|Wolbach|Firestone|Kennett)[^,.;\n]{0,30}\b\d{4}?)",
        re.IGNORECASE,
    )

    def extract_claims(self, text: str) -> ExtractedClaims:
        """Parse text into distinct falsifiable propositions."""
        text = text.strip()
        if not text:
            return ExtractedClaims(raw_text="", claims=[], total_claims=0)

        # Break text into candidate sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        claims: List[FalsifiableClaim] = []

        for sent in sentences:
            # Check for physical / kinematic claims
            is_kinematic = bool(
                re.search(
                    r"\b(saw|blade|cut|kerf|feed rate|rpm|striation|groove|core #?7|rotation|lathe|toolmark|conical|thrust|hardness|granite|diorite|basalt|quartz)\b",
                    sent,
                    re.IGNORECASE,
                )
            )
            # Check for stratigraphic / chronology claims
            is_stratigraphic = bool(
                re.search(
                    r"\b(black mat|younger dryas|sediment|horizon|strata|microspherule|platinum|iridium|nanodiamond|12,800|dating|isochronous)\b",
                    sent,
                    re.IGNORECASE,
                )
            )
            # Check for metrological claims
            is_metrological = bool(
                re.search(
                    r"\b(petrie|flinders|chris dunn|micrometer|optical flat|parallelism|tolerance|depth of cut|feed depth|dimension)\b",
                    sent,
                    re.IGNORECASE,
                )
            )
            # Check for statutory / constitutional claims
            is_statutory = bool(
                re.search(
                    r"\b(anti-deficiency act|war powers resolution|false claims act|qui tam|article ii|executive order|statute|u\.s\.c\.|usc|jurisdiction)\b",
                    sent,
                    re.IGNORECASE,
                )
            )

            measurements = self.MEASUREMENT_PATTERN.findall(sent)
            citations = self.CITATION_PATTERN.findall(sent)

            if is_kinematic or is_stratigraphic or is_metrological or is_statutory or measurements or citations:
                if is_kinematic:
                    c_type = "PHYSICAL_KINEMATIC"
                elif is_stratigraphic:
                    c_type = "STRATIGRAPHIC_CHRONOLOGY"
                elif is_metrological:
                    c_type = "METROLOGICAL_MEASUREMENT"
                elif is_statutory:
                    c_type = "STATUTORY_LEGAL"
                elif measurements:
                    c_type = "EMPIRICAL_STUDY"
                else:
                    c_type = "GENERAL_ASSERTION"

                claims.append(
                    FalsifiableClaim(
                        claim_text=sent,
                        claim_type=c_type,
                        quantities_or_units=measurements,
                        citations_referenced=citations,
                    )
                )

        # If no specialized sentences matched, treat full sentence/paragraph as general claim if non-empty
        if not claims and len(text) > 10:
            claims.append(
                FalsifiableClaim(
                    claim_text=text[:300],
                    claim_type="GENERAL_ASSERTION",
                )
            )

        return ExtractedClaims(
            raw_text=text,
            claims=claims,
            total_claims=len(claims),
        )
