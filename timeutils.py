"""
A collection of helpful functions for using datetime
"""
from datetime import datetime, timedelta, time

DATE_FORMATSTRING = "%Y-%m-%d"
DATETIME_FORMATSTRING = "%Y-%m-%d %H:%M:%S"


def hours_between(start: datetime, end: datetime):
    if type(start) is str:
        start = datetime.strptime(start, DATETIME_FORMATSTRING)
    if type(end) is str:
        end = datetime.strptime(end, DATETIME_FORMATSTRING)

    duration = end - start
    return time2decimal(duration)


def date_from_offset(day_offset):
    day_start = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return day_start + timedelta(days=day_offset)


def time2decimal(time_in: time):
    if type(time_in) is timedelta:
        return time_in.total_seconds() / 3600.
    if type(time_in) is str:
        time_in = datetime.strptime(time_in, DATETIME_FORMATSTRING)
    # try:
    #     time_in.hour
    # except AttributeError:
    #     time_in = datetime.strptime(time_in, DATETIME_FORMATSTRING)
    return time_in.hour + time_in.minute / 60 + time_in.second / 3600.
