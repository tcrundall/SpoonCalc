from kivy.config import Config
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.stacklayout import StackLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy_garden.graph import Graph, LinePlot
from kivy.clock import Clock

from datetime import datetime, timedelta
import sqlite3
# import pandas as pd

# Android specific imports
from kivy.utils import platform
from pathlib import Path
import os

import analyser
import dbtools
import timeutils

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    request_permissions([
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE
    ])
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
        colnames = ['start', 'end', 'duration', 'name',
                    'cogload', 'physload', 'energy']
        query_text = f'''
            SELECT {', '.join(colnames)}
            FROM activities
        '''
        contents = dbtools.submit_query(query_text)

        max_length = {i: 0 for i in range(len(colnames))}
        for entry in contents:
            for i, value in enumerate(entry):
                max_length[i] = max(max_length[i], len(str(value)))
        for i, colname in enumerate(colnames):
            max_length[i] = max(max_length[i], len(colname))

        SEP = ' | '

        # print([des[0] for des in c.description])
        formatted_header = SEP.join([col.ljust(max_length[i])
                                     for i, col in enumerate(colnames)])
        print(formatted_header)
        formatted_contents = '\n'.join([SEP.join([
            str(val).ljust(max_length[i]) for i, val in enumerate(entry)
        ]) for entry in contents])
        print(formatted_contents)
        self.text = '\n'.join((formatted_header, formatted_contents))

        super().open(**kwargs)


