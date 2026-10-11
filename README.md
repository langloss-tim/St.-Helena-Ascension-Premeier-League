# Match Simulator

Any club. Any nation. Ninety minutes.

Live at **https://sthapl.streamlit.app**, deployed on Streamlit Cloud from this repo's `main` branch.

## Simulator

Pick two sides and press **Kick off**. The game plays out from 1' to 90' in
about 90 seconds: goals, yellow and red cards, half time and full time. A
**Skip to full time** button jumps to the end.

- **Clubs:** 3,207 clubs are listed (`clubs.json`). Any other club can be
  typed in by name and it plays too. A club that isn't listed gets a fixed
  rating made from its name, so the same club always plays at the same strength.
- **Nations:** all 211 FIFA member associations, plus every member of the
  International Island Games Association (IIGA).

Each side has one Elo-style rating. The rating gap (plus a home edge, unless
*Neutral venue* is ticked) sets each side's expected goals. Then every minute is
played out at random. A red card cuts that side's scoring for the rest of the
game. All of this is in `sim.py`.

## Leagues

Look up any league's table and matches.

- The 216 leagues and cups in `leagues.json` are live from ESPN's public
  scoreboard: the table, live games, results from the last two weeks and
  fixtures for the next two weeks.
- For any other league, type its name. The site finds that league's newest
  season page on Wikipedia and shows its table, plus the results grid when the
  page has one.

## Files

| File | What it does |
| --- | --- |
| `app.py` | The Streamlit site |
| `sim.py` | Nations, club ratings and the match engine |
| `clubs.json` | `[name, flag code, rating]` for every listed club |
| `leagues.py` | ESPN and Wikipedia lookups |
| `leagues.json` | `[slug, name]` for every ESPN league |
| `flags/` | Vendored flag images. Any other code loads from flagcdn |

Run locally: `pip install -r requirements.txt && streamlit run app.py`
