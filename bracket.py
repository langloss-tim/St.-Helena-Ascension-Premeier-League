"""
The SHPL postseason bracket.

Per division (top five qualify):

    WILD CARD      #4  v  #5          -> winner takes the last bracket place
    SEMI-FINAL 1   #1  v  WC winner
    SEMI-FINAL 2   #2  v  #3
    DIVISION FINAL  SF1 winner v SF2 winner

The two division champions then meet in the GRAND FINAL.

Every tie is a single game. Before the postseason starts the bracket is a
projection off the current tables; once games appear in season.json's
"playoffs" list it fills in round by round, resolving each round before the
next so a slot is only named when it is actually decided.
"""

import teams

ROUNDS = ["Wild Card", "Semi-Final", "Division Final", "Grand Final"]


def _slot(row=None, label=None, seed=None):
    if row is not None:
        return {"seed": seed or row.get("rank"), "team": row, "label": row["name"]}
    return {"seed": seed, "team": None, "label": label or "TBD"}


def _series(a, b, round_name, division=None):
    return {
        "round": round_name, "division": division,
        "a": a, "b": b,
        "game": None, "winner": None, "best_of": 1,
        "games": [],
    }


def _ids(series):
    return {
        (series["a"]["team"] or {}).get("id"),
        (series["b"]["team"] or {}).get("id"),
    } - {None}


def _attach(series, games):
    """Give a series its game, if one has been played, and set the winner."""
    want = _ids(series)
    if len(want) != 2 or series["game"] is not None:
        return False
    for g in games:
        if {g["home"]["id"], g["away"]["id"]} != want:
            continue
        if g.get("round") and series["round"] and g["round"] != series["round"]:
            continue
        series["game"] = g
        series["games"] = [g]
        if g["completed"]:
            hs, as_ = g["home"]["score"], g["away"]["score"]
            win_id = g["home"]["id"] if hs > as_ else (g["away"]["id"] if as_ > hs else None)
            if win_id:
                series["winner"] = "A" if (series["a"]["team"] or {}).get("id") == win_id else "B"
        return True
    return False


def _winner_row(series):
    if series["winner"] == "A":
        return series["a"]["team"]
    if series["winner"] == "B":
        return series["b"]["team"]
    return None


def build_bracket(standings, matches):
    games = [m for m in matches if m.get("stage") == "playoff"]
    has_postseason = bool(games)

    divisions = []
    for conf in standings.get("conferences", []):
        table = conf.get("table", [])
        seeds = {i: table[i - 1] for i in range(1, 6) if len(table) >= i}
        div = conf["island"]

        wc = _series(_slot(seeds.get(4), "4th place", 4),
                     _slot(seeds.get(5), "5th place", 5), "Wild Card", div)
        sf1 = _series(_slot(seeds.get(1), "1st place", 1),
                      _slot(None, "Wild Card winner"), "Semi-Final", div)
        sf2 = _series(_slot(seeds.get(2), "2nd place", 2),
                      _slot(seeds.get(3), "3rd place", 3), "Semi-Final", div)
        df = _series(_slot(None, "Semi-Final 1 winner"),
                     _slot(None, "Semi-Final 2 winner"), "Division Final", div)

        # Resolve round by round: a slot fills only once the tie before it is won.
        _attach(wc, games)
        w = _winner_row(wc)
        if w:
            sf1["b"] = _slot(w, seed=wc["a"]["seed"] if wc["winner"] == "A" else wc["b"]["seed"])
        _attach(sf1, games)
        _attach(sf2, games)
        for src, key in ((sf1, "a"), (sf2, "b")):
            w = _winner_row(src)
            if w:
                df[key] = _slot(w, seed=(src["a"]["seed"] if src["winner"] == "A"
                                         else src["b"]["seed"]))
        _attach(df, games)

        divisions.append({
            "island": div,
            "name": conf.get("name", div),
            "wc": wc, "sf": [sf1, sf2], "df": df,
            "champion": _winner_row(df),
        })

    final = _series(_slot(None, "St. Helena champion"),
                    _slot(None, "Ascension champion"), "Grand Final")
    for i, d in enumerate(divisions[:2]):
        if d["champion"]:
            final["a" if i == 0 else "b"] = _slot(d["champion"])
    _attach(final, games)

    return {
        "has_postseason": has_postseason,
        "divisions": divisions,
        "conferences": divisions,   # older name, same data
        "final": final,
        "champion": _winner_row(final),
    }
