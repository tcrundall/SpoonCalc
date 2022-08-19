from datetime import datetime, timedelta
import os
from pathlib import Path
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy_garden.graph import Graph, LinePlot

from spooncalc import analyser, timeutils
from spooncalc.dbtools import Database

Builder.load_file(os.path.join(
    Path(__file__).parent.absolute(),
    "plotscreen.kv"
))


class PlotScreen(Screen):
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

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.ymax_persistent = 27
        self.start = -7
        self.span = 8
        self.end = 0
        self.mode = "weekly"
        self.day_offset = 0
        self.plot_initialized = False

    def on_pre_enter(self) -> None:
        """
        Method(s) to be executed before switching to this window.
        """

        if not self.plot_initialized:
            self.init_plot()
        self.plot_initialized = True
        self.update_plot()

    def init_plot(self) -> None:
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
        self.spoons_per_day = analyser.fetch_daily_totals(
            self.db, self.start, self.span
        )
        self.plot = LinePlot(color=[1, 1, 0, 1], line_width=1.5)
        self.plot.points = [(-d, spoons)
                            for d, spoons in self.spoons_per_day.items()]
        self.graph.add_plot(self.plot)

        self.plot_average = LinePlot(color=[1, 1, 1, 1], line_width=2.)
        self.graph.add_plot(self.plot_average)
        self.average_current_plot()

    def update_plot(self) -> None:
        """
        Update plot, reflecting changes in mode and/or x-range
        """

        if self.mode == "daily":
            self.plot_daily()
            return
        # mode: weekly or monthly
        self.spoons_per_day = analyser.fetch_daily_totals(
            self.db, self.start, self.span
        )
        self.graph.xmin = self.start
        self.graph.xmax = self.start + self.span - 1
        self.plot.points = [(d, spoons)
                            for d, spoons in self.spoons_per_day.items()]
        ymax_current = max(self.spoons_per_day.values())
        self.ymax_persistent = max(ymax_current * 1.1, self.ymax_persistent)
        self.graph.ymax = self.ymax_persistent
        self.average_current_plot()

    def average_current_plot(self) -> None:
        """
        Take the current monthly or weekly plot and over plot
        an average
        """
        average_span = 3
        xs = [x for x, _ in self.plot.points]
        ys = [y for _, y in self.plot.points]

        av_ys = []
        for i in range(len(ys) + 1 - average_span):
            av_ys.append(sum(ys[i:i + average_span]) / average_span)
        av_xs = xs[1:-1]
        self.plot_average.points = zip(av_xs, av_ys)

    def shift_window_left(self) -> None:
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

    def shift_window_right(self) -> None:
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

    def set_weekly(self) -> None:
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

    def set_monthly(self) -> None:
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

    def set_daily(self) -> None:
        """
        Set the current mode to daily, updating key attributes as required
        """

        if self.mode == "daily":
            return
        self.mode = "daily"
        self.update_plot()

    def plot_daily(self) -> None:
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

        xs, ys = analyser.fetch_cumulative_time_spoons(
            self.db, self.day_offset
        )

        # If plotting for a past day, extend line plot to end of x range
        if self.day_offset < 0 and max(xs) < self.graph.xmax:
            xs.append(self.graph.xmax)
            ys.append(ys[-1])

        self.plot.points = list(zip(xs, ys))
        self.update_daily_title()

    def update_daily_title(self) -> None:
        """Update the title of the daily plot"""

        date = datetime.now().date() + timedelta(days=self.day_offset)
        self.plot_title = date.strftime("%A %d.%m")
