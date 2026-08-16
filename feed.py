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
FEED_URL = f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{GH_BRANCH}/feed.json"

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


def load_feed():
    """Return the whole snapshot dict, or raise FeedUnavailable.

    Order: published data branch -> local feed.json -> live fetch.
    """
    # 1) published feed on the data branch
    try:
        r = requests.get(FEED_URL, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except (requests.RequestException, ValueError):
        pass

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
