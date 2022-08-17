from dataclasses import dataclass
from datetime import datetime
# from typing import Union

from spooncalc import timeutils, analyser


@dataclass
class ActivityLog:
    id: int = None
    # start: Union[datetime, str]
    start: datetime = None
    end: datetime = None
    name: str = "Activity Name"
    cogload: float = 1.0
    physload: float = 1.0
    energy: float = 1.0

    def __post_init__(self):
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

    def get_duration(self):
        if self.start and self.end:
            return self.end - self.start

        return None

    def get_value_string(self):
        return f"""
            "{self.start}",
            "{self.end}",
            "{self.get_duration()}",
            "{self.name}",
            "{self.cogload}",
            "{self.physload}",
            "{self.energy}"
        """

    def is_everything_today(self):
        """Check if start and end datetimes are today"""
        return (self.start.date() == self.end.date() == datetime.now().date())

    def get_spoons(self):
        """
        Calculate spoons spent by this activity
        """
        duration = timeutils.time2decimal(self.end - self.start)
        return analyser.calculate_spoons(duration, self.cogload, self.physload)