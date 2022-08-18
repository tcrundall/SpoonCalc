from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from spooncalc import timeutils

PHYSLOAD_BOOST_SPOON_VALUE = 2.


@dataclass
class ActivityLog:
    start: datetime
    end: datetime
    id: Optional[int] = None
    name: str = "Activity Name"
    cogload: float = 1.0
    physload: float = 1.0
    energy: float = 1.0
    phone: bool = False
    screen: bool = False
    productive: bool = False
    leisure: bool = False
    rest: bool = False
    exercise: bool = False
    physload_boost: bool = False
    necessary: bool = False
    social: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.start, str):
            self.start = datetime.strptime(
                self.start,
                timeutils.DATETIME_FORMATSTRING,
            )

        if isinstance(self.end, str):
            self.end = datetime.strptime(
                self.end,
                timeutils.DATETIME_FORMATSTRING,
            )

        if isinstance(self.cogload, str):
            self.cogload = float(self.cogload)

        if isinstance(self.physload, str):
            self.physload = float(self.physload)

        if isinstance(self.physload, str):
            self.physload = float(self.physload)

    # The property decorator enforces `activitylog.duration` usage
    @property
    def duration(self) -> timedelta:
        """The duration is a derived value"""
        return self.end - self.start

    def get_value_string(self) -> str:
        """
        Generates long string of all values

        This is used for building SQL requests.

        Note: this is bad, because it relies on the identical ordering
        of attributes wherever this SQL is done.
        TODO:   instead, when generating SQL request, loop over attribute
                names and use getattr
        """
        return f"""
            "{self.start}",
            "{self.end}",
            "{self.duration}",
            "{self.name}",
            "{self.cogload}",
            "{self.physload}",
            "{self.energy}"
        """

    def is_everything_today(self) -> bool:
        """Check if start and end datetimes are today"""
        return (self.start.date() == self.end.date() == datetime.now().date())

    def get_spoons(self) -> float:
        """
        Calculate spoons spent by this activity
        """
        duration = timeutils.time2decimal(self.end - self.start)

        # Augment physload when physload_boost is used
        augmented_physload = self.physload
        if self.physload_boost:
            augmented_physload += PHYSLOAD_BOOST_SPOON_VALUE

        return duration * (self.cogload + augmented_physload)

    @property
    def spoons(self) -> float:
        return self.get_spoons()
