"""
App-side data loader.

Primary source: the `data` branch published by the GitHub Action, read over
raw.githubusercontent.com (GitHub is reachable from Streamlit Cloud; the score
feed itself is not). Falls back to a local feed.json, then to a direct live
fetch — so it also works when running locally.

Everything returned here matches the shape the UI already expects:
  - get_standings()        -> same dict as espn.get_standings()
  - get_matches()          -> list like espn.get_matches(), 'start' as datetime
  - get_win_probabilities(id) -> dict or None
"""

import json
import os
from datetime import datetime

import requests

import espn

# If you rename the GitHub repo, update these two lines (owner / repo).
GH_OWNER = "langloss-tim"
GH_REPO = "St.-Helena-Ascension-Premeier-League"
GH_BRANCH = "data"
_RAW = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{GH_BRANCH}"
FEED_URL = f"{_RAW}/feed.json"
SEASONS_URL = f"{_RAW}/seasons.json"


def _archive_url(season):
    return f"{_RAW}/feed-{season}.json"


_TIMEOUT = 12


class FeedUnavailable(RuntimeError):
    pass


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _hydrate_matches(raw_matches):
    out = []
    for m in raw_matches:
        mm = dict(m)
        mm["start"] = _parse_dt(m.get("start"))
        out.append(mm)
    return out


def load_seasons():
    """Return a sorted list of season years that have an archived feed, or []."""
    try:
        r = requests.get(SEASONS_URL, timeout=_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return sorted({int(x) for x in data})
    except (requests.RequestException, ValueError, TypeError):
        pass
    return []


def load_feed(season=None):
    """Return a season snapshot dict, or raise FeedUnavailable.

    season=None loads the current/live feed. A specific year loads that season's
    archive (falling back to the current feed if the archive is missing).
    Order: published data branch -> local feed.json -> live fetch.
    """
    urls = [FEED_URL] if season is None else [_archive_url(season), FEED_URL]
    for url in urls:
        try:
            r = requests.get(url, timeout=_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except (requests.RequestException, ValueError):
            continue

    # 2) local snapshot (handy for local dev / offline)
    if os.path.exists("feed.json"):
        try:
            with open("feed.json", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            pass

    # 3) last resort: build it live right now (works off a non-blocked network)
    try:
        matches = espn.get_matches()
        winprobs = {}
        for m in matches:
            if m["state"] == "pre":
                wp = espn.get_win_probabilities(m["id"])
                if wp:
                    winprobs[m["id"]] = wp
        standings = espn.get_standings()
        return {
            "generated_at": None,
            "season": standings.get("season", ""),
            "standings": standings,
            "matches": [{**m, "start": m["start"].isoformat() if m["start"] else None} for m in matches],
            "winprobs": winprobs,
        }
    except espn.ESPNError as e:
        raise FeedUnavailable(str(e))


# Convenience accessors used by the UI ------------------------------------- #
def get_standings(feed):
    return feed.get("standings", {"season": "", "conferences": []})


def get_matches(feed):
    return _hydrate_matches(feed.get("matches", []))


def get_win_probabilities(feed, event_id):
    return (feed.get("winprobs") or {}).get(str(event_id))


def generated_at(feed):
    return _parse_dt(feed.get("generated_at"))
