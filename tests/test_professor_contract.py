import pytest

from timetable_scrapers import CourseEntry
from timetable_scrapers.professor_contract import (
    ALLOWED_ITEM_KEYS,
    build_ingest_payload,
    course_entry_to_professor_item,
    get_institution_id,
)
from timetable_scrapers.utils.structured_datetime import (
    parse_exam_date,
    parse_time_range_24h,
)


def test_parse_exam_date_text_format():
    assert parse_exam_date("Saturday 6th December 2025") == "2025-12-06"
    assert parse_exam_date("13th December 2025") == "2025-12-13"
    assert parse_exam_date("1st January 2026") == "2026-01-01"


def test_parse_exam_date_iso_format():
    assert parse_exam_date("2025-12-01") == "2025-12-01"
    assert parse_exam_date("2025-12-01 00:00:00") == "2025-12-01"


def test_parse_exam_date_slash_format():
    assert parse_exam_date("Mon 12/02/26") == "2026-02-12"
    assert parse_exam_date("12/02/2026") == "2026-02-12"
    assert parse_exam_date("01/01/2025") == "2025-01-01"


def test_parse_exam_date_invalid():
    assert parse_exam_date("") is None
    assert parse_exam_date("invalid date") is None
    assert parse_exam_date("not a date string") is None
    assert parse_exam_date(None) is None


def test_parse_time_range_24h_12hour_format():
    start, end = parse_time_range_24h("8:30AM-11:30AM")
    assert start == "08:30"
    assert end == "11:30"

    start, end = parse_time_range_24h("2:00PM-4:00PM")
    assert start == "14:00"
    assert end == "16:00"


def test_parse_time_range_24h_24hour_format():
    start, end = parse_time_range_24h("08:00-10:00")
    assert start == "08:00"
    assert end == "10:00"

    start, end = parse_time_range_24h("14:30-16:30")
    assert start == "14:30"
    assert end == "16:30"


def test_parse_time_range_24h_hrs_suffix():
    start, end = parse_time_range_24h("0800-1000 HRS")
    assert start == "08:00"
    assert end == "10:00"


def test_parse_time_range_24h_dot_separator():
    start, end = parse_time_range_24h("2.30 pm - 4.30pm")
    assert start == "14:30"
    assert end == "16:30"


def test_parse_time_range_24h_single_time():
    start, end = parse_time_range_24h("8:00AM")
    assert start == "08:00"
    assert end is None


def test_parse_time_range_24h_invalid():
    start, end = parse_time_range_24h("")
    assert start is None
    assert end is None

    start, end = parse_time_range_24h("invalid")
    assert start is None
    assert end is None


def test_course_entry_to_professor_item_removes_datetime_str():
    entry = CourseEntry(
        course_code="CSC 101",
        day="Monday",
        time="9:00AM-11:00AM",
        datetime_str="2025-01-01T09:00:00Z",
    )
    item = course_entry_to_professor_item(entry)
    assert "datetime_str" not in item
    assert item["course_code"] == "CSC 101"


def test_course_entry_to_professor_item_moves_datetime_str_to_raw_data():
    entry = CourseEntry(
        course_code="CSC 101",
        datetime_str="2025-01-01T09:00:00Z",
    )
    item = course_entry_to_professor_item(entry)
    assert "datetime_str" not in item
    assert item["raw_data"]["datetime_str"] == "2025-01-01T09:00:00Z"


def test_course_entry_to_professor_item_only_allowed_keys():
    entry = CourseEntry(
        course_code="CSC 101",
        day="Monday",
        time="9:00AM-11:00AM",
        venue="Room 101",
        campus="Main",
        coordinator="Dr. Smith",
        hrs="2",
        invigilator="Dr. Jones",
        course_name="Introduction to CS",
        datetime_str="2025-01-01T09:00:00Z",
    )
    item = course_entry_to_professor_item(entry)
    for key in item.keys():
        assert key in ALLOWED_ITEM_KEYS, f"Key '{key}' is not in allowed keys"


def test_course_entry_to_professor_item_with_structured_datetime():
    entry = CourseEntry(
        course_code="CSC 101",
        day="Monday 1st January 2025",
        time="9:00AM-11:00AM",
    )
    item = course_entry_to_professor_item(
        entry,
        exam_date="2025-01-01",
        start_time="09:00",
        end_time="11:00",
    )
    assert item["exam_date"] == "2025-01-01"
    assert item["start_time"] == "09:00"
    assert item["end_time"] == "11:00"
    assert item["day"] == "Monday 1st January 2025"
    assert item["time"] == "9:00AM-11:00AM"


def test_course_entry_to_professor_item_omits_empty_values():
    entry = CourseEntry(
        course_code="CSC 101",
        day="",
        time="",
        venue="",
        campus="",
    )
    item = course_entry_to_professor_item(entry)
    assert "day" not in item or item["day"] == ""
    assert "time" not in item or item["time"] == ""
    assert "venue" not in item
    assert "campus" not in item


