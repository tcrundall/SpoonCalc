"""
A collection of helpful functions for using datetime
"""
from datetime import datetime, timedelta, time


DATE_FORMATSTRING = "%Y-%m-%d"
DATETIME_FORMATSTRING = "%Y-%m-%d %H:%M:%S"
DAY_BOUNDARY = 3         # o'Clock chosen as the divider between days


def hours_between(start: datetime, end: datetime):
    if type(start) is str:
        start = datetime.strptime(start, DATETIME_FORMATSTRING)
    if type(end) is str:
        end = datetime.strptime(end, DATETIME_FORMATSTRING)

    duration = end - start
    return time2decimal(duration)


def date_from_offset(day_offset):
    day_start = datetime.now().replace(
        hour=DAY_BOUNDARY, minute=0, second=0, microsecond=0
    )
    return day_start + timedelta(days=day_offset)


def date_midnight_from_offset(day_offset):
    day_start = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return day_start + timedelta(days=day_offset)


def time2decimal(time_in: time):
    if type(time_in) is timedelta:
        decimal_time = time_in.total_seconds() / 3600.
        if decimal_time < DAY_BOUNDARY:
            decimal_time += 24.
        return decimal_time
    if type(time_in) is str:
        time_in = datetime.strptime(time_in, DATETIME_FORMATSTRING)
    # TODO: handle times between midnight and `hour_cutoff`
    decimal_time = (
        time_in.hour
        + time_in.minute / 60
        + time_in.second / 3600
    )
    if decimal_time < DAY_BOUNDARY:
        decimal_time += 24.
    return decimal_time
