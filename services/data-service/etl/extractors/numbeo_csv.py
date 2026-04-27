"""Extract cost data from Numbeo CSV and cities supplement CSV."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def extract_costs() -> pd.DataFrame:
    """Load Numbeo cost data from CSV.

    Expected columns: city_name, country_code, meal_mid_usd, transport_day_usd, hotel_3star_usd
    """
    path = DATA_DIR / "numbeo_costs.csv"
    if not path.exists():
        raise FileNotFoundError(f"Numbeo CSV not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df)} rows from {path}")
    return df


def extract_cities_supplement() -> pd.DataFrame:
    """Load supplementary tourism cities (non-capitals) from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population
    """
    path = DATA_DIR / "cities_supplement.csv"
    if not path.exists():
        logger.warning(f"Cities supplement CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} supplementary cities from {path}")
    return df


def extract_russia_cities_phase2() -> pd.DataFrame:
    """Load Russian cities Phase 2 expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    """
    path = DATA_DIR / "russia_cities_phase2.csv"
    if not path.exists():
        logger.warning(f"Russia Phase 2 cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Russian cities from Phase 2 file from {path}")
    return df


def extract_cis_cities_phase2b() -> pd.DataFrame:
    """Load CIS cities Phase 2B expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    """
    path = DATA_DIR / "cis_cities_phase2b.csv"
    if not path.exists():
        logger.warning(f"CIS Phase 2B cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} CIS cities from Phase 2B file from {path}")
    return df


def extract_turkey_resorts_phase2c() -> pd.DataFrame:
    """Load Turkey resorts Phase 2C expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    """
    path = DATA_DIR / "turkey_resorts_phase2c.csv"
    if not path.exists():
        logger.warning(f"Turkey Phase 2C resorts CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Turkey resorts from Phase 2C file from {path}")
    return df


def extract_north_africa_phase2d() -> pd.DataFrame:
    """Load North Africa cities Phase 2D expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    """
    path = DATA_DIR / "north_africa_phase2d.csv"
    if not path.exists():
        logger.warning(f"North Africa Phase 2D cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} North Africa cities from Phase 2D file from {path}")
    return df


def extract_global_cities_phase2e() -> pd.DataFrame:
    """Load global top cities Phase 2E expansion from GeoNames-sourced CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Source: GeoNames cities15000 dataset (CC-BY), filtered to pop>=500k, top cities per country.
    """
    path = DATA_DIR / "global_cities_phase2e.csv"
    if not path.exists():
        logger.warning(f"Global cities Phase 2E CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} global cities from Phase 2E file from {path}")
    return df


def extract_sea_cities_phase2f() -> pd.DataFrame:
    """Load South-East Asia / Indian Ocean cities Phase 2F expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Bali (Ubud/Seminyak/Nusa Penida/Kuta), Sri Lanka, Thailand islands,
    Vietnam resorts, Myanmar (Bagan), Laos, Philippines islands, Maldives, Seychelles.
    """
    path = DATA_DIR / "sea_cities_phase2f.csv"
    if not path.exists():
        logger.warning(f"SEA Phase 2F cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} SEA/Indian Ocean cities from Phase 2F file from {path}")
    return df


def extract_china_cities_phase2g() -> pd.DataFrame:
    """Load China tourist cities Phase 2G expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: scenic/nature (Zhangjiajie, Huangshan, Jiuzhaigou, Zhangye), Tibet (Lhasa),
    Yunnan (Lijiang, Dali, Shangri-La), Hainan (Sanya), historic (Pingyao, Chengde, Dunhuang),
    Silk Road (Kashgar), Guangxi (Yangshuo), business/culture (Suzhou).
    """
    path = DATA_DIR / "china_cities_phase2g.csv"
    if not path.exists():
        logger.warning(f"China Phase 2G cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} China tourist cities from Phase 2G file from {path}")
    return df


def extract_japan_cities_phase2h() -> pd.DataFrame:
    """Load Japan tourist cities Phase 2H expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Nara, Hakone, Takayama, Kanazawa, Nikko, Hiroshima, Nagasaki, Fukuoka,
    Nagoya, Sapporo, Matsumoto, Beppu (onsen), Miyajima, Kamakura, Okinawa.
    """
    path = DATA_DIR / "japan_cities_phase2h.csv"
    if not path.exists():
        logger.warning(f"Japan Phase 2H cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Japan tourist cities from Phase 2H file from {path}")
    return df


def extract_middle_east_cities_phase2i() -> pd.DataFrame:
    """Load Middle East cities Phase 2I expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: UAE (Abu Dhabi), Jordan (Petra, Wadi Rum, Aqaba, Amman), Israel (Jerusalem, Tel Aviv),
    Oman (Muscat, Salalah), Saudi Arabia (Al Ula, Riyadh, Jeddah), Qatar (Doha), Lebanon (Beirut).
    """
    path = DATA_DIR / "middle_east_cities_phase2i.csv"
    if not path.exists():
        logger.warning(f"Middle East Phase 2I cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Middle East cities from Phase 2I file from {path}")
    return df


def extract_japan_extra_phase2h() -> pd.DataFrame:
    """Load extra Japan tourist destinations Phase 2H expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Yakushima (UNESCO), Kinosaki Onsen, Magome (Kiso Valley).
    """
    path = DATA_DIR / "japan_extra_phase2h.csv"
    if not path.exists():
        logger.warning(f"Japan extra Phase 2H cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} extra Japan cities from Phase 2H file from {path}")
    return df


def extract_middle_east_extra_phase2i() -> pd.DataFrame:
    """Load extra Middle East tourist destinations Phase 2I expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Jerash (JO, Roman ruins), Dead Sea (JO), Nizwa (OM, fort/souq).
    """
    path = DATA_DIR / "middle_east_extra_phase2i.csv"
    if not path.exists():
        logger.warning(f"Middle East extra Phase 2I cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} extra Middle East cities from Phase 2I file from {path}")
    return df


def extract_south_asia_phase2j() -> pd.DataFrame:
    """Load South Asia tourist cities Phase 2J expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: India (Jaipur, Goa, Kerala, Varanasi, Rishikesh, Agra, Udaipur, Amritsar, Darjeeling,
    Mysore, Hampi, Leh, Manali, Shimla, Pushkar, Jodhpur, Kochi, Kolkata, Hyderabad, Ahmedabad,
    Varkala, Pondicherry, Coorg, Ooty),
    Sri Lanka (Colombo, Kandy, Sigiriya, Ella, Trincomalee, Galle, Mirissa, Anuradhapura, Jaffna,
    Nuwara Eliya),
    Nepal (Kathmandu, Pokhara, Chitwan, Namche Bazaar),
    Maldives (Male, Baa Atoll),
    Bangladesh (Dhaka, Chittagong, Cox's Bazar),
    Bhutan (Bhutan, Paro),
    Pakistan (Lahore, Islamabad, Hunza, Skardu).
    """
    path = DATA_DIR / "south_asia_phase2j.csv"
    if not path.exists():
        logger.warning(f"South Asia Phase 2J cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} South Asia tourist cities from Phase 2J file from {path}")
    return df


def extract_latin_america_phase2k() -> pd.DataFrame:
    """Load Latin America tourist cities Phase 2K expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Mexico (Mexico City, Cancun, Tulum, Playa del Carmen, Oaxaca, Guadalajara,
    San Cristobal, Guanajuato, Merida, Chichen Itza),
    Brazil (Rio, Sao Paulo, Salvador, Florianopolis, Foz do Iguacu, Manaus, Recife, Natal,
    Fortaleza, Belem, Porto Alegre, Belo Horizonte, Maceio),
    Argentina (Buenos Aires, Mendoza, Bariloche, Ushuaia, Salta, Cordoba, Iguazu Falls),
    Peru (Lima, Cusco, Machu Picchu, Arequipa, Iquitos, Puno, Trujillo),
    Colombia (Medellin, Cartagena, Bogota, Cali, Santa Marta, Barranquilla),
    Chile (Santiago, Valparaiso, Atacama, Torres del Paine, Puerto Natales, Valdivia, Punta Arenas),
    Ecuador (Quito, Galapagos, Cuenca, Manta),
    Bolivia (La Paz, Sucre, Uyuni),
    Uruguay (Montevideo), Paraguay (Asuncion, Encarnacion),
    Cuba (Havana, Trinidad, Varadero),
    Dominican Republic (Punta Cana),
    Panama (Panama City), Costa Rica (San Jose),
    Venezuela (Caracas, Maracaibo),
    Guatemala (Antigua, Guatemala City), Central America (San Salvador, Tegucigalpa, Managua).
    """
    path = DATA_DIR / "latin_america_phase2k.csv"
    if not path.exists():
        logger.warning(f"Latin America Phase 2K cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Latin America tourist cities from Phase 2K file from {path}")
    return df


def extract_north_america_phase2l() -> pd.DataFrame:
    """Load North America cities Phase 2L expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: USA (Portland, Denver, Nashville, Atlanta, Boston, Minneapolis, Detroit, Memphis,
    Baltimore, Louisville, Oklahoma City, Albuquerque, Tucson, Fresno, Sacramento,
    Colorado Springs, Kansas City, Raleigh, Virginia Beach, Omaha, Tampa, Sedona, Key West,
    Savannah, Maui, Kauai, Big Island, national parks),
    Canada (Quebec City, Victoria, Halifax, Banff, Jasper, Whistler, Niagara Falls).
    """
    path = DATA_DIR / "north_america_phase2l.csv"
    if not path.exists():
        logger.warning(f"North America Phase 2L cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} North America Phase 2L cities from {path}")
    return df


def extract_europe_phase2m() -> pd.DataFrame:
    """Load Europe missing segments Phase 2M expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Portugal (Madeira, Algarve, Sintra, Azores), Italy (Amalfi, Cinque Terre, Bologna,
    Verona, Siena, Bari, Sardinia, Sicily, Dolomites), Spain (Malaga, San Sebastian, Bilbao,
    Mallorca, Ibiza, Cordoba, Granada, Toledo, Canary Islands), France (Nantes, Strasbourg,
    Versailles, Provence, Alsace), Germany (Rhine Valley, Dresden, Nuremberg, Heidelberg,
    Bavarian Alps), Benelux, Ireland, Scandinavia, Baltics, Eastern Europe.
    """
    path = DATA_DIR / "europe_phase2m.csv"
    if not path.exists():
        logger.warning(f"Europe Phase 2M cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Europe Phase 2M cities from {path}")
    return df


def extract_oceania_phase2n() -> pd.DataFrame:
    """Load Oceania cities Phase 2N expansion from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Australia (Cairns, Darwin, Hobart, Uluru, Great Barrier Reef, Byron Bay, Broome,
    Whitsundays, Blue Mountains), New Zealand (Rotorua, Milford Sound, Nelson, Wanaka),
    Pacific Islands (Fiji, French Polynesia/Bora Bora/Tahiti, Palau, Vanuatu, etc.).
    """
    path = DATA_DIR / "oceania_phase2n.csv"
    if not path.exists():
        logger.warning(f"Oceania Phase 2N cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Oceania Phase 2N cities from {path}")
    return df


def extract_africa_phase2o() -> pd.DataFrame:
    """Load Africa expansion Phase 2O from CSV.

    Expected columns: name, country_code, lat, lng, region, subregion, population, radius_m
    Covers: Morocco (Marrakech, Fes, Casablanca, Chefchaouen, Sahara),
    Egypt (Luxor, Aswan, Siwa), Kenya (Masai Mara, Amboseli, Lamu, Diani Beach),
    Tanzania (Zanzibar, Kilimanjaro, Ngorongoro), South Africa (Winelands, Garden Route,
    Kruger), Zimbabwe/Botswana (Victoria Falls, Okavango), Namibia (Sossusvlei, Etosha),
    Indian Ocean islands (Mauritius, Seychelles, Reunion), Ethiopia cultural sites.
    """
    path = DATA_DIR / "africa_phase2o.csv"
    if not path.exists():
        logger.warning(f"Africa Phase 2O cities CSV not found: {path}, skipping.")
        return pd.DataFrame()
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} Africa Phase 2O cities from {path}")
    return df
