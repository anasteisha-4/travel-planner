import re

DESTINATION_RU: dict[str, str] = {
    "Abu Dhabi": "Абу-Даби",
    "Agadir": "Агадир",
    "Agra": "Агра",
    "Aktau": "Актау",
    "Alanya": "Аланья",
    "Algarve": "Алгарве",
    "Algiers": "Алжир",
    "Almaty": "Алматы",
    "Amalfi Coast": "Амальфитанское побережье",
    "Amsterdam": "Амстердам",
    "Anapa": "Анапа",
    "Ankara": "Анкара",
    "Antalya": "Анталья",
    "Aqaba": "Акаба",
    "Arkhangelsk": "Архангельск",
    "Ashgabat": "Ашхабад",
    "Astana": "Астана",
    "Astrakhan": "Астрахань",
    "Athens": "Афины",
    "Azores": "Азорские острова",
    "Baku": "Баку",
    "Bali": "Бали",
    "Bangkok": "Бангкок",
    "Barcelona": "Барселона",
    "Beijing": "Пекин",
    "Berlin": "Берлин",
    "Blue Mountains": "Голубые горы",
    "Bodrum": "Бодрум",
    "Brussels": "Брюссель",
    "Bucharest": "Бухарест",
    "Budapest": "Будапешт",
    "Buenos Aires": "Буэнос-Айрес",
    "Cairo": "Каир",
    "Cancun": "Канкун",
    "Cape Town": "Кейптаун",
    "Cebu": "Себу",
    "Colombo": "Коломбо",
    "Copenhagen": "Копенгаген",
    "Crete": "Крит",
    "Delhi": "Дели",
    "Doha": "Доха",
    "Dubai": "Дубай",
    "Dushanbe": "Душанбе",
    "Edinburgh": "Эдинбург",
    "El Nido": "Эль-Нидо",
    "Florence": "Флоренция",
    "Frankfurt": "Франкфурт",
    "Fethiye": "Фетхие",
    "Fez": "Фес",
    "Guangzhou": "Гуанчжоу",
    "Hanoi": "Ханой",
    "Helsinki": "Хельсинки",
    "Hong Kong": "Гонконг",
    "Hurghada": "Хургада",
    "Iceland Blue Lagoon": "Голубая лагуна",
    "Istanbul": "Стамбул",
    "Jakarta": "Джакарта",
    "Jerusalem": "Иерусалим",
    "Kazan": "Казань",
    "Koh Samui": "Самуи",
    "Komodo": "Комодо",
    "Kyoto": "Киото",
    "Kuala Lumpur": "Куала-Лумпур",
    "Kutaisi": "Кутаиси",
    "Langkawi": "Лангкави",
    "Las Vegas": "Лас-Вегас",
    "Lisbon": "Лиссабон",
    "Lofoten Islands": "Лофотенские острова",
    "London": "Лондон",
    "Los Angeles": "Лос-Анджелес",
    "Madrid": "Мадрид",
    "Male": "Мале",
    "Maldives": "Мальдивы",
    "Marrakech": "Марракеш",
    "Mexico City": "Мехико",
    "Milan": "Милан",
    "Minsk": "Минск",
    "Moscow": "Москва",
    "Munich": "Мюнхен",
    "New York": "Нью-Йорк",
    "Nice": "Ницца",
    "Nizhniy Novgorod": "Нижний Новгород",
    "Osaka": "Осака",
    "Paris": "Париж",
    "Petra": "Петра",
    "Phuket": "Пхукет",
    "Porto": "Порту",
    "Prague": "Прага",
    "Reykjavik": "Рейкьявик",
    "Riga": "Рига",
    "Riyadh": "Эр-Рияд",
    "Rome": "Рим",
    "Samarkand": "Самарканд",
    "San Francisco": "Сан-Франциско",
    "Santorini": "Санторини",
    "Sapporo": "Саппоро",
    "Seoul": "Сеул",
    "Shanghai": "Шанхай",
    "Sharm El Sheikh": "Шарм-эш-Шейх",
    "Singapore": "Сингапур",
    "Sochi": "Сочи",
    "Stockholm": "Стокгольм",
    "Sydney": "Сидней",
    "Tallinn": "Таллин",
    "Tashkent": "Ташкент",
    "Tbilisi": "Тбилиси",
    "Tokyo": "Токио",
    "Ushuaia": "Ушуая",
    "Valletta": "Валлетта",
    "Venice": "Венеция",
    "Vienna": "Вена",
    "Warsaw": "Варшава",
    "Yerevan": "Ереван",
    "Zanzibar": "Занзибар",
    "Zurich": "Цюрих",
    "Amboseli": "Амбосели",
    "Budta": "Будта",
    "Camayenne": "Камайенн",
    "Chitwan": "Читван",
    "Colombo Fort": "Форт Коломбо",
    "El Aaiún": "Эль-Аюн",
    "Etosha": "Этоша",
    "Evaton": "Эватон",
    "Franz Josef": "Франц-Иосиф",
    "Kampung Baru Subang": "Кампунг-Бару-Субанг",
    "Kinosaki Onsen": "Киносаки-онсэн",
    "Landmannalaugar": "Ландманналёйгар",
    "Magome": "Магомэ",
    "Maldives South Ari": "Южный Ари-Атолл",
    "Mata-Utu": "Мата-Уту",
    "Nairobi Karen": "Карен, Найроби",
    "Natal Beach": "Натал",
    "Ngorongoro": "Нгоронгоро",
    "Olkhon": "Ольхон",
    "Pai": "Пай",
    "Port-aux-Français": "Порт-о-Франсе",
    "Rasapūdipalem": "Расапудипалем",
    "Rhine Valley": "Долина Рейна",
    "Rwanda Volcanoes": "Вулканы Руанды",
    "Shubrā al Khaymah": "Шубра-эль-Хейма",
    "Soshanguve": "Сошангуве",
    "Sulţānah": "Султана",
    "Talatona": "Талатона",
    "Tanzania Pemba": "о. Пемба",
    "Uganda Bwindi": "Бвинди",
    "Vang Vieng": "Ванг-Вьенг",
    "Whitsundays": "Уитсанди",
    "Yalata": "Ялата",
}

