"""
Analyse data stored in database and generate
informative plots
"""
from spooncalc import dbtools
from spooncalc import timeutils

DATABASE = "spooncalc.db"


def calculate_daily_totals(start_day_offset, span):
    """
    Calculate total spoon expenditure per day for the `span`
    days beginning at `start_day_offset`

    Parameters
    ----------
    start_day_offset : int
        day (offset from today) that starts the span of days
    span : int
        the number of days to calculate

    Examples
    --------
    >>> calculate_daily_totals(-2, 3)
    {-2: 20.5, -1: 22.5, 0: 4.25}
    """

    spoons_each_day = {
        i: calculate_daily_total(i) for i in range(start_day_offset,
                                                   start_day_offset + span)
    }
    return spoons_each_day


def calculate_daily_total(day_offset):
    """
    Calculate total spoons spent `day_offset` days from now.

    Parameters
    ----------
    day_offset : int
        The number of days between today and day in question.
        `day_offset`=0 is today, `day_offset`=-1 is yesterday

    Returns
    -------
    float
        The total number of spoons spent on this day
    """

    entries = dbtools.get_logs_from_day(
        day_offset=day_offset,
        colnames=['duration', 'cogload', 'physload']
    )

    spoons = 0
    for entry in entries:
        spoons += calculate_spoons(**entry)

    return spoons


def calculate_spoons(duration, cogload, physload, **kwargs):
    """
    Convert load levels and duration into energy spent with units
    "spoons".

    The formula used is:
        duration [in hours] * (cogload + physload)

    Current implementation of data storage stores cog- and physload
    as floats, however for backwards compatibility this method
    can also handle the old style of strings.
    where cogload and physload are mapped:
        "v. low"  --> 0
        "low"     --> 0.5
        "mid"     --> 1
        "high"    --> 1.5
        "v. high" --> 2

    Parameters
    ----------
    duration: str
        string representaiton HH:MM:SS e.g. '2:00:00'
    cogload: str
        spoons per hour cost of cognitive load
            [0 | 0.5 | 1 | 1.5 | 2] or ['low' | 'mid' | 'high']
    physload: str
        spoons per hour cost of physical load
            [0 | 0.5 | 1 | 1.5 | 2] or ['low' | 'mid' | 'high']
    **kwargs:
        ignore any superfluous keys. This makes expanding entries
        more convenient, as entries are permitted to have extra columns

    Example
    -------
    >>> calculate_spoons("2:00:00", "1.5", "mid")
    5
    """
    res = parse_duration_string(duration) \
        * (parse_load_string(cogload)
           + parse_load_string(physload))
    return res


def parse_duration_string(dur_str):
    """Convert duration string into hours

    Parameters
    ----------
    dur_str : str
        Duration with the format [H]H:MM:SS]
    """
    hours, mins, secs = [int(el) for el in dur_str.split(':')]
    return hours + mins / 60. + secs / 3600.


def parse_load_string(load_str):
    """Convert load string to a float

    Loads are stored as (strings of) floats, but for backwards
    compatibility, this method can also handle conversions from
    the stored words.
    """
    try:
        return float(load_str)
    except ValueError:
        load_dict = {
            "low": 0.,
            "mid": 1.,
            "high": 2.,
        }
        return load_dict[load_str]


def average_spoons_per_day(day_offset_start=-14, day_offset_end=0):
    """
    Calculate the average spoons per day, averaged between
    `day_offset_start` and `day_offset_end`.

    Defaults are past two weeks

    Parameters
    ----------
    day_offset_start : int
        number of days between now and starting day
    day_offset_end : int
        number of days between now and (exclusive) ending day

    Example
    -------
    start=-14, end=0: spoons per day, averaged over past 14 days
                      (i.e.not including today)
    """
    entries = dbtools.get_entries_between_offsets(
        day_offset_start,
        day_offset_end,
        colnames=['duration', 'cogload', 'physload'],
    )
    total_spoons = 0
    for entry in entries:
        total_spoons += calculate_spoons(**entry)

    return total_spoons / (day_offset_end - day_offset_start)


