SUPPORTED_CURRENCY_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.93,
    "RUB": 90.0,
    "GBP": 0.79,
    "AED": 3.67,
    "TRY": 32.0,
    "THB": 36.0,
    "CNY": 7.2,
    "JPY": 150.0,
    "KZT": 450.0,
    "GEL": 2.65,
    "AMD": 395.0,
}


def normalize_currency(currency: str | None) -> str:
    code = (currency or "USD").upper()
    return code if code in SUPPORTED_CURRENCY_RATES else "USD"


def convert_usd(amount_usd: float | None, currency: str | None) -> float | None:
    if amount_usd is None:
        return None
    return round(amount_usd * SUPPORTED_CURRENCY_RATES[normalize_currency(currency)], 2)
