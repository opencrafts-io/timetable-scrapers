from timetable_scrapers import ScraperRegistry


def test_scrapers_registered():
    names = set(ScraperRegistry.list_scrapers())
    assert {"kca", "strath", "nursing_exams", "daystar"} <= names


def test_get_scraper():
    assert ScraperRegistry.get_scraper("kca").institution_name == "kca"

