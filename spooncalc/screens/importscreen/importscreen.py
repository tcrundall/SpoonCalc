import os

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.app import App
app = App.get_running_app()

from spooncalc import dbtools


class ImportScreen(Screen):
    """
    A screen that allows users to re-import previously exported data

    Methods
    -------
    on_import_press(filename)
        Parses activities in provided csv and inserts into database
    """

    def on_import_press(self, filename):
        """
        Import activites from a csv file into database, ignoring duplicates

        Paramters
        ---------
        filename : str
            Relative path from `EXTERNALSTORAGE` to a csv file previously
            outputted by SpoonCalculator (see `MenuWindow.export_database`)
        """

        print(filename)
        filepath = os.path.join(app.EXTERNALSTORAGE, filename)
        with open(filepath, 'r') as fp:
            _ = fp.readline()       # skip header
            for line in fp:
                print(line)
                self.insert_if_unique(line)

    def insert_if_unique(self, csv_row):
        """
        Take a raw csv row, extract relevant data, and insert into database.

        If the row already exists in database (i.e. all data entries match
        exactly), then the row is skipped

        Paramters
        ---------
        csv_row : str
            A raw csv row from a previous database export
        """
        _, start, end, duration, name, cogload, physload, energy =\
            csv_row.strip().split(',')

        query_text = f"""
            SELECT EXISTS(
                SELECT * from activities WHERE
                    start="{start}"
                    AND end="{end}"
                    AND duration="{duration}"
                    AND name="{name}"
                    AND cogload = "{cogload}"
                    AND physload = "{physload}"
                    AND energy = "{energy}"
            );
        """
        contents = dbtools.submit_query(query_text)
        if contents[0][0] == 1:
            return

        query_text = f"""
            INSERT INTO activities
                (start, end, duration, name, cogload, physload, energy)
                VALUES(
                    "{start}", "{end}", "{duration}", "{name}", "{cogload}",
                    "{physload}", "{energy}"
                );
        """
        dbtools.submit_query(query_text)

    pass

    def switch_screen(self, screen_name):
        app.switch_screen(screen_name)


Builder.load_file('importscreen.kv')
