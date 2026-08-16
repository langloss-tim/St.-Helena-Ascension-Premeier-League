# ⚽ St. Helena Premier League

A live fan site for a fictional South Atlantic soccer league covering **St. Helena**
and **Ascension**. Every club is a re-brand of a real MLS side, and all data —
standings, live/upcoming/past scores, and win probabilities — is pulled **live**
from ESPN's public MLS feed. As real MLS matches are played and new seasons begin,
the site updates itself.

- **St. Helena** clubs mirror the MLS **Eastern Conference**
- **Ascension** clubs mirror the MLS **Western Conference**

## Features
- **League Tables** — standings for each island, updating with real MLS results
  (P / W / D / L / GD / Pts, top-9 playoff line highlighted).
- **Matches** — Live, Upcoming, and Results tabs with scores and kick-off times
  (shown in St. Helena time).
- **Win %** — for upcoming fixtures, a home / draw / away win probability derived
  from ESPN match-preview betting odds (de-vigged so the three add to 100%).
- **Clubs** — the full SHPL ↔ MLS mapping.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Cloud)
1. Push this folder to a GitHub repo (via GitHub Desktop on Windows).
2. On https://share.streamlit.io create a new app, point it at the repo, and set
   the main file to `app.py`.
3. No secrets or API keys needed — the ESPN feed is public.

## How it works
| File | Purpose |
|------|---------|
| `teams.py` | The 30-club SHPL ↔ MLS mapping (names, islands, ESPN IDs, colours). Edit here if a team name/colour changes. |
| `espn.py`  | Data layer: fetches ESPN standings/scoreboard/odds and returns clean, re-branded dicts. |
| `app.py`   | Streamlit UI: tables, match cards, win-probability bars. |
| `.streamlit/config.toml` | Dark theme. |

Data source: ESPN MLS endpoints (league slug `usa.1`), which require no key.
This is an unofficial, non-commercial fan project.

## Notes / future season changes
- Nothing needs updating between seasons — the standings and fixtures come from
  whatever season ESPN is currently serving.
- If ESPN ever changes a team's internal ID, update its `espn_id` in `teams.py`.
- Win probabilities appear only once a bookmaker posts odds (usually a few days
  before kick-off); until then the card shows a "not published yet" note.
