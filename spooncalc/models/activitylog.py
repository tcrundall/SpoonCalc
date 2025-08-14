from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Optional,
    Union,
)

from spooncalc import timeutils

PHYSLOAD_BOOST_SPOON_VALUE = 2.0
LOAD_DICT = {
    "low": 0.0,
    "mid": 1.0,
    "high": 2.0,
}


QUALIFIERS = [
    "necessary",
    "leisure",
    "rest",
    "productive",
    "social",
    "phone",
    "screen",
    "boost",
    "exercise",
    "misc",
]


def clean_param(param: Any) -> Union[datetime, bool, float, str]:
    if not isinstance(param, str):
        return param
    try:
        return datetime.strptime(param, timeutils.DATETIME_FORMATSTRING)
    except ValueError:
        pass

    # Handle booleans
    if param.lower() == "true":
        return True
    elif param.lower() in ["false", "none"]:
        return False

    try:
        return float(param)
    except ValueError:
        pass

    # Backwards compatibility for when loads were stored as labels
    if param in LOAD_DICT:
        return LOAD_DICT[param]

    return str(param)


@dataclass
class ActivityLog:
    start: datetime
    end: datetime
    id: Optional[int] = None
    name: str = "Activity Name"
    cogload: float = 1.0
    physload: float = 1.0
    energy: float = 1.0
    necessary: bool = False
    leisure: bool = False
    rest: bool = False
    productive: bool = False
    social: bool = False
    phone: bool = False
    screen: bool = False
    exercise: bool = False
    boost: bool = False
    misc: bool = False

    # The property decorator enforces `activitylog.duration` usage
    @property
    def duration(self) -> timedelta:
        """The duration is a derived value"""
        return self.end - self.start

    def is_everything_today(self) -> bool:
        """Check if start and end datetimes are today"""
        return self.start.date() == self.end.date() == datetime.now().date()

    def get_spoons(self) -> float:
        """
        Calculate spoons spent by this activity
        """
        # Augment physload when physload_boost is used
        augmented_physload = self.physload
        if self.boost:
            augmented_physload += PHYSLOAD_BOOST_SPOON_VALUE

        return self.hours * (self.cogload + augmented_physload)

    @property
    def spoons(self) -> float:
        return self.get_spoons()

    @property
    def hours(self) -> float:
        return timeutils.time2decimal(self.duration)
