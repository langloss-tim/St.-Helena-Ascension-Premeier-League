"""
The national team: squad and games, read from national.json.

This sits beside the league, not inside it. Nothing here touches season.json,
the tables, the Golden Boot or the projections, and nothing in league.py reads
this file.

A score is always written Saint Helena first: `gf` is Saint Helena's goals and
`ga` the opponent's, whether the game was at home or away. Both null means the
game hasn't been played yet.

Run standalone to check the file:  python national.py
"""

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent / "national.json"

POSITIONS = [("GK", "Goalkeepers"), ("DF", "Defenders"),
             ("MF", "Midfielders"), ("FW", "Forwards")]
_POS_CODES = {code for code, _ in POSITIONS}


class DataError(ValueError):
    """national.json has something the page can't show honestly."""


def load(path=PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for p in data.get("players", []):
        if p.get("pos") not in _POS_CODES:
            raise DataError(f"unknown position {p.get('pos')!r} for {p.get('name')!r}")
    for g in data.get("games", []):
        gf, ga = g.get("gf"), g.get("ga")
        if (gf is None) != (ga is None):
            raise DataError(f"half a score against {g.get('opponent')!r}: {gf}-{ga}")
        if not isinstance(g.get("home"), bool):
            raise DataError(f"home must be true/false against {g.get('opponent')!r}")
    return data


def played(data):
    return [g for g in data.get("games", []) if g.get("gf") is not None]


def upcoming(data):
    return [g for g in data.get("games", []) if g.get("gf") is None]


def outcome(g):
    if g.get("gf") is None:
        return None
    return "W" if g["gf"] > g["ga"] else ("L" if g["gf"] < g["ga"] else "D")


def squad_by_position(data):
    """[(code, label, [names])] in GK, DF, MF, FW order, as entered within each."""
    players = data.get("players", [])
    return [(code, label, [p["name"] for p in players if p["pos"] == code])
            for code, label in POSITIONS]


def record(data):
    games = played(data)
    res = [outcome(g) for g in games]
    return {
        "played": len(games),
        "wins": res.count("W"),
        "draws": res.count("D"),
        "losses": res.count("L"),
        "gf": sum(g["gf"] for g in games),
        "ga": sum(g["ga"] for g in games),
        "clean_sheets": sum(1 for g in games if g["ga"] == 0),
        "upcoming": len(upcoming(data)),
    }


if __name__ == "__main__":
    d = load()
    for code, label, names in squad_by_position(d):
        print(f"{label} ({len(names)}): {', '.join(names)}")
    r = record(d)
    print(f"\nP{r['played']} W{r['wins']} D{r['draws']} L{r['losses']} "
          f"{r['gf']}-{r['ga']}, {r['clean_sheets']} clean sheets, "
          f"{r['upcoming']} upcoming")
    for g in d["games"]:
        where = "vs" if g["home"] else "at"
        score = f"{g['gf']}-{g['ga']} {outcome(g)}" if g["gf"] is not None else "upcoming"
        print(f"  {where} {g['opponent']}: {score}")
