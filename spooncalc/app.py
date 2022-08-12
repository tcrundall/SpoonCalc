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
from kivy.config import Config
Config.set('graphics', 'width', '393')
Config.set('graphics', 'height', '830')

from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.stacklayout import StackLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy_garden.graph import Graph, LinePlot
from kivy.clock import Clock
from kivy.core.window import Window

from datetime import datetime, timedelta
import sqlite3
# import pandas as pd       # pandas not playing nicely with buildozer

from kivy.utils import platform
from pathlib import Path
import os

from spooncalc import analyser
from spooncalc import dbtools
from spooncalc import timeutils

# Android specific imports
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


class ImportWindow(Screen):
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
        filepath = os.path.join(EXTERNALSTORAGE, filename)
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


class PlotWindow(Screen):
    """
    A window that displays various informative plots

    Attributes
    ----------
    ymax_persistent : int
        The plots' shared max y, increased as needed, but not reduced
    start : int
        The starting day (a plot's x min) in terms of offset from today
    span : int
        The range of days (a plot's x range)
    end : int
        The ending day (a plot's x max) in terms of offset from today
    mode : str ("daily" | "weekly" | "monthly")
        Sets the plotting mode from a defined set. "daily" is a single day,
        shows cumulative spoons spent over hours. "weekly" (or "monthly")
        show the total spoons spent each day, over days with a span of
        7 (or 28)
    day_offset : int
        For "daily" plots, sets the day desired
    plot_title : StringProperty
        The title of the plot, accessible by kivy lang
    plot_initialized : bool
        A flag indicating plot initialization status
    """
    plot_title = StringProperty("Weekly")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ymax_persistent = 27
        self.start = -7
        self.span = 8
        self.end = 0
        self.mode = "weekly"
        self.day_offset = 0
        self.plot_initialized = False

    def on_pre_enter(self):
        """
        Method(s) to be executed before switching to this window.
        """
        if not self.plot_initialized:
            self.init_plot()
        self.plot_initialized = True
        self.update_plot()

    def init_plot(self):
        """
        Initializes the kivy_garden.Graph and .LinePlot objects

        LinePlot will be updated to reflect changes in mode and x-range
        """
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

        # The default mode is weekly, so we plot daily totals
        self.spoons_per_day = analyser.calculate_daily_totals(
            self.start, self.span)
        self.plot = LinePlot(color=[1, 1, 0, 1], line_width=1.5)
        self.plot.points = [(-d, spoons)
                            for d, spoons in self.spoons_per_day.items()]
        self.graph.add_plot(self.plot)

    def update_plot(self):
        """
        Update plot, reflecting changes in mode and/or x-range
        """
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
        """
        Shift the plot to show earlier data.

        The amount to shift is determined by the current mode
        """
        if self.mode == "weekly":
            self.start -= 1
        elif self.mode == "monthly":
            self.start -= 7
        elif self.mode == "daily":
            self.day_offset -= 1
        self.update_plot()

    def shift_window_right(self):
        """
        Shift the plot to show later data.

        The amount to shift is determined by the current mode
        """
        if self.mode == "weekly":
            self.start += 1
        elif self.mode == "monthly":
            self.start += 7
        elif self.mode == "daily":
            self.day_offset += 1
        self.update_plot()

    def set_weekly(self):
        """
        Set the current mode to weekly, updating key attributes as required
        """
        if self.mode == "weekly":
            return
        self.mode = "weekly"
        self.plot_title = self.mode.capitalize()
        self.start = -7
        self.span = 8
        self.graph.x_ticks_major = 1
        self.update_plot()

    def set_monthly(self):
        """
        Set the current mode to monthly, updating key attributes as required
        """
        if self.mode == "monthly":
            return
        self.mode = "monthly"
        self.plot_title = self.mode.capitalize()
        self.start = -28
        self.span = 29
        self.graph.x_ticks_major = 7
        self.update_plot()

    def set_daily(self):
        """
        Set the current mode to daily, updating key attributes as required
        """
        if self.mode == "daily":
            return
        self.mode = "daily"
        self.update_plot()

    def plot_daily(self):
        """
        Plot the cumulative spoon expenditure over a 24 hour period.

        The daily plot uses hours for the x units and therefore has different
        graph properties to the weekly and monthly modes.

        Note that since users may stay up past midnight, the `DAY_BOUNDARY`
        is not necessarily equal to 0 (i.e. midnight). Currently it is set to
        3am.
        """
        self.graph.xmin = timeutils.DAY_BOUNDARY
        self.graph.xmax = timeutils.DAY_BOUNDARY + 24
        self.graph.ymin = 0
        self.graph.ymax = self.ymax_persistent
        self.graph.x_ticks_major = 3
        self.graph.y_ticks_major = 5

        xs, ys = analyser.cumulative_time_spoons(self.day_offset)

        # If plotting for a past day, extend line plot to end of x range
        if self.day_offset < 0 and max(xs) < self.graph.xmax:
            xs.append(self.graph.xmax)
            ys.append(ys[-1])

        self.plot.points = list(zip(xs, ys))
        self.update_daily_title()

    def update_daily_title(self):
        date = datetime.now().date() + timedelta(days=self.day_offset)
        self.plot_title = date.strftime("%A %d.%m")


