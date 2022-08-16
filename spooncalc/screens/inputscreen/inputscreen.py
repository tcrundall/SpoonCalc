from datetime import datetime, timedelta
import os
from pathlib import Path

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.button import Button

from spooncalc import timeutils
from spooncalc.models.activitylog import ActivityLog

Builder.load_file(os.path.join(
    Path(__file__).parent.absolute(),
    "inputscreen.kv"
))


class InputScreen(Screen):
    """
    This screen allows the user to input an activity.

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

    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.activitylog = ActivityLog()

    def on_pre_enter(self):
        """
        Before entering, reset all load values, toggles and times

        TODO: this is currently bugged (see issue #36).
        Values and toggles not resetting properly
        """

        # Reset title
        self.title = "Log Activity"
        self.activitylog = ActivityLog()
        self.ids.activity_name.text = self.activitylog.name

        # Reset load toggles
        default_pressed_toggle_ids = ["cog_mid", "phys_mid", "energy_mid"]
        for toggle_id in default_pressed_toggle_ids:
            if self.ids[toggle_id].state == "normal":
                self.ids[toggle_id]._do_press()

        # Reset times
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

        self.activitylog.end = timeutils.round_datetime(datetime.now())
        self.activitylog.start = self.db.get_latest_endtime()

        # If start time is not from today, then set 1 hour before end time
        if (self.activitylog.start.date() != datetime.now().date()):
            self.activitylog.start = self.activitylog.end - timedelta(hours=1)

    def set_cogload(self, cogload):
        self.activitylog.cogload = cogload

    def set_physload(self, physload):
        self.activitylog.physload = physload

    def set_energy(self, energy):
        self.activitylog.energy = energy

    def update_time_displays(self):
        """
        Update the string time displays, reflecting changes from start
        and end times.
        """

        # If start or end time is not from today, include dates in display
        if self.activitylog.is_everything_today():
            format_string = "%H:%M"
        else:
            format_string = "%d/%m\n%H:%M\n"

        self.start_display = self.activitylog.start.strftime(format_string)
        self.end_display = self.activitylog.end.strftime(format_string)

    def on_start_time_press(self, button: Button):
        """
        Inc-/decrement the end time based on pressed button and update display

        The value to be inc-/decremented is inferred from the
        button's text.
        """

        self.activitylog.start += timedelta(
            minutes=self.time_buttons[button.text]
        )

        # if duration would be negative, shift end time to 1 hourafter start
        duration = self.activitylog.end - self.activitylog.start
        if duration.total_seconds() <= 0:
            self.activitylog.end = self.activitylog.start + timedelta(hours=1)
        self.update_time_displays()

    def on_end_time_press(self, button: Button):
        """
        Inc-/decrement the end time based on pressed button and update display

        The value to be inc-/decremented is inferred from the
        button's text.
        """

        self.activitylog.end += timedelta(
            minutes=self.time_buttons[button.text]
        )

        # If the duration would be negative, shift start to 1 hour before end
        duration = self.activitylog.end - self.activitylog.start
        if duration.total_seconds() <= 0:
            self.activitylog.start = self.activitylog.end - timedelta(hours=1)
        self.update_time_displays()

    def insert_into_database(self):
        """
        Insert current inputted data into the database
        """

        duration_timedelta = self.activitylog.get_duration()

        if duration_timedelta and duration_timedelta.total_seconds() < 0:
            return False

        raw_activity_name = self.ids['activity_name'].text
        for char in ',.:-\"\'':
            self.activitylog.name = raw_activity_name.replace(char, '')

        query_text = f"""
            INSERT INTO activities
                (start, end, duration, name, cogload, physload, energy)
                VALUES(
                    {self.activitylog.get_value_string()}
                );
        """
        self.db.submit_query(query_text)

        return True

    def on_save_press(self):
        """
        Handle press of "Save" button
        """

        successful = self.insert_into_database()
        if successful:
            self.manager.switch_screen("menuscreen")
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
