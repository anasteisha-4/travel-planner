import logging
from decimal import Decimal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Cache for rates relative to USD
# Format: {"USD": {CUR: Rate}}
_rates_cache: dict[str, dict[str, Decimal]] = {}


async def _fetch_usd_rates() -> dict[str, Decimal]:
    """Fetches and caches latest rates relative to USD."""
    if "USD" in _rates_cache:
        return _rates_cache["USD"]

    api_key = settings.FXR_API_KEY or "fxr_demo_lmasdg193"
    url = f"https://api.fxratesapi.com/latest?api_key={api_key}&base=USD"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        if not data.get("success"):
            logger.warning("FXRatesAPI returned non-success: %s", data.get("error", "Unknown error"))
            return {}

        rates = {k: Decimal(str(v)) for k, v in data.get("rates", {}).items()}
        # Ensure USD itself is there
        if "USD" not in rates:
            rates["USD"] = Decimal("1.0")

        _rates_cache["USD"] = rates
        return rates
    except Exception:
        logger.exception("Failed to fetch exchange rates from FXRatesAPI")
        return {}


async def get_exchange_rates(base: str = "USD") -> dict[str, Decimal]:
    """
    Returns latest rates relative to requested 'base'.
    Calculates from USD base internally to avoid API plan restrictions.
    """
    base = base.upper()
    usd_rates = await _fetch_usd_rates()
    if not usd_rates:
        return {}

    if base == "USD":
        return usd_rates

    # If we need rates relative to RUB:
    # 1 RUB = (1/RUB_rate_to_USD) USD
    # 1 RUB = (1/RUB_rate_to_USD) * (CUR_rate_to_USD) CUR
    # New_Rate_CUR = CUR_rate_to_USD / RUB_rate_to_USD

    base_rate_to_usd = usd_rates.get(base)
    if not base_rate_to_usd:
        logger.warning("Base currency %s not found in USD rates", base)
        return {}

    return {k: (v / base_rate_to_usd).quantize(Decimal("0.00000001")) for k, v in usd_rates.items()}


def convert_amount(amount: Decimal, from_currency: str, to_currency: str, rates: dict[str, Decimal]) -> Decimal | None:
    """
    Converts amount using provided rates. 'rates' MUST be relative to some base.
    Formula: amount * (to_rate / from_rate)
    """
    from_c = from_currency.upper()
    to_c = to_currency.upper()

    if from_c == to_c:
        return amount

    # Regardless of what the rates are relative to, the ratio (to_rate / from_rate) is constant.
    rate_from = rates.get(from_c)
    rate_to = rates.get(to_c)

    if not rate_from or not rate_to:
        return None

    return (amount / rate_from) * rate_to


def clear_cache() -> None:
    _rates_cache.clear()
