"""
The SHPL engine.

Everything the site shows is computed here from season.json: the division
tables, each club's form, and the model's win projection for a fixture that
hasn't been played yet. There is no external feed — the results file is the
league.

A match in season.json looks like:
    {"home": "Bellboys FC", "away": "Harts United", "hs": 3, "as": 2}

  * hs/as present  -> played (full time)
  * hs/as null     -> upcoming fixture
  * "live": true   -> in progress. Give it a "kickoff" timestamp and the
                      clock runs itself: the card shows however many minutes
                      have passed since then, recomputed on every page load.
                      A literal "minute" still works as an override.

Friendlies live in their own "friendlies" list. They are played against clubs
from outside the league, they count for NOTHING — no points, no goals, no form,
no place in the tables — and they appear on one screen only: that club's own
page. Everything else on the site ignores them.

Optional per-match keys: "note", "kickoff", "minute", "date" (overrides the
matchday's).
"""

import json
import math
import os
import re
from datetime import datetime, timezone

import teams

SEASON_FILE = "season.json"

# How the model weights a club's record when projecting a fixture.
_W_POINTS = 0.60      # points per game
_W_GOALDIFF = 0.28    # goal difference per game
_GD_CLIP = 4.0        # a 16-1 shouldn't make a club infinitely good
_HOME_ADV = 0.45      # goals-ish edge for hosting
_DRAW_BAND = 0.45     # controls how often the model calls a draw
_SLOPE = 1.20
_MIN_PCT = 3.0        # never show a 0% chance


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _here(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def load_season_file(path=None):
    with open(path or _here(SEASON_FILE), encoding="utf-8") as f:
        return json.load(f)


def _side(team, score):
    return {
        "id": team.id,
        "name": team.name,
        "score": score,
        "winner": False,
        "primary": team.primary,
        "secondary": team.secondary,
    }


def _external(name):
    """A club from outside the SHPL. It has no id in teams.py and never will —
    it exists only to be named on the other half of a friendly."""
    tid = "ext-" + re.sub(r"[^a-z0-9]+", "", str(name).lower())
    return {"id": tid, "name": str(name), "score": None, "winner": False,
            "primary": "#7c8595", "secondary": "#3a4150", "external": True}


def build_friendlies(data):
    """Non-league friendlies, in the same shape as every other match."""
    out = []
    for i, raw in enumerate(data.get("friendlies", []), start=1):
        club = teams.resolve(raw["club"])
        cs, os_ = raw.get("cs"), raw.get("os")
        played = cs is not None and os_ is not None
        at_home = raw.get("home", True)

        mine, theirs = _side(club, cs), _external(raw["opponent"])
        theirs["score"] = os_
        if played and cs != os_:
            mine["winner"] = cs > os_
            theirs["winner"] = os_ > cs
        home, away = (mine, theirs) if at_home else (theirs, mine)

        out.append({
            "id": f"friendly-{i}",
            "state": "post" if played else "pre",
            "status_detail": "FT (friendly)" if played else "",
            "start": raw.get("date"),
            "date": raw.get("date"),
            "completed": played,
            "division": club.division,
            "matchday": None,
            "stage": "friendly",
            "round": "Friendly",
            "note": raw.get("note", ""),
            "home": home,
            "away": away,
        })
    return out


def _slug(division):
    return "sth" if division == teams.ST_HELENA else "asc"


def build_matches(data):
    """Flatten season.json into the match list the UI renders."""
    out = []
    for block in data.get("matchdays", []):
        division = teams.resolve_division(block["division"])
        n = block.get("n")
        for i, raw in enumerate(block.get("matches", []), start=1):
            out.append(_one_match(raw, division, n, i, block.get("date"),
                                  stage="regular", round_name=""))

    out.extend(build_friendlies(data))

    for i, raw in enumerate(data.get("playoffs", []), start=1):
        division = (teams.resolve_division(raw["division"])
                    if raw.get("division") else None)
        out.append(_one_match(raw, division, None, i, raw.get("date"),
                              stage="playoff", round_name=raw.get("round", "")))
    return out


FULL_TIME = 90


def _live_minute(raw):
    """The clock for a match in progress, worked out from its kickoff rather
    than written down. Storing the kickoff once means the minute is right
    whenever the page is opened, with nothing left to keep updating by hand.

    Returns "" when there is no usable kickoff, so the caller can fall back to
    a "minute" written in directly."""
    ko = raw.get("kickoff")
    if not ko:
        return ""
    try:
        start = datetime.fromisoformat(str(ko).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if start.tzinfo is None:                       # bare timestamp means UTC
        start = start.replace(tzinfo=timezone.utc)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    minute = int(elapsed // 60) + 1                # the 1st minute is "1'"
    if minute < 1:
        return "0'"
    return f"{min(minute, FULL_TIME)}'"


def _one_match(raw, division, matchday, idx, block_date, stage, round_name):
    home = teams.resolve(raw["home"])
    away = teams.resolve(raw["away"])
    hs, as_ = raw.get("hs"), raw.get("as")
    played = hs is not None and as_ is not None
    live = bool(raw.get("live")) and played

    if live:
        state, completed = "in", False
        detail = _live_minute(raw) or raw.get("minute") or "LIVE"
    elif played:
        state, completed = "post", True
        detail = raw.get("status") or "FT"
    else:
        state, completed = "pre", False
        detail = ""

    if stage == "playoff":
        prefix = "po"
    else:
        prefix = _slug(division)
    mid = f"{prefix}-{'md%s' % matchday if matchday else round_name.lower().replace(' ', '') or 'x'}-{idx}"

    h, a = _side(home, hs), _side(away, as_)
    if completed and hs != as_:
        h["winner"] = hs > as_
        a["winner"] = as_ > hs

    date_str = raw.get("date") or block_date
    return {
        "id": mid,
        "state": state,
        "status_detail": detail,
        "start": date_str,
        "date": date_str,
        "completed": completed,
        "division": division,
        "matchday": matchday,
        "stage": stage,
        "round": round_name,
        "note": raw.get("note", ""),
        "home": h,
        "away": a,
    }


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
def _blank(team):
    return {
        "id": team.id, "name": team.name,
        "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "gf": 0, "ga": 0, "gd": 0, "points": 0,
        "primary": team.primary, "secondary": team.secondary,
        "form": [],
    }


def build_standings(data, matches):
    rows = {t.id: _blank(t) for t in teams.TEAMS}

    for m in matches:
        if m["stage"] != "regular" or m["state"] not in ("post", "in"):
            continue
        if not m["completed"]:
            continue  # a live game only counts once it's final
        hs, as_ = m["home"]["score"], m["away"]["score"]
        for side, mine, theirs in ((m["home"], hs, as_), (m["away"], as_, hs)):
            r = rows[side["id"]]
            r["played"] += 1
            r["gf"] += mine
            r["ga"] += theirs
            if mine > theirs:
                r["wins"] += 1
                r["points"] += 3
                r["form"].append("W")
            elif mine == theirs:
                r["draws"] += 1
                r["points"] += 1
                r["form"].append("D")
            else:
                r["losses"] += 1
                r["form"].append("L")

    for r in rows.values():
        r["gd"] = r["gf"] - r["ga"]
        r["form"] = r["form"][-5:]

    conferences = []
    for division in teams.DIVISIONS:
        table = [rows[t.id] for t in teams.TEAMS if t.division == division]
        # Points, then goal difference, then goals scored, then wins, then name.
        table.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], -r["wins"], r["name"]))
        for i, r in enumerate(table, start=1):
            r["rank"] = i
        conferences.append({
            "name": teams.DIVISION_NAME[division],
            "island": division,
            "table": table,
        })

    return {"season": str(data.get("season", "")), "conferences": conferences}


