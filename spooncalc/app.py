"""Spoon Calculator App for android

This script defines and runs a kivy-based application used to
track a user's energy expenditure in terms of the abstract unit
of "spoons".

This app requires the following python libraries:
- kivy
- kivy_garden
- sqlite3

This file can be executed on mac or windows, or can be
built into an APK using buildozer/python4android.
"""

import sys
import os
# os.environ["KIVY_NO_CONSOLELOG"] = '1'


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(sys.argv[0]))

    return os.path.join(base_path, relative_path)


from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.core.window import Window
from kivy.resources import resource_add_path
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.app import App
from kivy.utils import platform
from pathlib import Path

from spooncalc import dbtools

# Android specific imports
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    request_permissions([
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE
    ])

# Set external storage
if platform == 'android':
    EXTERNALSTORAGE = primary_external_storage_path()

if platform == 'macosx':
    home = str(Path.home())
    EXTERNALSTORAGE = home

resource_add_path(resource_path(os.path.join('spooncalc', 'screens', 'menuscreen')))
resource_add_path(resource_path(os.path.join('spooncalc', 'screens', 'inputscreen')))
resource_add_path(resource_path(os.path.join('spooncalc', 'screens', 'plotscreen')))
resource_add_path(resource_path(os.path.join('spooncalc', 'screens', 'logsscreen')))
resource_add_path(resource_path(os.path.join('spooncalc', 'screens', 'importscreen')))

print(f'{platform=}')
print(f'{EXTERNALSTORAGE=}')

DATABASE = 'spooncalc.db'


class MyScreenManager(ScreenManager):
    pass


class SpoonCalcApp(App):
    """
    The main class for Spoon Calculator.

    This class holds all the (python) methods required for building,
    initialising, and reacting.
    """
    name = "SpoonCalc"
    title = "SpoonCalc"

    def build(self):
        """
        This method builds the app, initialising what must be initialised.

        Spoon Calculator relies on a database for storing and retriving
        activity data. If this database doesn't exist yet, it is created
        here.

        We also initialise our custom WindowManager and instantiate all
        the required windows.
        """
        self.EXTERNALSTORAGE = EXTERNALSTORAGE
        self.DATABASE = DATABASE

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
        dbtools.submit_query(query_text)
        print("---- Activities table created ----")

        from spooncalc.screens.menuscreen import menuscreen
        from spooncalc.screens.inputscreen import inputscreen
        from spooncalc.screens.plotscreen import plotscreen
        from spooncalc.screens.logsscreen import logsscreen
        from spooncalc.screens.importscreen import importscreen

        self.root = ScreenManager()
        self.menuscreen = menuscreen.MenuScreen()
        self.inputscreen = inputscreen.InputScreen()
        self.plotscreen = plotscreen.PlotScreen()
        self.logsscreen = logsscreen.LogsScreen()
        self.importscreen = importscreen.ImportScreen()
        self.screens = {
            "menuscreen": self.menuscreen,
            "inputscreen": self.inputscreen,
            "plotscreen": self.plotscreen,
            "logsscreen": self.logsscreen,
            "importscreen": self.importscreen,
        }
        self.screen_history = []
        Window.bind(on_key_up=self.back_button)
        Window.softinput_mode = "below_target"
        self.root.transition = FadeTransition()
        # self.switch_screen("logsscreen")
        self.switch_screen("menuscreen")
        return self.root

    def switch_screen(self, screen_name):
        self.root.switch_to(self.screens.get(screen_name))
        self.screen_history.append(screen_name)

    def back_button(self, instance, keyboard, *args):
        if keyboard in (1001, 27):
            self.screen_history.pop()
            if self.screen_history != []:
                self.root.switch_to(self.screens.get(self.screen_history[-1]))
            else:
                self.stop()
            return True
