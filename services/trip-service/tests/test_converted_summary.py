from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_converted_summary_multipair(client, auth_headers, trip_data):
    # Create trip with USD budget
    trip_data["currency"] = "USD"
    trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
    trip_id = trip_resp.json()["id"]

    # Add 100 RUB expense
    client.post(
        f"/api/trips/{trip_id}/expenses",
        json={
            "amount": "100",
            "currency": "RUB",
            "category": "food",
        },
        headers=auth_headers,
    )

    # Add 10 EUR expense
    client.post(
        f"/api/trips/{trip_id}/expenses",
        json={
            "amount": "10",
            "currency": "EUR",
            "category": "transport",
        },
        headers=auth_headers,
    )

    # Mock FXR API response
    # 1 USD = 100 RUB, 0.9 EUR
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "success": True,
        "base": "USD",
        "rates": {
            "RUB": 100,
            "EUR": 0.5,
            "USD": 1.0,
        },  # 1 USD = 100 RUB (so 100 RUB = 1 USD), 1 USD = 0.5 EUR (so 10 EUR = 20 USD)
    }

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        # Request converted summary in USD
        response = client.get(
            f"/api/trips/{trip_id}/expenses/converted-summary?target_currency=USD", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # 100 RUB = 1 USD
        # 10 EUR = 20 USD
        # Total = 21 USD
        assert Decimal(data["total"]) == Decimal("21.00")
        assert Decimal(data["by_category"]["food"]) == Decimal("1.00")
        assert Decimal(data["by_category"]["transport"]) == Decimal("20.00")
        assert data["target_currency"] == "USD"
        assert "RUB" in data["original_currencies"]
        assert "EUR" in data["original_currencies"]
