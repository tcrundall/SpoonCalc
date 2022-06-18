from kivy.config import Config
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.garden.graph import Graph, LinePlot

from datetime import datetime, timedelta
import sqlite3
# import pandas as pd

# Android specific imports
from kivy.utils import platform
from pathlib import Path
import os

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

    EXTERNALSTORAGE = primary_external_storage_path()
if platform == 'macosx':
    home = str(Path.home())
    EXTERNALSTORAGE = home

print(f'{platform=}')
print(f'{EXTERNALSTORAGE=}')

DATABASE = 'spooncalc.db'


class MyPopup(Popup):
    text = StringProperty()

    def open(self, **kwargs):
        query_text = '''
            select start, end, duration, name, cogload, physload, energy 
            from activities
        '''
        conn = sqlite3.connect(DATABASE)

        c = conn.cursor()
        c.execute(query_text)
        contents = c.fetchall()
        max_length = {i: 0 for i in range(len(c.description))}
        header = [col[0] for col in c.description]
        for entry in contents:
            for i, value in enumerate(entry):
                max_length[i] = max(max_length[i], len(str(value)))
        for i, colname in enumerate(header):
            max_length[i] = max(max_length[i], len(colname))

        SEP = ' | '

        print([des[0] for des in c.description])
        formatted_header = SEP.join([str(col[0]).ljust(max_length[i])
                                     for i, col in enumerate(c.description)])
        print(formatted_header)
        formatted_contents = '\n'.join([SEP.join([
            str(val).ljust(max_length[i]) for i, val in enumerate(entry)
        ]) for entry in contents])
        print(formatted_contents)
        self.text = '\n'.join((formatted_header, formatted_contents))

        conn.close()

        super().open(**kwargs)


class MenuWindow(Screen):
    def export_database(self):
        filename = os.path.join(EXTERNALSTORAGE, 'spoon-output.csv')
        with open(filename, 'w') as fp:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("SELECT * FROM activities")
            contents = c.fetchall()
            SEP = ','
            formatted_header = SEP.join([str(col[0])
                                        for col in c.description])
            formatted_contents = '\n'.join([SEP.join([
                str(val) for val in entry
            ]) for entry in contents])
            text = '\n'.join((formatted_header, formatted_contents))
            fp.write(text)

            conn.close()


