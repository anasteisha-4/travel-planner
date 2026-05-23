"""
Opening hours parser for POI filtering in itineraries.

Supports simplified OSM opening_hours format:
- "24/7" → always open
- "Mo-Su HH:MM-HH:MM" → parse day ranges and hours
- "Su off" → closed on Sundays
- Fallback: assume open if format not recognized
"""

import re
from datetime import datetime, time


class OpeningHoursParser:
    DAYS_MAPPING = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}

    @staticmethod
    def _parse_time(hour: str, minute: str, *, is_close: bool = False) -> time | None:
        hour_int = int(hour)
        minute_int = int(minute)
        if minute_int < 0 or minute_int > 59:
            return None
        if hour_int == 24 and is_close:
            return time(23, 59)
        if hour_int > 24 and is_close:
            return time(23, 59)
        if hour_int < 0 or hour_int > 23:
            return None
        return time(hour_int, minute_int)

    @staticmethod
    def is_open(opening_hours: str | None, dt: datetime) -> bool:
        """
        Check if POI is open at given datetime.

        Args:
            opening_hours: OSM opening_hours string (or None)
            dt: datetime to check

        Returns:
            True if open (or unknown), False if definitively closed
        """
        if not opening_hours or opening_hours.strip() == "":
            return True  # Assume open if no data

        opening_hours = opening_hours.strip()

        # Special case: 24/7
        if opening_hours == "24/7":
            return True

        # Parse simplified format: "Mo-Su HH:MM-HH:MM"
        match = re.match(r"(\w{2})-(\w{2})\s+(\d{2}):(\d{2})-(\d{2}):(\d{2})", opening_hours)
        if match:
            day_start_str, day_end_str, h_open, m_open, h_close, m_close = match.groups()

            day_start = OpeningHoursParser.DAYS_MAPPING.get(day_start_str)
            day_end = OpeningHoursParser.DAYS_MAPPING.get(day_end_str)

            if day_start is None or day_end is None:
                return True  # Unknown format, assume open

            current_day = dt.weekday()
            current_time = dt.time()

            open_time = OpeningHoursParser._parse_time(h_open, m_open)
            close_time = OpeningHoursParser._parse_time(h_close, m_close, is_close=True)
            if open_time is None or close_time is None:
                return True

            # Check if day is in range
            day_in_range = (
                (day_start <= current_day <= day_end)
                if day_start <= day_end
                else (current_day >= day_start or current_day <= day_end)
            )

            if not day_in_range:
                return False

            # Check if time is in range
            return open_time <= current_time < close_time

        # Parse "HH:MM-HH:MM" pattern (without specific days, applies all days)
        match = re.match(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$", opening_hours)
        if match:
            h_open, m_open, h_close, m_close = match.groups()
            current_time = dt.time()

            open_time = OpeningHoursParser._parse_time(h_open, m_open)
            close_time = OpeningHoursParser._parse_time(h_close, m_close, is_close=True)
            if open_time is None or close_time is None:
                return True
            return open_time <= current_time < close_time

        # Handle "off" days: "Su off", "Mo off"
        if " off" in opening_hours:
            # Simple: if string contains day + "off", check if today is that day
            for day_code in OpeningHoursParser.DAYS_MAPPING:
                if f"{day_code} off" in opening_hours and OpeningHoursParser.DAYS_MAPPING[day_code] == dt.weekday():
                    return False
            return True

        # Default: assume open if we can't parse
        return True

    @staticmethod
    def validate_format(opening_hours: str) -> bool:
        """
        Validate if opening_hours string is in expected format.
        Used for sanity checks.
        """
        if not opening_hours or opening_hours.strip() == "":
            return True

        opening_hours = opening_hours.strip()

        # Check against patterns
        patterns = [
            r"^24/7$",
            r"^\w{2}-\w{2}\s+\d{2}:\d{2}-\d{2}:\d{2}$",
            r"^\d{2}:\d{2}-\d{2}:\d{2}$",
            r"^(\w{2}\s+off)(,\s*\w{2}\s+off)*$",
        ]

        for pattern in patterns:
            if re.match(pattern, opening_hours):
                return True

        # Still valid if it contains some expected patterns
        return bool(re.search(r"\d{2}:\d{2}", opening_hours) or "24/7" in opening_hours)
