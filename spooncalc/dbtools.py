"""
A collection of helper functions for interacting with database
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, List
import sqlite3
from sqlite3 import Cursor as SQLCursor

from spooncalc import timeutils
from spooncalc.models.activitylog import ActivityLog, clean_param


class Cursor:
    """A context manager for connecting to sqlite3 databases"""
    def __init__(self, db_path: str) -> None:
        """Initialize the context manager"""
        self.db_path = db_path

    def __enter__(self) -> SQLCursor:
        """
        Upon entering the context manager, build the connection and return
        a cursor
        """
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """
        Upon exiting the context manager, commmit the changes and close
        the connection
        """
        self.conn.commit()
        self.conn.close()


class Database:
    DATE_FORMATSTRING = "%Y-%m-%d"
    DATETIME_FORMATSTRING = "%Y-%m-%d %H:%M:%S"
    ACTIVITIES_COLNAMES = (
        'start',
        'end',
        'name',
        'duration',
        'cogload',
        'physload',
        'energy',
        'necessary',
        'leisure',
        'rest',
        'productive',
        'social',
        'phone',
        'screen',
        'exercise',
        'physload_boost',
        'misc',
    )

    def __init__(self, db_path: str = "spooncalc.db") -> None:
        """
        Initialize a Database object

        Parameters
        ----------
        db_path : str
            a path to the database file. The file may not exist.
        """
        self.db_path = db_path
        self.initialize_database()
        self.add_missing_columns()

    def submit_query(self, query_text) -> List[Any]:
        """
        A helper function for fetching results of a query

        Parameters
        ----------
        query_text : str
            A complete sqlite3 request

        Returns
        -------
        contents
            the contents of the response, for a standard SELECT
            this is a list of tuples, where each tuple corresponds
            to a result, and each element in the tuple corresponds
            to the selected columns
        """

        with Cursor(self.db_path) as c:
            c.execute(query_text)
            contents = c.fetchall()

        return contents

    def get_logs_from_day(
        self,
        day_offset: int,
    ) -> List[ActivityLog]:

        """
        Calculate total spoons spent on the day
        `day_offset` days from today.

        If `day_offset` is 0, then we're calculating today,
        `day_offset` = -1 is yesterday, etc...

        Parameters
        ----------
        day_offset : int
            The number of days between today and day in question.
            `day_offset`=0 is today, `day_offset`=-1 is yesterday

        Returns
        -------
        list(dict(str: str))
            Each list element is a dict corresponding to a returned row. The
            keys are the column names, the values are the column entry of
            that row.
        """

        logs = self.get_logs_between_offsets(
            day_offset,
            day_offset + 1,
        )
        return logs

    def get_logs_between_offsets(
        self,
        start: int,
        end: int,
    ) -> List[ActivityLog]:
        """
        Get all logs between day offsets [start, end).

        This is a convenience wrapper of get_logs_between_datetimes,
        avoiding usage of specific datetimes, when standard day boundaries
        suffice.

        Note that the boundary time between adjacent days is not necessarily
        midnight, and is set by timeutils.DAY_BOUNDARY (currently 3am).

        Parameters
        ----------
        start : int
            The starting day_offset
        end : int
            The ending day_offset

        Returns
        -------
        list(dict(str: str))
            Each list element is a dict corresponding to a returned row. The
            keys are the column names, the values are the column entry of
            that row.

        Examples
        --------
            start=-1, end=0: all logs from yesterday
            start=-1, end=-1: no results
            start=-1, end=1: all logs from yesterday and today
        """

        start_datetime = timeutils.datetime_from_offset(start)
        end_datetime = timeutils.datetime_from_offset(end)
        logs = self.get_logs_between_datetimes(
            start_datetime,
            end_datetime,
        )
        return logs

    def get_logs_between_datetimes(
        self,
        start: datetime,
        end: datetime,
    ) -> List[ActivityLog]:
        """
        Get all logs between the datetimes `start` and `end`.

        Parameters
        ----------
        start : datetime
            the lower limit date-time of desired range
        end : datetime
            the upper limit date-time of desired range

        Returns
        -------
        list(dict(str: str))
            Each list element is a dict corresponding to a returned row. The
            keys are the column names, the values are the column entry of
            that row.
        """

        colnames = ['id'] + list(self.ACTIVITIES_COLNAMES)

        start_date_str = start.strftime(self.DATETIME_FORMATSTRING)
        end_date_str = end.strftime(self.DATETIME_FORMATSTRING)

        query_text = f"""
            SELECT {', '.join(colnames)}
            FROM activities
            WHERE start BETWEEN "{start_date_str}" and "{end_date_str}"
        """
        contents = self.submit_query(query_text)

        logs = []
        for entry in contents:
            params = map(clean_param, entry)
            log_pars = {
                k: v for k, v in zip(colnames, params)
                if k != "duration"
            }
            logs.append(ActivityLog(**log_pars))    # type: ignore

        return logs

    def delete_entry(self, id: int) -> None:
        """
        Delete the entry which matches `id`

        Parameters
        ----------
        id : int
            an id corresponding to the database entry to be deleted
        """

        query_text = f"""
            DELETE FROM activities
            WHERE id = {id};
        """
        self.submit_query(query_text)

    def get_latest_endtime(self) -> datetime | None:
        """
        Acquire the latest end time in database

        If there is no end time, then return a datetime of
        roughly an hour ago.

        Returns
        -------
        datetime | None
            Either latest end time, or if not available, None
        """

        query_text = """
            SELECT MAX (end) FROM activities
        """
        contents = self.submit_query(query_text)
        latest_end = contents[0][0]
        if isinstance(latest_end, str):
            return datetime.strptime(latest_end, self.DATETIME_FORMATSTRING)

        # If no latest time available, return None
        return None

    def get_earliest_starttime(self, day_offset: int) -> datetime:
        """
        Get the earliest start time in database for given day.
        If none available, return start boundary of that day.

        Note that start boundary is set by timeutils.DAY_BOUNDARY.

        Paramters
        ---------
        day_offset : int
            The number of days between today and day in question.
            `day_offset`=0 is today, `day_offset`=-1 is yesterday

        Returns
        -------
        datetime
            Either the starting time of earliest activty, or
            start of day.
        """

        datetime_str = timeutils.datetime_from_offset(day_offset)\
            .strftime(self.DATETIME_FORMATSTRING)

        query_text = f"""
            SELECT MIN (start) FROM activities
            WHERE start >= "{datetime_str}"
        """
        contents = self.submit_query(query_text)
        earliest_start = contents[0][0]

        if earliest_start:
            return datetime.strptime(
                earliest_start,
                self.DATETIME_FORMATSTRING
            )

        # If nothing in database, return start of target day
        today_start = datetime.now().replace(
            hour=timeutils.DAY_BOUNDARY,
            minute=0,
            second=0,
            microsecond=0
        )
        target_day_start = today_start + timedelta(days=day_offset)
        return target_day_start

    def initialize_database(self) -> None:
        # Dynamically generate column names
        col_props = ', '.join(
            [f'{col} text NOT NULL' for col in self.ACTIVITIES_COLNAMES]
        )

        query_text = f"""
            CREATE TABLE if not exists activities(
                id integer PRIMARY KEY,
                {col_props}
        );
        """
        self.submit_query(query_text)

    def get_colnames(self) -> List[str]:
        with Cursor(self.db_path) as c:
            c.execute("SELECT * from activities limit 1")
            c.fetchall()
            description = c.description

        return [d[0] for d in description]

    def add_missing_columns(self) -> None:
        """If database was initialized by outdated code, update tables with
        new columns"""
        db_colnames = self.get_colnames()

        for colname in self.ACTIVITIES_COLNAMES:
            if colname not in db_colnames:
                self.submit_query(f"""
                    ALTER TABLE activities
                    ADD {colname} text;
                """)

    def export_database(self, filename: str) -> None:
        """
        Export the entire activities database as a csv file.
        """
        # Request entire contents of database
        # filename = os.path.join(self.EXTERNALSTORAGE, 'spoon-output.csv')
        with Cursor(self.db_path) as c:
            c.execute("SELECT * FROM activities")
            contents = c.fetchall()
            description = c.description

        # Construct the csv file header from the request's description
        SEP = ','
        formatted_header = SEP.join([str(col[0])
                                    for col in description])
        formatted_contents = '\n'.join([SEP.join([
            str(val) for val in entry
        ]) for entry in contents])

        # Avoid exporting empty database (and risking an overwrite)
        if len(contents) == 0:
            return
        text = '\n'.join((formatted_header, formatted_contents))

        with open(filename, 'w') as fp:
            fp.write(text)

    def insert_activitylog(self, log: ActivityLog) -> None:
        # Get the table columns that are also activity log attributes
        valid_cols = [c for c in self.ACTIVITIES_COLNAMES if hasattr(log, c)]

        # Get the corresponding values of the valid column names
        values = [str(getattr(log, c)) for c in valid_cols]

        query_text = f"""
            INSERT INTO activities(
                    {','.join(valid_cols)}
                )
                VALUES(
                    "{'", "'.join(values)}"
                );
        """
        self.submit_query(query_text)

    def insert_activitylog_if_unique(self, log: ActivityLog) -> None:
        """
        Perhaps a better way is to add all logs, then remove duplicates
        """
        valid_cols = [c for c in self.ACTIVITIES_COLNAMES if hasattr(log, c)]

        # Use column names to dynamically generate equality checks
        equality_checks = [
            f'{col}="{getattr(log, col)}"' for col in valid_cols
        ]

        # Check to see if this activity is already in the database
        query_text = f"""
            SELECT EXISTS(
                SELECT * from activities WHERE
                    {" AND ".join(equality_checks)}
            );
        """
        contents = self.submit_query(query_text)
        if contents[0][0] > 0:
            return

        self.insert_activitylog(log)
