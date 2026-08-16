"""
St. Helena Premier League — team branding layer.

Every SHPL team is a rebrand of a real MLS club. All live data (standings,
scores, fixtures, win %) comes from the real MLS club via the ESPN API; we
just swap the name, island, and colours on display.

St. Helena  -> MLS Eastern Conference
Ascension   -> MLS Western Conference

The `espn_id` values are ESPN's team IDs (verified against the live MLS teams
endpoint). If ESPN ever changes an ID, update it here — nothing else needs to
change.
"""

# island constants
ST_HELENA = "St. Helena"
ASCENSION = "Ascension"

# One row per club:
#   shpl_name, espn_id, mls_name, island, primary_color, secondary_color
_TEAMS = [
    # ---------------- St. Helena (MLS Eastern Conference) ----------------
    ("Bellboys",          "20232", "Inter Miami CF",          ST_HELENA, "#F7B5CD", "#231F20"),
    ("Rovers",            "18986", "Nashville SC",            ST_HELENA, "#ECE83A", "#1D1D1B"),
    ("Fugees",            "10739", "Philadelphia Union",      ST_HELENA, "#0E2B3B", "#B49759"),
    ("Harts",             "17606", "New York City FC",        ST_HELENA, "#6CACE4", "#041E42"),
    ("La Verde",          "189",   "New England Revolution",  ST_HELENA, "#0A2240", "#CE0E2D"),
    ("Old Boys",          "182",   "Chicago Fire FC",         ST_HELENA, "#141B4D", "#8DC8E8"),
    ("Wirebirds",         "18267", "FC Cincinnati",           ST_HELENA, "#FE5000", "#003087"),
    ("STH Young Boys",    "18418", "Atlanta United FC",       ST_HELENA, "#80000B", "#221F1F"),
    ("Spurs",             "7318",  "Toronto FC",              ST_HELENA, "#B81137", "#455560"),
    ("Jamestown",         "190",   "Red Bull New York",       ST_HELENA, "#ED1E36", "#002D62"),
    ("Halftree Hollow",   "193",   "D.C. United",             ST_HELENA, "#231F20", "#EF3E42"),
    ("Crystal Rangers",   "12011", "Orlando City SC",         ST_HELENA, "#633492", "#FDE192"),
    ("Longwood",          "183",   "Columbus Crew",           ST_HELENA, "#FEDD00", "#000000"),
    ("Lakers",            "9720",  "CF Montréal",             ST_HELENA, "#00529B", "#000000"),
    ("Ballez",            "21300", "Charlotte FC",            ST_HELENA, "#1A85C8", "#000000"),

    # ---------------- Ascension (MLS Western Conference) ----------------
    ("77 Devils",         "9727",  "Vancouver Whitecaps",     ASCENSION, "#00245E", "#95A5C6"),
    ("Island Boyz",       "18966", "LAFC",                    ASCENSION, "#000000", "#C39E6D"),
    ("Wanderers",         "191",   "San Jose Earthquakes",    ASCENSION, "#0051BA", "#000000"),
    ("VC Milan",          "6077",  "Houston Dynamo FC",       ASCENSION, "#FF6B00", "#101820"),
    ("Georgetown",        "21812", "St. Louis CITY SC",       ASCENSION, "#DC1E34", "#101820"),
    ("Two Boats",         "4771",  "Real Salt Lake",          ASCENSION, "#B30838", "#F4C800"),
    ("Inbetweeners",      "185",   "FC Dallas",               ASCENSION, "#E81F3E", "#0C2340"),
    ("Saints Club",       "184",   "Colorado Rapids",         ASCENSION, "#960A2C", "#8BB8E8"),
    ("Hearts Ascension",  "17362", "Minnesota United FC",     ASCENSION, "#8CD2F4", "#231F20"),
    ("77 Angels",         "9723",  "Portland Timbers",        ASCENSION, "#00482B", "#D69A00"),
    ("Baked Bean Streamers","9726","Seattle Sounders FC",     ASCENSION, "#5D9741", "#236192"),
    ("MCR",               "22529", "San Diego FC",            ASCENSION, "#00AEEF", "#101820"),
    ("Encompass United",  "187",   "LA Galaxy",               ASCENSION, "#00245D", "#FBB515"),
    ("After Eights",      "20906", "Austin FC",               ASCENSION, "#00B140", "#000000"),
    ("Interserve United", "186",   "Sporting Kansas City",    ASCENSION, "#91B0D5", "#002F65"),
]


class Team:
    __slots__ = ("shpl_name", "espn_id", "mls_name", "island", "primary", "secondary")

    def __init__(self, shpl_name, espn_id, mls_name, island, primary, secondary):
        self.shpl_name = shpl_name
        self.espn_id = espn_id
        self.mls_name = mls_name
        self.island = island
        self.primary = primary
        self.secondary = secondary

    def __repr__(self):
        return f"<Team {self.shpl_name} ({self.mls_name})>"


TEAMS = [Team(*row) for row in _TEAMS]

# Fast lookups
BY_ESPN_ID = {t.espn_id: t for t in TEAMS}
BY_SHPL_NAME = {t.shpl_name: t for t in TEAMS}


def team_by_espn_id(espn_id):
    """Return the SHPL Team for an ESPN team id, or None if unknown."""
    return BY_ESPN_ID.get(str(espn_id))


def display_name(espn_id, fallback=""):
    """SHPL name for an ESPN id; falls back to the given text (e.g. the raw
    MLS name) if we don't have a mapping — so nothing ever renders blank."""
    t = BY_ESPN_ID.get(str(espn_id))
    return t.shpl_name if t else fallback


ISLANDS = [ST_HELENA, ASCENSION]

# Sanity check: exactly 30 teams, 15 per island, no duplicate IDs.
assert len(TEAMS) == 30, f"expected 30 teams, got {len(TEAMS)}"
assert len(BY_ESPN_ID) == 30, "duplicate ESPN id in team map"
assert sum(1 for t in TEAMS if t.island == ST_HELENA) == 15
assert sum(1 for t in TEAMS if t.island == ASCENSION) == 15
