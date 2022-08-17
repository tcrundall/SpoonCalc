from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox

from spooncalc.models.activitylog import ActivityLog


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

    def __init__(self, activitylog: ActivityLog, **kwargs) -> None:
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
        activitylog: ActivityLog
            An activity log built from the contents of a database entry.
            This activity log must have a unique id
        """

        super().__init__(
            size_hint=(1, None),
            size=("20dp", "30dp"),
            **kwargs,
        )
        if activitylog.id is None:
            raise UserWarning("Require an id generated from database")
        self.activitylog = activitylog
        self.db_id = activitylog.id
        self.orientation = "horizontal"

        time_label = Label(text=self.get_timetext(), size_hint=(0.2, 1))
        self.add_widget(time_label)

        name_label = Label(
            text=f"{self.activitylog.name}",
            size_hint=(0.45, 1)
        )
        self.add_widget(name_label)

        self.add_widget(
            Label(text=f"{self.activitylog.cogload:.1f}", size_hint=(0.1, 1))
        )
        self.add_widget(
            Label(text=f"{self.activitylog.physload:.1f}", size_hint=(0.1, 1))
        )
        spoons = self.activitylog.get_spoons()
        self.add_widget(Label(text=f"{spoons:.1f}", size_hint=(0.1, 1)))

        self.checkbox = CheckBox(
            size_hint=(0.05, 1),
            group="day_logs",
            color=(0, 1, 0, 1),
        )
        self.add_widget(self.checkbox)

    def get_timetext(self) -> str:
        """Generate text for the time label, e.g. 9:00-10:00"""

        start = self.activitylog.start.strftime("%H:%M")
        end = self.activitylog.end.strftime("%H:%M")
        return f'{start}-{end}'
