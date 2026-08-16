"""
Build a single feed.json snapshot of the league.

Run by the GitHub Action (see .github/workflows/update-data.yml) on a schedule.
GitHub's runners can reach the score feed even though Streamlit Cloud's IPs are
blocked, so the Action fetches here and publishes the result to the `data`
branch; the app then just reads that JSON (see feed.py) — no live calls from
Streamlit, no 403.

Output: ./feed.json
"""

import json
import sys
from datetime import date, datetime, timezone

import espn


def build():
    standings = espn.get_standings()
    # Whole season, so the app can show every match day played this year.
    year = datetime.now(timezone.utc).year
    matches = espn.get_matches(start=date(year, 1, 1), end=date(year, 12, 31))

    # Win probabilities only for fixtures that haven't started yet.
    winprobs = {}
    for m in matches:
        if m["state"] == "pre":
            try:
                wp = espn.get_win_probabilities(m["id"])
            except espn.ESPNError:
                wp = None
            if wp:
                winprobs[m["id"]] = wp

    # datetimes -> ISO strings so the snapshot is plain JSON
    matches_out = []
    for m in matches:
        mm = dict(m)
        mm["start"] = m["start"].isoformat() if m["start"] else None
        matches_out.append(mm)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "season": standings.get("season", ""),
        "standings": standings,
        "matches": matches_out,
        "winprobs": winprobs,
    }


def main():
    feed = build()
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, separators=(",", ":"))
    print(
        f"Wrote feed.json — season {feed['season']}, "
        f"{len(feed['matches'])} matches, {len(feed['winprobs'])} win-prob entries."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # surface a clear failure in the Action log
        print(f"build_feed failed: {e!r}", file=sys.stderr)
        sys.exit(1)
