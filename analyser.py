"""
Analyse data stored in database and generate
informative plots
"""
import dbtools
import timeutils

DATABASE = "spooncalc.db"


def calculate_daily_totals(start_day, span):
    """
    Calculate total spoon expenditure per day for
    previous `n_days_back`
    """
    spoons_each_day = {
        i: calculate_daily_total(i) for i in range(start_day,
                                                   start_day + span)
    }
    return spoons_each_day


def calculate_daily_total(day_offset):
    """
    Calculate total spoons spent on the day
    `day_offset` days from now,
    negative values indicate past days

    If `day_offset` is 0, then we're calculating today,
    `day_offset` = -1 is yesterday, etc...
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
    Current formula spoons is:
        duration [hours] * (cogload + physload)
    where cogload and physload are mapped:
        "low" --> 0
        "mid" --> 1
        "high" -> 2
    Such that, an hour doing something low phys load and low cog load
    costs 0 spoons.

    30 mins of mid cogload and high physload costs 1.5 spoons

    Parameters
    ----------
    duration: str
        string representaiton HH:MM:SS e.g. '2:00:00'
    cogload: str
        'low' | 'mid' | 'high'
    physload: str
        'low' | 'mid' | 'high'
    **kwargs:
        ignore any superfluous keys. This makes expanding entries
        more convenient.
    """
    res = parse_duration_string(duration) \
        * (parse_load_string(cogload)
           + parse_load_string(physload))
    return res


def parse_duration_string(dur_str):
    hours, mins, secs = [int(el) for el in dur_str.split(':')]
    return hours + mins / 60. + secs / 3600.


def parse_load_string(load_str):
    try:
        return float(load_str)
    except ValueError:
        load_dict = {
            "low": 0,
            "mid": 1,
            "high": 2,
        }
        return load_dict[load_str]


def average_spoons_per_day(day_offset_start=-14, day_offset_end=0):
    """
    Calculate the average spoons per day, averaged between
    `day_offset_start` and `day_offset_end`.

    Defaults are past two weeks

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

    x_left = xs[x_right_ix - 1]
    x_right = xs[x_right_ix]
    y_left = ys[x_right_ix - 1]
    y_right = ys[x_right_ix]

    dx = x - x_left
    grad = (y_right - y_left) / (x_right - x_left)

    return y_left + dx * grad


def calc_mean(values):
    n = len(values)
    return sum(values) / n


def calc_stdev(values, mean):
    n = len(values)
    total = 0
    for val in values:
        total += (val - mean)**2
    return (total / n)**(0.5)


def get_mean_and_spread(day_offset_start=-14, day_offset_end=0):
    """
    Get mean and spread of cumulative daily spoon plots.
    """
    cumulative_plots = [
        cumulative_time_spoons(day_offset)
        for day_offset in range(day_offset_start, day_offset_end)
    ]
    """
    equivalent to:
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
