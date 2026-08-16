"""
Data layer for the St. Helena Premier League.

Everything here talks to ESPN's public (unofficial) MLS API — no key required —
and returns plain Python dicts already re-branded into SHPL names via teams.py.
The UI layer (app.py) never sees a raw ESPN payload.

Endpoints used (league slug usa.1 == MLS):
  standings  : /apis/v2/sports/soccer/usa.1/standings
  scoreboard : /apis/site/v2/sports/soccer/usa.1/scoreboard?dates=YYYYMMDD[-YYYYMMDD]
  summary    : /apis/site/v2/sports/soccer/usa.1/summary?event=<id>   (odds -> win %)

All season-specific numbers come straight from the live feed, so when the 2027
season starts and matches are played the tables and fixtures update on their own.
"""

from datetime import datetime, timedelta, timezone

import requests

import teams

SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1"
CORE = "https://site.api.espn.com/apis/v2/sports/soccer/usa.1"
TIMEOUT = 12
HEADERS = {"User-Agent": "SHPL/1.0 (+streamlit)"}


class ESPNError(RuntimeError):
    pass


def _get(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise ESPNError(f"Could not reach ESPN ({e}).") from e
    except ValueError as e:
        raise ESPNError("ESPN returned an unreadable response.") from e


# --------------------------------------------------------------------------- #
# Standings / tables
# --------------------------------------------------------------------------- #
def _stat(stats, name, default=0):
    for s in stats:
        if s.get("name") == name or s.get("type") == name:
            v = s.get("value")
            return v if v is not None else s.get("displayValue", default)
    return default


def get_standings():
    """Return {season, conferences: [{name, island, table:[row,...]}]}.

    Each row: rank, shpl_name, mls_name, espn_id, played, wins, draws, losses,
    gf, ga, gd, points, form(list of 'W'/'D'/'L' or []), primary, secondary.
    Rows are sorted by points then goal difference (ESPN's own order is kept
    when present, but we re-sort defensively).
    """
    data = _get(f"{CORE}/standings")
    season = _season_label(data.get("season"))

    # ESPN maps its own conference names to islands via the team map: whichever
    # island our teams in that conference belong to.
    conferences = []
    for child in data.get("children", []):
        entries = child.get("standings", {}).get("entries", [])
        rows = []
        island_votes = {}
        for e in entries:
            team = e.get("team", {})
            espn_id = str(team.get("id", ""))
            stats = e.get("stats", [])
            mapped = teams.team_by_espn_id(espn_id)
            if mapped:
                island_votes[mapped.island] = island_votes.get(mapped.island, 0) + 1
            rows.append({
                "espn_id": espn_id,
                "shpl_name": teams.display_name(espn_id, team.get("displayName", "?")),
                "mls_name": team.get("displayName", ""),
                "played": int(_stat(stats, "gamesPlayed")),
                "wins": int(_stat(stats, "wins")),
                "draws": int(_stat(stats, "ties")),
                "losses": int(_stat(stats, "losses")),
                "gf": int(_stat(stats, "pointsFor")),
                "ga": int(_stat(stats, "pointsAgainst")),
                "gd": int(_stat(stats, "pointDifferential")),
                "points": int(_stat(stats, "points")),
                "primary": mapped.primary if mapped else "#888888",
                "secondary": mapped.secondary if mapped else "#222222",
            })

        rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"]))
        for i, r in enumerate(rows, start=1):
            r["rank"] = i

        island = max(island_votes, key=island_votes.get) if island_votes else child.get("name", "")
        conferences.append({
            "name": child.get("name", ""),
            "island": island,
            "table": rows,
        })

    # Order: St. Helena first, then Ascension
    conferences.sort(key=lambda c: 0 if c["island"] == teams.ST_HELENA else 1)
    return {"season": season, "conferences": conferences}


def _season_label(season):
    if not season:
        return ""
    yr = season.get("year") or season.get("displayName")
    return str(yr) if yr else ""


# --------------------------------------------------------------------------- #
# Matches / fixtures
# --------------------------------------------------------------------------- #
def _ymd(d):
    return d.strftime("%Y%m%d")


def get_matches(days_back=7, days_ahead=14):
    """Return a list of match dicts across a date window, newest-first grouped
    later by the UI. Each match:

      id, state ('pre'|'in'|'post'), status_detail, start (datetime, UTC),
      home/away: {espn_id, shpl_name, mls_name, score, winner, primary, secondary},
      completed (bool), venue (str)
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_ahead)
    rng = f"{_ymd(start)}-{_ymd(end)}"
    data = _get(f"{SITE}/scoreboard", params={"dates": rng, "limit": 300})

    matches = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        status = ev.get("status", {}).get("type", {})
        competitors = comp.get("competitors", [])
        home = away = None
        for c in competitors:
            side = {
                "espn_id": str(c.get("team", {}).get("id", "")),
                "shpl_name": teams.display_name(
                    c.get("team", {}).get("id", ""),
                    c.get("team", {}).get("displayName", "?"),
                ),
                "mls_name": c.get("team", {}).get("displayName", ""),
                "score": _to_int(c.get("score")),
                "winner": bool(c.get("winner", False)),
            }
            mapped = teams.team_by_espn_id(side["espn_id"])
            side["primary"] = mapped.primary if mapped else "#888888"
            side["secondary"] = mapped.secondary if mapped else "#222222"
            if c.get("homeAway") == "home":
                home = side
            else:
                away = side
        if not home or not away:
            continue

        matches.append({
            "id": str(ev.get("id", "")),
            "state": status.get("state", "pre"),
            "status_detail": status.get("shortDetail") or status.get("detail", ""),
            "start": _parse_dt(ev.get("date")),
            "completed": bool(status.get("completed", False)),
            "venue": (comp.get("venue") or {}).get("fullName", ""),
            "home": home,
            "away": away,
        })

    matches.sort(key=lambda m: m["start"] or datetime.max.replace(tzinfo=timezone.utc))
    return matches


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Win probability (from the match preview / betting odds)
# --------------------------------------------------------------------------- #
def _implied(moneyline):
    """American moneyline -> implied probability (with the book's vig still in)."""
    try:
        ml = float(moneyline)
    except (TypeError, ValueError):
        return None
    if ml == 0:
        return None
    return (-ml) / (-ml + 100) if ml < 0 else 100 / (ml + 100)


def get_win_probabilities(event_id):
    """Return {home_pct, draw_pct, away_pct, source} for a fixture, or None if
    ESPN has no preview odds yet (odds usually appear a few days out).

    Percentages are de-vigged (normalised to sum to 100) so they read as a
    clean 'chance to win' — the same figure MLS match previews quote.
    """
    data = _get(f"{SITE}/summary", params={"event": event_id})
    books = data.get("pickcenter") or data.get("odds") or []
    if not books:
        return None
    book = books[0]

    home_ml = (book.get("homeTeamOdds") or {}).get("moneyLine")
    away_ml = (book.get("awayTeamOdds") or {}).get("moneyLine")
    draw_ml = (book.get("drawOdds") or {}).get("moneyLine")

    ph, pa, pd = _implied(home_ml), _implied(away_ml), _implied(draw_ml)
    if ph is None or pa is None:
        return None
    if pd is None:
        pd = 0.0

    total = ph + pa + pd
    if total <= 0:
        return None
    return {
        "home_pct": round(ph / total * 100, 1),
        "draw_pct": round(pd / total * 100, 1),
        "away_pct": round(pa / total * 100, 1),
        "source": book.get("provider", {}).get("name", "ESPN"),
    }
