"""
Match simulator: who is playing, how strong they are, and a minute-by-minute
90' game between them.

Strength is one Elo-style number per side. Nations are listed by hand below
(every FIFA member association plus every Island Games member, with the
United States played as its 48 contiguous states and Canada as North and
South). Clubs come from clubs.json, and a club that isn't in it still plays -- it gets a steady
rating made from its name, so typing the same club twice gives the same side.
"""

import hashlib
import json
import math
import random
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent

# name, flag code, rating   (flag code "" = no flag image for that side)
# Grouped by confederation; 211 FIFA member associations in all.
FIFA = {
    "UEFA": [
        ("Albania", "al", 1620), ("Andorra", "ad", 1050), ("Armenia", "am", 1450),
        ("Austria", "at", 1800), ("Azerbaijan", "az", 1400), ("Belarus", "by", 1450),
        ("Belgium", "be", 1900), ("Bosnia and Herzegovina", "ba", 1600),
        ("Bulgaria", "bg", 1500), ("Croatia", "hr", 1930), ("Cyprus", "cy", 1400),
        ("Czechia", "cz", 1750), ("Denmark", "dk", 1880), ("England", "gb-eng", 2050),
        ("Estonia", "ee", 1350), ("Faroe Islands", "fo", 1300), ("Finland", "fi", 1600),
        ("France", "fr", 2080), ("Georgia", "ge", 1680), ("Germany", "de", 1980),
        ("Gibraltar", "gi", 1000), ("Greece", "gr", 1750), ("Hungary", "hu", 1730),
        ("Iceland", "is", 1600), ("Israel", "il", 1550), ("Italy", "it", 1920),
        ("Kazakhstan", "kz", 1450), ("Kosovo", "xk", 1550), ("Latvia", "lv", 1300),
        ("Liechtenstein", "li", 1000), ("Lithuania", "lt", 1300),
        ("Luxembourg", "lu", 1400), ("Malta", "mt", 1250), ("Moldova", "md", 1250),
        ("Montenegro", "me", 1550), ("Netherlands", "nl", 2000),
        ("North Macedonia", "mk", 1530), ("Northern Ireland", "gb-nir", 1580),
        ("Norway", "no", 1850), ("Poland", "pl", 1720), ("Portugal", "pt", 2020),
        ("Republic of Ireland", "ie", 1650), ("Romania", "ro", 1680),
        ("Russia", "ru", 1700), ("San Marino", "sm", 850), ("Scotland", "gb-sct", 1850),
        ("Serbia", "rs", 1750), ("Slovakia", "sk", 1700), ("Slovenia", "si", 1650),
        ("Spain", "es", 2170), ("Sweden", "se", 1700), ("Switzerland", "ch", 1830),
        ("Turkey", "tr", 1850), ("Ukraine", "ua", 1770), ("Wales", "gb-wls", 1700),
    ],
    "CONMEBOL": [
        ("Argentina", "ar", 2140), ("Bolivia", "bo", 1550), ("Brazil", "br", 2000),
        ("Chile", "cl", 1700), ("Colombia", "co", 1950), ("Ecuador", "ec", 1900),
        ("Paraguay", "py", 1800), ("Peru", "pe", 1700), ("Uruguay", "uy", 1900),
        ("Venezuela", "ve", 1700),
    ],
    "CONCACAF": [
        ("Anguilla", "ai", 800), ("Antigua and Barbuda", "ag", 1100), ("Aruba", "aw", 1050),
        ("Bahamas", "bs", 1300), ("Barbados", "bb", 1450), ("Belize", "bz", 1100),
        ("Bermuda", "bm", 1150), ("British Virgin Islands", "vg", 850),
        ("Canada", "ca", 1800), ("Cayman Islands", "ky", 950), ("Costa Rica", "cr", 1650),
        ("Cuba", "cu", 1250), ("Curaçao", "cw", 1550), ("Dominica", "dm", 1000),
        ("Dominican Republic", "do", 1300), ("El Salvador", "sv", 1450),
        ("Grenada", "gd", 1150), ("Guatemala", "gt", 1500), ("Guyana", "gy", 1250),
        ("Haiti", "ht", 1450), ("Honduras", "hn", 1550), ("Jamaica", "jm", 1600),
        ("Mexico", "mx", 1850), ("Montserrat", "ms", 1000), ("Nicaragua", "ni", 1300),
        ("Panama", "pa", 1720), ("Puerto Rico", "pr", 1150),
        ("Saint Kitts and Nevis", "kn", 1100), ("Saint Lucia", "lc", 1050),
        ("Saint Vincent and the Grenadines", "vc", 1050), ("Suriname", "sr", 1450),
        ("Trinidad and Tobago", "tt", 1450), ("Turks and Caicos Islands", "tc", 800),
        ("United States", "us", 1950), ("US Virgin Islands", "vi", 800),
    ],
    "CAF": [
        ("Algeria", "dz", 1720), ("Angola", "ao", 1550), ("Benin", "bj", 1500),
        ("Botswana", "bw", 1350), ("Burkina Faso", "bf", 1600), ("Burundi", "bi", 1400),
        ("Cameroon", "cm", 1680), ("Cape Verde", "cv", 1600),
        ("Central African Republic", "cf", 1350), ("Chad", "td", 1100),
        ("Comoros", "km", 1450), ("Congo", "cg", 1400), ("DR Congo", "cd", 1700),
        ("Djibouti", "dj", 950), ("Egypt", "eg", 1750), ("Equatorial Guinea", "gq", 1500),
        ("Eritrea", "er", 1000), ("Eswatini", "sz", 1200), ("Ethiopia", "et", 1300),
        ("Gabon", "ga", 1550), ("Gambia", "gm", 1450), ("Ghana", "gh", 1600),
        ("Guinea", "gn", 1550), ("Guinea-Bissau", "gw", 1450), ("Ivory Coast", "ci", 1750),
        ("Kenya", "ke", 1450), ("Lesotho", "ls", 1250), ("Liberia", "lr", 1300),
        ("Libya", "ly", 1450), ("Madagascar", "mg", 1400), ("Malawi", "mw", 1350),
        ("Mali", "ml", 1680), ("Mauritania", "mr", 1450), ("Mauritius", "mu", 1100),
        ("Morocco", "ma", 1950), ("Mozambique", "mz", 1450), ("Namibia", "na", 1400),
        ("Niger", "ne", 1350), ("Nigeria", "ng", 1700), ("Rwanda", "rw", 1350),
        ("São Tomé and Príncipe", "st", 1000), ("Senegal", "sn", 1850),
        ("Seychelles", "sc", 950), ("Sierra Leone", "sl", 1400), ("Somalia", "so", 900),
        ("South Africa", "za", 1650), ("South Sudan", "ss", 1150), ("Sudan", "sd", 1350),
        ("Tanzania", "tz", 1400), ("Togo", "tg", 1400), ("Tunisia", "tn", 1650),
        ("Uganda", "ug", 1450), ("Zambia", "zm", 1500), ("Zimbabwe", "zw", 1400),
    ],
    "AFC": [
        ("Afghanistan", "af", 1150), ("Australia", "au", 1750), ("Bahrain", "bh", 1450),
        ("Bangladesh", "bd", 1050), ("Bhutan", "bt", 850), ("Brunei", "bn", 850),
        ("Cambodia", "kh", 1000), ("China", "cn", 1450), ("Chinese Taipei", "tw", 1050),
        ("Guam", "gu", 850), ("Hong Kong", "hk", 1200), ("India", "in", 1250),
        ("Indonesia", "id", 1400), ("Iran", "ir", 1820), ("Iraq", "iq", 1600),
        ("Japan", "jp", 1950), ("Jordan", "jo", 1620), ("Kuwait", "kw", 1300),
        ("Kyrgyzstan", "kg", 1350), ("Laos", "la", 950), ("Lebanon", "lb", 1350),
        ("Macau", "mo", 750), ("Malaysia", "my", 1300), ("Maldives", "mv", 1000),
        ("Mongolia", "mn", 950), ("Myanmar", "mm", 1100), ("Nepal", "np", 1050),
        ("North Korea", "kp", 1350), ("Oman", "om", 1500), ("Pakistan", "pk", 950),
        ("Palestine", "ps", 1450), ("Philippines", "ph", 1150), ("Qatar", "qa", 1550),
        ("Saudi Arabia", "sa", 1600), ("Singapore", "sg", 1100),
        ("South Korea", "kr", 1820), ("Sri Lanka", "lk", 900), ("Syria", "sy", 1450),
        ("Tajikistan", "tj", 1400), ("Thailand", "th", 1450), ("Timor-Leste", "tl", 850),
        ("Turkmenistan", "tm", 1250), ("United Arab Emirates", "ae", 1550),
        ("Uzbekistan", "uz", 1700), ("Vietnam", "vn", 1400), ("Yemen", "ye", 1200),
    ],
    "OFC": [
        ("American Samoa", "as", 700), ("Cook Islands", "ck", 850), ("Fiji", "fj", 1150),
        ("New Caledonia", "nc", 1250), ("New Zealand", "nz", 1600),
        ("Papua New Guinea", "pg", 1050), ("Samoa", "ws", 800),
        ("Solomon Islands", "sb", 1200), ("Tahiti", "pf", 1100), ("Tonga", "to", 750),
        ("Vanuatu", "vu", 1100),
    ],
}

