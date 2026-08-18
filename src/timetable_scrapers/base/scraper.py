from abc import ABC, abstractmethod
from typing import Any, BinaryIO, List, Union
import logging
import re

from ..schemas import CourseEntry
from ..utils.time_parser import validate_entry

_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(value: Any) -> Any:
    """Collapse embedded newlines/whitespace runs (e.g. from wrapped Excel cells) to a single space."""
    if not isinstance(value, str):
        return value
    return _WHITESPACE_RE.sub(" ", value).strip()


class BaseTimetableScraper(ABC):
    """
    Abstract base class for all timetable scrapers.
    All scrapers must inherit from this class and implement the abstract methods.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def institution_name(self) -> str:
        """
        Unique indentifier for the scraper.
        Used for registration in a registry
        """
        pass

    @property
    def timezone(self) -> str:
        """
        Institution's timezone for time conversion.
        Defaults to UTC. Override in subclasses.
        """
        return "UTC"

    @abstractmethod
    def extract(self, file: Union[BinaryIO, str]) -> List[CourseEntry]:
        """
        Extract timetable data from a file
        Args:
            file: file object or path (preferrably excel)
        Returns:
            List of CourseEntry objects in standardized format
        Raises:
            Exception if file cannot be read or parsed.
        """
        pass

    def validate_entry(self, entry: CourseEntry) -> bool:
        """
        Validate Course entry
        """
        is_valid, error = validate_entry(entry)
        if not is_valid:
            self.logger.warning(f"Invalid entry for {entry.course_code}: {error}")
        return is_valid

    # very expensive method call :(
    def normalize_output(self, entries: List[CourseEntry]) -> List[CourseEntry]:
        """
        Applies validation and any normalization.
        """
        for entry in entries:
            entry.course_code = _clean_text(entry.course_code)
            entry.venue = _clean_text(entry.venue)
            entry.coordinator = _clean_text(entry.coordinator)
            entry.raw_data = {k: _clean_text(v) for k, v in entry.raw_data.items()}
        return [entry for entry in entries if self.validate_entry(entry)]
