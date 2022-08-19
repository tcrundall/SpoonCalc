from kivy.uix.stacklayout import StackLayout

# from spooncalc.models.activitylog import ActivityLog
from spooncalc.dbtools import Database
from .titlebox import TitleBox
from .entrybox import EntryBox


class LogsLayout(StackLayout):
    """
    A container for displaying all activity logs from a given day.

    The first 'initialisation' is handled by
    LogsWindow's on_pre_enter call.

    Attributes
    ----------
    current_day : int
        the day in question, encoded as an offset from today
    boxes : list[EntryBox]
        a list of all entryBoxes, where each entryBox is a widget
        displaying partial information of a logged activity.
    """

    current_day = 0
    boxes = []

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Set the stacking order: left-to-right, then top-to-bottom
        self.orientation = 'lr-tb'

    def pass_db_reference(self, db: Database) -> None:
        """Provide this class with reference to object wrapping database"""
        self.db = db

    def update(self) -> None:
        """
        Update the list of all children (EntryBox) Widgets.

        Convert each of the `current_day`s database logs into an
        EntryBox, and add them (in time order) to this StackedLayout
        """

        self.clear_widgets()
        self.boxes: list[EntryBox] = []

        # Grab all logs from today
        logs = self.db.get_logs_from_day(self.current_day)

        # Sort logs by start time
        logs = sorted(logs, key=lambda l: l.start)

        self.add_widget(TitleBox())             # Add a header
        for activitylog in logs:
            entry_box = EntryBox(activitylog)
            self.boxes.append(entry_box)
            self.add_widget(entry_box)

    def delete_entry(self) -> None:
        """
        Find the checked EntryBox, and delete corresponding entry
        from database.
        """

        for entrybox in self.boxes:
            if entrybox.checkbox._get_active():
                self.db.delete_entry(entrybox.db_id)
                self.update()
                return

    def decrement_day(self) -> None:
        """ Display logs for previous day """

        self.current_day -= 1
        self.update()

    def increment_day(self) -> None:
        """ Display logs for following day """

        self.current_day += 1
        self.update()
