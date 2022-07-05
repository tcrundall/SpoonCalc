"""
A collection of helper functions for interacting with database
"""
import sqlite3
from datetime import datetime, timedelta

DATABASE = "spooncalc.db"


def get_logs_from_day(n_days_ago, colnames=None):
    """
    Calculate total spoons spent on `n_days_ago` day.

    If `n_days_ago` is 0, then we're calculating today,
    `n_days_ago` = 1 is yesterday, etc...
    """
    if colnames is None:
        colnames = [
            'id', 'start', 'end', 'name', 'duration', 'cogload', 'physload'
        ]

    now = datetime.now()
    start_date = now - timedelta(days=n_days_ago)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date = now - timedelta(days=n_days_ago) + timedelta(days=1)
    end_date_str = end_date.strftime('%Y-%m-%d')

    query_text = f"""
        SELECT {', '.join(colnames)}
        FROM activities
        WHERE start BETWEEN "{start_date_str}" and "{end_date_str}"
    """

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(query_text)

    contents = c.fetchall()
    conn.close()

    entries = [
        {colname: value for colname, value in zip(colnames, entry)}
        for entry in contents
    ]

    return entries
