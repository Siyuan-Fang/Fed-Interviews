"""Fed officials appearing in the sample.

Keys are the surname as spelt in headlines, including one misspelling carried by the
calendar export; values are the dataset label.
"""

ROSTER = {
    "Barkin": "Barkin", "Bostic": "Bostic", "Bowman": "Bowman", "Bullard": "Bullard",
    "Clarida": "Clarida", "Collins": "Collins", "Daly": "Daly", "Dudley": "Dudley",
    "Evans": "Charles Evans", "Goolsbee": "Goolsbee", "Gooolsbee": "Goolsbee",
    "Hammack": "Hammack", "Harker": "Harker", "Kaplan": "Kaplan", "Kashkari": "Kashkari",
    "Kugler": "Kugler", "Mester": "Mester", "Miran": "Miran", "Musalem": "Musalem",
    "Waller": "Waller", "Williams": "Williams",
}


def speaker_of(text):
    """The official named in `text`, or None if no roster surname appears."""
    return next((label for name, label in ROSTER.items() if name in str(text)), None)