def cumulative_time_spoons(day_offset=0):
    """
    Generate data points for a cumulative spoon expenditure
    for a given day.

    x points are end times of entries, in units of hours.

    Parameters
    ----------
    day_offset : int
        number of days between today and target day

    Returns
    -------
    xs
        the times (in hours) of each data point
    ys
        the cumulative spent spoons of each data point

    TODO:   Set points to be at both start and end of each activity,
            thereby resulting in a flat line for periods with no
            logged activities.
    """
    colnames = [
        'start',
        'end',
        'duration',
        'cogload',
        'physload',
    ]

    entries = dbtools.get_entries_between_offsets(
        day_offset,
        day_offset + 1,
        colnames=colnames,
    )

    entries = sorted(entries, key=lambda e: e['end'])

    earliest_starttime = timeutils.time2decimal(
        dbtools.get_earliest_starttime(day_offset)
    )

    # Initialise points s.t. flat line between start and first entry
    xs = [0., earliest_starttime]
    ys = [0., 0.]
    total_spoons = 0.
    for entry in entries:
        hours_since_midnight = timeutils.hours_between(
            timeutils.date_midnight_from_offset(day_offset),
            entry['end'],
        )
        total_spoons += calculate_spoons(**entry)
        xs.append(hours_since_midnight)
        ys.append(total_spoons)
    return xs, ys


def linearly_interpolate(x, xs, ys):
    """
    Get the y value corresponding to x, linearly
    interpolating between xs and ys as needed.

    x is assumed to be between the bounds of xs.
    xs and ys assumed to be sorted

    Parameters
    ----------
    x : float
        target x, for which we want an interpolated y
    xs : list(float)
        a sorted list of x values which contains x
    ys : list(float)
        a sorted list of y values
    """
    # Handle case where x is beyond bounds of xs
    if x >= xs[-1]:
        return ys[-1]

    # Find first element in xs that is larger than desired x
    x_right_ix = 0
    while x_right_ix < len(xs):
        if xs[x_right_ix] > x:
            break
        x_right_ix += 1

    # Get the two neighbouring points of x
    x_left = xs[x_right_ix - 1]
    x_right = xs[x_right_ix]
    y_left = ys[x_right_ix - 1]
    y_right = ys[x_right_ix]

    # Calculate the gradient (rise over run)
    grad = (y_right - y_left) / (x_right - x_left)

    # Follow segment between neighbouring points until we reach x
    dx = x - x_left
    return y_left + dx * grad


def calc_mean(values):
    """Calculate the mean of a set of values"""
    n = len(values)
    return sum(values) / n


def calc_stdev(values, mean=None):
    """Calculate the standard deviation of a set of values"""
    if mean is None:
        mean = calc_mean(values)
    n = len(values)
    total = 0
    for val in values:
        total += (val - mean)**2
    return (total / n)**(0.5)


def get_mean_and_spread(day_offset_start=-14, day_offset_end=0):
    """
    Get mean and spread of cumulative daily spoon plots.

    Parameters
    ----------
    day_offset_start : int
        number of days between today and start day
    day_offset_end : int
        number of days between today and end day

    Returns
    -------
    times : list(float)
        the x value of each data point, with units "hours"
    mean : list(float)
        the mean at each time
    below : list(float)
        one standard deviation below the mean at each time
    above: list(float)
        one standard deviation above the mean at each time

    TODO:   Don't use std, because this can lead to decreasing
            curves for `below`, but rather calculate the 67.5%
            and 32.5%.
    """
    cumulative_plots = [
        cumulative_time_spoons(day_offset)
        for day_offset in range(day_offset_start, day_offset_end)
    ]

    """
    the following pure python is equivalent to:
    times = numpy.linspace(
        timeutils.day_start_hour(),
        timeutils.day_end_hour(),
        0.25
    )
    """
    dt = 0.25       # 15 min resolution
    times = []
    t = timeutils.day_start_hour()
    while t < timeutils.day_end_hour():
        times.append(t)
        t += dt

    means = []
    above = []
    below = []
    for time in times:
        cumulative_spoons = [
            linearly_interpolate(time, xs, ys) for xs, ys in cumulative_plots
        ]
        mean = calc_mean(cumulative_spoons)
        stdev = calc_stdev(cumulative_spoons, mean)
        means.append(mean)
        above.append(mean + stdev)
        below.append(mean - stdev)

    return times, means, below, above
