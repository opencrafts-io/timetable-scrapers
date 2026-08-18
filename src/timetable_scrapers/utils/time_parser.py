import re
from datetime import datetime, timedelta
from typing import Tuple
import logging

from ..schemas import CourseEntry

logger = logging.getLogger(__name__)

# Static offsets; none of these institutions' timezones observe DST.
TIMEZONE_OFFSETS_HOURS = {
    "UTC": 0,
    "EAT": 3,  # East Africa Time
}


def parse_exam_datetime(
    day_str: str,
    time_str: str,
    timezone_str: str = "UTC",
) -> str:
    """
    Convert day and time strings to ISO 8601 UTC format.

    Interprets day_str/time_str as local time in `timezone_str` and converts
    to UTC before appending the 'Z' suffix.
    Handles day strings like "MONDAY 20/04/26", "2026-04-20", "20/04/26", etc.

    Returns:
        ISO 8601 UTC datetime string (e.g., "2026-04-20T09:00:00Z")
        Returns empty string if parsing fails.
    """
    if not day_str or not time_str:
        logger.warning(f"Missing day_str or time_str: day={day_str}, time={time_str}")
        return ""

    try:
        clean_day = str(day_str).upper().strip()
        day_prefixes = [
            "WEDNESDAY", "THURSDAY", "SATURDAY", "MONDAY", "TUESDAY", "FRIDAY", "SUNDAY",
            "THURS", "WEDN", "WED", "THU", "MON", "TUE", "FRI", "SAT", "SUN",
        ]
        for prefix in day_prefixes:
            if clean_day.startswith(prefix):
                remaining = clean_day[len(prefix):].strip()
                if not remaining or remaining[0].isdigit() or remaining[0] in " /-, ":
                    clean_day = remaining
                    break

        clean_day = clean_day.lstrip(", ").strip()
        clean_day = re.sub(r'(\d+)(ST|ND|RD|TH)\b', r'\1', clean_day)
        clean_day = re.sub(r'\s+', ' ', clean_day).strip()

        day_formats = [
            "%d/%m/%y",   # 20/04/26
            "%d/%m/%Y",   # 20/04/2026
            "%Y-%m-%d",   # 2026-04-20
            "%d-%m-%Y",   # 20-04-2026
            "%d-%m-%y",   # 20-04-26
            "%d %b %Y",   # 20 Apr 2026
            "%d %B %Y",   # 20 April 2026
        ]
        day_obj = None
        for fmt in day_formats:
            try:
                day_obj = datetime.strptime(clean_day, fmt)
                break
            except ValueError:
                continue

        if not day_obj:
            logger.warning(f"Unable to parse day: '{day_str}' (cleaned: '{clean_day}')")
            return ""

        time_clean = str(time_str).replace('.', ':').replace(' ', '').upper()

        # Try multiple time formats
        time_formats = [
            "%I:%M%p",  # 9:00AM, 11:00PM
            "%I%p",     # 9AM
            "%H:%M",    # 14:00
            "%H%M",     # 1400
        ]
        time_obj = None
        for tfmt in time_formats:
            try:
                time_obj = datetime.strptime(time_clean, tfmt).time()
                break
            except ValueError:
                continue

        if not time_obj:
            logger.warning(f"Unable to parse time: '{time_str}' (cleaned: '{time_clean}')")
            return ""

        offset_hours = TIMEZONE_OFFSETS_HOURS.get(timezone_str.upper())
        if offset_hours is None:
            logger.warning(f"Unknown timezone '{timezone_str}', treating as UTC")
            offset_hours = 0

        local_dt = datetime.combine(day_obj.date(), time_obj)
        utc_dt = local_dt - timedelta(hours=offset_hours)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    except Exception as e:
        logger.warning(f"Failed to parse datetime: day={day_str}, time={time_str}: {e}")
        return ""


def calculate_duration(start_iso: str, end_iso: str) -> str:
    """
    Calculate duration between two ISO 8601 timestamps.

    Returns:
        Duration string (e.g., "2 hours") or empty string if invalid.
    """
    try:
        start = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))

        total_seconds = (end - start).total_seconds()

        if total_seconds < 0:
            logger.warning(f"end_time before start_time: {start_iso} to {end_iso}")
            return ""

        hours = total_seconds / 3600

        return str(hours)

    except Exception as e:
        logger.warning(f"Failed to calculate duration: {e}")
        return ""


def validate_entry(entry: CourseEntry) -> Tuple[bool, str]:
    """
    Validate CourseEntry against Professor API contract.

    Returns:
        (is_valid, error_message)
    """
    if not entry.course_code or not entry.course_code.strip():
        return False, "course_code cannot be empty"

    if not entry.venue or not entry.venue.strip():
        return False, "venue cannot be empty"

    if not entry.start_time:
        return False, "start_time is required"

    if not entry.end_time:
        return False, "end_time is required"
    try:
        start = datetime.fromisoformat(entry.start_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(entry.end_time.replace('Z', '+00:00'))

        if end <= start:
            return False, "end_time must be after start_time"
    except ValueError:
        return False, "start_time and end_time must be valid ISO 8601 format"

    return True, ""
