"""
A collection of helper functions for interacting with database
"""
import sqlite3
from datetime import datetime, timedelta

from spooncalc import timeutils


class Database:
    DATE_FORMATSTRING = "%Y-%m-%d"
    DATETIME_FORMATSTRING = "%Y-%m-%d %H:%M:%S"

    def __init__(self, db="spooncalc.db"):
        self.db = db
        self.initialize_database()

    def submit_query(self, query_text):
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

        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute(query_text)
        contents = c.fetchall()
        conn.commit()
        conn.close()
        return contents

    def get_logs_from_day(self, day_offset, colnames=None):
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

        entries = self.get_entries_between_offsets(
            day_offset,
            day_offset + 1,
            colnames=colnames
        )
        return entries

    def get_entries_between_offsets(self, start: int, end: int, colnames=None):
        """
        Get all entries between day offsets [start, end).

        This is a convenience wrapper of get_entries_between_datetimes,
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
        colnames : list(str), optional
            The list of database column names. If None, defaults are those
            used by get_entries_between_datetimes:
                'id', 'start', 'end', 'name', 'duration', 'cogload', 'physload'

        Returns
        -------
        list(dict(str: str))
            Each list element is a dict corresponding to a returned row. The
            keys are the column names, the values are the column entry of
            that row.

        Examples
        --------
            start=-1, end=0: all entries from yesterday
            start=-1, end=-1: no results
            start=-1, end=1: all entries from yesterday and today
        """

        start_datetime = timeutils.datetime_from_offset(start)
        end_datetime = timeutils.datetime_from_offset(end)
        entries = self.get_entries_between_datetimes(
            start_datetime,
            end_datetime,
            colnames=colnames
        )
        return entries

    def get_entries_between_datetimes(
        self,
        start: datetime,
        end: datetime,
        colnames=None,
    ):
        """
        Get all entries between the datetimes `start` and `end`.

        Parameters
        ----------
        start : datetime
            the lower limit date-time of desired range
        end : datetime
            the upper limit date-time of desired range
        colnames : list(str), optional
            the column names to be included in the db SELECT query,
            if None, the defaults are used:
                'id', 'start', 'end', 'name', 'duration', 'cogload', 'physload'

        Returns
        -------
        list(dict(str: str))
            Each list element is a dict corresponding to a returned row. The
            keys are the column names, the values are the column entry of
            that row.
        """

        if colnames is None:
            colnames = [
                'id', 'start', 'end', 'name', 'duration', 'cogload', 'physload'
            ]

        start_date_str = start.strftime(self.DATETIME_FORMATSTRING)
        end_date_str = end.strftime(self.DATETIME_FORMATSTRING)

        query_text = f"""
            SELECT {', '.join(colnames)}
            FROM activities
            WHERE start BETWEEN "{start_date_str}" and "{end_date_str}"
        """
        contents = self.submit_query(query_text)

        entries = [
            {colname: value for colname, value in zip(colnames, entry)}
            for entry in contents
        ]

        return entries

    def delete_entry(self, id):
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

    def get_latest_endtime(self):
        """
        Acquire the latest end time in database

        If there is no end time, then return a datetime of
        roughly an hour ago.

        Returns
        -------
        datetime
            Either latest end time, or roughly an hour ago

        TODO:   Instead of failing silently, maybe return None and
                generate this alternative time above.
        """

        query_text = """
            SELECT MAX (end) FROM activities
        """
        contents = self.submit_query(query_text)
        latest_end = contents[0][0]
        # If no latest time available, set to roughly an hour ago
        if latest_end is None:
            return timeutils.get_nowish() - timedelta(hours=1)

        return datetime.strptime(latest_end, self.DATETIME_FORMATSTRING)

    def get_earliest_starttime(self, day_offset):
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
        if earliest_start is None:
            today_start = datetime.now().replace(
                hour=timeutils.DAY_BOUNDARY,
                minute=0,
                second=0,
                microsecond=0
            )
            target_day_start = today_start + timedelta(days=day_offset)
            return target_day_start

        return datetime.strptime(earliest_start, self.DATETIME_FORMATSTRING)

    def initialize_database(self):
        query_text = """
            CREATE TABLE if not exists activities(
                id integer PRIMARY KEY,
                start text NOT NULL,
                end text NOT NULL,
                duration text NOT NULL,
                name text NOT NULL,
                cogload text NOT NULL,
                physload text NOT NULL,
                energy text NOT NULL
        );
        """
        self.submit_query(query_text)

    def export_database(self, filename):
        """
        Export the entire activities database as a csv file.
        """
        # Request entire contents of database
        # filename = os.path.join(self.EXTERNALSTORAGE, 'spoon-output.csv')
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute("SELECT * FROM activities")
        contents = c.fetchall()

        # Construct the csv file header from the request's description
        SEP = ','
        formatted_header = SEP.join([str(col[0])
                                    for col in c.description])
        formatted_contents = '\n'.join([SEP.join([
            str(val) for val in entry
        ]) for entry in contents])
        conn.close()

        # Avoid exporting empty database (and risking an overwrite)
        if len(contents) == 0:
            return
        text = '\n'.join((formatted_header, formatted_contents))

        with open(filename, 'w') as fp:
            fp.write(text)