class MenuWindow(Screen):
    """
    The main "home" window with access to all features

    Attributes
    ----------
    spoons_spent_display : StringProperty
        label showing total spoons spent today over the average daily total
    plot_initialized : bool
        A flag indicating initialization status of the home screen plot
    """
    spoons_spent_display = StringProperty()
    plot_initialized = False

    def on_enter(self, *args):
        """
        Methods to execute right before switching to this window

        These methods depend on the existence of the database, however
        the database is only guaranteed to exist after App.build() is
        executed. Therefore the methods arent executed here, but scheduled
        (with a time delay of 0 seconds). Scheduled tasks seem to be run
        only after the app is built.
        """
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

        Parameters
        ----------
        dt : float, unused
            only included to satisfy schedulable methods signature requirement
        """
        spoons_today = analyser.calculate_daily_total(0)
        spoons_average = analyser.average_spoons_per_day(-14, 0)
        self.spoons_spent_display =\
            f"{spoons_today:.0f} / {spoons_average:.0f}"

    def export_database(self):
        """
        Export the entire activities database as a csv file.
        """
        # Request entire contents of database
        filename = os.path.join(EXTERNALSTORAGE, 'spoon-output.csv')
        conn = sqlite3.connect(DATABASE)
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

    def init_plot(self, dt=None):
        """
        Initialize the home screen plot.

        This plot shows the cumulative spoon expenditure for the current day,
        and the mean (+/- 1 standard deviation) of the last 14 days.

        Note that in this method the only ploints plotted is that for the mean
        and standard deviation offsets (mean, below, above). The points for
        today are plotted in .update_plot(). Done this way, the mean (+/- std)
        must only be calculated once per day.

        Parameters
        ----------
        dt : float, unused
            only included to satisfy signature requirement of schedulable
            methods
        """
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

        # Initialize all the LinePlot objects
        self.today = LinePlot(color=[1, 1, 0, 1], line_width=3)
        self.mean = LinePlot(color=[1, 0, 0, 1], line_width=1.5)
        self.below = LinePlot(color=[1, 0, 0, 0.8], line_width=1.5)
        self.above = LinePlot(color=[1, 0, 0, 0.8], line_width=1.5)

        # Get the mean (plus and minus 1 standard deviation) of past 14 days
        # and provide points to LinePlot objects
        xs, mean, below, above = analyser.get_mean_and_spread()
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above)

        self.graph.add_plot(self.mean)
        self.graph.add_plot(self.below)
        self.graph.add_plot(self.above)
        self.graph.add_plot(self.today)

    def update_plot(self, dt=None):
        """
        Update the plot by plotting the day's cumulative spoons.

        Note that the mean, below and above plots remain unchanged.
        """
        print("Plotting daily!")
        today = 0
        xs, ys = analyser.cumulative_time_spoons(day_offset=today)

        self.today.points = list(zip(xs, ys))

    def update_mean_and_spread(self):
        """
        Update the mean and standard deviation plots

        This mthod is only ever activated when the database is updated
        via an "import". Note that this method could be getting called from
        kivy lang.
        """
        xs, mean, below, above = analyser.get_mean_and_spread()
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above)


# class MainWidget(BoxLayout):
class InputWindow(Screen):
    """
    This window allows the user to input an activity.

    Attributes
    ----------
    title : StringProperty
        the title of the window, accessible by Kivy
    start_display : StringProperty
        string representation of activity start time, accessible by kivy
    end_display : StringProperty
        string representation of activity end time, accessible by kivy
    time_buttons : dict(str : int)
        dictionary converting the text for timing buttons to minutes
    cogload : float
        the cognitive load of activity (from 0 to 2 spoons per hour)
    physload : float
        the physical load of activity (from 0 to 2 spoons per hour)
    energ : float
        the current energy level of user (0, 1, or 2)
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
        """
        Before entering, reset all load values, toggles and times

        TODO: this is currently bugged (see issue #36).
        Values and toggles not resetting properly
        """
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
                    # TODO: Maybe `_do_press` can both set and unset toggles
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

        TODO:   incorporate timeutils.DAY_BOUNDARY in finding most
                recent activity. See issue #36
        """
        self.end_datetime = timeutils.round_datetime(datetime.now())
        self.start_datetime = dbtools.get_latest_endtime()

        # If start time is not from today, then set 1 hour before end time
        if (self.start_datetime.date() != datetime.now().date()):
            self.start_datetime = self.end_datetime - timedelta(hours=1)

    def update_time_displays(self):
        """
        Update the string time displays, reflecting changes from start
        and end times.
        """
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
        """
        Handle press of "Save" button
        """
        successful = self.insert_into_database()
        if successful:
            self.manager.go_back()
            print("NAILED IT!")
        else:
            self.title = "hmmm... bad data?"

    def get_widgets_in_group(self, group):
        """
        Collect all widgets that are a member of `group`.

        This is useful for finding all the toggles associated with
        physical load, such that we can guarantee one of them is set
        when entering the window
        """
        widgets = []
        for id, widget in self.ids.items():
            if hasattr(widget, 'group') and widget.group == group:
                widgets.append(widget)
        return widgets

    def get_down_from_group(self, group):
        """
        Identify which toggle from a provided widget group is down
        """
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


class StackedLogsLayout(StackLayout):
    """
    A container for displaying all activity logs from a given day.

    The first 'initialisation' is handled by
    LogsWindow's on_pre_enter call.

    Attributes
    ----------
    current_day : int
        the day in question, encoded as an offset from today
    boxes : list(EntryBox)
        a list of all entryBoxes, where each entryBox is a widget
        displaying partial information of a logged activity.
    """
    current_day = 0
    boxes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set the stacking order: left-to-right, then top-to-bottom
        self.orientation = 'lr-tb'

    def update(self):
        """
        Update the list of all children (EntryBox) Widgets.

        Convert each of the `current_day`s database entries into an
        EntryBox, and add them (in time order) to this StackedLayout
        """
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

        self.add_widget(TitleBox())             # Add a header
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
        """
        Find the checked EntryBox, and delete corresponding entry
        from database.
        """
        for entrybox in self.boxes:
            if entrybox.checkbox._get_active():
                dbtools.delete_entry(entrybox.db_id)
                self.update()
                return

    def decrement_day(self):
        """
        Display logs for previous day
        """
        self.current_day -= 1
        self.update()

    def increment_day(self):
        """
        Display logs for following day
        """
        self.current_day += 1
        self.update()


class TitleBox(BoxLayout):
    """
    A simple class that serves as a header "row" in the StackedLogsLayout
    """
    def __init__(self, **kwargs):
        super().__init__(
            size_hint=(1, None),
            size=("20dp", "30dp"),
            **kwargs,
        )
        self.orientation = "horizontal"
        # The size hints are hardcoded, but should match those of the EntryBox
        self.add_widget(Label(text="Time", size_hint=(0.2, 1)))
        self.add_widget(Label(text="Activity", size_hint=(0.45, 1)))
        self.add_widget(Label(text="Cog", size_hint=(0.1, 1)))
        self.add_widget(Label(text="Ph.", size_hint=(0.1, 1)))
        self.add_widget(Label(text="Sp.", size_hint=(0.1, 1)))
        self.add_widget(Label(text="X", size_hint=(0.05, 1)))


class EntryBox(BoxLayout):
    """
    A class that serves as a display widget for activity logs in
    the StackedLogsLayout.

    Attributes
    ----------
    db_id : int
        a unique identifier for the database entry whose data the EntryBox
        displays
    """
    def __init__(
        self, db_id, start, end,
        duration, name, cogload, physload,
        **kwargs
    ):
        """
        Initialize the EntryBox with the data from a database entry
        corresponding to a logged activity.

        An EntryBox is designed to look like a data row in a table.
        Each element in the data row is a Label with text taken from
        the inputted parameters. The size_hints are hardcoded, but should
        match those in TitleBox in order to maintain a "table" like
        appearance.

        Each EntryBox also has a CheckBox as the final element. All the
        CheckBoxes are assigned to the same group, which allows for
        a specific EntryBox to be selected, and thereby acted upon,
        e.g. StackedLogsLayout.delete_entry

        Parameters
        ----------
        db_id : int
            unique id from database
        start : str
            the start time of activity, already formatted as "HH:MM"
        end : str
            the end time of activity, already formatted as "HH:MM"
        duration : str
            the duration of activity, as formatted in database
        name : str
            activity name, as taken from database
        cogload : str
            cognitive load, as taken from database
        physload : str
            physical load, as taken from database

        TODO:   Write, and then utilize, a LoggedActivity class in order
                to avoid this formatting nonsense.
        """
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
    """
    The window manager which holds instances of all windows.

    The current window layout is:
        MenuWindow
            InputWindow
            PlotWindow
            LogsWindow
            ImportWindow
    """
    def go_back(self):
        """
        Handle event for going back to the previous screen.

        At the moment the screen layout is simple, such that
        "going back" always leads to the menu screen.
        """
        # Try and apply any screen specific "go back" stuff
        try:
            self.current_screen.pre_go_back()
        except AttributeError:
            pass

        self.transition.direction = "right"
        self.current = 'menu'


class SpoonCalcApp(App):
    """
    The main class for Spoon Calculator.

    This class holds all the (python) methods required for building,
    initialising, and reacting.
    """

    def on_start(self):
        """
        When starting the app up for the first time, we must bind the
        keyboard to the Window in order to capture input.

        Returning True tells Kivy that the start was successful
        """
        win = Window
        win.bind(on_keyboard=self.my_key_handler)
        return True

    def build(self):
        """
        This method builds the app, initialising what must be initialised.

        Spoon Calculator relies on a database for storing and retriving
        activity data. If this database doesn't exist yet, it is created
        here.

        We also initialise our custom WindowManager and instantiate all
        the required windows.
        """

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

        wm = WindowManager()
        wm.add_widget(MenuWindow(name="menu"))
        wm.add_widget(InputWindow(name="input"))
        wm.add_widget(LogsWindow(name="logs"))
        wm.add_widget(PlotWindow(name="plot"))
        wm.add_widget(ImportWindow(name="import"))
        self.manager = wm

        return wm

    def my_key_handler(self, window, keycode1, keycode2, text, modifiers):
        """
        This (potentially quite general) method captures the android "back" and
        either changes screen to MenuWindow or quits the app.

        The Android "back" command has the same keycode as <esc>

        Parameters
        ----------
        window : ?
            unused
        keycode1 : int
            the code of a pressed key
        keycode2 : int
            unused
        text : ?
            unused
        modifiers : ?
            unused
        """
        if keycode1 in [27]:
            if self.manager.current == 'menu':
                self.get_running_app().stop()
            self.manager.go_back()
            return True
        return False
