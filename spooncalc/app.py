from __future__ import annotations

import os
from pathlib import Path

# os.environ["KIVY_NO_CONSOLELOG"] = '1'

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.app import App
from kivy.utils import platform

from spooncalc.dbtools import Database
from spooncalc.screens.menuscreen import menuscreen
from spooncalc.screens.plotscreen import plotscreen
from spooncalc.screens.logsscreen import logsscreen
from spooncalc.screens.importscreen import importscreen
from spooncalc.screens.inputscreen import inputscreen
from spooncalc.models.activitylog import ActivityLog, clean_param

# Android specific imports and setup
if platform == 'android':
    from android.permissions import request_permissions        # type:ignore
    from android.permissions import Permission                 # type:ignore
    from android.storage import primary_external_storage_path  # type:ignore
    request_permissions([
        Permission.MANAGE_EXTERNAL_STORAGE
    ])

    # Set external storage
    if platform == 'android':
        EXTERNALSTORAGE = primary_external_storage_path()

elif platform == 'macosx':
    # Set external storage
    home = str(Path.home())
    EXTERNALSTORAGE = home
else:
    raise UserWarning(f"Unsupported: {platform=}")


class MyScreenManager(ScreenManager):
    """
   The screen manager which holds instances of all screens.
    The current screen layout is:
        MenuScreen
            InputScreen
            PlotScreen
            LogsScreen
            ImportScreen
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.screen_history = []
        self.transition = FadeTransition()

    def switch_screen(self, screen_name: str) -> None:
        """Switch to provided screen, and add the name to history stack"""
        self.current = screen_name
        self.screen_history.append(screen_name)

    def back_button(self) -> bool:
        """Use the screen history stack to change to the previous screen"""
        self.screen_history.pop()
        if self.screen_history != []:
            self.current = self.screen_history[-1]
        else:
            return False
        return True


class SpoonCalcApp(App):
    """
    The main class for Spoon Calculator.

    This class holds all the (python) methods required for building,
    initialising, and reacting.
    """
    title = "SpoonCalc"

    def build(self) -> MyScreenManager:
        """
        This method builds the app, initialising what must be initialised.

        Spoon Calculator relies on a database for storing and retriving
        activity data. If this database doesn't exist yet, it is created
        here.

        We also initialise our custom WindowManager and instantiate all
        the required windows.
        """
        self.EXTERNALSTORAGE = EXTERNALSTORAGE
        self.db = Database(db_path="spooncalc.db")

        sm = MyScreenManager()
        sm.add_widget(menuscreen.MenuScreen(
            export_callback=self.export_database,
            db=self.db,
        ))
        sm.add_widget(inputscreen.InputScreen(db=self.db))
        sm.add_widget(logsscreen.LogsScreen(db=self.db))
        sm.add_widget(plotscreen.PlotScreen(db=self.db))
        sm.add_widget(importscreen.ImportScreen(
            import_callback=self.import_csv_data
        ))
        self.manager = sm

        Window.bind(on_key_up=self.back_button)
        Window.softinput_mode = "below_target"
        sm.switch_screen("menuscreen")
        return sm

    def back_button(self, instance, keyboard, *args) -> bool:
        if keyboard in (1001, 27):
            success = self.manager.back_button()
            if not success:
                self.stop()
                return False
        return True

    def import_csv_data(self, filename) -> None:
        filepath = os.path.join(self.EXTERNALSTORAGE, filename)
        with open(filepath, 'r') as fp:
            header = fp.readline()       # skip header
            # colnames = header.strip().split(',')
            for line in fp:
                self.insert_if_unique(header, line)

    def insert_if_unique(self, header: str, csv_row: str) -> None:
        """
        Take a raw csv row, extract relevant data, and insert into database.

        If the row already exists in database (i.e. all data entries match
        exactly), then the row is skipped

        Paramters
        ---------
        header : str
            A raw csv header from a previous database export
        csv_row : str
            A raw csv row from a previous database export
        """
        colnames = header.strip().split(',')
        values = csv_row.strip().split(',')

        # Collect values applicable to ActivityLog class
        activitylog_params = {
            k: clean_param(v) for k, v in zip(colnames, values)
            if k in ActivityLog.__dict__['__dataclass_fields__']
        }

        activitylog = ActivityLog(**activitylog_params)  # type: ignore

        self.db.insert_activitylog_if_unique(activitylog)

    def export_database(self) -> None:
        """
        Export the entire activities database as a csv file.
        """
        filename = os.path.join(self.EXTERNALSTORAGE, 'spoon-output.csv')
        self.db.export_database(filename)
