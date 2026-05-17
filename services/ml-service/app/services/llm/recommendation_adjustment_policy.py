import uuid
from dataclasses import dataclass

from app.schemas.llm_quality import LLMQualityReview, LLMReviewAction, LLMReviewSeverity, LLMReviewStatus
from app.schemas.recommendation import ScoredDestination

NEAR_TIE_SCORE_DELTA = 0.05
WARNING_PENALTY = 0.12
SAFETY_WARNING_PENALTY = 0.22
CRITICAL_PENALTY = 0.45
SAFETY_CODES = ("safety", "risk", "unsafe", "crime", "conflict", "advisory", "security")


@dataclass
class RecommendationAdjustmentResult:
    results: list[ScoredDestination]
    applied_adjustments: list[dict]
    ignored_adjustments: list[dict]


def apply_recommendation_quality_review(
    results: list[ScoredDestination],
    review: LLMQualityReview | None,
    *,
    replacement_pool: list[ScoredDestination] | None = None,
) -> RecommendationAdjustmentResult:
    if review is None or review.status in {LLMReviewStatus.skipped, LLMReviewStatus.failed}:
        return RecommendationAdjustmentResult(results=results, applied_adjustments=[], ignored_adjustments=[])

    limit = len(results)
    known_ids = {item.destination_id for item in results}
    replacements = [item for item in (replacement_pool or []) if item.destination_id not in known_ids]
    updated = list(results) + replacements
    applied: list[dict] = []
    ignored: list[dict] = []

    updated, issue_applied, issue_ignored = _apply_issue_penalties(updated, review, replacements)
    applied.extend(issue_applied)
    ignored.extend(issue_ignored)

    for adjustment in review.suggested_adjustments:
        target_id = adjustment.target_destination_id or adjustment.target_id
        if adjustment.action == LLMReviewAction.note:
            ignored.append({"action": adjustment.action.value, "reason": "note_is_not_user_facing"})
            continue
        if target_id is not None and target_id not in {item.destination_id for item in updated}:
            ignored.append(
                {
                    "action": adjustment.action.value,
                    "target_id": str(target_id),
                    "reason": "unknown_destination_id",
                }
            )
            continue
        if adjustment.action in {LLMReviewAction.remove, LLMReviewAction.regenerate}:
            updated, did_apply = _remove_or_replace(updated, target_id, replacements)
            _record_adjustment(applied, ignored, did_apply, adjustment.action.value, target_id, "removed_or_replaced")
            continue
        if adjustment.action == LLMReviewAction.demote:
            updated, did_apply = _penalize_and_resort(updated, target_id, SAFETY_WARNING_PENALTY, "llm_demote")
            _record_adjustment(applied, ignored, did_apply, "demote", target_id, "llm_demote")
            continue
        if adjustment.action == LLMReviewAction.promote:
            updated, did_apply = _promote_near_tie(updated, target_id)
            _record_adjustment(applied, ignored, did_apply, "promote", target_id, "near_tie_promote")
            continue
        if adjustment.action == LLMReviewAction.swap:
            updated, did_apply = _swap_near_tie(updated, target_id, adjustment.target_order)
            _record_adjustment(applied, ignored, did_apply, "swap", target_id, "near_tie_swap")
            continue
        ignored.append({"action": adjustment.action.value, "reason": "unsupported_for_recommendations"})

    return RecommendationAdjustmentResult(
        results=_rank_top_unique(updated, limit),
        applied_adjustments=applied,
        ignored_adjustments=ignored,
    )


def _apply_issue_penalties(
    results: list[ScoredDestination],
    review: LLMQualityReview,
    replacements: list[ScoredDestination],
) -> tuple[list[ScoredDestination], list[dict], list[dict]]:
    updated = list(results)
    applied: list[dict] = []
    ignored: list[dict] = []
    for issue in review.issues:
        target_id = issue.destination_id or issue.target_id
        if target_id is None:
            if issue.severity != LLMReviewSeverity.info:
                ignored.append(
                    {"action": "issue_penalty", "issue_code": issue.code, "reason": "missing_destination_id"}
                )
            continue
        if target_id not in {item.destination_id for item in updated}:
            ignored.append(
                {
                    "action": "issue_penalty",
                    "issue_code": issue.code,
                    "target_id": str(target_id),
                    "reason": "unknown_destination_id",
                }
            )
            continue
        if issue.severity == LLMReviewSeverity.critical:
            updated, did_apply = _remove_or_replace(updated, target_id, replacements)
            _record_issue(applied, ignored, did_apply, issue.code, target_id, "critical_remove_or_replace")
            continue
        if issue.severity == LLMReviewSeverity.warning:
            penalty = SAFETY_WARNING_PENALTY if _is_safety_issue(issue.code) else WARNING_PENALTY
            updated, did_apply = _penalize_and_resort(updated, target_id, penalty, issue.code)
            _record_issue(applied, ignored, did_apply, issue.code, target_id, "warning_score_penalty")
    return updated, applied, ignored


