
import math
from kivy_garden.graph import Graph, LinePlot
from enum import Enum, auto
from spooncalc.dbtools import Database
from spooncalc import analyser


class PlotMode(Enum):
    WEEK = auto()
    MONTH = auto()


class DailyTotalsPlot:
    """
    Encapsulates data gathering and plot generation displayed
    by PlotScreen
    """
    def __init__(self, db: Database):
        self.db = db
        self.mode = PlotMode.WEEK
        self.week_xmax = 0
        self.xmin = -7
        self.xmax = self.week_xmax
        self.ymax_persistent = 30
        self.graph = Graph(
            xmin=self.xmin,
            xmax=self.xmax,
            ymin=0,
            ymax=self.ymax_persistent,
            border_color=[0, 1, 1, 1],
            tick_color=[0, 1, 1, 0.7],
            x_grid=True,
            y_grid=True,
            draw_border=True,
            x_grid_label=True,
            y_grid_label=True,
            x_ticks_major=1,
            y_ticks_major=5,
        )

        # # Nested data dicts with structure [day_offset, qualifier, value]
        # self.daily_hour_totals = {}
        self.plot = LinePlot(color=[1, 1, 0, 1], line_width=1)
        self.graph.add_plot(self.plot)
        self.average_plot = LinePlot(color=[1, 1, 1, 1], line_width=1.5)
        self.graph.add_plot(self.average_plot)

        # Nested data dicts with structure [day_offset, value]
        self.daily_spoon_totals = {}

        self.update_plot()

    def update_data(self) -> None:
        for day_offset in range(self.xmin, self.xmax + 1):
            if day_offset not in self.daily_spoon_totals:
                self.daily_spoon_totals[day_offset] =\
                    analyser.fetch_daily_total(self.db, day_offset)
        self.ymax_persistent = max(
            self.ymax_persistent,
            1.1 * max(self.daily_spoon_totals.values())
        )

    def update_plot(self) -> None:

        # Update daily totals line plot
        self.update_data()
        points = [(x, self.daily_spoon_totals[x])
                  for x in range(self.xmin, self.xmax + 1)]
        self.graph.xmin = self.xmin
        self.graph.xmax = self.xmax
        self.graph.ymax = self.ymax_persistent
        self.plot.points = points

        # Update averaging line plot
        average_span = 3
        xs = [x for x, _ in self.plot.points]
        ys = [y for _, y in self.plot.points]

        av_ys = []
        for i in range(len(ys) + 1 - average_span):
            av_ys.append(sum(ys[i:i + average_span]) / average_span)
        av_xs = xs[1:-1]
        self.average_plot.points = zip(av_xs, av_ys)

    def shift_left(self) -> None:
        if self.mode == PlotMode.WEEK:
            self.shift_x_range(-1)
        if self.mode == PlotMode.MONTH:
            self.shift_x_range(-7)

    def shift_right(self) -> None:
        if self.mode == PlotMode.WEEK:
            self.shift_x_range(1)
        if self.mode == PlotMode.MONTH:
            self.shift_x_range(7)

    def shift_x_range(self, shift_size):
        self.xmin += shift_size
        self.xmax += shift_size
        self.update_plot()

    def set_mode(self, mode: PlotMode):
        if mode == self.mode:
            return

        self.mode = mode
        if mode == PlotMode.WEEK:
            self.xmax = self.xmax - 7   # focus window on second last week
            self.xmin = self.xmax - 7
            self.graph.x_ticks_major = 1
        elif mode == PlotMode.MONTH:
            # Shift xmax to nearest, more positive, multiple of 7,
            # aaaand then add one week
            self.xmax = (math.ceil(self.xmax / 7) + 1) * 7
            self.xmin = self.xmax - 28
            self.graph.x_ticks_major = 7

        self.update_plot()
