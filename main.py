from kivy.config import Config
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.app import App
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout

import datetime
import json
import os
import sqlite3
import time

DATA_DIR = 'data'
DATABASE = 'activitytracker.db'

LOW = 1
MID = 2
HI = 3


class MainWidget(BoxLayout):
    duration = 60
    duration_min = NumericProperty(0)
    duration_hr = NumericProperty(duration // 60)

    end_time = time.localtime().tm_hour * 60
    # print(f"{end_time=}")
    end_time_min = NumericProperty(0)
    end_time_hr = NumericProperty(end_time // 60)
    # end_time_hr = end_time // 60
    # print(end_time // 60)
    # print(f"{int(end_time_hr)}")
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
        if toggle.state == "down":
            for id in self.button_ids[load]:
                if self.ids[id] != toggle:
                    self.ids[id].state = "normal"

    # def on_toggle_cog(self, toggle):
    #     """
    #     Ensure only one cognitive load toggle can
    #     be down.
    #     """
    #     if toggle.state == 'down':
    #         for id in self.cog_button_ids:
    #             # import ipdb; ipdb.set_trace()
    #             if self.ids[id] != toggle:
    #                 self.ids[id].state = "normal"

    # def on_toggle_phys(self, toggle):
    #     """
    #     Ensure only one physical load toggle can
    #     be down.
    #     """
    #     if toggle.state == 'down':
    #         for id in self.phys_button_ids:
    #             # import ipdb; ipdb.set_trace()
    #             if self.ids[id] != toggle:
    #                 self.ids[id].state = "normal"

    def on_toggle_duration(self, widget):
        duration = 0
        for id, val in self.duration_toggles.items():
            if self.ids[id].state == "down":
                duration += val
        self.duration_min = duration % 60
        self.duration_hr = duration // 60

    # def on_dur_text_validate(self, widget):
    #     duration = None
    #     # assume x:xx format
    #     duration = widget.text.split(':')

    #     try:
    #         duration = int(widget.text)
    #     except ValueError:
    #         pass
    #     if duration is None

    def on_end_time_press(self, button: Button):
        self.end_time += self.end_time_buttons[button.text]
        self.end_time %= (24 * 60)

        self.end_time_min = self.end_time % 60
        self.end_time_hr = self.end_time // 60

    # def on_toggle_energy(self, toggle: ToggleButton):
    #     """
    #     Ensure only one physical load toggle can
    #     be down.
    #     """
    #     print(f"{toggle.parent.text=}")
    #     print(f"{toggle.parent.ids=}")
    #     print(f"{self.ids=}")
    #     print(f"{toggle.text=}")
    #     print(f"{toggle.proxy_ref=}")
    #     # print(f"{toggle.=}")
    #     if toggle.state == 'down':
    #         for id in self.energy_button_ids:
    #             # import ipdb; ipdb.set_trace()
    #             if self.ids[id] != toggle:
    #                 self.ids[id].state = "normal"

    def insert_into_database(self):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO activities VALUES (:name), (:cogload), (:end)",
                  {
                      'name': self.ids['activity_name'].text,
                      'cogload': self.get_level('cog'),
                      'end': self.end_time,
                  })
        conn.commit()
        c.execute("SELECT * FROM activities")
        contents = c.fetchall()
        conn.commit()
        print(contents)
        
        conn.close()

    def on_save_press(self):
        save_dict = self.build_save_dict()
        filename = os.path.join(DATA_DIR, self.generate_ativity_name())
        with open(filename, 'w') as fp:
            save_json = json.dump(save_dict, fp)

        self.insert_into_database()

    def get_level(self, load):
        for id in self.button_ids[load]:
            if self.ids[id].state == "down":
                return id.split('_')[-1]
        return -1

    def build_save_dict(self):
        activity_log = {}
        for load in ['cog', 'phys', 'energy']:
            activity_log[load] = self.get_level(load)
        activity_log['duration'] = self.duration
        activity_log['end_time'] = self.end_time
        activity_log['activity_name'] = self.ids['activity_name'].text
        return activity_log

    def generate_ativity_name(self):
        """
        date, time, name
        """
        now = time.localtime()
        filename = f"{now.tm_year}_{now.tm_mon:02}_{now.tm_mday:02}_" +\
                   f"{now.tm_hour:02}_{now.tm_min:02}_{now.tm_sec:02}"
        # TODO: set `activity name` to a default string
        if self.ids['activity_name'].text != "Activity name":
            filename += f"_{self.ids['activity_name'].text}"
        filename += '.json'
        return filename


class ActivityTrackerApp(App):
    def build(self):
        print("BUILDING APP!!!")
        conn = sqlite3.connect(DATABASE)

        c = conn.cursor()

        # c.execute("""CREATE TABLE if not exists activities(
        c.execute("DROP TABLE if exists activities")
        c.execute("""CREATE TABLE activities(
            name text
            cogload text 
            endtime text
        )
        """)

        conn.commit()

        conn.close()


if __name__ == '__main__':
    ActivityTrackerApp().run()
