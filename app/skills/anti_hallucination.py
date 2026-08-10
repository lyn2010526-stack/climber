"""Anti-hallucination system — fact verification, confidence scoring, and source citation."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIABLE = "unverifiable"


class ClaimVerification(BaseModel):
    """Result of verifying a single claim."""
    claim: str
    confidence: ConfidenceLevel
    sources: list[str] = Field(default_factory=list)
    supporting_evidence: str = ""
    contradicting_evidence: str = ""
    notes: str = ""


class HallucinationGuard:
    """Post-generation verification system."""

    UNCERTAINTY_PATTERNS = [
        r"\bI (think|believe|guess|assume|suppose)\b",
        r"\b(probably|likely|maybe|perhaps|possibly)\b",
        r"\b(as far as I know|to my knowledge|if I recall)\b",
        r"\b(I'm not sure|I don't recall|I'm uncertain)\b",
    ]

    FACT_PATTERNS = [
        r"\b\d{4}\b",
        r"\b\d+%\b",
        r"\b\d+\s*(million|billion|thousand)\b",
        r"\b(according to|research shows|studies? (show|found|indicate))\b",
        r"\b(is the (largest|smallest|fastest|first|last|only))\b",
    ]

    def extract_claims(self, text: str) -> list[str]:
        """Extract verifiable factual claims from text."""
        claims = []
        sentences = re.split(r"[.!?]+", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            for pattern in self.FACT_PATTERNS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    claims.append(sentence)
                    break
        return claims[:5]

    def detect_uncertainty(self, text: str) -> list[str]:
        """Find phrases that indicate model uncertainty."""
        uncertain = []
        for pattern in self.UNCERTAINTY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            uncertain.extend(matches)
        return uncertain

    async def verify_claim(self, claim: str) -> ClaimVerification:
        """Verify a single claim using web search."""
        sources = []
        evidence = ""

        try:
            import urllib.parse
            url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(claim[:100])}"
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                text = resp.text
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()[:2000]
                evidence = text
                sources.append(f"duckduckgo.com/search?q={urllib.parse.quote(claim[:50])}")
        except Exception as e:
            logger.warning("Claim verification search failed", error=str(e))

        confidence = self._assess_confidence(claim, evidence)

        return ClaimVerification(
            claim=claim,
            confidence=confidence,
            sources=sources,
            supporting_evidence=evidence[:500] if evidence else "",
        )

    def _assess_confidence(self, claim: str, evidence: str) -> ConfidenceLevel:
        """Assess confidence based on evidence match."""
        if not evidence:
            return ConfidenceLevel.UNVERIFIABLE

        claim_words = set(re.findall(r"\b[a-z]{4,}\b", claim.lower()))
        evidence_lower = evidence.lower()

        matches = sum(1 for word in claim_words if word in evidence_lower)
        ratio = matches / max(len(claim_words), 1)

        if ratio > 0.6:
            return ConfidenceLevel.HIGH
        if ratio > 0.3:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    async def verify_response(self, response: str) -> dict[str, Any]:
        """Full verification of a model response."""
        claims = self.extract_claims(response)
        uncertainty = self.detect_uncertainty(response)

        verifications: list[ClaimVerification] = []
        for claim in claims[:3]:
            v = await self.verify_claim(claim)
            verifications.append(v)

        if verifications:
            scores = {
                ConfidenceLevel.HIGH: 3,
                ConfidenceLevel.MEDIUM: 2,
                ConfidenceLevel.LOW: 1,
                ConfidenceLevel.UNVERIFIABLE: 0,
            }
            avg_score = sum(scores[v.confidence] for v in verifications) / len(verifications)
            if avg_score > 2.3:
                overall = ConfidenceLevel.HIGH
            elif avg_score > 1.5:
                overall = ConfidenceLevel.MEDIUM
            elif avg_score > 0.5:
                overall = ConfidenceLevel.LOW
            else:
                overall = ConfidenceLevel.UNVERIFIABLE
        else:
            overall = ConfidenceLevel.MEDIUM

        return {
            "overall_confidence": overall.value,
            "claims_checked": len(verifications),
            "uncertainty_flags": len(uncertainty),
            "verifications": [v.model_dump() for v in verifications],
            "recommendation": self._get_recommendation(overall, len(uncertainty)),
        }

    def _get_recommendation(self, confidence: ConfidenceLevel, uncertainty_count: int) -> str:
        if confidence == ConfidenceLevel.HIGH and uncertainty_count == 0:
            return "Response appears well-supported. No action needed."
        if confidence == ConfidenceLevel.MEDIUM:
            return "Some claims could benefit from additional verification."
        if confidence in (ConfidenceLevel.LOW, ConfidenceLevel.UNVERIFIABLE):
            return "Key claims lack supporting evidence. Recommend human review."
        if uncertainty_count > 2:
            return "Response contains multiple uncertainty flags. Verify before acting."
        return "Review recommended for flagged claims."

    def format_citations(self, text: str, sources: list[str]) -> str:
        """Add citation markers to text."""
        if not sources:
            return text

        formatted = text + "\n\n---\n**Sources:**\n"
        for i, source in enumerate(sources, 1):
            formatted += f"{i}. {source}\n"
        return formatted


# Global singleton
hallucination_guard = HallucinationGuard()
