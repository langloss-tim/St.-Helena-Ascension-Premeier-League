"""
Playoff bracket builder.

The bracket is derived from the current standings (top 9 of each conference) using
the standard playoff format, and any postseason games in the feed are matched to
the bracket by the two teams involved — so it fills itself in as the playoffs are
played, without relying on round labels from the feed.

During the regular season there are no postseason games, so the bracket shows the
*projected* seeding and matchups. Once Decision Day locks the table, those seeds
become final; once games are played, winners advance automatically.

Format (per conference):
  Wild Card:     seed 8 v seed 9              (single game)
  Round One:     1 v WC, 4 v 5, 3 v 6, 2 v 7  (best of 3)
  Semifinals:    (1/WC v 4/5), (3/6 v 2/7)    (single game)
  Conf Final:    the two semifinal winners     (single game)
Then the two conference champions meet in the Cup Final (single game).
"""


def _is_postseason(m):
    slug = (m.get("season_slug") or "regular-season").lower()
    return slug not in ("regular-season", "", "pre-season", "preseason")


def _game_winner(m, team_id):
    """'A' if team_id won, 'B' if lost, 'D' draw/unknown."""
    hs, as_ = m["home"]["score"], m["away"]["score"]
    if hs is None or as_ is None:
        return "D"
    is_home = m["home"]["espn_id"] == team_id
    mine = hs if is_home else as_
    theirs = as_ if is_home else hs
    return "A" if mine > theirs else ("B" if mine < theirs else "D")


def _slot_from_seed(seeds, n):
    row = seeds.get(n)
    if row:
        return {"team": row, "seed": n, "label": row["shpl_name"]}
    return {"team": None, "seed": n, "label": f"Seed {n}"}


def _placeholder(label):
    return {"team": None, "seed": None, "label": label}


def _series(post, slot_a, slot_b, best_of, label):
    """Build one matchup; count wins from postseason games between the two teams."""
    a, b = slot_a, slot_b
    games, awins, bwins = [], 0, 0
    if a["team"] and b["team"]:
        ida, idb = a["team"]["espn_id"], b["team"]["espn_id"]
        for m in post:
            ids = {m["home"]["espn_id"], m["away"]["espn_id"]}
            if {ida, idb} <= ids and m["state"] in ("in", "post"):
                games.append(m)
                w = _game_winner(m, ida)
                if w == "A":
                    awins += 1
                elif w == "B":
                    bwins += 1
    need = 2 if best_of == 3 else 1
    winner = "A" if awins >= need else ("B" if bwins >= need else None)
    return {"a": a, "b": b, "awins": awins, "bwins": bwins,
            "games": games, "best_of": best_of, "winner": winner, "label": label}


def _winner_slot(series, fallback):
    if series["winner"] == "A":
        return series["a"]
    if series["winner"] == "B":
        return series["b"]
    return _placeholder(fallback)


def _build_conference(conf, post):
    table = conf.get("table", [])
    seeds = {i + 1: table[i] for i in range(min(9, len(table)))}

    wc = _series(post, _slot_from_seed(seeds, 8), _slot_from_seed(seeds, 9), 1, "Wild Card")
    r1 = [
        _series(post, _slot_from_seed(seeds, 1), _winner_slot(wc, "Wild Card winner"), 3, "Round One"),
        _series(post, _slot_from_seed(seeds, 4), _slot_from_seed(seeds, 5), 3, "Round One"),
        _series(post, _slot_from_seed(seeds, 3), _slot_from_seed(seeds, 6), 3, "Round One"),
        _series(post, _slot_from_seed(seeds, 2), _slot_from_seed(seeds, 7), 3, "Round One"),
    ]
    sf = [
        _series(post, _winner_slot(r1[0], "R1 winner"), _winner_slot(r1[1], "R1 winner"), 1, "Semifinal"),
        _series(post, _winner_slot(r1[2], "R1 winner"), _winner_slot(r1[3], "R1 winner"), 1, "Semifinal"),
    ]
    cf = _series(post, _winner_slot(sf[0], "Finalist"), _winner_slot(sf[1], "Finalist"), 1, "Conference Final")
    return {"island": conf.get("island", ""), "wc": wc, "r1": r1, "sf": sf, "cf": cf,
            "champion": _winner_slot(cf, "Conference champion")}


def build_bracket(standings, matches):
    post = [m for m in matches if _is_postseason(m)]
    confs = [_build_conference(c, post) for c in standings.get("conferences", [])]

    final = None
    if len(confs) >= 2:
        final = _series(post, confs[0]["champion"], confs[1]["champion"], 1, "Cup Final")

    return {"has_postseason": len(post) > 0, "conferences": confs, "final": final}