# Two FIFA members play as smaller sides instead of as one team. The United
# States is its 48 contiguous states (no Alaska or Hawaii) and Canada is North
# and South. Every state has the same rating, the band that plays like about
# 100th in the world (90th-110th). "Georgia (USA)" keeps the state apart from
# the country Georgia.
STATE = 1450
SPLIT = {
    "United States": [
        ("Alabama", "us-al", STATE), ("Arizona", "us-az", STATE), ("Arkansas", "us-ar", STATE),
        ("California", "us-ca", STATE), ("Colorado", "us-co", STATE),
        ("Connecticut", "us-ct", STATE), ("Delaware", "us-de", STATE),
        ("Florida", "us-fl", STATE), ("Georgia (USA)", "us-ga", STATE), ("Idaho", "us-id", STATE),
        ("Illinois", "us-il", STATE), ("Indiana", "us-in", STATE), ("Iowa", "us-ia", STATE),
        ("Kansas", "us-ks", STATE), ("Kentucky", "us-ky", STATE),
        ("Louisiana", "us-la", STATE), ("Maine", "us-me", STATE), ("Maryland", "us-md", STATE),
        ("Massachusetts", "us-ma", STATE), ("Michigan", "us-mi", STATE),
        ("Minnesota", "us-mn", STATE), ("Mississippi", "us-ms", STATE),
        ("Missouri", "us-mo", STATE), ("Montana", "us-mt", STATE),
        ("Nebraska", "us-ne", STATE), ("Nevada", "us-nv", STATE),
        ("New Hampshire", "us-nh", STATE), ("New Jersey", "us-nj", STATE),
        ("New Mexico", "us-nm", STATE), ("New York", "us-ny", STATE),
        ("North Carolina", "us-nc", STATE), ("North Dakota", "us-nd", STATE),
        ("Ohio", "us-oh", STATE), ("Oklahoma", "us-ok", STATE), ("Oregon", "us-or", STATE),
        ("Pennsylvania", "us-pa", STATE), ("Rhode Island", "us-ri", STATE),
        ("South Carolina", "us-sc", STATE), ("South Dakota", "us-sd", STATE),
        ("Tennessee", "us-tn", STATE), ("Texas", "us-tx", STATE), ("Utah", "us-ut", STATE),
        ("Vermont", "us-vt", STATE), ("Virginia", "us-va", STATE),
        ("Washington", "us-wa", STATE), ("West Virginia", "us-wv", STATE),
        ("Wisconsin", "us-wi", STATE), ("Wyoming", "us-wy", STATE),
    ],
    "Canada": [
        ("South Canada", "ca", 1750), ("North Canada", "ca", 1050),
    ],
}

