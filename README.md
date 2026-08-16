# ⚽ St. Helena Premier League

A live fan site for a South Atlantic soccer league covering **St. Helena** and
**Ascension**. Standings, live/upcoming/past scores, and win probabilities are
pulled from a live sports feed and update automatically as matches are played
and new seasons begin.

- **St. Helena** clubs play in the **Eastern Conference**
- **Ascension** clubs play in the **Western Conference**

## Features
- **League Tables** — standings for each island, updating live with real results
  (P / W / D / L / GD / Pts, top-9 playoff line highlighted).
- **Matches** — Live, Upcoming, and Results tabs with scores and kick-off times
  (shown in St. Helena time).
- **Win %** — for upcoming fixtures, a home / draw / away win probability derived
  from pre-match preview odds (normalised so the three add to 100%).
- **Clubs** — the fifteen clubs of each island.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Cloud)
1. Push this folder to a public GitHub repo (via GitHub Desktop on Windows).
2. On https://share.streamlit.io create a new app, point it at the repo, and set
   the main file to `app.py`.
3. No secrets or API keys needed.

## How it works
| File | Purpose |
|------|---------|
| `teams.py` | The club map (SHPL names, islands, source IDs, colours). Edit here to change a name or colour. |
| `espn.py`  | Data layer: fetches standings/scoreboard/odds and returns clean, re-branded data. |
| `app.py`   | Streamlit UI: tables, match cards, win-probability bars. |
| `.streamlit/config.toml` | Dark theme. |

This is an unofficial, non-commercial fan project.

## Notes / future season changes
- Nothing needs updating between seasons — standings and fixtures come from
  whatever season the feed is currently serving.
- If a club's source ID ever changes, update its `espn_id` in `teams.py`.
- Win probabilities appear only once preview odds are posted (usually a few days
  before kick-off); until then the card shows a "not published yet" note.
