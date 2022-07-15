"""
A collection of helper functions for interacting with database
"""
import sqlite3
import timeutils
from datetime import datetime, timedelta


DATABASE = "spooncalc.db"
DATE_FORMATSTRING = "%Y-%m-%d"
DATETIME_FORMATSTRING = "%Y-%m-%d %H:%M:%S"


def submit_query(query_text):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(query_text)
    contents = c.fetchall()
    conn.commit()
    conn.close()
    return contents


def get_logs_from_day(day_offset, colnames=None):
    """
    Calculate total spoons spent on the day
    `day_offset` days from today.

    If `day_offset` is 0, then we're calculating today,
    `day_offset` = -1 is yesterday, etc...
    """
    entries = get_entries_between_offsets(
        day_offset,
        day_offset + 1,
        colnames=colnames
    )
    return entries


def get_entries_between_offsets(start: int, end: int, colnames=None):
    """
    Get all entries between day offsets [start, end).

    Examples
    --------
    start=-1, end=0: all entries from yesterday
    start=-1, end=-1: no results
    start=-1, end=1: all entries from yesterday and today
    """
    # Use "date" to drop time component (equivalent to midnight, start of day)
    now_date = datetime.now().date()
    # TODO: utilise "datetime_from_offset"
    start_date = timeutils.date_from_offset(start)
    end_date = timeutils.date_from_offset(end)
    entries = get_entries_between_datetimes(
        start_date,
        end_date,
        colnames=colnames
    )
    return entries


def get_entries_between_datetimes(
    start: datetime,
    end: datetime,
    colnames=None,
):
    """
    Get all entries between the datetimes `start` and `end`.
    """
    if colnames is None:
        colnames = [
            'id', 'start', 'end', 'name', 'duration', 'cogload', 'physload'
        ]

    start_date_str = start.strftime(DATETIME_FORMATSTRING)
    end_date_str = end.strftime(DATETIME_FORMATSTRING)

    query_text = f"""
        SELECT {', '.join(colnames)}
        FROM activities
        WHERE start BETWEEN "{start_date_str}" and "{end_date_str}"
    """
    contents = submit_query(query_text)

    entries = [
        {colname: value for colname, value in zip(colnames, entry)}
        for entry in contents
    ]

    return entries


def delete_entry(id):
    query_text = f"""
        DELETE FROM activities
        WHERE id = {id};
    """
    submit_query(query_text)


def get_latest_endtime():
    """
    Acquire the latest end time in database
    """
    query_text = """
        SELECT MAX (end) FROM activities
    """
    contents = submit_query(query_text)
    latest_end = contents[0][0]
    return datetime.strptime(latest_end, DATETIME_FORMATSTRING)


def get_earliest_starttime(day_offset):
    """
    Get the earliest start time in database for given day.
    If none available, return start of that day.
    """
    datetime_str = timeutils.date_from_offset(day_offset)\
        .strftime(DATETIME_FORMATSTRING)

    query_text = f"""
        SELECT MIN (start) FROM activities
        WHERE start >= "{datetime_str}"
    """
    contents = submit_query(query_text)
    earliest_start = contents[0][0]
    if earliest_start is None:
        today_start = datetime.now().replace(
            hour=timeutils.DAY_BOUNDARY,
            minute=0,
            second=0,
            microsecond=0
        )
        target_day_start = today_start + timedelta(days=day_offset)
        return target_day_start

    return datetime.strptime(earliest_start, DATETIME_FORMATSTRING)
