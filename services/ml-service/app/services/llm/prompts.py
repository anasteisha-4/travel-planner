import json

RECOMMENDATION_QUALITY_PROMPT_VERSION = "recommendation_quality_v3"
ITINERARY_QUALITY_PROMPT_VERSION = "itinerary_quality_v2"

RECOMMENDATION_QUALITY_TEMPLATE = (
    "You are a strict travel recommendation quality gate. Review the ranked recommendation list. "
    "Return only compact JSON matching the schema. Do not write user-facing prose. "
    "Every nullable field required by the schema must be present as null when unknown. "
    "Use only destination_id values that are present in the supplied recommendations. "
    "If a destination has safety, feasibility, visa, budget, or preference-fit problems, attach a structured issue "
    "with destination_id and add a suggested adjustment. Use demote for moderate issues, remove for critical safety "
    "or infeasible issues, and swap/promote only for near-tie ranking corrections. "
    "Do not blindly trust model scores, explanation_tags, or climate_match when they conflict with common travel sense. "
    "For beach + Mediterranean/warm-climate requests, actively penalize cold, northern, inland, or non-resort city breaks "
    "during weak beach months, even if the scorer marked them as beach. "
    "When region is Europe and the profile indicates English-speaking, Mediterranean, international, or Paris-like travel, "
    "do not let domestic Russian destinations dominate the top ranks unless they clearly match those preferences. "
    "For budget checks, compare avg_daily_cost_usd with budget_max_per_day_usd, not with budget_max_usd. "
    "Only mark budget critical when avg_daily_cost_usd * typical_duration_days plus known route cost exceeds budget_max_usd. "
    "For economy budgets, penalize premium/very expensive destinations unless the budget evidence clearly fits. "
    "Return at most 4 highest-impact issues and at most 4 adjustments. "
    "Keep each message under 140 characters. Keep defense_trace short and put no preference recap into user_summary_ru."
)

ITINERARY_QUALITY_TEMPLATE = (
    "You are a strict travel itinerary quality gate. Return only compact JSON matching the schema. "
    "Do not write markdown or prose outside JSON. Every nullable field required by the schema must be present as null "
    "when unknown. Review safety, feasibility, opening-time, route-density, budget, and preference fit. "
    "Also verify that the route follows the supplied algorithm summary: POI utility should match user preferences, "
    "daily order should be geographically coherent, and coordinates must be plausible for the destination. "
    "The final itinerary should include the destination's most popular and recognizable tourist places when they are "
    "feasible for the user's duration, pace, budget, season, and preferences; flag routes that omit obvious must-see "
    "POIs without a clear constraint-based reason. "
    "The destination object is authoritative: if the user asks for Roman history while destination is Tarragona, "
    "interpret that as Roman heritage in Tarragona, not as a request to switch to Rome. "
    "External candidate routes may have unverified opening hours; do not reject solely because opening_status is unknown. "
    "If status is caution or reject, every actionable issue must have a concrete adjustment that changes the route: "
    "remove, swap, replace_item, adjust_time, add_candidate_poi, regenerate, or generate_external_route. "
    "Use note only for residual context after the route-changing adjustments. "
    "Return at most 4 highest-impact issues and at most 3 adjustments. Keep each message under 120 characters. "
    "For synthetic fallback routes or routes without coordinates, return one concise caution/reject issue rather than "
    "listing every item. Do not suggest add_candidate_poi unless candidate evidence is present in the context."
)


def quality_review_json_schema() -> dict:
    nullable_string = {"type": ["string", "null"]}
    nullable_integer = {"type": ["integer", "null"]}
    candidate_poi_schema = {
        "type": ["object", "null"],
        "additionalProperties": False,
        "required": [
            "name",
            "category",
            "lat",
            "lng",
            "address",
            "source_url",
            "official_url",
            "suggested_visit_duration_minutes",
            "opening_hours",
            "estimated_price",
            "estimated_price_currency",
            "price_source_url",
            "confidence",
            "reason",
        ],
        "properties": {
            "name": {"type": "string"},
            "category": nullable_string,
            "lat": {"type": ["number", "null"]},
            "lng": {"type": ["number", "null"]},
            "address": nullable_string,
            "source_url": nullable_string,
            "official_url": nullable_string,
            "suggested_visit_duration_minutes": nullable_integer,
            "opening_hours": nullable_string,
            "estimated_price": {"type": ["number", "null"]},
            "estimated_price_currency": nullable_string,
            "price_source_url": nullable_string,
            "confidence": {"type": ["number", "null"]},
            "reason": nullable_string,
        },
    }
    issue_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["code", "severity", "message", "evidence", "destination_id", "target_id", "item_id", "day"],
        "properties": {
            "code": {"type": "string"},
            "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
            "message": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "destination_id": nullable_string,
            "target_id": nullable_string,
            "item_id": nullable_string,
            "day": nullable_integer,
        },
    }
    adjustment_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "action",
            "reason",
            "target_id",
            "target_destination_id",
            "replacement_id",
            "target_day",
            "target_order",
            "candidate_poi",
            "payload",
        ],
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "note",
                    "demote",
                    "promote",
                    "remove",
                    "swap",
                    "regenerate",
                    "replace_item",
                    "adjust_time",
                    "add_candidate_poi",
                    "generate_external_route",
                ],
            },
            "reason": {"type": "string"},
            "target_id": nullable_string,
            "target_destination_id": nullable_string,
            "replacement_id": nullable_string,
            "target_day": nullable_integer,
            "target_order": nullable_integer,
            "candidate_poi": candidate_poi_schema,
            "payload": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "required": ["notes"],
                "properties": {"notes": nullable_string},
            },
        },
    }
    return {
        "name": "llm_quality_review",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "status",
                "confidence",
                "provider",
                "model",
                "prompt_version",
                "issues",
                "suggested_adjustments",
                "user_summary_ru",
                "defense_trace",
            ],
            "properties": {
                "status": {"type": "string", "enum": ["ok", "caution", "reject", "skipped", "failed"]},
                "confidence": {"type": "number"},
                "provider": {"type": ["string", "null"]},
                "model": {"type": ["string", "null"]},
                "prompt_version": {"type": "string"},
                "issues": {"type": "array", "items": issue_schema},
                "suggested_adjustments": {"type": "array", "items": adjustment_schema},
                "user_summary_ru": {"type": ["string", "null"]},
                "defense_trace": {"type": ["string", "null"]},
            },
        },
    }


def compact_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
