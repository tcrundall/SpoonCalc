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

# os.environ["KIVY_NO_CONSOLELOG"] = '1'

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.core.window import Window
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


print(f'{platform=}')
print(f'{EXTERNALSTORAGE=}')

DATABASE = 'spooncalc.db'


class MyScreenManager(ScreenManager):
    """
    The window manager which holds instances of all windows.
    The current window layout is:
        MenuWindow
            InputWindow
            PlotWindow
            LogsWindow
            ImportWindow
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.screen_history = []
        self.transition = FadeTransition()

    def switch_screen(self, screen_name):
        self.current = screen_name
        self.screen_history.append(screen_name)

    def back_button(self):
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

        # These need to be imported here (and not at start of file)
        # because they require app to be running.
        from spooncalc.screens.menuscreen import menuscreen
        from spooncalc.screens.inputscreen import inputscreen
        from spooncalc.screens.plotscreen import plotscreen
        from spooncalc.screens.logsscreen import logsscreen
        from spooncalc.screens.importscreen import importscreen

        sm = MyScreenManager()
        sm.add_widget(menuscreen.MenuScreen())
        sm.add_widget(inputscreen.InputScreen())
        sm.add_widget(logsscreen.LogsScreen())
        sm.add_widget(plotscreen.PlotScreen())
        sm.add_widget(importscreen.ImportScreen())
        self.manager = sm

        Window.bind(on_key_up=self.back_button)
        Window.softinput_mode = "below_target"
        sm.switch_screen("menuscreen")
        return sm

    def back_button(self, instance, keyboard, *args):
        if keyboard in (1001, 27):
            success = self.manager.back_button()
            if not success:
                self.stop()
            return True
