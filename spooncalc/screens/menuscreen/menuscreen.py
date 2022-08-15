import os
from pathlib import Path
import sqlite3

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy_garden.graph import Graph, LinePlot

from spooncalc import analyser, timeutils

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

    def on_enter(self, *args):
        """
        Methods to execute right before switching to this window

        These methods depend on the existence of the database, however
        the database is only guaranteed to exist after App.build() is
        executed. Therefore the methods arent executed here, but scheduled
        (with a time delay of 0 seconds). Scheduled tasks seem to be run
        only after the app is built.
        """
        # This is ugly, but I don't know how to fix.
        # Database won't be set up yet, so need to wait until
        # App.build() is executed...
        Clock.schedule_once(self.update_spoons_spent_display, 0)
        if not self.plot_initialized:
            Clock.schedule_once(self.init_plot, 0)
            self.plot_initialized = True
        Clock.schedule_once(self.update_plot, 0)
        return super().on_enter(*args)

    def update_spoons_spent_display(self, dt=None):
        """
        Update display of spoons spent today over daily spoons spent
        averaged over past fortnight

        Parameters
        ----------
        dt : float, unused
            only included to satisfy schedulable methods signature requirement
        """
        spoons_today = analyser.calculate_daily_total(0)
        spoons_average = analyser.average_spoons_per_day(-14, 0)
        self.spoons_spent_display =\
            f"{spoons_today:.0f} / {spoons_average:.0f}"

    def export_database(self):
        """
        Export the entire activities database as a csv file.
        """
        # Request entire contents of database
        filename = os.path.join(app.EXTERNALSTORAGE, 'spoon-output.csv')
        conn = sqlite3.connect(app.DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM activities")
        contents = c.fetchall()

        # Construct the csv file header from the request's description
        SEP = ','
        formatted_header = SEP.join([str(col[0])
                                    for col in c.description])
        formatted_contents = '\n'.join([SEP.join([
            str(val) for val in entry
        ]) for entry in contents])
        conn.close()

        # Avoid exporting empty database (and risking an overwrite)
        if len(contents) == 0:
            return
        text = '\n'.join((formatted_header, formatted_contents))

        with open(filename, 'w') as fp:
            fp.write(text)

    def init_plot(self, dt=None):
        """
        Initialize the home screen plot.

        This plot shows the cumulative spoon expenditure for the current day,
        and the mean (+/- 1 standard deviation) of the last 14 days.

        Note that in this method the only ploints plotted is that for the mean
        and standard deviation offsets (mean, below, above). The points for
        today are plotted in .update_plot(). Done this way, the mean (+/- std)
        must only be calculated once per day.

        Parameters
        ----------
        dt : float, unused
            only included to satisfy signature requirement of schedulable
            methods
        """
        self.graph = Graph(
            xmin=timeutils.DAY_BOUNDARY,
            xmax=timeutils.DAY_BOUNDARY + 24,
            ymin=0, ymax=35,
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
        xs, mean, below, above = analyser.get_mean_and_spread()
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above)

        self.graph.add_plot(self.mean)
        self.graph.add_plot(self.below)
        self.graph.add_plot(self.above)
        self.graph.add_plot(self.today)

    def update_plot(self, dt=None):
        """
        Update the plot by plotting the day's cumulative spoons.

        Note that the mean, below and above plots remain unchanged.
        """
        print("Plotting daily!")
        today = 0
        xs, ys = analyser.cumulative_time_spoons(day_offset=today)

        self.today.points = list(zip(xs, ys))

    def update_mean_and_spread(self):
        """
        Update the mean and standard deviation plots

        This mthod is only ever activated when the database is updated
        via an "import". Note that this method could be getting called from
        kivy lang.
        """
        xs, mean, below, above = analyser.get_mean_and_spread()
        self.mean.points = zip(xs, mean)
        self.below.points = zip(xs, below)
        self.above.points = zip(xs, above)
