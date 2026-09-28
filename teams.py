"""
Barbados Premier League — clubs.

The Barbados Premier League is its own competition. The twelve clubs below and
their colours are the whole roster, and every result comes from season.json
(see league.py).

One table of twelve. There are no divisions.
"""

# The whole league is one table. The UI still speaks of a "division" in a few
# places; there is exactly one.
BARBADOS = "Barbados"

DIVISION_NAME = {
    BARBADOS: "Barbados Premier League",
}

# One row per club:
#   id, name, division, primary, secondary, aliases
# `aliases` exist so results can be entered with the short name people
# actually say ("Weymouth", "Lions") and still land on the right club.
_TEAMS = [
    ("weymouth",    "Weymouth Wales FC",       BARBADOS, "#C8102E", "#FFFFFF",
     ("Weymouth Wales", "Weymouth", "Wales")),
    ("bagatelle",   "Bagetelle FC",            BARBADOS, "#1E6B3A", "#F2C200",
     ("Bagetelle", "Bagatelle", "Bagatelle FC")),
    ("brittonshill", "Britton's Hill United",  BARBADOS, "#1F4E9E", "#FFFFFF",
     ("Britton's Hill", "Brittons Hill", "Britton's", "Brittons", "Brittons Hill United", "Britton\u2019s Hill United",
      "Britton's Hill Utd")),
    ("ellerton",    "Ellerton FC",             BARBADOS, "#F28C28", "#1D1D1B",
     ("Ellerton",)),
    ("wotton",      "Wotton FC",               BARBADOS, "#7A2E8E", "#F4C800",
     ("Wotton",)),
    ("lions",       "St. Andrew's Lions FC",   BARBADOS, "#E3B505", "#0E2B3B",
     ("St. Andrew's Lions", "St Andrews Lions", "St Andrew's Lions", "Saint Andrew's Lions",
      "St. Andrew\u2019s Lions FC", "St. Andrew Lions", "St Andrew Lions", "Lions")),
    ("fitts",       "Fitts Village FC",        BARBADOS, "#22B8CF", "#0B3A44",
     ("Fitts Village", "Fitts")),
    ("green",       "Green United",            BARBADOS, "#17A66B", "#0A2240",
     ("Green Utd", "Green")),
    ("blackspurs",  "Blackspurs FC",           BARBADOS, "#2B2B2B", "#E8E8E8",
     ("Blackspurs", "Black Spurs")),
    ("atlas",       "Atlas United",            BARBADOS, "#8E1537", "#F4F4F4",
     ("Atlas", "Atlas Utd")),
    ("kingspark",   "Kings Park Rangers FC",   BARBADOS, "#6CACE4", "#041E42",
     ("Kings Park Rangers", "Kings Park", "King's Park Rangers", "KPR", "Rangers")),
    ("spartans",    "Spartens FC",             BARBADOS, "#B49759", "#1D1D1B",
     ("Spartens", "Spartans", "Spartans FC")),
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

    # The rest of the app talks about "islands"; there is one: Barbados.
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
        _key = _label.lower().replace(".", "").replace("  ", " ").strip()
        _clash = _LOOKUP.get(_key)
        if _clash is not None and _clash is not _t:
            raise AssertionError(
                f"{_label!r} would resolve to two clubs: "
                f"{_clash.name} and {_t.name}")
        _LOOKUP[_key] = _t


def resolve(label):
    """Find a club from any reasonable spelling. Raises KeyError if unknown —
    a typo in the results file should fail loudly, not invent a club."""
    key = str(label).lower().replace(".", "").strip()
    t = _LOOKUP.get(key)
    if t is None:
        raise KeyError(f"Unknown club: {label!r}")
    return t



# Division labels accepted in season.json. There is only one, and a block may
# leave "division" out entirely.
_DIVISION_LOOKUP = {
    "barbados": BARBADOS, "barbados premier league": BARBADOS, "bpl": BARBADOS,
    "league": BARBADOS,
}


def resolve_division(label):
    """Accept any reasonable spelling of the division name (or none at all)."""
    if label is None or str(label).strip() == "":
        return BARBADOS
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


ISLANDS = [BARBADOS]
DIVISIONS = ISLANDS

assert len(TEAMS) == 12, f"expected 12 clubs, got {len(TEAMS)}"
assert len(BY_ID) == 12, "duplicate club id"
