"""
League lookup: a table and matches for any league.

The 216 leagues and cups in leagues.json come straight from ESPN's public
scoreboard API (live tables, results and fixtures). Every other country's top
league (world_leagues.json -- the Caribbean, Africa, Asia, Oceania, the rest of
Europe and the Island Games) and any name typed in is looked up on Wikipedia
instead: the newest season article that carries a league table, plus its
results grid when it has one, or the league's info box when there's no table.
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


def world_leagues():
    """[(region, country, flag code, league name)] -- the top league of every
    country ESPN doesn't cover, looked up on Wikipedia."""
    try:
        rows = json.loads((HERE / "world_leagues.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
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


def _wiki_html(title):
    d = _get(WIKI, action="parse", page=title, prop="text", format="json", redirects=1)
    return d.get("parse", {}).get("text", {}).get("*", "")


def _wiki_tables(title, html=None):
    html = html if html is not None else _wiki_html(title)
    # A hand-typed span like colspan="2style=..." makes pandas give up on the
    # whole page; keep the number and drop the junk.
    html = re.sub(r'(colspan|rowspan)="?(\d+)[^"\s>]*"?', r'\1="\2"', html)
    try:
        return pd.read_html(io.StringIO(html))
    except (ValueError, ImportError):   # ImportError: pandas wanted html5lib
        pass
    # Still failing: read the tables one at a time and skip the broken one.
    from lxml import html as lh
    out = []
    for t in lh.fromstring(html).xpath("//table[not(ancestor::table)]"):
        try:
            out.extend(pd.read_html(io.StringIO(lh.tostring(t, encoding="unicode"))))
        except (ValueError, ImportError):
            continue
    return out


def _flat(cols):
    return [str(c[-1] if isinstance(c, tuple) else c) for c in cols]


def _is_league_table(t):
    cols = _flat(t.columns)
    return (len(t) >= 3 and any(c.startswith("Pts") for c in cols)
            and any(c.startswith(("Team", "Club")) for c in cols))


def _is_results_grid(t):
    """Home team down the side, away team across the top. Usually headed
    "Home \\ Away"; some pages head it "Team" over a row of short codes."""
    cols = _flat(t.columns)
    if "Home" in cols[0] and "Away" in cols[0]:
        return True
    codes = [c for c in cols[1:] if re.fullmatch(r"[A-ZÀ-Þ0-9.]{2,5}", c)]
    return cols[0].startswith(("Team", "Club", "Home")) and len(codes) >= 4 \
        and len(codes) >= len(cols) - 2 and abs(len(t) - len(codes)) <= 1


def _clean(t):
    t = t.copy()
    t.columns = _flat(t.columns)
    t = t.loc[:, ~t.columns.duplicated()]
    return t.fillna("").astype(str).replace(r"\[[^\]]*\]", "", regex=True)


def _season_year(title):
    m = re.match(r"^(\d{4})", title)
    return int(m.group(1)) if m else 0


# Words every league name shares; they can't tell one league from another.
GENERIC = {"league", "premier", "football", "division", "first", "super", "national",
           "championship", "the", "liga", "ligue", "pro", "professional", "senior",
           "soccer", "elite", "top", "and", "season", "primera", "honour", "honor"}


def _words(text):
    return {w for w in re.findall(r"\w+", text.casefold()) if len(w) > 2 and not w.isdigit()}


OTHER_SPORTS = re.compile(r"(?i)hockey|basketball|cricket|rugby|handball|volleyball|bandy|"
                          r"futsal|lacrosse|baseball|netball|women|beach soccer")


def _about(title, query):
    """A page only counts if it carries every distinctive word of the league
    asked for ("Jamaica" in Jamaica Premier League) -- otherwise a search for
    one league lands on another country's, or on a cricket league."""
    if OTHER_SPORTS.search(title) and not OTHER_SPORTS.search(query):
        return False
    if query.startswith("="):
        query = query[1:]
        stem = re.sub(r"^\d{4}(?:[–-]\d{2,4})?\s+", "", title)
        return stem.casefold() == query.strip().casefold()
    want = _words(query) - GENERIC
    if not want:
        # A name made only of common words ("Liga Primera") must match the
        # title exactly, year aside -- or Chile's "Liga de Primera" would do.
        stem = re.sub(r"^\d{4}(?:[–-]\d{2,4})?\s+", "", title)
        return stem.casefold() == query.strip().casefold()
    return want <= _words(title)


def wiki_league(query):
    """Newest Wikipedia season article for `query` that has a league table.
    Returns {title, url, tables:[DataFrame], grid: DataFrame|None,
    facts:[(label, value)]} or None. `facts` is only filled when there is no
    table to show."""
    query = query.strip()
    search = query.lstrip("=")
    titles = []
    for q in (f"{search} season", search):
        for t in _wiki_search(q):
            if t not in titles:
                titles.append(t)
    seasons = sorted((t for t in titles if _season_year(t) and _about(t, query)),
                     key=_season_year, reverse=True)
    for title in seasons[:5] + [t for t in titles if not _season_year(t) and _about(t, query)][:2]:
        page = _wiki_html(title)
        tables = _wiki_tables(title, page)
        league = [_clean(t) for t in tables if _is_league_table(t)]
        if not league:
            continue
        grids = [_clean(t) for t in tables if _is_results_grid(t)]
        standings = [g for g in (_standings_from(t) for t in league[:4]) if g["rows"]]
        teams = [r["team"] for g in standings for r in g["rows"]]
        played = [m for g in grids for m in _grid_matches(g, teams)]
        # A pairing left blank in one grid but already played in another (leagues
        # that meet three times split the grids) is not a game still to come.
        met = {(m["home"], m["away"]) for m in played if m["state"] == "post"}
        grid_games = [m for m in played if m["state"] == "post"
                      or (m["home"], m["away"]) not in met]
        matches = _footballboxes(page) + _dedupe_fixtures(grid_games)
        return {"title": title, "tables": league, "grid": grids[0] if grids else None,
                "standings": standings, "matches": matches, "facts": [],
                "url": _url(title)}
    # No table anywhere: fall back to the league's own article and its info
    # box (founded, clubs, champions...). Some leagues -- Saint Helena's among
    # them -- publish nothing more than that.
    for title in [t for t in titles if not _season_year(t) and _about(t, query)][:2]:
        facts = _infobox(_wiki_tables(title))
        league_box = any(re.search(r"(?i)clubs|champion|pyramid|level|teams", a)
                         for a, _ in facts)
        if facts and league_box:
            return {"title": title, "tables": [], "grid": None, "standings": [],
                    "matches": [], "facts": facts, "url": _url(title)}
    return None


def _url(title):
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")


def _infobox(tables):
    """[(label, value)] from the first two-column info box on the page."""
    for t in tables:
        if t.shape[1] == 2 and 2 <= len(t) <= 30:
            rows = []
            for a, b in t.astype(str).itertuples(index=False):
                a, b = (re.sub(r"\[[^\]]*\]", "", x).strip() for x in (a, b))
                if a and b and a != b and a != "nan" and b != "nan":
                    rows.append((a, b))
            if rows:
                return rows
    return []


# --------------------------------------------------------------------------- #
# Wikipedia -> the same shapes ESPN gives, so both draw the same way
# --------------------------------------------------------------------------- #
# Qualification / relegation bands, in the order a table usually lists them.
BAND_COLORS = ["#2e7d32", "#1e88e5", "#00acc1", "#8e24aa", "#f9a825", "#6d4c41", "#c62828"]
SCORE = re.compile(r"(\d+)\s*[–\-−]\s*(\d+)")


def _team_name(text):
    """'KÍ (C)' -> 'KÍ'. Drops the champion/qualified/relegated markers."""
    text = re.sub(r"\s*\((?:[A-Z]{1,2}(?:,\s*[A-Z]{1,2})*)\)", "", str(text))
    return re.sub(r"\s+", " ", text).strip()


def _num(v):
    v = str(v).replace("−", "-").replace("–", "-").strip()
    v = re.sub(r"^([+\-]?\d+)\.0$", r"\1", v)
    return v if re.fullmatch(r"[+\-]?\d+", v) else ""


def _standings_from(t):
    # "Teamvte" -> "Team": the v·t·e links of a navbox template land in the header.
    cols = {re.sub(r"\s*v\W*t\W*e$", "", c.split("[")[0].strip()): c for c in t.columns}
    def col(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None
    c_pos, c_team = col("Pos", "Rank", "#"), col("Team", "Club")
    c_note = next((c for c in t.columns if c.startswith(("Qualification", "Promotion",
                                                         "Relegation"))), None)
    keys = {"gp": col("Pld", "P", "GP"), "w": col("W"), "d": col("D"), "l": col("L"),
            "gf": col("GF", "F"), "ga": col("GA", "A"), "gd": col("GD"), "pts": col("Pts")}
    notes, rows = {}, []
    for i, r in enumerate(t.to_dict("records")):
        team = _team_name(r.get(c_team, "")) if c_team else ""
        pts = _num(r.get(keys["pts"], "")) if keys["pts"] else ""
        if not team or pts == "":
            continue
        note = str(r.get(c_note, "")).strip() if c_note else ""
        if note and note not in notes:
            notes[note] = BAND_COLORS[len(notes) % len(BAND_COLORS)]
        row = {k: (_num(r.get(c, "")) if c else "") for k, c in keys.items()}
        rank = _num(r.get(c_pos, "")) if c_pos else ""
        row.update(rank=rank or str(len(rows) + 1), team=team, logo="",
                   note=note, color=notes.get(note, ""))
        rows.append(row)
    return {"name": "", "rows": rows}


def _match(home, away, hs=None, as_=None, when="", label=""):
    played = hs is not None
    return {"date": when, "state": "post" if played else "pre",
            "detail": "FT" if played else "", "home": home, "away": away,
            "home_logo": "", "away_logo": "", "hs": hs, "as": as_, "label": label}


def _grid_matches(g, teams):
    """A results grid (home team down, away across) -> one match per score in
    each cell. An empty cell is a game still to be played."""
    rows = [_team_name(x) for x in g.iloc[:, 0]]
    abbrs = list(g.columns[1:])
    # Columns run in the same order as the rows; match by position.
    away_names = rows if len(abbrs) == len(rows) else abbrs
    out = []
    for i, home in enumerate(rows):
        for j, away in enumerate(away_names):
            if j >= len(abbrs) or home == away:
                continue
            cell = str(g.iat[i, j + 1]).strip()
            scores = SCORE.findall(cell)
            for hs, as_ in scores:
                out.append(_match(home, away, hs, as_))
            if not scores and cell in ("", "a", "—") and cell != "—":
                out.append(_match(home, away))
    return out


def _dedupe_fixtures(ms):
    seen, out = set(), []
    for m in ms:
        key = (m["home"], m["away"])
        if m["state"] == "pre":
            if key in seen:
                continue
            seen.add(key)
        out.append(m)
    return out


def _footballboxes(page):
    """Dated games laid out one box each (common for cups and playoffs)."""
    if "footballbox" not in page:
        return []
    from lxml import html as lh
    doc = lh.fromstring(page)
    out = []
    for box in doc.xpath('//div[contains(@class,"footballbox")]'):
        def text(cls):
            el = box.xpath(f'.//*[contains(@class,"{cls}")]')
            return re.sub(r"\s+", " ", el[0].text_content()).strip() if el else ""
        home, away, score = text("fhome"), text("faway"), text("fscore")
        if not home or not away:
            continue
        when = ""
        stamp = box.xpath('.//span[contains(@class,"bday")]/text()')
        if stamp:
            when = stamp[0] + "T12:00Z"
        m = SCORE.search(score)
        if not m and when and when[:10] < date.today().isoformat():
            continue        # already played but no score on the page
        label = text("fdate")
        out.append(_match(_team_name(home), _team_name(away),
                          m.group(1) if m else None, m.group(2) if m else None, when, label))
    return out
