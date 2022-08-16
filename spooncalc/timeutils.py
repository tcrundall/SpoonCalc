"""
A collection of helpful functions for using datetime
"""
from datetime import datetime, timedelta, time


DATE_FORMATSTRING = "%Y-%m-%d"
DATETIME_FORMATSTRING = "%Y-%m-%d %H:%M:%S"
DAY_BOUNDARY = 3         # o'Clock chosen as the divider between days


def day_start_hour():
    """Get the "starting" hour of the day"""
    return DAY_BOUNDARY


def day_end_hour():
    """Get the "ending" hour of the day"""
    return DAY_BOUNDARY + 24


def hours_between(start: datetime, end: datetime):
    """Calculate the time between to datetimes, in hours.

    The inputs can be datetime objects or strings that
    match the DATETIME_FORMATSTRING format
    """
    if type(start) is str:
        start = datetime.strptime(start, DATETIME_FORMATSTRING)
    if type(end) is str:
        end = datetime.strptime(end, DATETIME_FORMATSTRING)

    duration = end - start
    return time2decimal(duration)


def datetime_from_offset(day_offset):
    """Get the start of the day `day_offset` from today, as a datetime"""
    day_start = datetime.now().replace(
        hour=DAY_BOUNDARY, minute=0, second=0, microsecond=0
    )
    return day_start + timedelta(days=day_offset)


def date_midnight_from_offset(day_offset):
    """Get the starting midnight of the day `day_offset` as a datetime"""
    day_start = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return day_start + timedelta(days=day_offset)


def time2decimal(time_in: time):
    """Convert a time from various types to hours in decimal"""
    if type(time_in) is timedelta:
        decimal_time = time_in.total_seconds() / 3600.
        # .... no idea what this was here for. Just seems plain wrong
        # if decimal_time < DAY_BOUNDARY:
        #     decimal_time += 24.
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


def round_datetime(dati: datetime, minute_interval=15):
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


def get_nowish(interval_mins=15):
    """Get the datetime for now, rounded to nearest 15 mins"""
    return round_datetime(datetime.now(), minute_interval=interval_mins)
