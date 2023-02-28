import os
from pathlib import Path
from typing import Callable

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy_garden.graph import Graph, LinePlot

from spooncalc import analyser, timeutils
from spooncalc.dbtools import Database

Builder.load_file(os.path.join(
    Path(__file__).parent.absolute(),
    "menuscreen.kv"
))


class MenuScreen(Screen):
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

    def __init__(
        self,
        export_callback: Callable,
        db: Database,
        **kwargs
    ) -> None:

        super().__init__(**kwargs)
        self.export_callback = export_callback
        self.db = db
        # TODO: find out why this must be executed after super().__init__
        self.init_plot()

    def on_pre_enter(self) -> None:
        """
        Methods to execute right before switching to this window
        """

        self.update_spoons_spent_display()
        self.update_plot()

    def update_spoons_spent_display(self) -> None:
        """
        Update display of spoons spent today over daily spoons spent
        averaged over past fortnight
        """

        spoons_today = analyser.fetch_daily_total(self.db, 0)
        spoons_average = analyser.fetch_average_spoons_per_day(self.db, -14, 0)
        self.spoons_spent_display =\
            f"{spoons_today:.0f} / {spoons_average:.0f}"

    def export_database(self) -> None:
        """ Export the entire activities database as a csv file.  """

        self.export_callback()

    def init_plot(self) -> None:
        """
        Initialize the home screen plot.

        This plot shows the cumulative spoon expenditure for the current day,
        and the mean (+/- 1 standard deviation) of the last 14 days.

        Note that in this method the only ploints plotted is that for the mean
        and standard deviation offsets (mean, below, above). The points for
        today are plotted in .update_plot(). Done this way, the mean (+/- std)
        must only be calculated once per day.
        """

        self.graph = Graph(
            xmin=timeutils.DAY_BOUNDARY,
            xmax=timeutils.DAY_BOUNDARY + 24,
            ymin=0, ymax=50,
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
        xs, mean, below, above = analyser.get_mean_and_spread(self.db, -28, 0)
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above)

        self.graph.add_plot(self.mean)
        self.graph.add_plot(self.below)
        self.graph.add_plot(self.above)
        self.graph.add_plot(self.today)

    def update_plot(self) -> None:
        """
        Update the plot by plotting the day's cumulative spoons.

        Note that the mean, below and above plots remain unchanged.
        """

        today = 0
        xs, ys = analyser.fetch_cumulative_time_spoons(
            db=self.db,
            day_offset=today
        )

        self.today.points = list(zip(xs, ys))

    def update_mean_and_spread(self) -> None:
        """
        Update the mean and standard deviation plots

        This method is only ever activated when the database is updated
        via an "import". Note that this method could be getting called from
        kivy lang.
        """

        xs, mean, below, above = analyser.get_mean_and_spread(db=self.db)
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above)
