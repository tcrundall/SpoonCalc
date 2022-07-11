"""
A collection of helper functions for interacting with database
"""
import sqlite3
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
    if colnames is None:
        colnames = [
            'id', 'start', 'end', 'name', 'duration', 'cogload', 'physload'
        ]

    now = datetime.now()
    start_date = now + timedelta(days=day_offset)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date = now + timedelta(days=day_offset) + timedelta(days=1)
    end_date_str = end_date.strftime('%Y-%m-%d')

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
