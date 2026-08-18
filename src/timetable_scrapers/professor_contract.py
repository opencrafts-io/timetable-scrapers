from typing import Any, Dict, Iterable, List, Optional
import logging
import requests

from .schemas import CourseEntry
from datetime import datetime
logger = logging.getLogger(__name__)

INSTITUTION_ID_MAP: Dict[str, str] = {
    "kca": "123",
    "strath": "5461",
    "nursing_exams": "5426",
    "daystar": "5426",
}


def get_institution_id(scraper_name: str) -> str:
    """
    Map a scraper registry name to a stable institution ID.
    """
    institution_id = INSTITUTION_ID_MAP.get(scraper_name)
    if institution_id is None:
        available = ", ".join(sorted(INSTITUTION_ID_MAP.keys()))
        raise ValueError(
            f"Unknown scraper name: '{scraper_name}'. Available scrapers: {available}"
        )
    return institution_id


def get_semester(dt: Optional[datetime] = None) -> str:
    """
    Generate semester string based on month.
    Jan-Apr -> Jan, May-Aug -> May, Sept-Dec -> Sept
    Appends 2-digit year.
    """
    if dt is None:
        dt = datetime.now()
    year_suffix = str(dt.year)[-2:]
    month = dt.month
    if month <= 4:
        return f"Jan{year_suffix}"
    elif month <= 8:
        return f"May{year_suffix}"
    else:
        return f"Sept{year_suffix}"


def build_ingest_payload(
    scraper_name: str,
    entries: Iterable[CourseEntry],
    chunk_size: int = 5000,
) -> List[Dict[str, Any]]:
    """
    Build Professor API-compliant ingest payloads.

    Features:
        - Deduplicates by (institution_id, semester_id, course_code)
        - Chunks large batches if needed
        - Preserves last-write-wins for duplicates
    """
    institution_id = get_institution_id(scraper_name)
    current_semester = get_semester()

    entries_list = list(entries)
    if not entries_list:
        logger.warning("No entries to ingest")
        return []

    # Deduplicate entries (last-wins policy)
    deduplicated = {}
    for entry in entries_list:
        key = (institution_id, current_semester, entry.course_code)
        deduplicated[key] = entry

    if len(deduplicated) < len(entries_list):
        logger.info(
            f"Deduplicated {len(entries_list)} entries to {len(deduplicated)} "
            f"(removed {len(entries_list) - len(deduplicated)} duplicates)"
        )

    # Convert to dictionaries
    items = []
    for entry in deduplicated.values():
        d = entry.to_dict()
        
        # Validation based on data contract
        if not d.get("course_code"):
            raise ValueError(f"course_code is required and cannot be empty. Got: {d}")
        if not d.get("start_time"):
            raise ValueError(f"start_time is required. Got: {d}")
        if not d.get("end_time"):
            raise ValueError(f"end_time is required. Got: {d}")
        if not d.get("venue"):
            raise ValueError(f"venue is required and cannot be empty. Got: {d}")
        if not d.get("hrs"):
            raise ValueError(f"hrs is required. Got: {d}")
            
        d["institution"] = institution_id
        d["semester"] = current_semester
        items.append(d)

    # Chunk if necessary
    payloads = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i : i + chunk_size]
        payload = {
            "items": chunk,
        }
        payloads.append(payload)
        logger.info(f"Built payload with {len(chunk)} items")

    return payloads