from typing import Any, Dict, Iterable, List, Optional
import logging
import requests

from .schemas import CourseEntry

logger = logging.getLogger(__name__)

INSTITUTION_ID_MAP: Dict[str, str] = {
    "kca": "123",
    "strath": "5461",
    "nursing_exams": "5426",
    "school_exams": "5426",
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


def build_ingest_payload(
    institution_id: str,
    entries: Iterable[CourseEntry],
    semester_id: Optional[int] = None,
    chunk_size: int = 5000,
) -> List[Dict[str, Any]]:
    """
    Build Professor API-compliant ingest payloads.

    Features:
        - Deduplicates by (institution_id, semester_id, course_code)
        - Chunks large batches if needed
        - Preserves last-write-wins for duplicates
    """
    if not institution_id:
        raise ValueError("institution_id is required")

    entries_list = list(entries)
    if not entries_list:
        logger.warning("No entries to ingest")
        return []

    # Deduplicate entries (last-wins policy)
    deduplicated = {}
    for entry in entries_list:
        key = (institution_id, semester_id, entry.course_code)
        deduplicated[key] = entry

    if len(deduplicated) < len(entries_list):
        logger.info(
            f"Deduplicated {len(entries_list)} entries to {len(deduplicated)} "
            f"(removed {len(entries_list) - len(deduplicated)} duplicates)"
        )

    # Convert to dictionaries
    items = [entry.to_dict() for entry in deduplicated.values()]

    # Chunk if necessary
    payloads = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i : i + chunk_size]
        payload = {
            "institution_id": institution_id,
            "semester_id": semester_id,
            "items": chunk,
        }
        payloads.append(payload)
        logger.info(f"Built payload with {len(chunk)} items")

    return payloads


def send_to_professor(
    payloads: List[Dict[str, Any]],
    api_url: str,
    api_token: str,
) -> Dict[str, Any]:
    """
    Send ingest payloads to Professor API.
    """
    total_created = 0
    total_updated = 0
    errors = []

    for idx, payload in enumerate(payloads):
        try:
            logger.info(
                f"Sending payload {idx + 1}/{len(payloads)} ({len(payload['items'])} items)"
            )

            response = requests.post(
                api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_token}",
                },
                timeout=30,
            )

            response.raise_for_status()

            result = response.json()
            total_created += result.get("created_count", 0)
            total_updated += result.get("updated_count", 0)

            logger.info(
                f"Payload {idx + 1}: Created {result.get('created_count', 0)}, "
                f"Updated {result.get('updated_count', 0)}"
            )

        except requests.exceptions.RequestException as e:
            error_msg = f"Payload {idx + 1}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        "total_created": total_created,
        "total_updated": total_updated,
        "payloads_sent": len(payloads),
        "errors": errors,
    }
