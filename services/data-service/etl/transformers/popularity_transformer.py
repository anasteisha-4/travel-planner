"""Transform Wikipedia pageview data into normalized crowd_index scores.

crowd_index captures SEASONAL variation:
  - seasonal_index = views[month] / annual_mean_for_this_destination
    > 1.0 = busier than this destination's average month
    < 1.0 = quieter than average
  - crowd_index = this seasonal_index globally normalized to [0, 1]
    using p5/p95 across all destinations × months.

This way:
  - Paris August (1.64× its average) → high crowd_index
  - Paris November (0.78× its average) → low crowd_index
  - Reykjavik June (3×) → very high crowd_index
  - Same crowd_index can be compared across destinations.

Absolute popularity (Paris >> Fakaofo) is preserved in avg_pageviews.
The ML model uses avg_pageviews for global popularity ranking and
crowd_index for "when to visit" decisions.
"""

import logging

logger = logging.getLogger(__name__)


def transform_popularity(raw: list[dict]) -> list[dict]:
    filtered = [item for item in raw if len(item.get("monthly_views", {})) >= 6]
    skipped = len(raw) - len(filtered)

    if not filtered:
        logger.warning("No popularity data to transform.")
        return []

    # Pass 1: compute seasonal indices for all destinations
    dest_seasonal: list[tuple[str, str | None, dict[int, int], dict[int, float]]] = []
    all_seasonal_indices: list[float] = []

    for item in filtered:
        monthly_views: dict[int, int] = item["monthly_views"]
        annual_mean = sum(monthly_views.values()) / len(monthly_views)
        if annual_mean == 0:
            continue
        seasonal = {
            month: views / annual_mean for month, views in monthly_views.items()
        }
        dest_seasonal.append(
            (item["destination_id"], item.get("article"), monthly_views, seasonal)
        )
        all_seasonal_indices.extend(seasonal.values())

    # p5/p95 of seasonal indices for robust global normalization
    all_seasonal_indices.sort()
    n = len(all_seasonal_indices)
    p5 = all_seasonal_indices[int(n * 0.05)]
    p95 = all_seasonal_indices[int(n * 0.95)]
    spread = p95 - p5 if p95 > p5 else 1.0

    # Pass 2: build records
    records = []
    for destination_id, article, monthly_views, seasonal in dest_seasonal:
        for month in range(1, 13):
            views = monthly_views.get(month)
            si = seasonal.get(month)
            if views is None or si is None:
                continue

            crowd_index = round(max(0.0, min(1.0, (si - p5) / spread)), 4)

            records.append(
                {
                    "destination_id": destination_id,
                    "month": month,
                    "avg_pageviews": views,
                    "crowd_index": crowd_index,
                    "wikipedia_article": article,
                    "data_year": None,
                }
            )

    logger.info(
        f"Transformed {len(records)} popularity records "
        f"({skipped} skipped). "
        f"Seasonal index range: p5={p5:.2f}x, p95={p95:.2f}x annual mean."
    )
    return records
