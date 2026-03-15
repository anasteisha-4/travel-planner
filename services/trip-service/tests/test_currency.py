from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.currency_service import clear_cache, convert_amount, get_exchange_rates


@pytest.fixture(autouse=True)
def reset_cache():
    clear_cache()


@pytest.mark.asyncio
async def test_get_exchange_rates_usd():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "base": "USD", "rates": {"RUB": 100, "EUR": 0.9}}

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        rates = await get_exchange_rates("USD")
        assert rates["RUB"] == Decimal("100")
        assert rates["EUR"] == Decimal("0.9")
        assert rates["USD"] == Decimal("1.0")


@pytest.mark.asyncio
async def test_get_exchange_rates_rub():
    # If base is RUB, and rates relative to USD are RUB:100, EUR:0.9
    # Then 1 RUB = 0.01 USD
    # And 1 RUB = 0.01 * 0.9 EUR = 0.009 EUR
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "base": "USD", "rates": {"RUB": 100, "EUR": 0.8}}

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        rates = await get_exchange_rates("RUB")
        # 1 RUB = 1/100 USD = 0.01 USD
        assert rates["USD"] == Decimal("0.01")
        # 1 RUB = (0.8 / 100) EUR = 0.008 EUR
        assert rates["EUR"] == Decimal("0.008")
        assert rates["RUB"] == Decimal("1.0")


def test_convert_amount():
    rates_relative_to_usd = {"USD": Decimal("1.0"), "RUB": Decimal("100.0"), "EUR": Decimal("0.8")}

    # 10 EUR to RUB
    # 10 * (100 / 0.8) = 10 * 125 = 1250
    amount = Decimal("10")
    converted = convert_amount(amount, "EUR", "RUB", rates_relative_to_usd)
    assert converted == Decimal("1250")

    # 1000 RUB to USD
    # 1000 * (1.0 / 100.0) = 10
    converted = convert_amount(Decimal("1000"), "RUB", "USD", rates_relative_to_usd)
    assert converted == Decimal("10")