def _is_safety_issue(code: str) -> bool:
    normalized = code.lower()
    return any(part in normalized for part in SAFETY_CODES)


def _remove_or_replace(
    results: list[ScoredDestination],
    target_id: uuid.UUID | None,
    replacements: list[ScoredDestination],
) -> tuple[list[ScoredDestination], bool]:
    if target_id is None:
        return results, False
    kept = [item for item in results if item.destination_id != target_id]
    if len(kept) == len(results):
        return results, False
    while replacements and len(kept) < len(results):
        candidate = replacements.pop(0)
        if candidate.destination_id not in {item.destination_id for item in kept}:
            kept.append(candidate)
    return kept, True


def _penalize_and_resort(
    results: list[ScoredDestination],
    target_id: uuid.UUID | None,
    penalty: float,
    reason_code: str,
) -> tuple[list[ScoredDestination], bool]:
    if target_id is None:
        return results, False
    updated = []
    did_apply = False
    for item in results:
        if item.destination_id != target_id:
            updated.append(item)
            continue
        did_apply = True
        next_score = max(0.0, item.score - penalty)
        updated.append(
            item.model_copy(
                update={
                    "score": next_score,
                    "score_breakdown": {**item.score_breakdown, "llm_quality_penalty": -penalty},
                    "explanation_tags": _append_tag(item.explanation_tags, f"llm_adjusted:{reason_code}"),
                }
            )
        )
    if not did_apply:
        return results, False
    return sorted(updated, key=lambda item: item.score, reverse=True), True


def _promote_near_tie(
    results: list[ScoredDestination], target_id: uuid.UUID | None
) -> tuple[list[ScoredDestination], bool]:
    if target_id is None:
        return results, False
    index = next((idx for idx, item in enumerate(results) if item.destination_id == target_id), None)
    if index is None or index == 0:
        return results, False
    previous = results[index - 1]
    current = results[index]
    if abs(previous.score - current.score) > NEAR_TIE_SCORE_DELTA:
        return results, False
    updated = list(results)
    updated[index - 1], updated[index] = updated[index], updated[index - 1]
    return updated, True


def _swap_near_tie(
    results: list[ScoredDestination],
    target_id: uuid.UUID | None,
    target_order: int | None,
) -> tuple[list[ScoredDestination], bool]:
    if target_id is None or target_order is None or target_order < 1 or target_order > len(results):
        return results, False
    current_index = next((idx for idx, item in enumerate(results) if item.destination_id == target_id), None)
    if current_index is None:
        return results, False
    target_index = target_order - 1
    if current_index == target_index:
        return results, False
    if abs(results[current_index].score - results[target_index].score) > NEAR_TIE_SCORE_DELTA:
        return results, False
    updated = list(results)
    item = updated.pop(current_index)
    updated.insert(target_index, item)
    return updated, True


def _append_tag(tags: list[str], tag: str) -> list[str]:
    return tags if tag in tags else [*tags, tag]


def _rank_top_unique(results: list[ScoredDestination], limit: int) -> list[ScoredDestination]:
    unique: dict[uuid.UUID, ScoredDestination] = {}
    for item in sorted(results, key=lambda result: result.score, reverse=True):
        unique.setdefault(item.destination_id, item)
        if len(unique) == limit:
            break
    return list(unique.values())


def _record_adjustment(
    applied: list[dict],
    ignored: list[dict],
    did_apply: bool,
    action: str,
    target_id: uuid.UUID | None,
    reason: str,
) -> None:
    target = str(target_id) if target_id else None
    if did_apply:
        applied.append({"action": action, "target_id": target, "reason": reason})
    else:
        ignored.append({"action": action, "target_id": target, "reason": reason})


def _record_issue(
    applied: list[dict],
    ignored: list[dict],
    did_apply: bool,
    issue_code: str,
    target_id: uuid.UUID,
    reason: str,
) -> None:
    payload = {"action": "issue_penalty", "issue_code": issue_code, "target_id": str(target_id), "reason": reason}
    if did_apply:
        applied.append(payload)
    else:
        ignored.append(payload)
