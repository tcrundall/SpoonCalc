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

    def __init__(self, activitylog: ActivityLog, **kwargs):
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

    def get_timetext(self):
        start = self.activitylog.start.strftime("%H:%M")
        end = self.activitylog.end.strftime("%H:%M")
        return f'{start}-{end}'
