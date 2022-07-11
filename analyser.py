"""
Analyse data stored in database and generate
informative plots
"""
import dbtools

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


def calculate_spoons(duration, cogload, physload):
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
