from spooncalc.dbtools import Database
from spooncalc import timeutils, analyser

from kivy_garden.graph import Graph, LinePlot


class HourlyCumulative:

    def __init__(self, db: Database) -> None:
        self.db = db
        self.xmin = timeutils.DAY_BOUNDARY
        self.xmax = timeutils.DAY_BOUNDARY + 24
        self.ymax_persistent = 30
        self.day_offset = 0

        self.graph = Graph(
            xmin=timeutils.DAY_BOUNDARY,
            xmax=timeutils.DAY_BOUNDARY + 24,
            ymin=0,
            ymax=self.ymax_persistent,
            border_color=[0, 1, 1, 1],
            tick_color=[0, 1, 1, 0.7],
            x_grid=True,
            y_grid=True,
            draw_border=True,
            x_grid_label=True,
            y_grid_label=True,
            x_ticks_major=3,
            y_ticks_major=5,
        )

        self.plot = LinePlot(color=[1, 1, 0, 1], line_width=1.5)
        self.graph.add_plot(self.plot)

    def update_data(self):
        xs, ys = analyser.fetch_cumulative_time_spoons(
            self.db, self.day_offset,
        )
        # If plotting for a past day, extend line plot to end of x range
        if self.day_offset < 0 and max(xs) < self.graph.xmax:
            xs.append(self.graph.xmax)
            ys.append(ys[-1])

        self.plot.points = list(zip(xs, ys))
        # self.update_daily_title()

    def update_plot(self):
        self.update_data()

    def shift_left(self):
        self.day_offset -= 1
        self.update_plot()

    def shift_right(self):
        self.day_offset += 1
        self.update_plot()
