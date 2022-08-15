from datetime import datetime, timedelta
import os
from pathlib import Path
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.app import App
from kivy.properties import StringProperty
app = App.get_running_app()

Builder.load_file(os.path.join(
    Path(__file__).parent.absolute(),
    "logsscreen.kv"
))


class LogsScreen(Screen):
    """
    A window for displaying (and deleting) all logs for a given day.

    This window main widget is a scrollview of StackedLogsLayout, but
    this is handled in kivy lang.

    Attributes
    ----------
    title : StringProperty
        the window title, showing the date of the day in quesiton

    TODO: Include day name in title
    """
    title = StringProperty(datetime.today().strftime('%d.%m.%Y'))

    def update_title(self, day_offset):
        """
        Update the title, reflecting change of the day in question
        """
        day_delta = timedelta(days=day_offset)
        current_day = datetime.today() + day_delta
        self.title = current_day.strftime('%d.%m.%Y')

    def on_pre_enter(self, *args):
        """
        Update the stackedLogsLayout (bound in kivy lang) before
        entering this window.
        """
        self.ids["logs_display"].update()
        super().on_pre_enter(*args)

    def switch_screen(self, screen_name):
        app.switch_screen(screen_name)