# --------------------------------------------------------------------------- #
# Golden Boot
# --------------------------------------------------------------------------- #
def _flag(code):
    """A two-letter country code as a flag emoji, built from the regional
    indicator block — so a new country only needs its code, never a new image."""
    code = (code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


def build_scorers(data):
    """The scoring chart, ranked. Players level on goals share a rank, and the
    next rank skips accordingly (6, 5, 5, 5, 4 -> 1, 2, 2, 2, 5)."""
    rows = []
    for i, raw in enumerate(data.get("scorers", [])):
        rows.append({
            "_order": i,
            "name": raw["name"],
            "goals": int(raw.get("goals", 0)),
            "country": raw.get("country", ""),
            "code": (raw.get("code") or "").upper(),
            "flag": _flag(raw.get("code")),
        })
    # Players level on goals keep the order they were entered in, rather than
    # being reshuffled alphabetically behind the league's back.
    rows.sort(key=lambda r: (-r["goals"], r["_order"]))

    rank, last_goals = 0, None
    for i, r in enumerate(rows, start=1):
        if r["goals"] != last_goals:
            rank, last_goals = i, r["goals"]
        r["rank"] = rank
        r.pop("_order", None)
    return rows


# --------------------------------------------------------------------------- #
# Projections — the site's own model, in place of a betting market
# --------------------------------------------------------------------------- #
def _strength(row):
    if not row or not row["played"]:
        return 0.0
    ppg = row["points"] / row["played"]
    gdpg = max(-_GD_CLIP, min(_GD_CLIP, row["gd"] / row["played"]))
    return _W_POINTS * ppg + _W_GOALDIFF * gdpg


def _logistic(x):
    return 1.0 / (1.0 + math.exp(-_SLOPE * x))


def build_winprobs(standings, matches):
    """Model win/draw/loss chances for every fixture still to be played."""
    by_id = {}
    for conf in standings["conferences"]:
        for r in conf["table"]:
            by_id[r["id"]] = r

    out = {}
    for m in matches:
        if m["state"] != "pre" or m["stage"] == "friendly":
            continue
        d = _strength(by_id.get(m["home"]["id"])) - _strength(by_id.get(m["away"]["id"]))
        if m["stage"] == "playoff":
            d -= _HOME_ADV / 2  # neutral-ish venue in the postseason
        d += _HOME_ADV

        home = _logistic(d - _DRAW_BAND)
        away = _logistic(-d - _DRAW_BAND)
        draw = max(0.05, 1.0 - home - away)

        pct = [max(_MIN_PCT, p * 100) for p in (home, draw, away)]
        total = sum(pct)
        home, draw = (round(p * 100 / total, 1) for p in pct[:2])
        # The last share takes the rounding remainder, so the three always add
        # up to exactly 100 — the win bar is drawn straight from these numbers.
        away = round(100.0 - home - draw, 1)
        out[m["id"]] = {
            "home_pct": home, "draw_pct": draw, "away_pct": away,
            "source": "SHPL model",
        }
    return out


# --------------------------------------------------------------------------- #
# The snapshot every page renders from
# --------------------------------------------------------------------------- #
def build_feed(data=None, path=None):
    data = data if data is not None else load_season_file(path)
    matches = build_matches(data)
    standings = build_standings(data, matches)
    winprobs = build_winprobs(standings, matches)
    return {
        "scorers": build_scorers(data),
        "generated_at": data.get("updated") or "",
        "season": str(data.get("season", "")),
        "standings": standings,
        "matches": matches,
        "winprobs": winprobs,
        "playoffs_open": bool(data.get("playoffs_open")),
        "has_playoff_games": any(m["stage"] == "playoff" for m in matches),
    }


if __name__ == "__main__":
    f = build_feed()
    for conf in f["standings"]["conferences"]:
        print(f"\n{conf['name']}")
        print(f"{'#':>2} {'Club':<22}{'P':>3}{'W':>3}{'D':>3}{'L':>3}{'GF':>4}{'GA':>4}{'GD':>5}{'Pts':>5}  Form")
        for r in conf["table"]:
            print(f"{r['rank']:>2} {r['name']:<22}{r['played']:>3}{r['wins']:>3}{r['draws']:>3}"
                  f"{r['losses']:>3}{r['gf']:>4}{r['ga']:>4}{r['gd']:>+5}{r['points']:>5}  "
                  + "".join(r["form"]))
    print(f"\n{len(f['matches'])} matches, {len(f['winprobs'])} projections")
