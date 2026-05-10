from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_internal_db
from app.models import Destination, NameTranslationEntity
from app.services.destination_search import (
    DestinationSearchCandidate,
    destination_search_aliases,
    rank_destination_candidates,
)
from app.services.name_translation_service import (
    destination_display_payload,
    load_translations,
    resolve_destination_display_name,
)

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("/search")
def search_destinations(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_internal_db),
):
    destinations = (
        db.query(Destination)
        .filter(Destination.is_active == True)  # noqa: E712
        .all()
    )
    translations = load_translations(db, NameTranslationEntity.destination, [d.id for d in destinations])

    candidates: list[DestinationSearchCandidate] = []
    dest_map: dict[str, Destination] = {}
    for d in destinations:
        key_en = f"{d.name}|{d.id}"
        candidates.append(
            DestinationSearchCandidate(
                key=key_en,
                name=d.name,
                country_code=d.country_code,
                population=d.population,
                capital=d.capital,
            )
        )
        name_ru, _quality, _provider = resolve_destination_display_name(str(d.name), translations.get(str(d.id)))
        if name_ru and name_ru != d.name:
            candidates.append(
                DestinationSearchCandidate(
                    key=key_en,
                    name=name_ru,
                    country_code=d.country_code,
                    population=d.population,
                    capital=d.capital,
                )
            )
        for alias in destination_search_aliases(str(d.name), name_ru):
            candidates.append(
                DestinationSearchCandidate(
                    key=key_en,
                    name=alias,
                    country_code=d.country_code,
                    population=d.population,
                    capital=d.capital,
                )
            )
        dest_map[key_en] = d

    output = []
    selected = [dest_map[match.key] for match in rank_destination_candidates(q, candidates, limit)]

    for d in selected:
        output.append(
            {
                "id": str(d.id),
                "country_code": d.country_code,
                "lat": d.lat,
                "lng": d.lng,
                **destination_display_payload(str(d.id), d.name, translations),
            }
        )

    return output


@router.get("")
def list_destinations(
    country_code: str | None = None,
    region: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_internal_db),
):
    q = db.query(Destination)
    if active_only:
        q = q.filter(Destination.is_active == True)  # noqa: E712
    if country_code:
        q = q.filter(Destination.country_code == country_code.upper())
    if region:
        q = q.filter(Destination.region == region)
    destinations = q.order_by(Destination.name).all()
    translations = load_translations(db, NameTranslationEntity.destination, [d.id for d in destinations])
    return [
        {
            "id": str(d.id),
            "country_code": d.country_code,
            "lat": d.lat,
            "lng": d.lng,
            "region": d.region,
            "subregion": d.subregion,
            "capital": d.capital,
            **destination_display_payload(str(d.id), d.name, translations),
        }
        for d in destinations
    ]


@router.post("/by-ids")
def get_destinations_by_ids(
    ids: list[str],
    db: Session = Depends(get_internal_db),
):
    from uuid import UUID as _UUID

    try:
        uuid_ids = [_UUID(i) for i in ids]
    except ValueError:
        return []
    destinations = db.query(Destination).filter(Destination.id.in_(uuid_ids)).all()
    dest_map = {str(d.id): d for d in destinations}
    translations = load_translations(db, NameTranslationEntity.destination, [d.id for d in destinations])
    return [
        {
            "id": i,
            "country_code": dest_map[i].country_code,
            **destination_display_payload(i, dest_map[i].name, translations),
        }
        for i in ids
        if i in dest_map
    ]


@router.get("/{destination_id}")
def get_destination(destination_id: str, db: Session = Depends(get_internal_db)):
    from app.models import DestinationCosts, DestinationSafety

    dest = db.query(Destination).filter(Destination.id == destination_id).first()
    if not dest:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Destination not found")

    costs = db.query(DestinationCosts).filter(DestinationCosts.destination_id == dest.id).first()
    safety = db.query(DestinationSafety).filter(DestinationSafety.destination_id == dest.id).first()

    return {
        "id": str(dest.id),
        "country_code": dest.country_code,
        "lat": dest.lat,
        "lng": dest.lng,
        "region": dest.region,
        "avg_daily_cost_usd": costs.avg_daily_cost_usd if costs else None,
        "cost_index": costs.cost_index if costs else None,
        "safety_score": safety.safety_score if safety else None,
        **destination_display_payload(
            str(dest.id),
            dest.name,
            load_translations(db, NameTranslationEntity.destination, [dest.id]),
        ),
    }
