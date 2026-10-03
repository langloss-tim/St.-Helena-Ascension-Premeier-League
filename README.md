# Curaçao Promé Divishon

A fan site for the Curaçao Promé Divishon — ten clubs in one table.

Live at **https://sthapl.streamlit.app** — deployed on Streamlit Cloud from this repo's `main` branch.

The league is its own competition. It isn't wired to any outside sports feed:
**`season.json` is the league**, and every table, form guide, projection and
playoff bracket on the site is computed from it.

## The clubs

| | |
| --- | --- |
| Weymouth Wales FC | Fitts Village FC |
| Bagetelle FC | Green United |
| Britton's Hill United | Blackspurs FC |
| Ellerton FC | Atlas United |
| Wotton FC | Kings Park Rangers FC |
| St. Andrew's Lions FC | Spartens FC |

## Publishing results

Everything lives in `season.json`. Add a matchday, or fill in scores on one
that's already there, and the whole site updates — tables, form, club pages,
projections and the bracket.

```jsonc
{
  "n": 5,                          // matchday number
  "date": null,                    // optional; omit or use null if not set yet
  "matches": [
    {"home": "Weymouth Wales FC", "away": "Green United", "hs": 2, "as": 2},
    {"home": "Wotton FC", "away": "Atlas United", "hs": 1, "as": 0,
     "live": true, "minute": "67'"},
    {"home": "Ellerton FC", "away": "Spartens FC", "hs": null, "as": null}
  ]
}
```

* **`hs` / `as`** — home and away score. Both present = the match is final.
* **`null` scores** — an upcoming fixture. It shows on the Upcoming tab with
  the model's win projection.
* **`"live": true`** — in progress. It appears on the Live tab with `minute`
  on the card, and stays out of the table until it's final.
* Club names can be written short (`"Weymouth"`, `"Lions"`) — `teams.py` knows
  the aliases. An unknown name fails loudly rather than inventing a club.

Bump `"updated"` when you publish, so the sidebar shows the right date.

### Playoffs

The top four qualify:

```
SEMI-FINAL 1    #1 v #4
SEMI-FINAL 2    #2 v #3
FINAL           SF1 winner v SF2 winner
```

Every tie is a single game. Add postseason games to the `"playoffs"` list:

```jsonc
{"round": "Semi-Final", "home": "Green United", "away": "Atlas United", "hs": 3, "as": 1}
```

Rounds: `Semi-Final`, `Final`. The bracket resolves round by round, so a slot
is only named once the tie before it has actually been won. The Playoffs tab
unlocks as soon as a playoff game exists, or when you set
`"playoffs_open": true`.

### Top scorers

The Golden Boot chart is a `"scorers"` list. It shows in full on the Tables page
and as a top three on the Home page, laid out **name → goals → country flag**.

```jsonc
{"name": "Player Name", "goals": 6, "country": "Curaçao", "code": "CW"}
```

`code` is the two-letter country code; the flag emoji is built from it, so a new
country needs nothing but its code (`TR` → 🇹🇷, `ST` → 🇸🇹). Ranking is automatic,
and players level on goals share a rank and keep the order you entered them in.
Which club a player turns out for isn't published anywhere on the site.

### Matches outside the league

Matches against clubs from outside the league — a friendly, a cup tie, a
continental qualifier — go in a separate `"outside"` list. Each one names its
own `competition`, so a CAF tie is badged as a CAF tie and never as a friendly.
They count for **nothing** — no points, no goals, no form, no place in the
table — and they show on **one screen only: that club's own page**, under an
"Outside the league" heading below its league results.

(The older `"friendlies"` list is still read, so an archived season keeps
working.)

```jsonc
{"club": "Weymouth Wales FC", "opponent": "Opponent FC",
 "competition": "CAF Champions League Qualifier",  // headline on the club page
 "badge": "CAF",                                   // short chip beside HOME/AWAY
 "leg": "Second leg",                              // optional
 "home": false, "cs": 1, "os": 1,
 // "pens": {"cs": 3, "os": 2},                    // optional: settles a level
 //                                                // tie, and the club page
 //                                                // then reads W, not D
 "date": null, "note": "Weymouth Wales through 3-1 on aggregate"}
```

`cs` is the league club's score and `os` the opponent's, so there's no home/away
confusion — set `"home": false` if the club travelled. The opponent is just a
name; it needs no entry in `teams.py` and never gets one.

### National team

The **National Team** page reads `national.json` — the Curaçao men's
national team: the squad (`pos` is GK, DF, MF or FW) and every senior game since
January 2026. It is separate from the league: nothing in it touches the tables,
form or projections. A score is always Curaçao first (`gf`) and the opponent
second (`ga`), with `"home": true/false` for the venue (add `"neutral": true`
for a game at a neutral ground) and a `competition` label; leave both scores
`null` for a game still to be played, and add `"reds": 1` for a Curaçao
sending-off. Each player has `stats` for 2026: `saves` (goalkeepers), `goals`,
`assists`, `yellows`, `reds` — `null` (not confirmed) shows as a dash.
Tap a player on the Players screen to see them. `python national.py` checks the file.

### Archiving a season

Copy `season.json` to `season-<year>.json`, list the year in `seasons.json`,
then clear `season.json` for the new season. A Season picker appears in the
sidebar once more than one season exists.

## Files

| File | What it does |
| --- | --- |
| `season.json` | **The data.** Every result, fixture and playoff game. |
| `teams.py` | The ten clubs — colours, name aliases. |
| `league.py` | Turns `season.json` into tables, form and projections. |
| `feed.py` | Loads the current season or an archived one. |
| `bracket.py` | Builds the playoff bracket. |
| `national.json` / `national.py` | The national team's squad and games. |
| `app.py` | The Streamlit site — Home, Tables, Matches, Clubs, National Team, Playoffs. |
| `facts.py` | Daily soccer / Curaçao facts on the Home page. |

## Projections

Upcoming fixtures show a win / draw / loss projection. It's the site's own
model — points per game and goal difference per game, plus a home-field edge —
not a betting market. Early in a season, with only a few games played, treat it
as a rough read.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
python league.py      # prints the table in the terminal
```
