"""Compute destination_connectivity from rule-based country_code logic + manual overrides.

connectivity_score formula (0–1):
  0.5 * direct_moscow        — most impactful: no transit needed
  0.3 * (1 - transit/20)    — transit penalty: each transit hour reduces score
                               (capped at 20h: beyond that, score contribution = 0)
  0.2 * ground_access        — train_from_moscow: 1.0 if yes, 0.0 if no

transit = min_transit_hours if set, else 0 (direct) or 3 (hub transit inferred)

Post-2022 context:
- Direct flights from Russia suspended to EU/US/UK/most Western countries
- Main functional hubs: Dubai (AE), Istanbul (TR), Yerevan (AM), Tashkent (UZ), Tbilisi (GE)
- Mir card accepted only in TR, VN, CU, CIS countries
"""

import logging

logger = logging.getLogger(__name__)


HUB_FIELDS: dict[str, str] = {
    "dubai": "transit_via_dubai",
    "istanbul": "transit_via_istanbul",
    "yerevan": "transit_via_yerevan",
    "tashkent": "transit_via_tashkent",
    "tbilisi": "transit_via_tbilisi",
}


def compute_score(
    record: dict,
    excluded_hubs: list[str] | None = None,
) -> float:
    """Compute connectivity_score for a single record, optionally excluding hubs.

    Args:
        record: dict with keys matching DestinationConnectivity fields.
        excluded_hubs: list of hub names to treat as unavailable.
                       Valid values: "dubai", "istanbul", "yerevan", "tashkent", "tbilisi".

    Returns:
        float in [0, 1].
    """
    excluded = {h.lower() for h in (excluded_hubs or [])}

    direct_component = 0.5 if record["direct_from_moscow"] else 0.0

    if record["direct_from_moscow"]:
        transit_hours = 0.0
    else:
        # Check if any non-excluded hub is available
        transit_available = any(
            record.get(field, False)
            for hub, field in HUB_FIELDS.items()
            if hub not in excluded
        )
        if transit_available:
            transit_hours = record.get("min_transit_hours") or 3.0
        else:
            transit_hours = 20.0

    transit_component = 0.3 * max(0.0, 1.0 - transit_hours / 20.0)
    ground_component = 0.2 if record["train_from_moscow"] else 0.0

    return round(direct_component + transit_component + ground_component, 4)


def transform_connectivity(
    overrides: dict[str, dict], skip_existing: bool = False
) -> list[dict]:
    """Build connectivity records for all active destinations.

    Args:
        overrides: {country_code: connectivity_dict} from openflights.load_overrides()
        skip_existing: If True, skip destinations that already have a connectivity record.

    Returns list[dict] ready for upsert into destination_connectivity.
    """
    from app.database import SessionLocal
    from app.models import Destination
    from app.models.connectivity import DestinationConnectivity
    from etl.extractors.openflights import get_connectivity_for_country

    db = SessionLocal()
    try:
        destinations = (
            db.query(Destination)
            .filter(Destination.is_active == True)  # noqa: E712
            .all()
        )
        if skip_existing:
            existing = db.query(DestinationConnectivity.destination_id).all()
            existing_ids = {str(r[0]) for r in existing}
            before = len(destinations)
            destinations = [d for d in destinations if str(d.id) not in existing_ids]
            logger.info(
                f"skip_existing=True: skipping {before - len(destinations)}, {len(destinations)} remaining."
            )
    finally:
        db.close()

    records = []
    stats = {"direct": 0, "transit_only": 0, "no_connection": 0, "override": 0}

    for dest in destinations:
        cc = (dest.country_code or "").upper()
        data = get_connectivity_for_country(cc, overrides)

        transit_via_any = (
            data["transit_via_dubai"]
            or data["transit_via_istanbul"]
            or data["transit_via_yerevan"]
            or data["transit_via_tashkent"]
            or data["transit_via_tbilisi"]
        )

        score = compute_score(data)

        records.append(
            {
                "destination_id": str(dest.id),
                "direct_from_moscow": data["direct_from_moscow"],
                "direct_from_spb": data["direct_from_spb"],
                "direct_from_ekb": data["direct_from_ekb"],
                "direct_from_novosibirsk": data["direct_from_novosibirsk"],
                "transit_via_dubai": data["transit_via_dubai"],
                "transit_via_istanbul": data["transit_via_istanbul"],
                "transit_via_yerevan": data["transit_via_yerevan"],
                "transit_via_tashkent": data["transit_via_tashkent"],
                "transit_via_tbilisi": data["transit_via_tbilisi"],
                "train_from_moscow": data["train_from_moscow"],
                "train_hours_from_moscow": data.get("train_hours_from_moscow"),
                "flight_hours_from_moscow": data.get("flight_hours_from_moscow"),
                "min_transit_hours": data.get("min_transit_hours"),
                "connectivity_score": score,
                "mir_card_accepted": data["mir_card_accepted"],
                "data_source": data["data_source"],
                "data_year": 2025,
            }
        )

        if data["data_source"] == "manual_override":
            stats["override"] += 1
        if data["direct_from_moscow"]:
            stats["direct"] += 1
        elif transit_via_any:
            stats["transit_only"] += 1
        else:
            stats["no_connection"] += 1

    logger.info(
        f"Transformed {len(records)} connectivity records. "
        f"direct_msk={stats['direct']}, transit_only={stats['transit_only']}, "
        f"no_known_route={stats['no_connection']}, overrides_applied={stats['override']}."
    )
    return records
