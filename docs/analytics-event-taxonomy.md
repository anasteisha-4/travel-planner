# Triply Analytics Event Taxonomy

Updated: 2026-05-06

Purpose: document frontend events stored through Analytics Service `/api/v1/events`.
The taxonomy supports the diploma demo funnel and the future `hybrid-ranker-v2`
feedback loop.

## Shared Envelope

Every event is sent inside a batch item:

| Field | Required | Notes |
| --- | --- | --- |
| `session_id` | yes | UUID generated in `sessionStorage`; does not identify a person by itself. |
| `event_type` | yes | One of the documented event names below. |
| `entity_type` | no | Main object type: `destination`, `trip`, or omitted for profile/onboarding. |
| `entity_id` | no | Destination id or trip id when available. |
| `context` | no | Event-specific JSON fields. |
| `client_meta` | no | Reserved for device/app metadata. |
| `occurred_at` | no | Client timestamp; server `created_at` is used when absent. |

Authenticated requests are linked to `user_id` server-side from the JWT. Anonymous
or unauthenticated events keep only `session_id`.

## Privacy Notes

- Do not put email, login, access tokens, OAuth ids, free-text profile notes, or
  expense descriptions into `context`.
- Store destination/trip identifiers and coarse numeric values needed for model
  learning. For sensitive values, prefer booleans such as `has_budget` or bucketed
  values unless exact value is needed for a product metric.
- Free-text post-trip feedback is stored in the feedback table, not duplicated in
  event context.

## Recommendation Funnel

| Event | Source screen | Required context | Optional context | Entity |
| --- | --- | --- | --- | --- |
| `recommendation_impression` | `/recommendations` list render | `recommendation_id`, `destination_id`, `rank`, `score`, `model_version` | `month`, `region` | `destination:{destination_id}` |
| `recommendation_shown` | `/recommendations` batch render | `recommendation_id`, `count`, `model_version` | `month`, `region` | none |
| `recommendation_clicked` | recommendation card tap | `destination_id`, `score` | `recommendation_id`, `model_version`, `month`, `region` | `destination:{destination_id}` |
| `destination_detail_opened` | destination detail sheet | `destination_id` | `recommendation_id`, `model_version` | `destination:{destination_id}` |
| `recommendation_filter_changed` | recommendation filters | `filter`, `value` | `previous_value` | none |

Learning use: impressions are negative/neutral exposure candidates; clicks and
detail opens are positive engagement labels. `recommendation_id`, `rank`, and
`model_version` allow future counterfactual analysis and A/B comparison.

## Destination Validation And Budget

| Event | Source screen | Required context | Optional context | Entity |
| --- | --- | --- | --- | --- |
| `validation_viewed` | destination detail, trip create/edit form | `destination_id`, `travel_month`, `warnings_count`, `warning_types` | `recommendation_id`, `model_version`, `budget_per_day_usd`, `source` | `destination:{destination_id}` |
| `budget_prediction_viewed` | destination detail sheet | `destination_id`, `duration_days`, `people_count`, `currency`, `total_mid` | `recommendation_id`, `model_version`, `origin_city_name`, `travel_cost_source` | `destination:{destination_id}` |
| `budget_prediction_changed` | trip create budget preview | `destination_id`, `duration_days`, `people_count`, `currency`, `total_mid` | `recommendation_id`, `model_version`, `origin_city_name`, `travel_cost_source` | `destination:{destination_id}` |
| `budget_predicted` | legacy alias | existing context | existing context | destination or none |

Learning use: validation outcomes and budget assumptions explain why a user does
or does not continue from a recommendation to a trip.

## Trip Funnel

| Event | Source screen | Required context | Optional context | Entity |
| --- | --- | --- | --- | --- |
| `trip_created` | trip form save | `destination`, `currency`, `people_count` | `destination_id`, `budget`, `departure_city` | `trip:{trip_id}` |
| `trip_created_from_recommendation` | recommendation-to-trip save | `trip_id`, `recommendation_id`, `destination` | `model_version`, `destination_id`, `currency`, `people_count`, `budget` | `trip:{trip_id}` |
| `trip_opened` | trip detail | `trip_id`, `destination`, `status`, `currency`, `has_budget` | `destination_id` | `trip:{trip_id}` |
| `trip_status_changed` | trip detail status action | `trip_id`, `status` | `destination_id` | `trip:{trip_id}` |

Learning use: trip creation is the strongest pre-trip conversion label. Status
changes separate planned, active, completed, and cancelled trips.

## Itinerary, Expenses, And Feedback

| Event | Source screen | Required context | Optional context | Entity |
| --- | --- | --- | --- | --- |
| `itinerary_viewed` | trip itinerary tab | `trip_id`, `destination_id`, `duration_days`, `has_generated_itinerary` | `start_date` | `trip:{trip_id}` |
| `itinerary_generated` | itinerary generation success | `trip_id`, `destination_id`, `duration_days`, `days_count`, `places_count`, `has_template` | `start_date` | `trip:{trip_id}` |
| `itinerary_edited` | future itinerary editor | `trip_id`, `destination_id`, `edit_type` | `place_id`, `day` | `trip:{trip_id}` |
| `expense_added` | expense form create | `trip_id`, `expense_id`, `amount`, `currency`, `category` | `expense_date` | `trip:{trip_id}` |
| `expense_updated` | expense form edit | `trip_id`, `expense_id`, `amount`, `currency`, `category` | `expense_date` | `trip:{trip_id}` |
| `post_trip_feedback_submitted` | post-trip feedback sheet | `trip_id`, `destination`, `overall_rating` | `destination_rating`, `value_rating`, `actual_total_cost`, `actual_currency`, `would_revisit` | `trip:{trip_id}` |
| `post_trip_feedback_updated` | post-trip feedback edit | `trip_id`, `destination`, `overall_rating` | `destination_rating`, `value_rating`, `actual_total_cost`, `actual_currency`, `would_revisit` | `trip:{trip_id}` |

Learning use: generated itinerary and expense behavior connect the recommendation
to actual trip engagement. Post-trip feedback supplies explicit quality labels.

## Profile And Onboarding

| Event | Source screen | Required context | Optional context | Entity |
| --- | --- | --- | --- | --- |
| `profile_viewed` | `/profile` | `has_preferences`, `onboarding_completed` | `preferred_currency` | none |
| `profile_updated` | profile edit wizard save | `changed_fields` | `preferred_currency`, `onboarding_completed` | none |
| `profile_origin_changed` | profile edit wizard save | `origin_city_name`, `has_origin_coords` | `typical_duration` | none |
| `profile_budget_changed` | profile edit wizard save | `preferred_currency`, `has_budget_min`, `has_budget_max` | none | none |
| `profile_preferences_changed` | profile edit wizard save | `vacation_preferences_count`, `liked_destinations_count`, `language_comfort_count` | none | none |
| `onboarding_step_completed` | onboarding wizard | `step` | none | none |
| `onboarding_completed` | onboarding wizard finish | none | none | none |

Learning use: profile fields are the cold-start layer for recommendations. Profile
change events help invalidate stale behavioral aggregates and explain shifts in
recommendation outcomes.

## Funnel Reconstruction

Minimum path from recommendation to trip:

1. `recommendation_impression` with `recommendation_id`, `destination_id`, `rank`.
2. `recommendation_clicked` or `destination_detail_opened` for the same destination.
3. `validation_viewed` and/or `budget_prediction_viewed`.
4. `trip_created_from_recommendation` with `recommendation_id` and `trip_id`.
5. `trip_opened`, `itinerary_generated`, `expense_added`, and
   `post_trip_feedback_submitted` for downstream engagement and quality.

