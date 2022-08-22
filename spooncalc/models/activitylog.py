from __future__ import annotations

from typing import Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

from spooncalc import timeutils

PHYSLOAD_BOOST_SPOON_VALUE = 2.
LOAD_DICT = {
    'low': 0.,
    'mid': 1.,
    'high': 2.,
}


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
    phone: bool = False
    screen: bool = False
    productive: bool = False
    leisure: bool = False
    rest: bool = False
    exercise: bool = False
    physload_boost: bool = False
    necessary: bool = False
    social: bool = False
    misc: bool = False

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
