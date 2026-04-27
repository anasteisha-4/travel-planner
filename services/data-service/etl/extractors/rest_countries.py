"""Extract country data from REST Countries API."""

import logging

import httpx

logger = logging.getLogger(__name__)

REST_COUNTRIES_URL = (
    "https://restcountries.com/v3.1/all"
    "?fields=name,cca2,latlng,capitalInfo,region,subregion,capital,population,currencies"
)

REST_COUNTRIES_LANGUAGES_URL = "https://restcountries.com/v3.1/all?fields=cca2,languages"


def extract_countries() -> list[dict]:
    """Fetch all countries from REST Countries API."""
    with httpx.Client(timeout=30) as client:
        response = client.get(REST_COUNTRIES_URL)
        response.raise_for_status()
        data = response.json()
    logger.info(f"Fetched {len(data)} countries from REST Countries API.")
    return data


def extract_country_languages() -> dict[str, list[str]]:
    """Return {country_code_upper: [iso_639_1_code, ...]} from REST Countries.

    REST Countries uses ISO 639-3 keys (e.g. "eng", "fra").  They are mapped
    to ISO 639-1 (2-letter) codes via a curated lookup table; unknown codes
    are dropped to keep the list clean.
    """
    # ISO 639-3 → ISO 639-1 for the languages that appear in REST Countries
    _639_3_TO_1: dict[str, str] = {
        "afr": "af",
        "aka": "ak",
        "amh": "am",
        "ara": "ar",
        "arb": "ar",
        "aym": "ay",
        "aze": "az",
        "bak": "ba",
        "bel": "be",
        "ben": "bn",
        "bis": "bi",
        "bos": "bs",
        "bul": "bg",
        "cat": "ca",
        "ces": "cs",
        "cha": "ch",
        "che": "ce",
        "chv": "cv",
        "cor": "kw",
        "cos": "co",
        "cre": "cr",
        "cym": "cy",
        "dan": "da",
        "deu": "de",
        "div": "dv",
        "dzo": "dz",
        "ell": "el",
        "eng": "en",
        "epo": "eo",
        "est": "et",
        "eus": "eu",
        "fas": "fa",
        "fij": "fj",
        "fin": "fi",
        "fra": "fr",
        "fry": "fy",
        "gle": "ga",
        "glg": "gl",
        "glv": "gv",
        "grn": "gn",
        "guj": "gu",
        "hat": "ht",
        "hau": "ha",
        "hbs": "sr",
        "heb": "he",
        "her": "hz",
        "hin": "hi",
        "hmo": "ho",
        "hrv": "hr",
        "hun": "hu",
        "hye": "hy",
        "ibo": "ig",
        "iii": "ii",
        "iku": "iu",
        "ile": "ie",
        "ina": "ia",
        "ind": "id",
        "ipk": "ik",
        "isl": "is",
        "ita": "it",
        "jav": "jv",
        "jpn": "ja",
        "kal": "kl",
        "kan": "kn",
        "kas": "ks",
        "kat": "ka",
        "kau": "kr",
        "kaz": "kk",
        "khm": "km",
        "kik": "ki",
        "kin": "rw",
        "kir": "ky",
        "kom": "kv",
        "kon": "kg",
        "kor": "ko",
        "kua": "kj",
        "kur": "ku",
        "lao": "lo",
        "lat": "la",
        "lav": "lv",
        "lim": "li",
        "lin": "ln",
        "lit": "lt",
        "lub": "lu",
        "lug": "lg",
        "mah": "mh",
        "mal": "ml",
        "mar": "mr",
        "mkd": "mk",
        "mlg": "mg",
        "mlt": "mt",
        "mon": "mn",
        "mri": "mi",
        "msa": "ms",
        "mya": "my",
        "nau": "na",
        "nav": "nv",
        "nbl": "nr",
        "nde": "nd",
        "ndo": "ng",
        "nep": "ne",
        "nld": "nl",
        "nno": "nn",
        "nob": "nb",
        "nor": "no",
        "nya": "ny",
        "oci": "oc",
        "oji": "oj",
        "ori": "or",
        "orm": "om",
        "oss": "os",
        "pan": "pa",
        "pli": "pi",
        "pol": "pl",
        "por": "pt",
        "pus": "ps",
        "que": "qu",
        "roh": "rm",
        "ron": "ro",
        "run": "rn",
        "rus": "ru",
        "sag": "sg",
        "san": "sa",
        "sin": "si",
        "slk": "sk",
        "slv": "sl",
        "sme": "se",
        "smo": "sm",
        "sna": "sn",
        "snd": "sd",
        "som": "so",
        "sot": "st",
        "spa": "es",
        "sqi": "sq",
        "srd": "sc",
        "srp": "sr",
        "ssw": "ss",
        "sun": "su",
        "swa": "sw",
        "swe": "sv",
        "tah": "ty",
        "tam": "ta",
        "tat": "tt",
        "tel": "te",
        "tgk": "tg",
        "tgl": "tl",
        "tha": "th",
        "tir": "ti",
        "ton": "to",
        "tsn": "tn",
        "tso": "ts",
        "tuk": "tk",
        "tur": "tr",
        "twi": "tw",
        "uig": "ug",
        "ukr": "uk",
        "urd": "ur",
        "uzb": "uz",
        "ven": "ve",
        "vie": "vi",
        "vol": "vo",
        "wln": "wa",
        "wol": "wo",
        "xho": "xh",
        "yid": "yi",
        "yor": "yo",
        "zha": "za",
        "zho": "zh",
        "zsm": "ms",
        "zul": "zu",
        # extra variants seen in REST Countries data
        "fil": "tl",
        "pes": "fa",
        "cnr": "sr",
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(REST_COUNTRIES_LANGUAGES_URL)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"REST Countries languages fetch failed: {e}")
        return {}

    result: dict[str, list[str]] = {}
    for entry in data:
        cc = entry.get("cca2", "").upper()
        if not cc:
            continue
        langs_raw: dict = entry.get("languages", {})
        langs_639_1 = []
        seen: set[str] = set()
        for code_3 in langs_raw:
            code_1 = _639_3_TO_1.get(code_3.lower())
            if code_1 and code_1 not in seen:
                langs_639_1.append(code_1)
                seen.add(code_1)
        result[cc] = langs_639_1

    logger.info(f"Extracted languages for {len(result)} countries.")
    return result