_CYRILLIC_RE = re.compile("[А-Яа-яЁё]")
_BAD_TRANSLATION_MARKERS = (
    "значения",
    "не путать",
)


def has_cyrillic(value: str | None) -> bool:
    return bool(value and _CYRILLIC_RE.search(value))


def translate_destination_name(name: str | None) -> str | None:
    if not name or has_cyrillic(name):
        return name
    if name in DESTINATION_RU:
        return DESTINATION_RU[name]
    replacements = [
        (" Islands", "ские острова"),
        (" Island", " остров"),
        (" Coast", "ское побережье"),
        (" Mountains", "ские горы"),
        (" National Park", " национальный парк"),
        (" City", ""),
    ]
    for suffix, ru_suffix in replacements:
        if name.endswith(suffix):
            base = name[: -len(suffix)]
            return f"{DESTINATION_RU.get(base, base)}{ru_suffix}"
    return name


def is_usable_destination_translation(original_name: str, translated_name: str | None, provider: str | None) -> bool:
    if not translated_name or translated_name == original_name:
        return False
    if not has_cyrillic(translated_name):
        return False
    normalized = translated_name.casefold()
    if any(marker in normalized for marker in _BAD_TRANSLATION_MARKERS):
        return False
    if "(" in translated_name or ")" in translated_name:
        return False
    return provider != "nominatim_reverse_ru"


def resolve_destination_display_name(
    original_name: str,
    translated_name: str | None,
    provider: str | None,
) -> str:
    if is_usable_destination_translation(original_name, translated_name, provider):
        return str(translated_name)
    local_name = translate_destination_name(original_name)
    if local_name and local_name != original_name and has_cyrillic(local_name):
        return local_name
    return original_name
