"""
App-side data loader.

The league's data lives in the repo, in season.json — so there is nothing to
fetch, nothing to rate-limit and nothing to go down. Past seasons are kept
alongside it as season-<year>.json and listed in seasons.json.

Everything returned matches the shape the UI expects:
  - get_standings(feed)            -> {"season", "conferences": [...]}
  - get_matches(feed)              -> list of match dicts, 'day' as a date
  - get_win_probabilities(feed, id)-> dict or None
"""

import json
import os
from datetime import date, datetime

import league

_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT = os.path.join(_DIR, "season.json")
SEASONS_INDEX = os.path.join(_DIR, "seasons.json")


class FeedUnavailable(RuntimeError):
    pass


def _archive_path(season):
    return os.path.join(_DIR, f"season-{season}.json")


def _parse_day(s):
    """Accept '2026-08-16' or '2026-08-16T19:30'. Returns a date, or None."""
    if not s:
        return None
    text = str(s)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _hydrate(feed):
    for m in feed.get("matches", []):
        m["day"] = _parse_day(m.get("date"))
    return feed


def load_seasons():
    """Season years that have data. The current season always counts."""
    years = set()
    try:
        with open(SEASONS_INDEX, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            years.update(int(y) for y in data)
    except (OSError, ValueError, TypeError):
        pass
    try:
        with open(CURRENT, encoding="utf-8") as f:
            years.add(int(json.load(f).get("season")))
    except (OSError, ValueError, TypeError):
        pass
    return sorted(years)


def load_feed(season=None):
    """Build the season snapshot. season=None is the current season."""
    paths = [CURRENT] if season is None else [_archive_path(season), CURRENT]
    last_error = None
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            return _hydrate(league.build_feed(path=path))
        except (OSError, ValueError, KeyError) as e:
            last_error = e
    raise FeedUnavailable(
        f"could not read the results file ({last_error})" if last_error
        else "no results file found"
    )


# Convenience accessors used by the UI ------------------------------------- #
def get_standings(feed):
    return feed.get("standings", {"season": "", "conferences": []})


def get_matches(feed):
    return feed.get("matches", [])


def get_win_probabilities(feed, match_id):
    return (feed.get("winprobs") or {}).get(str(match_id))


def generated_at(feed):
    return _parse_day(feed.get("generated_at"))
