from kivy.uix.stacklayout import StackLayout

from spooncalc import dbtools
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

