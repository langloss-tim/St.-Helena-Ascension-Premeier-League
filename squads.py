"""
Club squads, read from squads.json.

Like the national team, this sits beside the league: nothing in league.py
reads it and nothing here moves a point. A club with no entry simply has no
squad screen.

Each player carries `countries`, a list of {name, code}. A player can have
more than one; an empty list means no country has been given, and the page
shows "---" rather than guessing.

Run standalone to check the file:  python squads.py
"""

import json
from pathlib import Path

import teams

PATH = Path(__file__).resolve().parent / "squads.json"

POSITIONS = [("GK", "Goalkeepers"), ("DF", "Defenders"),
             ("MF", "Midfielders"), ("FW", "Forwards")]
_POS_CODES = {code for code, _ in POSITIONS}


class DataError(ValueError):
    """squads.json has something the page can't show honestly."""


def load(path=PATH):
    """{club id: [player, ...]} — club names resolved through teams.py, so a
    typo in a club name fails loudly instead of hiding a squad."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    out = {}
    for club, players in (data.get("squads") or {}).items():
        team = teams.resolve(club)
        for p in players:
            if p.get("pos") not in _POS_CODES:
                raise DataError(f"unknown position {p.get('pos')!r} for {p.get('name')!r}")
            for c in p.get("countries") or []:
                if not c.get("name") or not c.get("code"):
                    raise DataError(f"country needs a name and a code for {p.get('name')!r}")
        out[team.id] = players
    return out


def by_position(players):
    """[(code, label, [players])] in GK, DF, MF, FW order, as entered within each."""
    return [(code, label, [p for p in players if p["pos"] == code])
            for code, label in POSITIONS]


if __name__ == "__main__":
    for club_id, players in load().items():
        print(f"{teams.BY_ID[club_id].name}: {len(players)} players")
        for code, label, group in by_position(players):
            print(f"  {label}: {len(group)}")