# class MainWidget(BoxLayout):
class InputWindow(Screen):
    """
    Activity input
    Use this widget to input an activity with the following properties:
        - namm
        - cognitive load
        - physical load
        - duration
        - end time
        - current energy level

    Limitations/assumptions:
        - can only input data for today
    
    Possible extensions:
        - snap begin time to end of last event
    """
    title = StringProperty()

    # duration_timedelta = 
    duration_display = StringProperty()

    end_datetime = datetime.now().replace(minute=0, second=0, microsecond=0)
    end_display = StringProperty()

    # start_datetime = end_datetime - duration_timedelta

    button_ids = {
        'cog': {
            'cog_low',
            'cog_mid',
            'cog_high',
        },
        'phys': {
            'phys_low',
            'phys_mid',
            'phys_high',
        },
        'energy': {
            'energy_low',
            'energy_mid',
            'energy_high',
        },
    }

    duration_toggles = {
        'dur_015': 15,
        'dur_030': 30,
        'dur_1': 60,
        'dur_2': 120,
        'dur_4': 240,
    }

    end_time_buttons = {
        '-1': -60,
        '-0:15': -15,
        '+0:15': 15,
        '+1': 60,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.set_defaults()

    # def set_defaults(self):
    def on_pre_enter(self):
        # Reset title
        self.title = "Log Activity"
        self.ids.activity_name.text = "Activity name"

        # Reset load toggles
        for load in ["cog", "phys", "energy"]:
            mid_button_id = f"{load}_mid"
            self.ids[mid_button_id].state = "down"
            self.on_toggle(self.ids[mid_button_id], load)

        # Reset duration toggles
        default_dur_down = ["dur_1"]
        for id, val in self.duration_toggles.items():
            if id in default_dur_down:
                self.ids[id].state = "down"
            else:
                self.ids[id].state = "normal"
        
        # Update displays

        self.on_toggle_duration(None)
        self.end_datetime = datetime.now().replace(
            minute=0, second=0, microsecond=0
        )
        self.end_display = self.end_datetime.strftime("%H:%M")
        self.start_datetime = self.end_datetime - self.duration_timedelta

    def on_toggle(self, toggle, load):
        """
        Ensure that exactly one toggle for load `load` is down

        Parameters
        ----------
        toggle: the toggle button
        load: ('cog'|'phys'|'energy')
        """
        if toggle.state == "down":
            for id in self.button_ids[load]:
                if self.ids[id] != toggle:
                    self.ids[id].state = "normal"

    def on_toggle_duration(self, widget):
        """
        Recalculate activity duration on each new toggle
        """
        duration_timedelta = timedelta()
        for id, val in self.duration_toggles.items():
            if self.ids[id].state == "down":
                duration_timedelta += timedelta(minutes=val)

        self.duration_timedelta = duration_timedelta
        self.duration_display = \
            ':'.join(str(self.duration_timedelta).split(':')[:2])

    def on_end_time_press(self, button: Button):
        """
        Inc-/decrement the end time based on pressed button and update display

        The value to be inc-/decremented is inferred from the 
        button's text.
        """
        self.end_datetime += timedelta(
            minutes=self.end_time_buttons[button.text]
        )
        self.end_display = self.end_datetime.strftime("%H:%M")

    def insert_into_database(self):
        """
        Insert current inputted data into the database
        """
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
            
        c.execute("INSERT INTO activities "
                  + "(start, end, duration, name, cogload, physload, energy) "
                  + " VALUES( "
                  + ":start, :end, :duration, "
                  + ":name, :cogload, :physload, :energy)",
                  {
                      'start': str(self.start_datetime),
                      'end': str(self.end_datetime),
                      'duration': str(self.duration_timedelta),
                      'name': self.ids['activity_name'].text,
                      'cogload': self.get_level('cog'),
                      'physload': self.get_level('phys'),
                      'energy': self.get_level('energy')
                  })
        conn.commit()
        c.execute("SELECT id, start, end, duration, name, cogload, physload, energy FROM activities")
        contents = c.fetchall()
        conn.commit()
        print(contents)

        conn.close()

    def on_save_press(self):
        self.insert_into_database()
        self.title = "Good job! :)"

        # Change view screen somehow...

    def get_level(self, load):
        for id in self.button_ids[load]:
            if self.ids[id].state == "down":
                return id.split('_')[-1]
        return -1

    # def generate_ativity_name(self):
    #     """
    #     date, time, name
    #     """
    #     now = time.localtime()
    #     now = datetime.now().replace(microsecond=0)
    #     filename = str(now).replace(' ', '_').replace(':','-')

    #     # TODO: set `activity name` to a default string
    #     if self.ids['activity_name'].text != "Activity name":
    #         filename += f"_{self.ids['activity_name'].text}"
    #     filename += '.json'
    #     return filename


class WindowManager(ScreenManager):
    pass


class SpoonCalcApp(App):
    def build(self):
        print("BUILDING APP!!!")
        conn = sqlite3.connect(DATABASE)

        c = conn.cursor()

        # c.execute("DROP TABLE if exists activities")
        # c.execute("""CREATE TABLE activities(
        c.execute("""CREATE TABLE if not exists activities(
            id integer PRIMARY KEY,
            start text NOT NULL,
            end text NOT NULL,
            duration text NOT NULL,
            name text NOT NULL,
            cogload text NOT NULL,
            physload text NOT NULL,
            energy text NOT NULL
        )
        """)

        conn.commit()

        conn.close()


if __name__ == '__main__':
    SpoonCalcApp().run()
