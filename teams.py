"""
St. Helena Premier League — clubs.

The SHPL is its own competition. Nothing here mirrors another league: the
twelve clubs below, their divisions and their colours are the whole roster,
and every result comes from season.json (see league.py).

Two divisions of six:
  St. Helena Division  🇸🇭
  Ascension Division   🇦🇨
"""

# Division constants (also used as the island label in the UI).
ST_HELENA = "St. Helena"
ASCENSION = "Ascension"

DIVISION_NAME = {
    ST_HELENA: "St. Helena Division",
    ASCENSION: "Ascension Division",
}

# One row per club:
#   id, name, division, primary, secondary, aliases
# `aliases` exist so results can be entered with the short name people
# actually say ("Harts", "Rovers") and still land on the right club.
_TEAMS = [
    # ---------------------- St. Helena Division ----------------------
    ("rovers",      "Rovers Saint Helena", ST_HELENA, "#ECE83A", "#1D1D1B",
     ("Rovers", "Rovers St Helena", "Rovers St. Helena", "Saint Helena Rovers")),
    ("bellboys",    "Bellboys FC",         ST_HELENA, "#F7B5CD", "#231F20",
     ("Bellboys", "Bell Boys", "Bellboys FC")),
    ("harts",       "Harts United",        ST_HELENA, "#6CACE4", "#041E42",
     ("Harts", "Hearts United", "Harts Utd")),
    ("fugees",      "Fugees FC",           ST_HELENA, "#B49759", "#0E2B3B",
     ("Fugees",)),
    ("laverde",     "La Verde FC",         ST_HELENA, "#17A66B", "#0A2240",
     ("La Verde", "LaVerde")),
    ("youngboys",   "STH Young Boys",      ST_HELENA, "#E0553B", "#221F1F",
     ("Young Boys", "STH Young Boys FC", "Sth Young Boys")),

    # ---------------------- Ascension Division -----------------------
    ("devils",      "77 Devils FC",        ASCENSION, "#E03131", "#101820",
     ("77 Devils", "Devils")),
    ("georgetown",  "Georgetown United",   ASCENSION, "#0F4C81", "#F4C800",
     ("Georgetown", "Georgetown Utd")),
    ("twoboats",    "Two Boats United",    ASCENSION, "#F4A300", "#B30838",
     ("Two Boats", "Two Boats Utd", "2 Boats United")),
    ("angels",      "77 Angels",           ASCENSION, "#EFE9D8", "#B99A3C",
     ("77 Angels FC", "Angels", "77 Angles")),
    ("islandboyz",  "Island Boyz",         ASCENSION, "#22B8CF", "#0B3A44",
     ("Island Boys", "Island Boyz FC")),
    ("vcmilan",     "VC Milan",            ASCENSION, "#8E1537", "#101820",
     ("Milan", "VC Milan FC")),
]


class Team:
    __slots__ = ("id", "name", "division", "primary", "secondary", "aliases")

    def __init__(self, tid, name, division, primary, secondary, aliases=()):
        self.id = tid
        self.name = name
        self.division = division
        self.primary = primary
        self.secondary = secondary
        self.aliases = tuple(aliases)

    # The rest of the app talks about "islands"; a division is one island.
    @property
    def island(self):
        return self.division

    def __repr__(self):
        return f"<Team {self.name}>"


TEAMS = [Team(*row) for row in _TEAMS]

BY_ID = {t.id: t for t in TEAMS}
BY_NAME = {t.name: t for t in TEAMS}

# Every spelling we accept when reading season.json -> team id.
_LOOKUP = {}
for _t in TEAMS:
    for _label in (_t.id, _t.name, *_t.aliases):
        _LOOKUP[_label.lower().replace(".", "").replace("  ", " ").strip()] = _t


def resolve(label):
    """Find a club from any reasonable spelling. Raises KeyError if unknown —
    a typo in the results file should fail loudly, not invent a club."""
    key = str(label).lower().replace(".", "").strip()
    t = _LOOKUP.get(key)
    if t is None:
        raise KeyError(f"Unknown club: {label!r}")
    return t



# Division labels accepted in season.json.
_DIVISION_LOOKUP = {
    "st. helena": ST_HELENA, "st helena": ST_HELENA, "saint helena": ST_HELENA,
    "st. helena division": ST_HELENA, "saint helena division": ST_HELENA,
    "sth": ST_HELENA,
    "ascension": ASCENSION, "ascension division": ASCENSION, "asc": ASCENSION,
}


def resolve_division(label):
    """Accept any reasonable spelling of a division name."""
    key = str(label).lower().strip()
    d = _DIVISION_LOOKUP.get(key)
    if d is None:
        raise KeyError(f"Unknown division: {label!r}")
    return d


def team_by_id(tid):
    return BY_ID.get(str(tid))


def display_name(tid, fallback=""):
    t = BY_ID.get(str(tid))
    return t.name if t else fallback


ISLANDS = [ST_HELENA, ASCENSION]
DIVISIONS = ISLANDS

assert len(TEAMS) == 12, f"expected 12 clubs, got {len(TEAMS)}"
assert len(BY_ID) == 12, "duplicate club id"
assert sum(1 for t in TEAMS if t.division == ST_HELENA) == 6
assert sum(1 for t in TEAMS if t.division == ASCENSION) == 6