def test_course_entry_to_professor_item_requires_course_code():
    entry = CourseEntry(course_code="")
    with pytest.raises(ValueError, match="course_code is required"):
        course_entry_to_professor_item(entry)

    entry = CourseEntry(course_code="   ")
    with pytest.raises(ValueError, match="course_code is required"):
        course_entry_to_professor_item(entry)


def test_get_institution_id_mapping():
    assert get_institution_id("kca") == "123"
    assert get_institution_id("strath") == "456"
    assert get_institution_id("nursing_exams") == "789"
    assert get_institution_id("daystar") == "789"


def test_get_institution_id_unknown_scraper():
    with pytest.raises(ValueError, match="Unknown scraper name"):
        get_institution_id("unknown_scraper")


def test_build_ingest_payload_structure():
    entries = [
        CourseEntry(
            course_code="CSC 101",
            day="Monday 1st January 2025",
            time="9:00AM-11:00AM",
        )
    ]
    payloads = build_ingest_payload(
        institution_id="123",
        semester_id=12,
        entries=entries,
    )
    assert len(payloads) == 1
    payload = payloads[0]
    assert "institution_id" in payload
    assert payload["institution_id"] == "123"
    assert "semester_id" in payload
    assert payload["semester_id"] == 12
    assert "items" in payload
    assert len(payload["items"]) == 1
    assert payload["items"][0]["course_code"] == "CSC 101"


def test_build_ingest_payload_without_semester_id():
    entries = [
        CourseEntry(
            course_code="CSC 101",
            day="Monday 1st January 2025",
            time="9:00AM-11:00AM",
        )
    ]
    payloads = build_ingest_payload(
        institution_id="123",
        semester_id=None,
        entries=entries,
    )
    assert len(payloads) == 1
    payload = payloads[0]
    assert "institution_id" in payload
    assert "semester_id" not in payload
    assert "items" in payload


def test_build_ingest_payload_deduplication():
    entries = [
        CourseEntry(course_code="CSC 101", day="Monday", time="9:00AM"),
        CourseEntry(course_code="CSC 101", day="Tuesday", time="10:00AM"),
        CourseEntry(course_code="CSC 102", day="Wednesday", time="11:00AM"),
    ]
    payloads = build_ingest_payload(
        institution_id="123",
        semester_id=12,
        entries=entries,
    )
    assert len(payloads) == 1
    payload = payloads[0]
    assert len(payload["items"]) == 2
    course_codes = [item["course_code"] for item in payload["items"]]
    assert "CSC 101" in course_codes
    assert "CSC 102" in course_codes
    csc101_item = next(item for item in payload["items"] if item["course_code"] == "CSC 101")
    assert csc101_item["day"] == "Tuesday"


def test_build_ingest_payload_chunking():
    entries = [
        CourseEntry(course_code=f"CSC {i:03d}", day="Monday", time="9:00AM")
        for i in range(1, 11)
    ]
    payloads = build_ingest_payload(
        institution_id="123",
        semester_id=12,
        entries=entries,
        chunk_size=3,
    )
    assert len(payloads) == 4
    assert len(payloads[0]["items"]) == 3
    assert len(payloads[1]["items"]) == 3
    assert len(payloads[2]["items"]) == 3
    assert len(payloads[3]["items"]) == 1


def test_build_ingest_payload_parses_structured_datetime():
    entries = [
        CourseEntry(
            course_code="CSC 101",
            day="Saturday 6th December 2025",
            time="2:00PM-4:00PM",
        )
    ]
    payloads = build_ingest_payload(
        institution_id="123",
        semester_id=12,
        entries=entries,
    )
    item = payloads[0]["items"][0]
    assert item["exam_date"] == "2025-12-06"
    assert item["start_time"] == "14:00"
    assert item["end_time"] == "16:00"


def test_build_ingest_payload_filters_empty_course_codes():
    entries = [
        CourseEntry(course_code="CSC 101", day="Monday", time="9:00AM"),
        CourseEntry(course_code="", day="Tuesday", time="10:00AM"),
        CourseEntry(course_code="   ", day="Wednesday", time="11:00AM"),
        CourseEntry(course_code="CSC 102", day="Thursday", time="12:00PM"),
    ]
    payloads = build_ingest_payload(
        institution_id="123",
        semester_id=12,
        entries=entries,
    )
    assert len(payloads) == 1
    assert len(payloads[0]["items"]) == 2
    course_codes = [item["course_code"] for item in payloads[0]["items"]]
    assert "CSC 101" in course_codes
    assert "CSC 102" in course_codes


def test_build_ingest_payload_empty_entries():
    payloads = build_ingest_payload(
        institution_id="123",
        semester_id=12,
        entries=[],
    )
    assert payloads == []


def test_build_ingest_payload_invalid_institution_id():
    entries = [CourseEntry(course_code="CSC 101", day="Monday", time="9:00AM")]
    with pytest.raises(ValueError, match="institution_id is required"):
        build_ingest_payload(
            institution_id="",
            semester_id=12,
            entries=entries,
        )
