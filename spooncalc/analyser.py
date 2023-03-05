"""
Analyse data stored in database and generate
informative plots
"""
from __future__ import annotations

from typing import List, Tuple

from spooncalc import timeutils
from spooncalc.dbtools import Database


def fetch_daily_totals(
    db: Database,
    start_day_offset: int,
    span: int
) -> dict:
    """
    Calculate total spoon expenditure per day for the `span`
    days beginning at `start_day_offset`

    Parameters
    ----------
    db : Database
        a reference to a database wrapper
    start_day_offset : int
        day (offset from today) that starts the span of days
    span : int
        the number of days to calculate

    Examples
    --------
    >>> calculate_daily_totals(db, -2, 3)
    {-2: 20.5, -1: 22.5, 0: 4.25}
    """

    spoons_each_day = {
        i: fetch_daily_total(db, i) for i in range(start_day_offset,
                                                   start_day_offset + span)
    }
    return spoons_each_day


def fetch_daily_total(db: Database, day_offset: int) -> float:
    """
    Calculate total spoons spent `day_offset` days from now.

    Parameters
    ----------
    db : Database
        a reference to a database wrapper
    day_offset : int
        The number of days between today and day in question.
        `day_offset`=0 is today, `day_offset`=-1 is yesterday

    Returns
    -------
    float
        The total number of spoons spent on this day
    """

    return sum(log.spoons for log in db.get_logs_from_day(day_offset))


def fetch_average_spoons_per_day(
    db: Database,
    day_offset_start: int = -14,
    day_offset_end: int = 0,
) -> float:
    """
    Calculate the average spoons per day, averaged between
    `day_offset_start` and `day_offset_end`.

    Defaults are past two weeks

    Parameters
    ----------
    db : Database
        a reference to a database wrapper
    day_offset_start : int
        number of days between now and starting day
    day_offset_end : int
        number of days between now and (exclusive) ending day

    Example
    -------
    start=-14, end=0: spoons per day, averaged over past 14 days
                      (i.e.not including today)
    """
    logs = db.get_logs_between_offsets(day_offset_start, day_offset_end)
    total_spoons = 0
    for log in logs:
        total_spoons += log.spoons

    return total_spoons / (day_offset_end - day_offset_start)


def fetch_cumulative_time_spoons(
    db: Database,
    day_offset: int = 0,
) -> Tuple[List[float], List[float]]:
    """
    Generate data points for a cumulative spoon expenditure
    for a given day.

    x points are end times of logs, in units of hours.

    Parameters
    ----------
    db : Database
        a reference to a database wrapper
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

    logs = db.get_logs_between_offsets(day_offset, day_offset + 1)
    logs = sorted(logs, key=lambda e: e.end)

    # if no logs, return a single point at (0,0)
    if not logs:
        return [0.], [0.]

    earliest_starttime = timeutils.time2decimal(
        min([e.start for e in logs]).time()
    )

    # Initialise points s.t. flat line between start and first log
    xs = [0., earliest_starttime]
    ys = [0., 0.]
    total_spoons = 0.
    for log in logs:
        hours_since_midnight = timeutils.hours_between(
            timeutils.date_midnight_from_offset(day_offset),
            str(log.end),      # (re)casting to str to satisfy typehints
        )
        total_spoons += log.spoons
        xs.append(hours_since_midnight)
        ys.append(total_spoons)

    return xs, ys


def linearly_interpolate(x: float, xs: List[float], ys: List[float]) -> float:
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


def calc_mean(values: List[float]) -> float:
    """Calculate the mean of a set of values"""
    n = len(values)
    return sum(values) / n


def calc_percentile(values: List[float], percentile: float) -> float:
    if len(values) == 0:
        return 0.
    if len(values) == 1:
        return values[0]
    if percentile >= 100.:
        return sorted(values)[-1]
    if percentile <= 0.:
        return sorted(values)[0]

    n = len(values)
    sorted_values = sorted(values)
    closest_lower_ix = int((n * percentile / 100.) // 1) - 1
    fraction_towards_upper = (n * percentile / 100.) % 1

    print(f"{values=}")
    print(f"{closest_lower_ix=}")
    print(f"{closest_lower_ix + 1=}")
    lower_value = sorted_values[closest_lower_ix]
    upper_value = sorted_values[closest_lower_ix + 1]

    return lower_value + fraction_towards_upper * (upper_value - lower_value)


def get_mean_and_spread(
    db: Database,
    day_offset_start: int = -14,
    day_offset_end: int = 0
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    Get mean and spread of cumulative daily spoon plots.

    Parameters
    ----------
    db : Database
        a reference to a database wrapper
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
    """
    cumulative_plots = [
        fetch_cumulative_time_spoons(db, day_offset)
        for day_offset in range(day_offset_start, day_offset_end)
    ]

    """
    the following pure python is equivalent to:
    times = numpy.linspace(
        timeutils.day_start_hour(),
        timeutils.day_end_hour(),
        24,
    )
    """
    dt = 1.0          # 60 min resolution
    times: List[float] = []
    t = timeutils.day_start_hour()
    while t <= timeutils.day_end_hour():
        times.append(t)
        t += dt

    means: List[float] = []
    above: List[float] = []
    below: List[float] = []
    for time in times:
        cumulative_spoons = [
            linearly_interpolate(time, xs, ys) for xs, ys in cumulative_plots
        ]
        means.append(calc_percentile(cumulative_spoons, 50))
        above.append(calc_percentile(cumulative_spoons, 84))
        below.append(calc_percentile(cumulative_spoons, 16))

    return times, means, below, above
