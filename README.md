# St. Helena Premier League

A fan site for the SHPL — twelve clubs playing across the islands of
St. Helena and Ascension.

Live at **https://sthapl.streamlit.app** — deployed on Streamlit Cloud from this repo's `main` branch.

The league is its own competition. It doesn't shadow any other league and it
isn't wired to any outside sports feed: **`season.json` is the league**, and
every table, form guide, projection and playoff bracket on the site is computed
from it.

## The clubs

| St. Helena Division 🇸🇭 | Ascension Division 🇦🇨 |
| --- | --- |
| Rovers Saint Helena | 77 Devils FC |
| Bellboys FC | Georgetown United |
| Harts United | Two Boats United |
| Fugees FC | 77 Angels |
| La Verde FC | Island Boyz |
| STH Young Boys | VC Milan |

Clubs play only inside their own division.

## Publishing results

Everything lives in `season.json`. Add a matchday, or fill in scores on one
that's already there, and the whole site updates — tables, form, club pages,
projections and the bracket.

```jsonc
{
  "n": 5,                          // matchday number
  "division": "St. Helena",        // "St. Helena" or "Ascension"
  "date": "2026-09-06",            // optional; omit or use null if not set yet
  "matches": [
    {"home": "Harts United", "away": "Fugees FC", "hs": 2, "as": 2},
    {"home": "Rovers Saint Helena", "away": "Bellboys FC", "hs": 1, "as": 0,
     "live": true, "minute": "67'"},
    {"home": "La Verde FC", "away": "STH Young Boys", "hs": null, "as": null}
  ]
}
```

* **`hs` / `as`** — home and away score. Both present = the match is final.
* **`null` scores** — an upcoming fixture. It shows on the Upcoming tab with
  the model's win projection.
* **`"live": true`** — in progress. It appears on the Live tab with `minute`
  on the card, and stays out of the table until it's final.
* Club names can be written short (`"Harts"`, `"Rovers"`) — `teams.py` knows
  the aliases. An unknown name fails loudly rather than inventing a club.

Bump `"updated"` when you publish, so the sidebar shows the right date.

### Playoffs

Top five in each division qualify:

```
WILD CARD       #4 v #5           winner takes the last place
SEMI-FINAL 1    #1 v WC winner
SEMI-FINAL 2    #2 v #3
DIVISION FINAL  SF1 winner v SF2 winner
GRAND FINAL     St. Helena champion v Ascension champion
```

Every tie is a single game. Add postseason games to the `"playoffs"` list:

```jsonc
{"round": "Wild Card", "division": "Ascension",
 "home": "Two Boats United", "away": "VC Milan", "hs": 3, "as": 1}
```

Rounds: `Wild Card`, `Semi-Final`, `Division Final`, `Grand Final` (the Grand
Final needs no `division`). The bracket resolves round by round, so a slot is
only named once the tie before it has actually been won. The Playoffs tab
unlocks as soon as a playoff game exists, or when you set
`"playoffs_open": true`.

### Top scorers

The Golden Boot chart is a `"scorers"` list. It shows in full on the Tables page
and as a top three on the Home page, laid out **name → goals → country flag**.

```jsonc
{"name": "Ronan Legg", "goals": 6, "country": "Saint Helena", "code": "SH"}
```

`code` is the two-letter country code; the flag emoji is built from it, so a new
country needs nothing but its code (`TR` → 🇹🇷, `ST` → 🇸🇹). Ranking is automatic,
and players level on goals share a rank and keep the order you entered them in.
Which club a player turns out for isn't published anywhere on the site.

### Friendlies

Matches against clubs from outside the league go in a separate `"friendlies"`
list. They count for **nothing** — no points, no goals, no form, no place in the
table — and they show on **one screen only: that club's own page**, under a
"Friendlies" heading below its league results.

```jsonc
{"club": "Fugees FC", "opponent": "New Stone Town FC", "home": true,
 "cs": 2, "os": 4, "date": null, "note": "Friendly"}
```

`cs` is the SHPL club's score and `os` the opponent's, so there's no home/away
confusion — set `"home": false` if the club travelled. The opponent is just a
name; it needs no entry in `teams.py` and never gets one.

### Archiving a season

Copy `season.json` to `season-<year>.json`, list the year in `seasons.json`,
then clear `season.json` for the new season. A Season picker appears in the
sidebar once more than one season exists.

## Files

| File | What it does |
| --- | --- |
| `season.json` | **The data.** Every result, fixture and playoff game. |
| `teams.py` | The twelve clubs — divisions, colours, name aliases. |
| `league.py` | Turns `season.json` into tables, form and projections. |
| `feed.py` | Loads the current season or an archived one. |
| `bracket.py` | Builds the playoff bracket. |
| `app.py` | The Streamlit site — Home, Tables, Matches, Clubs, Playoffs, Ask. |
| `ask.py` | The Ask assistant (needs `ANTHROPIC_API_KEY`). |
| `facts.py` | Daily soccer / St. Helena facts on the Home page. |

## Projections

Upcoming fixtures show a win / draw / loss projection. It's the site's own
model — points per game and goal difference per game, plus a home-field edge —
not a betting market. Early in a season, with only a few games played, treat it
as a rough read.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
python league.py      # prints both tables in the terminal
```

The Ask tab needs an `ANTHROPIC_API_KEY` in Streamlit secrets. Without one it
says so politely and every other page works as normal.