class ImportWindow(Screen):

    def on_import_press(self, filename):
        """
        Import activites from a csv file into database,
        ignoring duplicates
        """
        print(filename)
        filepath = os.path.join(EXTERNALSTORAGE, filename)
        with open(filepath, 'r') as fp:
            _ = fp.readline()       # skip header
            for line in fp:
                print(line)
                self.insert_if_unique(line)

    def insert_if_unique(self, csv_row):
        """
        If row doesn't exist in database, then insert it
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


class PlotWindow(Screen):
    """
    Display informative plots
    """
    ymax_persistent = 27
    start = -7
    span = 8
    end = 0
    mode = "weekly"
    day_start = 0
    plot_title = StringProperty(mode.capitalize())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.plot_initialized = False

    def on_pre_enter(self):
        if not self.plot_initialized:
            self.init_plot()
        self.plot_initialized = True
        self.update_plot()

    def init_plot(self):
        self.graph = Graph(
            xmin=self.start, xmax=self.start + self.span - 1,
            ymin=0, ymax=1,
            border_color=[0, 1, 1, 1],
            tick_color=[0, 1, 1, 0.7],
            x_grid=True, y_grid=True,
            draw_border=True,
            x_grid_label=True,
            y_grid_label=True,
            x_ticks_major=1,
            y_ticks_major=5,
        )
        self.ids.graph.add_widget(self.graph)

        self.spoons_per_day = analyser.calculate_daily_totals(
            self.start, self.span)
        self.plot = LinePlot(color=[1, 1, 0, 1], line_width=1.5)
        self.plot.points = [(-d, spoons)
                            for d, spoons in self.spoons_per_day.items()]
        self.graph.add_plot(self.plot)

    def update_plot(self):
        if self.mode == "daily":
            self.plot_daily()
            return
        # mode: weekly or monthly
        self.spoons_per_day = analyser.calculate_daily_totals(
            self.start, self.span)
        self.graph.xmin = self.start
        self.graph.xmax = self.start + self.span - 1
        self.plot.points = [(d, spoons)
                            for d, spoons in self.spoons_per_day.items()]
        ymax_current = max(self.spoons_per_day.values())
        self.ymax_persistent = max(ymax_current * 1.1, self.ymax_persistent)
        self.graph.ymax = self.ymax_persistent

    def shift_window_left(self):
        if self.mode == "weekly":
            self.start -= 1
        elif self.mode == "monthly":
            self.start -= 7
        elif self.mode == "daily":
            self.day_start -= 1
        self.update_plot()

    def shift_window_right(self):
        if self.mode == "weekly":
            self.start += 1
        elif self.mode == "monthly":
            self.start += 7
        elif self.mode == "daily":
            self.day_start += 1
        self.update_plot()

    def set_weekly(self):
        if self.mode == "weekly":
            return
        self.mode = "weekly"
        self.plot_title = self.mode.capitalize()
        self.start = -7
        self.span = 8
        self.graph.x_ticks_major = 1
        self.update_plot()

    def set_monthly(self):
        if self.mode == "monthly":
            return
        self.plot_title = self.mode.capitalize()
        self.mode = "monthly"
        self.start = -28
        self.span = 29
        self.graph.x_ticks_major = 7
        self.update_plot()

    def set_daily(self):
        if self.mode == "daily":
            return
        self.mode = "daily"
        self.update_plot()

    def plot_daily(self):
        print("Plotting daily!")
        self.graph.xmin = timeutils.DAY_BOUNDARY
        self.graph.xmax = timeutils.DAY_BOUNDARY + 24
        self.graph.ymin = 0
        self.graph.ymax = self.ymax_persistent
        self.graph.x_ticks_major = 3
        self.graph.y_ticks_major = 5

        xs, ys = analyser.cumulative_time_spoons(self.day_start)

        # If plotting for a past day, extend line plot to end of range
        if self.day_start < 0 and max(xs) < self.graph.xmax:
            xs.append(self.graph.xmax)
            ys.append(ys[-1])

        self.plot.points = list(zip(xs, ys))
        self.update_daily_title()

    def update_daily_title(self):
        date = datetime.now().date() + timedelta(days=self.day_start)
        self.plot_title = date.strftime("%A %d.%m")


class MenuWindow(Screen):
    spoons_spent_display = StringProperty()
    plot_initialized = False

    def on_enter(self, *args):
        # This is ugly, but I don't know how to fix.
        # Database won't be set up yet, so need to wait until
        # App.build() is executed...
        Clock.schedule_once(self.update_spoons_spent_display, 0)
        if not self.plot_initialized:
            Clock.schedule_once(self.init_plot, 0)
            self.plot_initialized = True
        Clock.schedule_once(self.update_plot, 0)
        return super().on_enter(*args)

    def update_spoons_spent_display(self, dt=None):
        """
        Update display of spoons spent today over daily spoons spent
        averaged over past fortnight
        """
        spoons_today = analyser.calculate_daily_total(0)
        spoons_average = analyser.average_spoons_per_day(-14, 0)
        self.spoons_spent_display =\
            f"{spoons_today:.0f} / {spoons_average:.0f}"

    def export_database(self):
        filename = os.path.join(EXTERNALSTORAGE, 'spoon-output.csv')
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
        conn.close()

        # Avoid exporting empty database (and risking an overwrite)
        if len(contents) == 0:
            return
        text = '\n'.join((formatted_header, formatted_contents))

        with open(filename, 'w') as fp:
            fp.write(text)

    def init_plot(self, dt=None):
        self.graph = Graph(
            xmin=timeutils.DAY_BOUNDARY,
            xmax=timeutils.DAY_BOUNDARY + 24,
            ymin=0, ymax=35,
            x_ticks_major=3,
            y_ticks_major=5,
            border_color=[0, 1, 1, 1],
            tick_color=[0, 1, 1, 0.7],
            x_grid=True, y_grid=True,
            draw_border=True,
            x_grid_label=True,
            y_grid_label=True,
            xlabel="O'Clock",
            ylabel="Spoons",
        )
        self.ids.menu_graph.add_widget(self.graph)

        self.today = LinePlot(color=[1, 1, 0, 1], line_width=3)
        self.mean = LinePlot(color=[1, 0, 0, 1], line_width=1.5)
        self.below = LinePlot(color=[1, 0, 0, 0.8], line_width=1.5)
        self.above = LinePlot(color=[1, 0, 0, 0.8], line_width=1.5)

        xs, mean, below, above = analyser.get_mean_and_spread()
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above)

        self.graph.add_plot(self.mean)
        self.graph.add_plot(self.below)
        self.graph.add_plot(self.above)
        self.graph.add_plot(self.today)

    def update_plot(self, dt=None):
        print("Plotting daily!")
        today = 0
        xs, ys = analyser.cumulative_time_spoons(day_offset=today)

        self.today.points = list(zip(xs, ys))
        # self.update_daily_title()

    def update_mean_and_spread(self):
        xs, mean, below, above = analyser.get_mean_and_spread()
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above) 


# class MainWidget(BoxLayout):
class InputWindow(Screen):
    """
    Activity input
    Use this widget to input an activity with the following properties:
        - name
        - cognitive load
        - physical load
        - duration
        - end time
        - current energy level
    """
    title = StringProperty()
    start_display = StringProperty()
    end_display = StringProperty()

    time_buttons = {
        '-1': -60,
        '-0:15': -15,
        '+0:15': 15,
        '+1': 60,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cogload = 1
        self.physload = 1
        self.energy = 1

    def on_pre_enter(self):
        # Reset title
        self.title = "Log Activity"
        self.ids.activity_name.text = "Activity name"
        self.cogload = 1
        self.physload = 1
        self.energy = 1

        # Reset load toggles
        for group in ["cogload", "physload", "energy"]:
            print(self.get_widgets_in_group(group))
            for toggle in self.get_widgets_in_group(group):
                if toggle.text.lower() == "mid":
                    toggle._do_press()

        # Reset times
        # start time set equal to latest end time
        # end time set to beginning of current hour (todo: nearest 15 mins?)
        self.initialize_times_to_default()
        self.update_time_displays()

    def initialize_times_to_default(self):
        """
        Initialize default end and start times.

        End time equal to nearest 15 mins.

        Start time is equal to end time of (chronologically) previous
        log, unless not today, in which case 1 hour before end time.
        """
        self.end_datetime = timeutils.round_datetime(datetime.now())
        self.start_datetime = dbtools.get_latest_endtime()

        # If start time is not from today, then set 1 hour before end time
        if (self.start_datetime.date() != datetime.now().date()):
            self.start_datetime = self.end_datetime - timedelta(hours=1)

    def update_time_displays(self):
        format_string = "%H:%M"
        detailed_format_string = "%d/%m\n%H:%M\n"

        # If start or end time is not from today, include dates in display
        now = datetime.now()
        if not (self.start_datetime.date() == self.end_datetime.date()
                == now.date()):
            format_string = detailed_format_string

        self.start_display = self.start_datetime.strftime(format_string)
        self.end_display = self.end_datetime.strftime(format_string)

    def on_start_time_press(self, button: Button):
        """
        Inc-/decrement the end time based on pressed button and update display

        The value to be inc-/decremented is inferred from the
        button's text.
        """
        self.start_datetime += timedelta(
            minutes=self.time_buttons[button.text]
        )
        duration = self.end_datetime - self.start_datetime
        if duration.total_seconds() <= 0:
            self.end_datetime = self.start_datetime + timedelta(hours=1)
        self.update_time_displays()

    def on_end_time_press(self, button: Button):
        """
        Inc-/decrement the end time based on pressed button and update display

        The value to be inc-/decremented is inferred from the
        button's text.
        """
        self.end_datetime += timedelta(
            minutes=self.time_buttons[button.text]
        )
        duration = self.end_datetime - self.start_datetime
        if duration.total_seconds() <= 0:
            self.start_datetime = self.end_datetime - timedelta(hours=1)
        self.update_time_displays()

    def insert_into_database(self):
        """
        Insert current inputted data into the database
        """
        duration_timedelta = self.end_datetime - self.start_datetime
        if duration_timedelta.total_seconds() < 0:
            return False

        raw_activity_name = self.ids['activity_name'].text
        for char in ',.:-\"\'':
            raw_activity_name = raw_activity_name.replace(char, '')

        query_text = f"""
            INSERT INTO activities
                (start, end, duration, name, cogload, physload, energy)
                VALUES(
                    "{self.start_datetime}",
                    "{self.end_datetime}",
                    "{duration_timedelta}",
                    "{raw_activity_name}",
                    "{self.cogload}", "{self.physload}", "{self.energy}"
                );
        """
        dbtools.submit_query(query_text)

        return True

    def on_save_press(self):
        successful = self.insert_into_database()
        if successful:
            self.manager.transition.direction = "right"
            self.parent.current = "menu"
            print("NAILED IT!")
        else:
            self.title = "hmmm... bad data?"

    def get_widgets_in_group(self, group):
        widgets = []
        for id, widget in self.ids.items():
            if hasattr(widget, 'group') and widget.group == group:
                widgets.append(widget)
        return widgets

    def get_down_from_group(self, group):
        toggle = [
            widget for id, widget in self.ids.items()
            if (
                hasattr(widget, 'group')
                and widget.group == group
                and widget.state == "down"
            )
        ]
        # todo: check if non-empty?
        return toggle


class LogsWindow(Screen):
    title = StringProperty(datetime.today().strftime('%d.%m.%Y'))

    def update_title(self, day_offset):
        day_delta = timedelta(days=day_offset)
        current_day = datetime.today() + day_delta
        self.title = current_day.strftime('%d.%m.%Y')

    def on_pre_enter(self, *args):
        self.ids["logs_display"].update()
        super().on_pre_enter(*args)


class StackedLogsLayout(StackLayout):
    """
    The first 'initialisation' is handled by
    LogsWindow's on_pre_enter call.
    """
    current_day = 0
    boxes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'lr-tb'

    def update(self):
        self.clear_widgets()
        print("Making entry row!")
        self.boxes = []

        # Grab all logs from today
        entries = dbtools.get_logs_from_day(
            self.current_day,
            colnames=[
                'id',
                'start',
                'end',
                'duration',
                'name',
                'cogload',
                'physload',
            ],
        )

        # Sort entries by start time
        entries = sorted(entries, key=lambda e: e['start'])

        self.add_widget(TitleBox())
        # for i in range(1, 6):
        for entry in entries:
            id = entry['id']
            start = entry['start'].split(' ')[1][:5]    # remove date, seconds
            end = entry['end'].split(' ')[1][:5]
            duration = entry['duration']
            name = entry['name']
            cogload = entry['cogload']
            physload = entry['physload']
            entry_box = EntryBox(
                id, start, end,
                duration, name,
                cogload, physload
            )
            self.boxes.append(entry_box)
            self.add_widget(entry_box)

    def delete_entry(self):
        """find checked row, and remove from database"""
        print("not yet implemented")
        for entrybox in self.boxes:
            if entrybox.checkbox._get_active():
                dbtools.delete_entry(entrybox.db_id)
                self.update()
                return

    def decrement_day(self):
        self.current_day -= 1
        self.update()

    def increment_day(self):
        self.current_day += 1
        self.update()


class TitleBox(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(1, None),
            size=("20dp", "30dp"),
            **kwargs,
        )
        self.orientation = "horizontal"
        self.add_widget(Label(text="Time", size_hint=(0.2, 1)))
        self.add_widget(Label(text="Activity", size_hint=(0.45, 1)))
        self.add_widget(Label(text="Cog", size_hint=(0.1, 1)))
        self.add_widget(Label(text="Ph.", size_hint=(0.1, 1)))
        self.add_widget(Label(text="Sp.", size_hint=(0.1, 1)))
        self.add_widget(Label(text="X", size_hint=(0.05, 1)))


class EntryBox(BoxLayout):
    def __init__(
        self, db_id, start, end,
        duration, name, cogload, physload,
        **kwargs
    ):
        super().__init__(
            size_hint=(1, None),
            size=("20dp", "30dp"),
            **kwargs,
        )
        self.db_id = db_id
        self.orientation = "horizontal"

        time_label = Label(
            text=f"{start}-{end}",
            size_hint=(0.2, 1),
            # size=("20dp", "100dp")
        )
        self.add_widget(time_label)

        name_label = Label(
            text=f"{name}",
            size_hint=(0.45, 1)
        )
        self.add_widget(name_label)

        self.add_widget(Label(text=str(cogload), size_hint=(0.1, 1)))
        self.add_widget(Label(text=str(physload), size_hint=(0.1, 1)))
        spoons = analyser.calculate_spoons(duration, cogload, physload)
        self.add_widget(Label(text=f"{str(spoons):<4}", size_hint=(0.1, 1)))

        self.checkbox = CheckBox(
            size_hint=(0.05, 1),
            group="day_logs",
            color=(0, 1, 0, 1),
        )

        self.add_widget(self.checkbox)


class WindowManager(ScreenManager):
    pass


class SpoonCalcApp(App):
    def on_start(self):
        print("--------------------------------------------------")
        print("-------------  ON START!!!  ----------------------")
        print("--------------------------------------------------")
        return True

    def on_resume(self):
        print("--------------------------------------------------")
        print("-------------  ON RESUME!!!  ---------------------")
        print("--------------------------------------------------")
        return True

    def on_pause(self):
        print("--------------------------------------------------")
        print("-------------  ON PAUSE!!!  ----------------------")
        print("--------------------------------------------------")
        return True

    def build(self):
        print("-----------------------------------------------")
        print("--------------- BUILDING APP!!! ---------------")
        print("-----------------------------------------------")

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


if __name__ == '__main__':
    print("---- IN MAIN ----")
    SpoonCalcApp().run()
