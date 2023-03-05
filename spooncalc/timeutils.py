"""
A collection of helpful functions for using datetime
"""
from __future__ import annotations

from datetime import datetime, timedelta, time


DATE_FORMATSTRING = "%Y-%m-%d"
DATETIME_FORMATSTRING = "%Y-%m-%d %H:%M:%S"
DAY_BOUNDARY = 3         # o'Clock chosen as the divider between days


def day_start_hour() -> int:
    """Get the "starting" hour of the day"""
    return DAY_BOUNDARY


def day_end_hour() -> int:
    """Get the "ending" hour of the day"""
    return DAY_BOUNDARY + 24


def within_todays_boundaries(dati: datetime) -> bool:
    """Establish if provided datetime occurs today, factoring in
    a non-midnight day boundary"""
    today_start = datetime_from_offset(day_offset=0)
    today_end = datetime_from_offset(day_offset=1)
    return today_start <= dati < today_end


def hours_between(start: datetime | str, end: datetime | str) -> float:
    """Calculate the time between to datetimes, in hours.

    The inputs can be datetime objects or strings that
    match the DATETIME_FORMATSTRING format
    """
    if type(start) is str:
        start = datetime.strptime(start, DATETIME_FORMATSTRING)
    if type(end) is str:
        end = datetime.strptime(end, DATETIME_FORMATSTRING)

    assert isinstance(start, datetime)       # assertions to satisfy type hints
    assert isinstance(end, datetime)

    duration = end - start
    return time2decimal(duration)


def datetime_from_offset(day_offset: int) -> datetime:
    """Get the start of the day `day_offset` from today, as a datetime"""
    effective_day_start = (
        # offset s.t. the hours before the "DAY_BOUDNARY" are part of yesterday
        datetime.now() - timedelta(hours=DAY_BOUNDARY)
    ).replace(hour=DAY_BOUNDARY, minute=0, second=0, microsecond=0)
    return effective_day_start + timedelta(days=day_offset)


def date_midnight_from_offset(day_offset: int) -> datetime:
    """Get the starting midnight of the day `day_offset` as a datetime"""

    effective_day_start = datetime_from_offset(day_offset)
    return effective_day_start - timedelta(hours=DAY_BOUNDARY)


def time2decimal(time_in: time | str | timedelta) -> float:
    """Convert a time from various types to hours in decimal

    TODO: Maybe include a reference datetime, e.g. last night's midnight,
          s.t. `time` or `datetime` inputs return number of hours since
          the reference, thereby avoiding increasing time by 24 if before
          `DAY_BOUNDARY`
    """

    if isinstance(time_in, datetime):
        raise UserWarning("You should explicitly provide time with .time()")

    if isinstance(time_in, timedelta):
        decimal_time = time_in.total_seconds() / 3600.
        return decimal_time

    if isinstance(time_in, str):
        time_in = datetime.strptime(time_in, DATETIME_FORMATSTRING).time()

    decimal_time = (
        time_in.hour
        + time_in.minute / 60
        + time_in.second / 3600
    )

    # Activities from tomorrow's early morning are included in today, so
    # for these activities we increase the time by 24 (hours) to ensure
    # correct ordering
    if decimal_time < DAY_BOUNDARY:
        decimal_time += 24.
    return decimal_time


def round_datetime(dati: datetime, minute_interval=15) -> datetime:
    """
    Round minutes to nearest given `minute_interval`, carrying the
    hour and day if necessary.
    """
    mins = dati.minute
    rounded_min = int(((mins + (minute_interval / 2)) // minute_interval)
                      * minute_interval)
    # Carry the hour if necessary
    if rounded_min >= 60:
        rounded_hour = dati.hour + 1
        rounded_min %= 60
    else:
        rounded_hour = dati.hour
    # Carry the day if necessary
    if rounded_hour >= 24:
        rounded_day = dati.day + 1
        rounded_hour %= 24
    else:
        rounded_day = dati.day

    return dati.replace(day=rounded_day,
                        hour=rounded_hour,
                        minute=rounded_min,
                        second=0,
                        microsecond=0)


def get_nowish(interval_mins=15) -> datetime:
    """Get the datetime for now, rounded to nearest 15 mins"""
    return round_datetime(datetime.now(), minute_interval=interval_mins)
