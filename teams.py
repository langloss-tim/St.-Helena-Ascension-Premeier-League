"""
Curaçao Promé Divishon — clubs.

The Curaçao Promé Divishon is its own competition. The ten clubs below (the
2025-26 top flight) and
their colours are the whole roster, and every result comes from season.json
(see league.py).

One table of ten. There are no divisions.
"""

# The whole league is one table. The UI still speaks of a "division" in a few
# places; there is exactly one.
CURACAO = "Curaçao"

DIVISION_NAME = {
    CURACAO: "Curaçao Promé Divishon",
}

# One row per club:
#   id, name, division, primary, secondary, aliases
# `aliases` exist so results can be entered with the short name people
# actually say ("Weymouth", "Lions") and still land on the right club.
_TEAMS = [
    ("scherpenheuvel", "RKSV Scherpenheuvel",  CURACAO, "#D0021B", "#FFFFFF",
     ("Scherpenheuvel", "Scherpenheuvel FC")),
    ("jongholland", "CRKSV Jong Holland",      CURACAO, "#1F4FA3", "#D0021B",
     ("Jong Holland", "Jong Holland FC")),
    ("victoryboys", "SV Victory Boys",         CURACAO, "#1E8F3E", "#FFFFFF",
     ("Victory Boys", "Victory Boys Bandariba", "Victory")),
    ("jongcolombia", "CRKSV Jong Colombia",    CURACAO, "#F2C500", "#1C3F94",
     ("Jong Colombia", "Colombia")),
    ("inter",       "CVV Inter Willemstad",    CURACAO, "#0B5D2E", "#FFFFFF",
     ("Inter Willemstad", "Inter", "CVV Inter")),
    ("dominguito",  "RKSV Centro Dominguito",  CURACAO, "#8E1B1B", "#FFFFFF",
     ("Centro Dominguito", "Dominguito")),
    ("bandaabou",   "UD Banda Abou",           CURACAO, "#F28C28", "#FFFFFF",
     ("Banda Abou", "UNDEBA", "UnDeBa Banda Abou", "UnDeBa")),
    ("barber",      "CSD Barber",              CURACAO, "#7CB342", "#C62828",
     ("Barber", "Centro Social Deportivo Barber")),
    # Colours not published anywhere we could find — placeholder sky blue.
    ("salina",      "SC Atletiko Salina",      CURACAO, "#00A3E0", "#FFFFFF",
     ("Atletiko Salina", "SC Atlétiko Saliña", "Atlétiko Saliña", "Salina")),
    ("subt",        "SV SUBT",                 CURACAO, "#0D2C8C", "#F4C800",
     ("SUBT",)),
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

    # The rest of the app talks about "islands"; there is one: Curaçao.
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
    "curaçao": CURACAO, "curacao": CURACAO, "promé divishon": CURACAO,
    "prome divishon": CURACAO, "cpd": CURACAO,
    "league": CURACAO,
}


def resolve_division(label):
    """Accept any reasonable spelling of the division name (or none at all)."""
    if label is None or str(label).strip() == "":
        return CURACAO
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


ISLANDS = [CURACAO]
DIVISIONS = ISLANDS

assert len(TEAMS) == 10, f"expected 10 clubs, got {len(TEAMS)}"
assert len(BY_ID) == 10, "duplicate club id"
