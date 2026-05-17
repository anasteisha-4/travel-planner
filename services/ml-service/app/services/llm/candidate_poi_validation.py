from dataclasses import dataclass, field

from app.schemas.llm_quality import LLMCandidatePOI


@dataclass
class CandidatePOIValidationResult:
    candidate: LLMCandidatePOI
    status: str
    display_allowed: bool = False
    duplicate_warnings: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)


def validate_candidate_poi(
    candidate: LLMCandidatePOI,
    *,
    duplicate_warnings: list[str] | None = None,
) -> CandidatePOIValidationResult:
    duplicates = duplicate_warnings or []
    missing = []
    if not candidate.name:
        missing.append("name")
    if candidate.lat is None or candidate.lng is None:
        missing.append("coordinates")
    if not candidate.source_url and not candidate.official_url:
        missing.append("source_url")
    if missing:
        return CandidatePOIValidationResult(
            candidate=candidate,
            status="needs_data",
            display_allowed=False,
            duplicate_warnings=duplicates,
            missing_fields=missing,
            rejection_reasons=["missing_evidence"],
        )
    if duplicates:
        return CandidatePOIValidationResult(
            candidate=candidate,
            status="duplicate",
            display_allowed=False,
            duplicate_warnings=duplicates,
            rejection_reasons=["catalog_duplicate"],
        )
    return CandidatePOIValidationResult(candidate=candidate, status="external_candidate", display_allowed=True)
