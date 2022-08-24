from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timedelta
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty

from spooncalc.dbtools import Database
from .dailytotalsplot import DailyTotalsPlot, PlotMode
from .hourlycumulative import HourlyCumulative

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
        self.daily_totals_plot = DailyTotalsPlot(self.db)
        self.hourly_cumulative = HourlyCumulative(self.db)

        self.current_plot = self.daily_totals_plot
        self.set_weekly()

    def on_pre_enter(self) -> None:
        """
        Method(s) to be executed before switching to this window.
        """
        self.current_plot.update_plot()

    def shift_window_left(self) -> None:
        """
        Shift the plot to show earlier data.

        The amount to shift is determined by the current mode
        """
        self.current_plot.shift_left()

    def shift_window_right(self) -> None:
        """
        Shift the plot to show later data.

        The amount to shift is determined by the current mode
        """
        self.current_plot.shift_right()

    def set_weekly(self) -> None:
        """
        Set the current mode to weekly, updating key attributes as required
        """
        self.ids.graph.remove_widget(self.current_plot.graph)
        self.daily_totals_plot.set_mode(PlotMode.WEEK)
        self.current_plot = self.daily_totals_plot
        self.plot_title = "Weekly"
        self.ids.graph.add_widget(self.current_plot.graph)

    def set_monthly(self) -> None:
        """
        Set the current mode to monthly, updating key attributes as required
        """
        self.daily_totals_plot.set_mode(PlotMode.MONTH)
        self.ids.graph.remove_widget(self.current_plot.graph)

        self.current_plot = self.daily_totals_plot
        self.plot_title = "Monthly"
        self.ids.graph.add_widget(self.current_plot.graph)

    def set_daily(self) -> None:
        """
        Set the current mode to daily, updating key attributes as required
        """
        self.ids.graph.remove_widget(self.current_plot.graph)

        self.current_plot = self.hourly_cumulative
        assert isinstance(self.current_plot, HourlyCumulative)
        date = datetime.now().date() \
            + timedelta(days=self.current_plot.day_offset)
        self.plot_title = date.strftime("%A %d.%m")
        self.ids.graph.add_widget(self.current_plot.graph)