# The 24 Island Games (IIGA) members. Bermuda, Cayman Islands, Faroe Islands
# and Gibraltar are FIFA members too and already appear above.
IIGA = [
    ("Åland", "ax", 1050), ("Alderney", "", 650), ("Bermuda", "bm", 1150),
    ("Cayman Islands", "ky", 950), ("Falkland Islands", "fk", 700),
    ("Faroe Islands", "fo", 1300), ("Frøya", "", 800), ("Gibraltar", "gi", 1000),
    ("Gotland", "", 900), ("Gozo", "", 950), ("Greenland", "gl", 850),
    ("Guernsey", "gg", 1000), ("Hitra", "", 800), ("Isle of Man", "im", 1050),
    ("Isle of Wight", "", 900), ("Jersey", "je", 1000), ("Menorca", "", 950),
    ("Orkney", "", 850), ("Saaremaa", "", 850), ("Sark", "", 450),
    ("Saint Helena", "sh", 1400), ("Shetland", "", 900), ("Western Isles", "", 800),
    ("Ynys Môn", "", 950),
]


def _nations():
    out = {}
    for conf, rows in FIFA.items():
        for name, code, rating in rows:
            for n, c, r in SPLIT.get(name, [(name, code, rating)]):
                out[n] = {"name": n, "code": c, "rating": r, "group": conf}
    for name, code, rating in IIGA:
        if name in out:
            out[name]["group"] += " · IIGA"
        else:
            out[name] = {"name": name, "code": code, "rating": rating, "group": "IIGA"}
    return out


