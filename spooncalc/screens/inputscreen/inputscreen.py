from datetime import datetime, timedelta
import os
from pathlib import Path

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty

from spooncalc import timeutils
from spooncalc.models.activitylog import ActivityLog
from spooncalc.dbtools import Database

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

    def __init__(self, db, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db: Database = db

    def on_pre_enter(self) -> None:
        """
        Before entering, reset all load values, toggles and times

        TODO: this is currently bugged (see issue #36).
        Values and toggles not resetting properly
        """

        # Initialize activitylog
        start, end = self.get_default_times()
        self.activitylog = ActivityLog(start=start, end=end)

        # Initialize screen display
        self.title = "Log Activity"
        self.update_time_displays()
        self.ids.activity_name.text = self.activitylog.name

        # Reset load toggles
        default_pressed_toggle_ids = ["cog_mid", "phys_mid", "energy_mid"]
        for toggle_id in default_pressed_toggle_ids:
            if self.ids[toggle_id].state == "normal":
                self.ids[toggle_id]._do_press()

    def get_default_times(self) -> tuple[datetime, datetime]:
        """
        Initialize default end and start times.

        End time equal to nearest 15 mins.

        Start time is equal to end time of (chronologically) previous
        log, unless not today, in which case 1 hour before end time.
        """

        start = self.db.get_latest_endtime()
        end = timeutils.get_nowish()

        # If start time invalid, set to an hour before end
        if start is None or not timeutils.within_todays_boundaries(start):
            start = end - timedelta(hours=1)

        return start, end

    def set_cogload(self, cogload: float) -> None:
        """Set the activitylog's cogload"""
        self.activitylog.cogload = cogload

    def set_physload(self, physload: float) -> None:
        """Set the activitylog's physload"""
        self.activitylog.physload = physload

    def set_energy(self, energy: float) -> None:
        """Set the activitylog's energy"""
        self.activitylog.energy = energy

    def update_time_displays(self) -> None:
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

    def on_time_press(self, target: str, minutes: int) -> None:
        """
        Inc-/decrement the start or end time and update display

        Parameters
        ----------
        target : str {"start", "end"}
            select either the start or end time
        minutes : int
            the number of minutes the selected time is to be adjusted by
        """

        time_increment = timedelta(minutes=minutes)
        if target == "start":
            self.activitylog.start += time_increment
        if target == "end":
            self.activitylog.end += time_increment

        # if duration would be negative, other time is 1 hour different
        duration = self.activitylog.end - self.activitylog.start
        if duration.total_seconds() <= 0:
            if target == "start":
                self.activitylog.end = \
                    self.activitylog.start + timedelta(hours=1)
            elif target == "end":
                self.activitylog.start = \
                    self.activitylog.end - timedelta(hours=1)

        self.update_time_displays()

    def insert_into_database(self) -> bool:
        """
        Insert data currently stored in activitylog into database
        """

        duration_timedelta = self.activitylog.duration

        if duration_timedelta and duration_timedelta.total_seconds() < 0:
            return False

        raw_activity_name = self.ids['activity_name'].text
        for char in ',.:-\"\'':
            self.activitylog.name = raw_activity_name.replace(char, '')

        self.db.insert_activitylog(self.activitylog)

        return True

    def on_save_press(self) -> None:
        """
        Handle press of "Save" button
        """

        successful = self.insert_into_database()
        if successful:
            self.manager.switch_screen("menuscreen")
        else:
            self.title = "hmmm... bad data?"

    # def get_widgets_in_group(self, group) -> list[Widget]:
    #     """
    #     Collect all widgets that are a member of `group`.

    #     This is useful for finding all the toggles associated with
    #     physical load, such that we can guarantee one of them is set
    #     when entering the window
    #     """

    #     widgets = []
    #     for _, widget in self.ids.items():
    #         if hasattr(widget, 'group') and widget.group == group:
    #             widgets.append(widget)
    #     return widgets

    # def get_down_from_group(self, group) -> list[Widget]:
    #     """
    #     Identify which toggle from a provided widget group is down
    #     """

    #     toggle = [
    #         widget for _, widget in self.ids.items()
    #         if (
    #             hasattr(widget, 'group')
    #             and widget.group == group
    #             and widget.state == "down"
    #         )
    #     ]
    #     # todo: check if non-empty?
    #     return toggle
