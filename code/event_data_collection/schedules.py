"""Programme grids for the networks that air on a fixed daily schedule.

Slots are US Eastern local time, half-open [start, end).
"""


def _m(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


BLOOMBERG = [
    ("01:00", "02:30", "Bloomberg_Daybreak_Europe"),
    ("02:30", "04:00", "Bloomberg_Markets_European_Open"),
    ("04:00", "07:00", "Bloomberg_Surveillance"),
    ("07:00", "09:00", "Bloomberg_Daybreak_Americas"),
    ("10:00", "11:00", "Bloomberg_Markets_Americas"),
    ("11:00", "12:00", "Bloomberg_Markets_European_Close"),
    ("12:00", "13:00", "Bloomberg_Markets_Balance_of_Power"),
    ("13:00", "15:30", "Bloomberg_Markets_Americas"),
    ("15:30", "17:00", "Whatd_You_Miss"),
    ("17:00", "18:00", "Bloomberg_Technology"),
    ("18:00", "19:00", "Bloomberg_Daybreak_Australia"),
    ("21:00", "23:00", "Bloomberg_Markets_Asia"),
]

CNBC = [
    ("04:00", "05:00", "Street_Signs"),
    ("05:00", "06:00", "Worldwide_Exchange"),
    ("06:00", "09:00", "Squawk_Box"),
    ("09:00", "11:00", "Squawk_on_the_Street"),
    ("11:00", "12:01", "Squawk_Alley"),
    ("12:00", "13:01", "Fast_Money_Halftime_Report"),
    ("13:00", "14:01", "The_Exchange"),
    ("14:00", "15:00", "Power_Lunch"),
    ("15:00", "17:00", "Closing_Bell"),
    ("17:00", "18:00", "Fast_Money"),
    ("18:00", "19:00", "Mad_Money"),
]

FBC = [
    ("06:00", "09:00", "Mornings_With_Maria_Bartiromo"),
    ("09:00", "12:00", "Varney__Company"),
    ("13:00", "14:00", "The_Big_Money_Show"),
    ("14:00", "15:00", "Making_Money_With_Charles_Payne"),
    ("15:00", "16:00", "The_Claman_Countdown"),
    ("16:00", "17:00", "Kudlow"),
    ("17:00", "19:00", "The_Evening_Edit"),
]

# CNN and Yahoo appearances are not tied to a recurring slot, so they get no grid.
GRIDS = {"BLOOMBERG": BLOOMBERG, "CNBC": CNBC, "FBC": FBC}


def programme(media, eastern):
    """Return the programme airing on `media` at Eastern-time `eastern`, else None."""
    grid = GRIDS.get(media)
    if grid is None:
        return None
    t = eastern.hour * 60 + eastern.minute
    return next((name for s, e, name in grid if _m(s) <= t < _m(e)), None)
