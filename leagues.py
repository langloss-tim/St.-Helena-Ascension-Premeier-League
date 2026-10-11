"""
League lookup: a table and matches for any league.

The 216 leagues and cups in leagues.json come straight from ESPN's public
scoreboard API (live tables, results and fixtures). Any other league name is
looked up on Wikipedia instead: the newest season article that carries a
league table, plus its results grid when it has one.
"""

import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
ESPN = "https://site.api.espn.com/apis"
WIKI = "https://en.wikipedia.org/w/api.php"
# Wikipedia asks for a descriptive User-Agent; ESPN answers 403 to that same
# string, so ESPN gets the requests default.
UA = {"User-Agent": "MatchSimulatorFanSite/1.0 (https://sthapl.streamlit.app)"}


class Unavailable(Exception):
    """The source could not be reached or had nothing usable."""


def espn_leagues():
    """[(slug, name)] for every league/cup ESPN covers, sorted by name."""
    rows = json.loads((HERE / "leagues.json").read_text(encoding="utf-8"))
    return [tuple(r) for r in rows]


def _get(url, **params):
    headers = UA if url.startswith(WIKI) else None
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        raise Unavailable(str(e)) from e


def _logo(team):
    logos = team.get("logos") or []
    return logos[0].get("href", "") if logos else team.get("logo", "")


def espn_standings(slug):
    """[{name, rows:[...]}] -- one group per table (cups have several)."""
    d = _get(f"{ESPN}/v2/sports/soccer/{slug}/standings")
    groups = d.get("children") or ([d] if d.get("standings") else [])
    out = []
    for g in groups:
        rows = []
        for e in g.get("standings", {}).get("entries", []):
            s = {x["name"]: x.get("displayValue", "") for x in e.get("stats", [])}
            note = e.get("note") or {}
            rows.append({
                "rank": s.get("rank", ""), "team": e["team"].get("displayName", ""),
                "logo": _logo(e["team"]), "gp": s.get("gamesPlayed", ""),
                "w": s.get("wins", ""), "d": s.get("ties", ""), "l": s.get("losses", ""),
                "gf": s.get("pointsFor", ""), "ga": s.get("pointsAgainst", ""),
                "gd": s.get("pointDifferential", ""), "pts": s.get("points", ""),
                "color": note.get("color", ""), "note": note.get("description", ""),
            })
        if rows:
            rows.sort(key=lambda r: int(r["rank"]) if str(r["rank"]).isdigit() else 999)
            out.append({"name": g.get("name", ""), "rows": rows})
    return out


def _scoreboard(slug, dates):
    return _get(f"{ESPN}/site/v2/sports/soccer/{slug}/scoreboard",
                dates=dates, limit=1000).get("events", [])


def espn_matches(slug, days_back=14, days_ahead=14, today=None):
    """Every match from days_back ago to days_ahead from now, oldest first.
    One ranged request when ESPN accepts it; ESPN's range lookup comes and goes,
    so otherwise it is one request per day, fetched side by side."""
    today = today or date.today()
    days = [today + timedelta(days=i) for i in range(-days_back, days_ahead + 1)]
    try:
        events = _scoreboard(slug, f"{days[0]:%Y%m%d}-{days[-1]:%Y%m%d}")
    except Unavailable:
        with ThreadPoolExecutor(10) as ex:
            got = list(ex.map(lambda d: _try_day(slug, d), days))
        if all(g is None for g in got):
            raise Unavailable("no scoreboard day could be fetched")
        events = [e for g in got if g for e in g]
    out, seen = [], set()
    for ev in events:
        if ev.get("id") in seen:
            continue
        seen.add(ev.get("id"))
        comp = (ev.get("competitions") or [{}])[0]
        sides = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        if "home" not in sides or "away" not in sides:
            continue
        st = ev.get("status", {}).get("type", {})
        out.append({
            "date": ev.get("date", ""),
            "state": st.get("state", "pre"),          # pre / in / post
            "detail": st.get("shortDetail", ""),
            "home": sides["home"]["team"].get("displayName", ""),
            "away": sides["away"]["team"].get("displayName", ""),
            "home_logo": _logo(sides["home"]["team"]),
            "away_logo": _logo(sides["away"]["team"]),
            "hs": sides["home"].get("score"), "as": sides["away"].get("score"),
        })
    out.sort(key=lambda m: m["date"])
    return out


def _try_day(slug, day):
    try:
        return _scoreboard(slug, f"{day:%Y%m%d}")
    except Unavailable:
        return None


# --------------------------------------------------------------------------- #
# Wikipedia fallback
# --------------------------------------------------------------------------- #
def _wiki_search(q, n=10):
    d = _get(WIKI, action="query", list="search", srsearch=q, format="json", srlimit=n)
    return [s["title"] for s in d.get("query", {}).get("search", [])]


def _wiki_tables(title):
    d = _get(WIKI, action="parse", page=title, prop="text", format="json", redirects=1)
    html = d.get("parse", {}).get("text", {}).get("*", "")
    try:
        return pd.read_html(io.StringIO(html))
    except ValueError:
        return []


def _flat(cols):
    return [str(c[-1] if isinstance(c, tuple) else c) for c in cols]


def _is_league_table(t):
    cols = _flat(t.columns)
    return (len(t) >= 3 and any(c.startswith("Pts") for c in cols)
            and any(c.startswith(("Team", "Club")) for c in cols))


def _is_results_grid(t):
    first = _flat(t.columns)[0]
    return "Home" in first and "Away" in first


def _clean(t):
    t = t.copy()
    t.columns = _flat(t.columns)
    t = t.loc[:, ~t.columns.duplicated()]
    return t.fillna("").astype(str).replace(r"\[[^\]]*\]", "", regex=True)


def _season_year(title):
    m = re.match(r"^(\d{4})", title)
    return int(m.group(1)) if m else 0


def _words(text):
    return {w for w in re.findall(r"\w+", text.casefold()) if len(w) > 2 and not w.isdigit()}


def _about(title, query):
    """Season titles must actually name the league asked for -- most of its
    words -- or a search for one league lands on some cup it played in."""
    want = _words(query)
    return not want or len(want & _words(title)) >= max(1, -(-len(want) * 3 // 5))


def wiki_league(query):
    """Newest Wikipedia season article for `query` that has a league table.
    Returns {title, url, tables:[DataFrame], grid: DataFrame|None} or None."""
    query = query.strip()
    titles = []
    for q in (f"{query} season", query):
        for t in _wiki_search(q):
            if t not in titles:
                titles.append(t)
    seasons = sorted((t for t in titles if _season_year(t) and _about(t, query)), key=_season_year, reverse=True)
    for title in seasons[:5] + [t for t in titles if not _season_year(t) and _about(t, query)][:2]:
        tables = _wiki_tables(title)
        league = [_clean(t) for t in tables if _is_league_table(t)]
        if not league:
            continue
        grid = next((_clean(t) for t in tables if _is_results_grid(t)), None)
        return {"title": title, "tables": league, "grid": grid,
                "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")}
    return None
