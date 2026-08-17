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
- **Ask** — type a real question in the search box ("who's most likely to win the
  league?", "who won the last Bellboys match?") and get a written answer, grounded
  in the same live season data the rest of the site shows. Club and match-day
  searches still resolve instantly without asking anything.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Cloud)
1. Push this folder to a public GitHub repo (via GitHub Desktop on Windows).
2. On https://share.streamlit.io create a new app, point it at the repo, and set
   the main file to `app.py`.
3. To switch on the **Ask** tab, add one secret in the app's
   **Settings → Secrets**:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   Everything else works without it — with no key, the Ask tab simply says the
   assistant is switched off.

## How it works
The score feed blocks datacenter IPs (like Streamlit Cloud's), so the app never
calls it directly. Instead:

1. A **GitHub Action** (`.github/workflows/update-data.yml`) runs every ~15 min
   on GitHub's servers, fetches everything, and publishes a `feed.json` to a
   separate **`data` branch**.
2. The **Streamlit app** reads that `feed.json` over `raw.githubusercontent.com`
   (GitHub is always reachable) — no direct feed calls, no 403.

| File | Purpose |
|------|---------|
| `teams.py` | The club map (SHPL names, islands, source IDs, colours). Edit here to change a name or colour. |
| `espn.py`  | Data layer: fetches standings/scoreboard/odds and returns clean, re-branded data. |
| `build_feed.py` | Run by the Action; bundles everything into `feed.json`. |
| `feed.py`  | App-side loader: reads the published `data` branch (with fallbacks). |
| `app.py`   | Streamlit UI: sidebar nav, tables, match cards, win-probability bars. |
| `ask.py`   | The Ask assistant: builds a plain-text season brief from `feed.json`, sends it with the question, and filters the answer on the way back. |
| `.streamlit/config.toml` | Dark theme. |

**One-time setup for the Action to publish:** in the repo on GitHub go to
**Settings → Actions → General → Workflow permissions** and choose
**"Read and write permissions"**, then Save. (If you rename the repo, update
`GH_OWNER`/`GH_REPO` at the top of `feed.py`.)

This is an unofficial, non-commercial fan project.

## Notes / future season changes
- Nothing needs updating between seasons — standings and fixtures come from
  whatever season the feed is currently serving.
- If a club's source ID ever changes, update its `espn_id` in `teams.py`.
- Win probabilities appear only once preview odds are posted (usually a few days
  before kick-off); until then the card shows a "not published yet" note.
