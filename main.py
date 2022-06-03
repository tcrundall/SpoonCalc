from kivy.config import Config
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.app import App
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout

from datetime import datetime, timedelta
import sqlite3

DATABASE = 'spooncalc.db'

LOW = 1
MID = 2
HI = 3


class MainWidget(BoxLayout):
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
    title = StringProperty("Log Activity")

    duration_timedelta = timedelta(hours=1)
    duration_display = StringProperty(
        ":".join(str(duration_timedelta).split(':')[:2])
    )

    end_datetime = datetime.now().replace(minute=0, second=0, microsecond=0)
    end_display = StringProperty(end_datetime.strftime("%H:%M"))

    start_datetime = end_datetime - duration_timedelta

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

    def on_toggle(self, toggle, load):
        """
        Ensure that exactly one toggle for load `load` is down
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

        print(f"{self.duration_timedelta=!s}")

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
        c.execute("INSERT INTO activities VALUES (:end), (:duration), " +
                  "(:name), (:cogload), (:physload), (:energy)",
                  {
                      'end': str(self.end_datetime),
                      'duration': str(self.duration_timedelta),
                      'name': self.ids['activity_name'].text,
                      'cogload': self.get_level('cog'),
                      'physload': self.get_level('phys'),
                      'energy': self.get_level('energy')
                  })
        conn.commit()
        c.execute("SELECT * FROM activities")
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


class SpoonCalcApp(App):
    def build(self):
        print("BUILDING APP!!!")
        conn = sqlite3.connect(DATABASE)

        c = conn.cursor()

        # c.execute("DROP TABLE if exists activities")
        # c.execute("""CREATE TABLE activities(
        c.execute("""CREATE TABLE if not exists activities(
            name text
            cogload text 
            endtime text
        )
        """)

        conn.commit()

        conn.close()


if __name__ == '__main__':
    SpoonCalcApp().run()