NATIONS = _nations()
assert sum(len(v) for v in FIFA.values()) == 211, "FIFA has 211 member associations"


@lru_cache(maxsize=1)
def clubs():
    """Every club in clubs.json, keyed by name: {name, code, rating}."""
    rows = json.loads((HERE / "clubs.json").read_text(encoding="utf-8"))
    return {n: {"name": n, "code": c, "rating": r} for n, c, r in rows}


def nation_names():
    return sorted(NATIONS, key=str.casefold)


def club_names():
    return list(clubs())


def _name_rating(name):
    """A typed-in club we have no rating for: a fixed number from its name,
    pitched at lower-division level."""
    h = int(hashlib.sha256(name.strip().casefold().encode()).hexdigest()[:8], 16)
    return 1150 + h % 301


def side(name, kind):
    """Look a side up by name (any capitalisation). Unknown clubs still play."""
    name = (name or "").strip()
    table = NATIONS if kind == "nation" else clubs()
    if name in table:
        return table[name]
    folded = {k.casefold(): v for k, v in table.items()}
    if name.casefold() in folded:
        return folded[name.casefold()]
    if kind == "nation":
        return None
    return {"name": name, "code": "", "rating": _name_rating(name)}


def expected_goals(home, away, neutral=False):
    """Average goals each side scores, from the rating gap. 0 gap = 1.35 each;
    every 100 points of gap moves about 30% of goals across."""
    gap = home["rating"] - away["rating"] + (0 if neutral else 65)
    k = 0.0028
    return (min(1.35 * math.exp(k * gap), 6.0),
            min(1.35 * math.exp(-k * gap), 6.0))


def simulate(home, away, neutral=False, seed=None):
    """Play 90 minutes. Returns {"xg": (h, a), "events": [...], "score": [h, a]}.
    Each event: {"min", "side" ("home"/"away"), "type" goal|yellow|red}.
    A red card takes a quarter off that side's scoring for the rest of the game."""
    rng = random.Random(seed)
    xh, xa = expected_goals(home, away, neutral)
    rate = {"home": xh / 90, "away": xa / 90}
    yellows = {"home": 0, "away": 0}
    events, score = [], {"home": 0, "away": 0}
    for minute in range(1, 91):
        for s in ("home", "away"):
            if rng.random() < rate[s]:
                score[s] += 1
                events.append({"min": minute, "side": s, "type": "goal"})
            if rng.random() < 2.0 / 90:
                yellows[s] += 1
                events.append({"min": minute, "side": s, "type": "yellow"})
            if rng.random() < 0.08 / 90:
                rate[s] *= 0.75
                events.append({"min": minute, "side": s, "type": "red"})
    return {"xg": (round(xh, 2), round(xa, 2)), "events": events,
            "score": [score["home"], score["away"]]}
