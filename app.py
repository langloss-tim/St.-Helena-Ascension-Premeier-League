"""
St. Helena Premier League — Streamlit app.

A fan site for a South Atlantic island league: twelve clubs across the
St. Helena and Ascension divisions. The competition is its own — it doesn't
shadow any other league, and it isn't wired to any outside sports feed.

Everything on every page (tables, form, results, fixtures, projections and the
playoff bracket) is computed from season.json by league.py. To publish new
scores, edit season.json.

Run locally:  streamlit run app.py
"""

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import streamlit.components.v1 as components

import bracket
import facts
import feed as datafeed
import teams

# The Ask tab is a bonus, not a load-bearing part of the site. If its module or
# its dependency is unavailable on the server, the tab politely switches itself
# off and every other page carries on exactly as before.
try:
    import ask
    ASK_IMPORT_ERROR = None
except Exception as _e:  # noqa: BLE001 - any import failure must stay non-fatal
    ask = None
    ASK_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"


def ask_ready():
    return ask is not None and ask.available()

st.set_page_config(
    page_title="St. Helena Premier League",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# St. Helena is UTC+0 all year.
# Times shown American-style in US Eastern; a world clock (Home) covers other zones.
LOCAL_TZ = ZoneInfo("America/New_York")

ISLAND_META = {
    teams.ST_HELENA: {"flag": "🇸🇭", "code": "sh", "accent": "#e4572e"},
    teams.ASCENSION: {"flag": "🇦🇨", "code": "ac", "accent": "#3d9be0"},
}


# flagcdn draws the real ensigns: St. Helena comes back with its shield (the
# wirebird and the ship), not a bare Union Jack. lipis/flag-icons was tried
# first and had to be abandoned -- its sh.svg is byte-for-byte the UK flag, so
# the site was flying Britain over the St. Helena Division.
CDN_ROOT = "https://flagcdn.com/w160"

# flagcdn has no AC: Ascension is an exceptionally reserved code rather than a
# full ISO country, so its flag is named outright instead of derived.
FLAG_OVERRIDES = {
    "ac": ("https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/"
           "Flag_of_Ascension_Island.svg/320px-Flag_of_Ascension_Island.svg.png"),
}


def flag_img(code, emoji="", label="", cls="flagimg"):
    """A flag as a drawn image rather than the regional-indicator emoji.
    Windows has no glyphs for those emoji -- it renders them as the two bare
    letters ("SH", "AC"), so the emoji on its own is not a flag on the machines
    this site is actually read on. The emoji stays as the alt text, which is
    what shows if the image cannot be fetched. Derived from the two-letter code
    alone, so a new island or country still needs nothing but its code."""
    code = (code or "").strip().lower()
    if len(code) != 2 or not code.isalpha():
        return emoji
    src = FLAG_OVERRIDES.get(code) or f"{CDN_ROOT}/{code}.png"
    return (f'<img class="{cls}" src="{src}" '
            f'alt="{emoji or label}" title="{label}" loading="lazy">')


def island_img(island, cls="flagimg"):
    """The flag for one of the two islands, ready to drop into markup."""
    meta = ISLAND_META.get(island, {})
    return flag_img(meta.get("code"), meta.get("flag", ""), str(island), cls)


# --------------------------------------------------------------------------- #
# Cached data (one snapshot powers every page)
# --------------------------------------------------------------------------- #
# Short TTL: a live match ticks its minute in season.json while it is being
# played, and a two-minute cache would show a minute that had already gone.
@st.cache_data(ttl=15, show_spinner=False)
def load_feed(season=None):
    return datafeed.load_feed(season)


@st.cache_data(ttl=600, show_spinner=False)
def load_seasons():
    return datafeed.load_seasons()


# Weather ------------------------------------------------------------------- #
WMO = {
    0: ("☀️", "Clear"), 1: ("🌤️", "Mainly clear"), 2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"), 45: ("🌫️", "Fog"), 48: ("🌫️", "Fog"),
    51: ("🌦️", "Light drizzle"), 53: ("🌦️", "Drizzle"), 55: ("🌦️", "Drizzle"),
    56: ("🌦️", "Freezing drizzle"), 57: ("🌦️", "Freezing drizzle"),
    61: ("🌧️", "Light rain"), 63: ("🌧️", "Rain"), 65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Freezing rain"), 67: ("🌧️", "Freezing rain"),
    71: ("🌨️", "Light snow"), 73: ("🌨️", "Snow"), 75: ("🌨️", "Heavy snow"),
    80: ("🌦️", "Showers"), 81: ("🌦️", "Showers"), 82: ("⛈️", "Heavy showers"),
    95: ("⛈️", "Thunderstorm"), 96: ("⛈️", "Thunderstorm"), 99: ("⛈️", "Thunderstorm"),
}
WEATHER_LOCATIONS = [
    ("St. Helena", "🇸🇭", "sh", -15.93, -5.72),
    ("Ascension", "🇦🇨", "ac", -7.93, -14.42),
]


@st.cache_data(ttl=1800, show_spinner=False)
def load_weather():
    out = []
    for name, flag, fcode, lat, lon in WEATHER_LOCATIONS:
        entry = {"name": name, "flag": flag, "fcode": fcode,
                 "temp": None, "code": None, "wind": None, "hum": None}
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": lat, "longitude": lon,
                        "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
                        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph"},
                timeout=8,
            )
            c = r.json()["current"]
            entry.update(temp=round(c["temperature_2m"]), code=int(c["weather_code"]),
                         wind=round(c["wind_speed_10m"]), hum=c.get("relative_humidity_2m"))
        except Exception:
            pass
        out.append(entry)
    return out


# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
CSS = """
<style>
:root{
  --bg:#0e1117; --panel:#161b26; --line:rgba(255,255,255,.09);
  --ink:#eef1f6; --muted:rgba(238,241,246,.55); --accent:#e4572e;
  --font: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
html{ font-size:19px; }   /* scales the whole app up */
html, body, [class*="st-"], .stMarkdown, p, span, div { font-family: var(--font); }

/* Sidebar */
section[data-testid="stSidebar"]{ min-width:290px; }
.side-title{ font-size:1.55rem; font-weight:800; line-height:1.1; margin:.2rem 0 .1rem; }
.side-sub{ font-size:.95rem; color:var(--muted); margin:0 0 .4rem; }
.stRadio label p { font-size:1.2rem !important; font-weight:600; }
button[data-baseweb="tab"]{ font-size:1.15rem !important; font-weight:600 !important; }
.block-container{ padding-top:2rem; max-width:1250px; }

/* Header */
.hero-title{ font-size:3.7rem; font-weight:800; letter-spacing:-1.5px; line-height:1.02; margin:0; }
.hero-sub{ font-size:1.35rem; color:var(--muted); margin:.5rem 0 0; }

/* Section eyebrow */
.eyebrow{ font-size:2rem; font-weight:800; letter-spacing:.1px; margin:.2rem 0 1.1rem;
          display:flex; align-items:center; gap:.7rem; }
.eyebrow .bar{ width:40px; height:5px; border-radius:99px; display:inline-block; }
.hint{ font-size:1.2rem; color:var(--muted); margin:-.2rem 0 1.4rem; }

.dot{ width:17px; height:17px; border-radius:50%; display:inline-block; flex:0 0 auto;
      box-shadow: inset 0 0 0 2px rgba(255,255,255,.22); vertical-align:middle; }

/* Standings table */
.tblwrap{ overflow-x:auto; -webkit-overflow-scrolling:touch; }
.tbl{ width:100%; border-collapse:separate; border-spacing:0; font-size:1.28rem; }
.tbl thead th{ text-transform:uppercase; font-size:.9rem; letter-spacing:.6px;
   color:var(--muted); font-weight:700; padding:.55rem .5rem; border-bottom:1px solid var(--line);
   text-align:center; }
.tbl thead th.l{ text-align:left; }
.tbl td{ padding:.85rem .5rem; border-bottom:1px solid rgba(255,255,255,.05); text-align:center; }
.tbl td.club{ text-align:left; font-weight:600; }
.tbl td.club .dot{ margin-right:.65rem; }
.tbl td.rank{ color:var(--muted); font-variant-numeric:tabular-nums; width:2.6rem; }
.tbl td.pts{ font-weight:800; font-size:1.5rem; color:#fff;
              background:#1c1f25; }
.tbl thead th.pts{ color:#fff; background:#1c1f25; }
/* Pts is pinned to the right edge. Its background MUST stay opaque -- with a
   translucent one the GD/GA cells scroll underneath and bleed through it,
   which reads as a smudged, double-printed column. #1c1f25 is exactly the old
   rgba(255,255,255,.06) already flattened onto --bg, so it looks unchanged. */
.tbl td.pts, .tbl thead th.pts{ position:sticky; right:0; z-index:2;
              box-shadow:-1px 0 0 var(--line); }
.tbl thead th.pts{ z-index:3; }
.legend .scoring{ color:var(--text); font-size:1.1rem; }
.legend .scoring b{ font-weight:800; }
.legend .scoring b.w{ color:#7fe08f; }
.legend .scoring b.d{ color:var(--muted); }
.legend .scoring b.l{ color:#ff9273; }
.tbl tr:hover td{ background:rgba(255,255,255,.03); }
.tbl tr:hover td.pts{ background:#23262c; }
.tbl tr.cutoff td{ border-bottom:2px solid rgba(255,255,255,.22); }
.tbl tr.qual td.rank{ color:#57c66a; font-weight:700; }
.legend{ font-size:1.05rem; color:var(--muted); margin-top:.9rem; }
.legend b{ color:#57c66a; }
.legend b.wc{ color:#f4b942; }
.tbl tr.wildcard td.rank{ color:#f4b942; font-weight:700; }
.tbl td.form{ text-align:left; white-space:nowrap; padding-left:.9rem; }
.tbl td.form .formchip{ width:1.55rem; height:1.55rem; font-size:.8rem; margin-right:.18rem; }
.tbl .tbd{ color:var(--muted); }
/* Side-by-side tables get half the width; shrink the furniture so the columns
   that remain still fit without forcing a scrollbar. */
.tbl.tight{ font-size:1.12rem; }
.tbl.tight thead th{ font-size:.82rem; padding:.5rem .34rem; }
.tbl.tight td{ padding:.7rem .34rem; }
.tbl.tight td.rank{ width:2.2rem; }
.tbl.tight td.pts{ font-size:1.32rem; }
.tbl.tight td.club .dot{ margin-right:.45rem; }
.champline{ margin-top:1rem; font-size:1.3rem; text-align:center;
            border:1px solid rgba(244,200,0,.5); border-radius:14px; padding:.9rem 1rem;
            background:rgba(244,200,0,.07); }

/* Match-day grouping */
.daygroup{ margin-bottom:1.6rem; }
.dayhdr{ display:flex; align-items:baseline; justify-content:space-between; gap:1rem;
   margin:1.4rem 0 .7rem; padding-bottom:.4rem; border-bottom:1px solid var(--line); }
.dayhdr > span:first-child{ font-size:1.35rem; font-weight:700; }
.dayhdr .daycount{ font-size:1rem; color:var(--muted); white-space:nowrap; }

/* Match cards */
.match{ border:1px solid var(--line); border-left-width:6px; border-radius:18px;
   padding:1.2rem 1.5rem; margin-bottom:1rem; background:var(--panel); }
.match .top{ display:flex; justify-content:space-between; align-items:center; margin-bottom:.65rem; }
.mrow{ display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.24rem 0; }
.tname{ display:flex; align-items:center; gap:.8rem; font-size:1.75rem; font-weight:600; }
.tname .dot{ width:20px; height:20px; }
.tname.win{ font-weight:800; }
.tname.lose{ color:var(--muted); }
.score{ font-size:2.2rem; font-weight:800; min-width:2rem; text-align:center;
        font-variant-numeric:tabular-nums; }
.status{ font-size:1.1rem; color:var(--muted); }
.kick{ font-size:1.15rem; color:var(--muted); margin-top:.6rem; }
.live{ color:#fff; background:var(--accent); padding:.22rem .7rem; border-radius:99px;
       font-size:.95rem; font-weight:800; letter-spacing:.4px; }
.match.islive{ border-color:var(--accent); }

/* Win probability bar */
.wp{ margin:.85rem 0 .2rem; }
.wp .bar{ height:15px; border-radius:99px; overflow:hidden; display:flex; }
.wp .bar > div{ height:100%; }
.wp .labels{ display:flex; justify-content:space-between; font-size:1.1rem; margin-top:.5rem; color:var(--ink); }
.wp .labels .mid{ color:var(--muted); }
.wp .note{ font-size:1rem; color:var(--muted); margin-top:.4rem; }

/* Club cards */
.clubgrid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:.9rem; }
.club{ border:1px solid var(--line); border-left-width:6px; border-radius:15px;
   padding:1.1rem 1.25rem; background:var(--panel); font-size:1.45rem; font-weight:600;
   display:flex; align-items:center; gap:.8rem; }

.foot{ color:var(--muted); font-size:1.05rem; margin-top:.5rem; }

/* Home / away tags */
.ha{ font-size:.72rem; font-weight:800; letter-spacing:.5px; padding:.12rem .5rem;
     border-radius:99px; margin-left:.2rem; vertical-align:middle; }
.ha.home{ background:rgba(87,198,106,.18); color:#7fe08f; }
.ha.away{ background:rgba(255,255,255,.08); color:var(--muted); }
.ha.friendly{ background:rgba(124,133,149,.22); color:#c3cad6;
              border:1px solid rgba(255,255,255,.14); }

/* Golden Boot */
.scorers{ border:1px solid var(--line); border-radius:14px; background:var(--panel);
          overflow:hidden; }
.scorer{ display:flex; align-items:center; gap:.75rem; padding:.75rem 1rem;
         border-bottom:1px solid rgba(255,255,255,.05); }
.scorer:last-child{ border-bottom:none; }
.scorer .srank{ min-width:2.1rem; color:var(--muted); font-weight:700;
                font-variant-numeric:tabular-nums; }
.scorer.lead .srank{ color:#f4c800; }
.scorer .sname{ font-size:1.25rem; font-weight:600; white-space:nowrap;
                overflow:hidden; text-overflow:ellipsis; min-width:0; }
.scorer .sgoals{ margin-left:auto; font-size:1.45rem; font-weight:800;
                 font-variant-numeric:tabular-nums; }
.scorer .sgoals small{ font-size:.8rem; font-weight:600; color:var(--muted);
                       margin-left:.3rem; }
/* The flag is an <img>, so it needs a drawn size rather than a font size.
   The span rule is the fallback for a country with no usable code. */
.scorer img.sflag{ width:2.1rem; height:auto; display:block; border-radius:3px;
                   box-shadow:0 0 0 1px rgba(255,255,255,.14); }
.scorer span.sflag{ font-size:1.5rem; line-height:1; min-width:2.1rem;
                    text-align:right; }
.scorer .srank, .scorer .sgoals, .scorer .sflag{ flex:none; }

/* Island/country flags in running text. Sized in em so they track whatever
   type they sit next to, from the small weather label to the club hero. */
.flagimg{ width:1.9em; height:auto; display:inline-block; vertical-align:-.26em;
          border-radius:2px; box-shadow:0 0 0 1px rgba(255,255,255,.14); }

/* Fact of the day (two compact cards side by side) */
.factrow{ display:grid; grid-template-columns:1fr 1fr; gap:.9rem; margin:.3rem 0 1.5rem; }
@media (max-width:800px){ .factrow{ grid-template-columns:1fr; } }
.factcard{ border:1px solid var(--line); border-left:5px solid var(--accent); border-radius:14px;
   padding:.9rem 1.1rem; background:var(--panel); }
.factcard.sh{ border-left-color:#3d9be0; }
.factlabel{ font-size:.82rem; font-weight:800; color:var(--accent); letter-spacing:.4px;
   text-transform:uppercase; margin-bottom:.35rem; }
.factlabel.sh{ color:#3d9be0; }
.facttext{ font-size:1.1rem; font-weight:500; line-height:1.4; }

/* Weather */
.wxrow{ display:grid; grid-template-columns:1fr 1fr; gap:.9rem; margin:.2rem 0 1.4rem; }
@media (max-width:800px){ .wxrow{ grid-template-columns:1fr; } }
.wx{ display:flex; align-items:center; gap:1rem; border:1px solid var(--line); border-radius:14px;
   padding:.9rem 1.2rem; background:var(--panel); }
.wx-emoji{ font-size:2.6rem; line-height:1; }
.wx-loc{ font-size:1.05rem; color:var(--muted); }
.wx-temp{ font-size:2rem; font-weight:800; line-height:1.1; }
.wx-sub{ font-size:.95rem; color:var(--muted); margin-top:.15rem; }

/* Match of the Day */
.motd{ border:1px solid var(--line); border-left:6px solid #f4c800; border-radius:18px;
   padding:1.3rem 1.6rem; background:var(--panel); margin-bottom:1.6rem; }
.motd-label{ font-size:1rem; font-weight:800; color:#f4c800; text-transform:uppercase;
   letter-spacing:.4px; margin-bottom:.6rem; }
.motd-teams{ display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; font-size:2rem; font-weight:800; }
.motd-v{ color:var(--muted); font-weight:600; font-size:1.4rem; margin:0 .3rem; }
.motd-when{ font-size:1.1rem; color:var(--muted); margin:.5rem 0 .2rem; }

/* Leaders */
.leader{ border:1px solid var(--line); border-left-width:6px; border-radius:16px;
   padding:1.1rem 1.3rem; background:var(--panel); }
.leader-isl{ font-size:1.05rem; color:var(--muted); margin-bottom:.4rem; }
.leader-name{ font-size:1.9rem; font-weight:800; display:flex; align-items:center; gap:.6rem; }
.leader-pts{ font-size:1.15rem; color:var(--muted); margin-top:.35rem; }

/* Club buttons */
div[data-testid="stButton"] > button{ font-size:1.25rem !important; font-weight:600 !important;
   padding:.75rem 1rem !important; border-radius:13px !important; }

/* Club detail */
.club-hero{ border:1px solid var(--line); border-left-width:8px; border-radius:18px;
   padding:1.3rem 1.6rem; background:var(--panel); margin:.6rem 0 1.2rem; }
.club-hero-name{ font-size:2.6rem; font-weight:800; display:flex; align-items:center; gap:.7rem; }
.club-hero-isl{ font-size:1.2rem; color:var(--muted); margin-top:.3rem; }

.statrow{ display:flex; flex-wrap:wrap; gap:.7rem; margin-bottom:1.4rem; }
.stat{ flex:1 1 auto; min-width:92px; border:1px solid var(--line); border-radius:14px;
   padding:.85rem 1rem; background:var(--panel); text-align:center; }
.stat .v{ font-size:1.8rem; font-weight:800; line-height:1; }
.stat .k{ font-size:.9rem; color:var(--muted); margin-top:.35rem; }

.formline{ display:flex; align-items:center; gap:.5rem; margin:.2rem 0 1.4rem; }
.formlabel{ font-size:1.1rem; color:var(--muted); margin-right:.3rem; }
.formchip{ display:inline-flex; align-items:center; justify-content:center; width:2rem; height:2rem;
   border-radius:8px; font-weight:800; font-size:1rem; }
.formchip.w{ background:rgba(87,198,106,.22); color:#7fe08f; }
.formchip.d{ background:rgba(255,255,255,.10); color:var(--muted); }
.formchip.l{ background:rgba(228,87,46,.20); color:#ff9273; }

/* Club-perspective match rows */
.cmatch{ display:flex; align-items:center; justify-content:space-between; gap:1rem;
   border:1px solid var(--line); border-left-width:6px; border-radius:14px;
   padding:.9rem 1.2rem; margin-bottom:.7rem; background:var(--panel); }
.cm-left{ display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; }
.cm-when{ font-size:1rem; color:var(--muted); min-width:5.5rem; }
.cm-opp{ font-size:1.4rem; font-weight:600; display:flex; align-items:center; gap:.5rem; }
.cm-right{ display:flex; align-items:center; gap:.7rem; }
.cm-score{ font-size:1.6rem; font-weight:800; font-variant-numeric:tabular-nums; }
.cm-pred{ font-size:1.2rem; font-weight:700; color:var(--accent); }
.cm-pred.muted{ color:var(--muted); font-weight:600; }

/* Playoff bracket */
.brk-cols{ display:flex; gap:1rem; overflow-x:auto; padding-bottom:.8rem; margin-bottom:1.4rem; }
.brk-col{ flex:0 0 auto; min-width:230px; display:flex; flex-direction:column; gap:.7rem; }
.brk-h{ font-size:1rem; font-weight:800; text-transform:uppercase; letter-spacing:.5px;
   color:var(--muted); padding-bottom:.3rem; border-bottom:1px solid var(--line); }
.series{ border:1px solid var(--line); border-radius:13px; background:var(--panel); padding:.7rem .85rem; }
.series.big{ max-width:420px; margin:0 auto; border-color:#f4c800; }
.steam{ display:flex; align-items:center; gap:.5rem; font-size:1.2rem; font-weight:600; padding:.18rem 0; }
.steam .seed{ font-size:.85rem; color:var(--muted); min-width:1.8rem; font-weight:700; }
.steam .swins{ margin-left:auto; font-weight:800; font-variant-numeric:tabular-nums; }
.steam .tbd{ color:var(--muted); font-weight:500; }
.steam.win{ font-weight:800; }
.steam.out{ opacity:.5; }
.smeta{ font-size:.85rem; color:var(--muted); margin-top:.4rem; border-top:1px solid rgba(255,255,255,.05);
   padding-top:.35rem; }
.brk-final{ margin-bottom:1rem; }
.brk-final .steam{ font-size:1.5rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Device sizing — the user picks their device and everything scales to fit.
# --------------------------------------------------------------------------- #
DEVICES = ["🖥️ Desktop", "💻 Laptop", "📟 iPad", "📱 Phone"]
# base font size (px) that all rem-based sizes scale from, and how many columns
# the side-by-side sections (tables, leaders) use.
DEVICE_CFG = {
    "🖥️ Desktop": {"px": 19, "cols": 2},
    "💻 Laptop":  {"px": 15, "cols": 2},
    "📟 iPad":    {"px": 15, "cols": 1},
    "📱 Phone":   {"px": 12, "cols": 1},
}


def apply_device_css(device):
    cfg = DEVICE_CFG.get(device, DEVICE_CFG["💻 Laptop"])
    px = cfg["px"]
    extra = f"<style>html{{font-size:{px}px !important;}}"
    if device in ("📱 Phone", "📟 iPad"):
        extra += ".factrow{grid-template-columns:1fr;}"
        extra += ".block-container{padding-left:.6rem;padding-right:.6rem;}"
    if device == "📱 Phone":
        extra += ".hero-title{font-size:2.3rem;letter-spacing:-.5px;}"
        extra += ".scorer{gap:.5rem;}.scorer img.sflag{width:1.8rem;}"
        extra += ".brk-col{min-width:200px;}"
    extra += "</style>"
    st.markdown(extra, unsafe_allow_html=True)


def device_cols(device):
    return DEVICE_CFG.get(device, DEVICE_CFG["💻 Laptop"])["cols"]


def dot(color):
    return f'<span class="dot" style="background:{color}"></span>'


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
def header(season):
    st.markdown('<p class="hero-title">St.&nbsp;Helena Premier League</p>', unsafe_allow_html=True)
    sub = "St. Helena &amp; Ascension · South Atlantic football"
    if season:
        sub += f" · {season} season"
    st.markdown(f'<p class="hero-sub">{sub}</p>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Tables page
# --------------------------------------------------------------------------- #
def render_standings(standings, ncols=2, device=None):
    # Two tables side by side each get HALF the width, so that is the layout
    # most likely to push Points off the edge -- not the single-column one,
    # which hands the whole width to one table. This test used to be the wrong
    # way round, so the widest column set was rendered in the narrowest box.
    # Points is the column people came to read, so drop the optional columns
    # widest-first (Form, then GF/GA) by how much room there actually is.
    if ncols == 1:
        level = "min" if device == "📱 Phone" else "full"
    else:
        level = "mid"

    def one(conf):
        meta = ISLAND_META.get(conf["island"], {"flag": "", "accent": "#888"})
        st.markdown(
            f'<div class="eyebrow"><span class="bar" style="background:{meta["accent"]}"></span>'
            f'{island_img(conf["island"])} {conf["name"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_standings_html(conf["table"], level=level), unsafe_allow_html=True)

    confs = standings["conferences"]
    if ncols == 1:
        for conf in confs:
            one(conf)
    else:
        cols = st.columns(len(confs), gap="large")
        for col, conf in zip(cols, confs):
            with col:
                one(conf)

def _standings_html(rows, level="full"):
    """The league table. Points is the point of it — it stays on screen at
    every width, and the columns that can be dropped are dropped around it."""
    show_form = level == "full"
    show_gfga = level in ("full", "mid")
    tcls = "tbl" if level == "full" else "tbl tight"

    cols = ['<th class="l">#</th>', '<th class="l">Club</th>',
            "<th>P</th>", "<th>W</th>", "<th>D</th>", "<th>L</th>"]
    if show_gfga:
        cols += ["<th>GF</th>", "<th>GA</th>"]
    cols += ["<th>GD</th>", '<th class="pts">Pts</th>']
    if show_form:
        cols.append('<th class="l">Form</th>')
    head = f'<table class="{tcls}"><thead><tr>' + "".join(cols) + "</tr></thead><tbody>"

    body = []
    for r in rows:
        classes = []
        if r["rank"] <= 3:
            classes.append("qual")
        elif r["rank"] <= 5:
            classes.append("wildcard")
        if r["rank"] == 5:
            classes.append("cutoff")  # last club still alive for the playoffs
        cls = f' class="{" ".join(classes)}"' if classes else ""

        cells = [f'<td class="rank">{r["rank"]}</td>',
                 f'<td class="club">{dot(r["primary"])}{r["name"]}</td>',
                 f'<td>{r["played"]}</td>', f'<td>{r["wins"]}</td>',
                 f'<td>{r["draws"]}</td>', f'<td>{r["losses"]}</td>']
        if show_gfga:
            cells += [f'<td>{r["gf"]}</td>', f'<td>{r["ga"]}</td>']
        cells += [f'<td>{r["gd"]:+d}</td>', f'<td class="pts">{r["points"]}</td>']
        if show_form:
            form = "".join(f'<span class="formchip {o.lower()}">{o}</span>'
                           for o in r.get("form", [])) or '<span class="tbd">–</span>'
            cells.append(f'<td class="form">{form}</td>')
        body.append(f"<tr{cls}>" + "".join(cells) + "</tr>")

    legend = ('<div class="legend">'
              '<span class="scoring"><b class="w">Win 3 pts</b> · '
              '<b class="d">Draw 1 pt</b> · <b class="l">Loss 0 pts</b></span><br>'
              'Ranked on points, then goal difference, then goals scored.<br>'
              '<b>Green</b> = straight into the semi-finals · '
              '<b class="wc">Amber</b> = 4th and 5th meet in the Wild Card game'
              '</div>')
    return '<div class="tblwrap">' + head + "".join(body) + "</tbody></table></div>" + legend

# --------------------------------------------------------------------------- #
# Matches page
# --------------------------------------------------------------------------- #
CLOCK_HTML = r"""
<style>
  body{ margin:0; font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#eef1f6; background:transparent; }
  .clockrow{ display:flex; gap:.6rem; overflow-x:auto; padding-bottom:.3rem; }
  .clk{ flex:0 0 auto; min-width:120px; border:1px solid rgba(255,255,255,.09); border-radius:12px;
        background:#161b26; padding:.6rem .8rem; }
  .clk.sh{ border-left:4px solid #e4572e; }
  .cl-l{ font-size:.8rem; color:#8b93a1; white-space:nowrap; }
  .cl-l span{ background:rgba(255,255,255,.08); padding:.02rem .3rem; border-radius:5px; margin-left:.2rem; }
  .cl-l img.flagimg{ width:1.6em; height:auto; vertical-align:-.25em; border-radius:2px;
                     box-shadow:0 0 0 1px rgba(255,255,255,.14); }
  .cl-t{ font-size:1.3rem; font-weight:800; font-variant-numeric:tabular-nums; margin-top:.15rem; }
</style>
<div class="clockrow" id="clocks"></div>
<script>
  const ZONES = [
    {label:"<img class='flagimg' src='https://flagcdn.com/w160/sh.png' alt='🇸🇭'> St. Helena", tz:"Atlantic/St_Helena", abbr:"GMT", sh:true},
    {label:"Eastern", tz:"America/New_York", abbr:"ET"},
    {label:"Central", tz:"America/Chicago", abbr:"CT"},
    {label:"Mountain", tz:"America/Denver", abbr:"MT"},
    {label:"Pacific", tz:"America/Los_Angeles", abbr:"PT"},
    {label:"Alaska", tz:"America/Anchorage", abbr:"AKT"},
    {label:"Hawaii", tz:"Pacific/Honolulu", abbr:"HT"}
  ];
  function tick(){
    const now = new Date();
    document.getElementById("clocks").innerHTML = ZONES.map(z => {
      const t = now.toLocaleTimeString('en-US', {timeZone:z.tz, hour:'numeric', minute:'2-digit', second:'2-digit'});
      return '<div class="clk'+(z.sh?' sh':'')+'"><div class="cl-l">'+z.label+' <span>'+z.abbr+'</span></div><div class="cl-t">'+t+'</div></div>';
    }).join("");
  }
  tick(); setInterval(tick, 1000);
</script>
"""


def clock_component():
    components.html(CLOCK_HTML, height=110, scrolling=False)


def league_only(matches):
    """Everything except friendlies. Friendlies count for nothing and belong on
    exactly one screen — the club's own page — so every other view filters
    through here."""
    return [m for m in matches if m.get("stage") != "friendly"]


def render_matches(matches, feed):
    matches = league_only(matches)
    focus = st.session_state.get("focus_group")
    if focus:
        group = [m for m in matches if _group_key(m) == focus]
        if st.button("← Show all matches"):
            st.session_state.focus_group = None
            st.rerun()
        st.markdown(f'<div class="eyebrow"><span class="bar" style="background:#e4572e"></span>'
                    f'{_group_label_html(focus)}</div>', unsafe_allow_html=True)
        if group:
            _render_day_groups(group, feed, show_prob=True, newest_first=False)
        else:
            st.info("Nothing scheduled there yet.")
        return

    live = [m for m in matches if m["state"] == "in"]
    upcoming = [m for m in matches if m["state"] == "pre"]
    past = [m for m in matches if m["state"] == "post"]

    tab_live, tab_up, tab_past = st.tabs(
        [f"🔴 Live ({len(live)})", f"📅 Upcoming ({len(upcoming)})", f"✅ Results ({len(past)})"]
    )
    with tab_live:
        if live:
            _render_day_groups(live, feed, show_prob=False, newest_first=False)
        else:
            st.info("No match is being played right now. Kick-offs show up here "
                    "the moment one starts.")
    with tab_up:
        if not upcoming:
            st.info("No fixtures announced yet — they'll appear here as soon as "
                    "the next matchday is set.")
        else:
            st.caption(f"{len(upcoming)} fixtures to come")
            _render_day_groups(upcoming, feed, show_prob=True, newest_first=False)
    with tab_past:
        if not past:
            st.info("No results yet this season.")
        else:
            days = len({_group_key(m) for m in past})
            st.caption(f"{len(past)} matches played across {days} matchdays this season")
            _render_day_groups(past, feed, show_prob=False, newest_first=True)

def _group_key(m):
    """Matches are grouped by matchday, not by calendar date — a matchday is
    how this league is actually scheduled, and fixtures often arrive before a
    date is set."""
    if m.get("stage") == "playoff":
        return f"playoff|{m.get('round') or 'Playoffs'}"
    return f"{m.get('division') or ''}|{m.get('matchday') or 0}"


def _group_sort(key):
    kind, rest = key.split("|", 1)
    if kind == "playoff":
        order = {"Wild Card": 1, "Semi-Final": 2, "Division Final": 3, "Grand Final": 4}
        return (2, order.get(rest, 9), rest)
    try:
        n = int(rest)
    except ValueError:
        n = 0
    return (1, n, kind)


def _group_label(key):
    kind, rest = key.split("|", 1)
    if kind == "playoff":
        return f"🏆 {rest}"
    meta = ISLAND_META.get(kind, {"flag": ""})
    name = teams.DIVISION_NAME.get(kind, kind)
    return f'{meta["flag"]} {name} · Matchday {rest}'


def _group_label_html(key):
    """The same label for the places that render HTML. _group_label itself has
    to stay plain text: it also fills button captions and the search haystack,
    neither of which can render a tag."""
    kind, rest = key.split("|", 1)
    if kind == "playoff":
        return f"🏆 {rest}"
    name = teams.DIVISION_NAME.get(kind, kind)
    return f'{island_img(kind)} {name} · Matchday {rest}'


def _day_label(m):
    """The date under a match card, when one has been set."""
    d = m.get("day")
    if not d:
        return ""
    return f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}, {d.year}"


def _render_day_groups(matches, feed, show_prob, newest_first):
    """Group matches by matchday and render each group in a single call."""
    groups = {}
    for m in matches:
        groups.setdefault(_group_key(m), []).append(m)

    keys = sorted(groups, key=_group_sort, reverse=newest_first)
    for key in keys:
        group = groups[key]
        n = len(group)
        dates = {_day_label(m) for m in group} - {""}
        count = f"{n} {'match' if n == 1 else 'matches'}"
        right = f"{dates.pop()} · {count}" if len(dates) == 1 else count
        header = (f'<div class="dayhdr"><span>{_group_label_html(key)}</span>'
                  f'<span class="daycount">{right}</span></div>')
        cards = "".join(_match_html(m, feed, show_prob) for m in group)
        st.markdown(f'<div class="daygroup">{header}{cards}</div>', unsafe_allow_html=True)

def _short_when(m):
    """Which matchday (or round) a match belongs to — the card's top line."""
    if m.get("stage") == "playoff":
        return m.get("round") or "Playoffs"
    if m.get("matchday"):
        return f"Matchday {m['matchday']}"
    return m.get("division") or ""


def _when_label(m):
    """A short, human line for when a match is / was played."""
    bits = []
    if m.get("stage") == "playoff":
        bits.append(m.get("round") or "Playoffs")
    elif m.get("matchday"):
        bits.append(f"Matchday {m['matchday']}")
    d = _day_label(m)
    if d:
        bits.append(d)
    if m.get("time"):
        bits.append(m["time"])
    return " · ".join(bits) or "Date to be confirmed"

def _is_draw(m):
    hs, as_ = m["home"]["score"], m["away"]["score"]
    return hs is not None and hs == as_


def _match_html(m, feed, show_prob):
    live = m["state"] == "in"
    home, away = m["home"], m["away"]
    show_score = m["state"] in ("in", "post")

    if live:
        top_left = f'<span class="live">● LIVE · {m["status_detail"]}</span>'
    else:
        top_left = f'<span class="status">{_short_when(m)}</span>'
    hosting = f'<span class="status">{home["name"]} hosting</span>'

    def row(side, is_home):
        s = side["score"] if side["score"] is not None else "–"
        score = f'<span class="score">{s}</span>' if show_score else '<span class="score"></span>'
        cls = "tname"
        if show_score and m["completed"]:
            cls += " win" if side.get("winner") else (" lose" if not _is_draw(m) else "")
        tag = '<span class="ha home">HOME</span>' if is_home else '<span class="ha away">AWAY</span>'
        return (f'<div class="mrow"><span class="{cls}">{dot(side["primary"])}{side["name"]}'
                f'{tag}</span>{score}</div>')

    when = _day_label(m) or "Date to be confirmed"
    if m.get("time"):
        when += f' · {m["time"]}'
    kick = "" if show_score else f'<div class="kick">🕓 {when}</div>'
    winbar = _winbar_html(m, feed) if show_prob else ""
    border = f'border-left-color:{home["primary"]};'
    card_cls = "match islive" if live else "match"

    return (f'<div class="{card_cls}" style="{border}">'
            f'<div class="top">{top_left}{hosting}</div>'
            f'{row(home, True)}{row(away, False)}{kick}{winbar}</div>')


def _winbar_html(m, feed):
    wp = datafeed.get_win_probabilities(feed, m["id"])
    if not wp:
        return ""
    h, d, a = wp["home_pct"], wp["draw_pct"], wp["away_pct"]
    hc, ac = m["home"]["primary"], m["away"]["primary"]
    return (
        '<div class="wp"><div class="bar">'
        f'<div style="width:{h}%;background:{hc}"></div>'
        f'<div style="width:{d}%;background:#7c8595"></div>'
        f'<div style="width:{a}%;background:{ac}"></div></div>'
        '<div class="labels">'
        f'<span>{m["home"]["name"]} · {h}%</span>'
        f'<span class="mid">Draw {d}%</span>'
        f'<span>{a}% · {m["away"]["name"]}</span></div>'
        '<div class="note">SHPL model projection · from form so far</div></div>'
    )


# --------------------------------------------------------------------------- #
# Home page
# --------------------------------------------------------------------------- #
def match_of_the_day(feed):
    """Pick a featured upcoming fixture: the most evenly-matched one the model
    can't call, else simply the next one up. Returns (match, projection) or None."""
    up = [m for m in league_only(datafeed.get_matches(feed)) if m["state"] == "pre"]
    if not up:
        return None
    scored = []
    for m in up[:40]:
        wp = datafeed.get_win_probabilities(feed, m["id"])
        if wp:
            scored.append((abs(wp["home_pct"] - wp["away_pct"]), m, wp))
    if scored:
        scored.sort(key=lambda x: x[0])
        return scored[0][1], scored[0][2]
    return up[0], None

def render_scorers(feed, limit=None):
    """The scoring chart. Reads left to right the way it was asked for:
    name, then goals, then the player's flag. The flag is an image rather
    than the regional-indicator emoji, because Windows draws that emoji as the
    bare letters ("SH", "TR") instead of a flag. The emoji is kept as the alt
    text, so it still stands in if the image cannot be fetched."""
    rows = feed.get("scorers") or []
    if not rows:
        return
    st.markdown('<div class="eyebrow"><span class="bar" style="background:#f4c800"></span>'
                '🥇 Golden Boot</div>', unsafe_allow_html=True)
    shown = rows[:limit] if limit else rows
    cards = ""
    for r in shown:
        cls = "scorer lead" if r["rank"] == 1 else "scorer"
        drawn = flag_img(r["code"], r["flag"], r["country"], "sflag")
        flag = (drawn if drawn.startswith("<img")
                else f'<span class="sflag" title="{r["country"]}">{drawn}</span>')
        cards += (f'<div class="{cls}"><span class="srank">{r["rank"]}</span>'
                  f'<span class="sname">{r["name"]}</span>'
                  f'<span class="sgoals">{r["goals"]}<small>goals</small></span>'
                  f'{flag}</div>')
    st.markdown(f'<div class="scorers">{cards}</div>', unsafe_allow_html=True)
    if limit and len(rows) > limit:
        st.caption(f"Top {limit} of {len(rows)} — the full chart is on the Tables page.")


def render_weather():
    cards = ""
    for w in load_weather():
        emoji, desc = WMO.get(w["code"], ("🌡️", "—")) if w["code"] is not None else ("🌡️", "Unavailable")
        temp = f'{w["temp"]}°F' if w["temp"] is not None else "—"
        extra = ""
        if w["temp"] is not None:
            extra = f'<div class="wx-sub">{desc} · 💨 {w["wind"]} mph · 💧 {w["hum"]}%</div>'
        cards += (f'<div class="wx"><div class="wx-emoji">{emoji}</div>'
                  f'<div><div class="wx-loc">{flag_img(w["fcode"], w["flag"], w["name"])} {w["name"]}</div>'
                  f'<div class="wx-temp">{temp}</div>{extra}</div></div>')
    st.markdown(f'<div class="wxrow">{cards}</div>', unsafe_allow_html=True)


def render_home(feed, ncols=2):
    clock_component()
    render_weather()

    day = datetime.now(LOCAL_TZ).timetuple().tm_yday
    st.markdown(
        '<div class="factrow">'
        f'<div class="factcard"><div class="factlabel">⚽ Soccer fact of the day</div>'
        f'<div class="facttext">{facts.soccer_fact(day)}</div></div>'
        f'<div class="factcard sh"><div class="factlabel sh">'
        f'{flag_img("sh", "🇸🇭", "St. Helena")} St. Helena fact of the day</div>'
        f'<div class="facttext">{facts.sthelena_fact(day)}</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    motd = match_of_the_day(feed)
    if motd:
        m, wp = motd
        h, a = m["home"], m["away"]
        bar = ""
        if wp:
            bar = ('<div class="wp"><div class="bar">'
                   f'<div style="width:{wp["home_pct"]}%;background:{h["primary"]}"></div>'
                   f'<div style="width:{wp["draw_pct"]}%;background:#7c8595"></div>'
                   f'<div style="width:{wp["away_pct"]}%;background:{a["primary"]}"></div></div>'
                   '<div class="labels">'
                   f'<span>{h["name"]} · {wp["home_pct"]}%</span>'
                   f'<span class="mid">Draw {wp["draw_pct"]}%</span>'
                   f'<span>{wp["away_pct"]}% · {a["name"]}</span></div></div>')
        st.markdown(
            '<div class="motd"><div class="motd-label">⭐ Match of the Day</div>'
            f'<div class="motd-teams">{dot(h["primary"])}{h["name"]}'
            f'<span class="motd-v">v</span>{dot(a["primary"])}{a["name"]}</div>'
            f'<div class="motd-when">🕓 {_when_label(m)} · {h["name"]} hosting</div>'
            f'{bar}</div>',
            unsafe_allow_html=True,
        )

    standings = datafeed.get_standings(feed)
    if standings["conferences"]:
        st.markdown('<div class="eyebrow"><span class="bar" style="background:#e4572e"></span>'
                    'Island leaders</div>', unsafe_allow_html=True)

        def leader(conf):
            meta = ISLAND_META.get(conf["island"], {"flag": "", "accent": "#888"})
            top = conf["table"][0] if conf["table"] else None
            if top:
                st.markdown(
                    f'<div class="leader" style="border-left-color:{top["primary"]}">'
                    f'<div class="leader-isl">{island_img(conf["island"])} {conf["island"]}</div>'
                    f'<div class="leader-name">{dot(top["primary"])}{top["name"]}</div>'
                    f'<div class="leader-pts">{top["points"]} pts · {top["wins"]}-{top["draws"]}-{top["losses"]}</div>'
                    f'</div>', unsafe_allow_html=True)

        if ncols == 1:
            for conf in standings["conferences"]:
                leader(conf)
        else:
            cols = st.columns(len(standings["conferences"]), gap="large")
            for col, conf in zip(cols, standings["conferences"]):
                with col:
                    leader(conf)

    render_scorers(feed, limit=3)

    # Next few fixtures
    matches = league_only(datafeed.get_matches(feed))
    upcoming = [m for m in matches if m["state"] == "pre"][:5]
    if upcoming:
        st.markdown('<div class="eyebrow"><span class="bar" style="background:#3d9be0"></span>'
                    'Next up</div>', unsafe_allow_html=True)
        html = "".join(_match_html(m, feed, show_prob=False) for m in upcoming)
        st.markdown(html, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Clubs page (grid -> click a club -> detail)
# --------------------------------------------------------------------------- #
def render_clubs(feed):
    st.markdown('<div class="hint">Tap a club to see its season — results, fixtures and predictions.</div>',
                unsafe_allow_html=True)
    for island in teams.ISLANDS:
        meta = ISLAND_META.get(island, {"flag": "", "accent": "#888"})
        st.markdown(
            f'<div class="eyebrow"><span class="bar" style="background:{meta["accent"]}"></span>'
            f'{island_img(island)} {island}</div>',
            unsafe_allow_html=True,
        )
        club_list = [t for t in teams.TEAMS if t.island == island]
        cols = st.columns(3)
        for i, t in enumerate(club_list):
            if cols[i % 3].button(t.name, key=f"club_{t.id}", use_container_width=True):
                st.session_state.selected_club = t.id
                st.rerun()
        st.write("")


def render_club_detail(feed, club_id):
    team = teams.BY_ID.get(str(club_id))
    if not team:
        st.session_state.selected_club = None
        st.rerun()
        return

    if st.button("← Back to all clubs"):
        st.session_state.selected_club = None
        st.rerun()

    meta = ISLAND_META.get(team.island, {"flag": "", "accent": "#888"})
    st.markdown(
        f'<div class="club-hero" style="border-left-color:{team.primary}">'
        f'<div class="club-hero-name">{dot(team.primary)}{team.name}</div>'
        f'<div class="club-hero-isl">{island_img(team.island)} {team.island}</div></div>',
        unsafe_allow_html=True,
    )

    # Standings summary
    standings = datafeed.get_standings(feed)
    row = None
    for conf in standings["conferences"]:
        for r in conf["table"]:
            if r["id"] == str(club_id):
                row = r
                break
    if row:
        stats = [
            (f"#{row['rank']}", f"in {team.island}"), (row["points"], "Points"),
            (row["played"], "Played"), (row["wins"], "Won"),
            (row["draws"], "Drawn"), (row["losses"], "Lost"),
            (f"{row['gd']:+d}", "Goal diff"),
        ]
        cells = "".join(f'<div class="stat"><div class="v">{v}</div><div class="k">{k}</div></div>'
                        for v, k in stats)
        st.markdown(f'<div class="statrow">{cells}</div>', unsafe_allow_html=True)

    # This club's matches
    matches = [m for m in datafeed.get_matches(feed)
               if m["home"]["id"] == str(club_id) or m["away"]["id"] == str(club_id)]
    played = [m for m in matches if m["state"] in ("in", "post")]
    upcoming = [m for m in matches if m["state"] == "pre"]

    # Form is a league record — a friendly never moves it.
    last5 = [m for m in league_only(played) if m["state"] == "post"][-5:]
    if last5:
        chips = "".join(_form_chip(m, club_id) for m in last5)
        st.markdown(f'<div class="formline"><span class="formlabel">Recent form</span>{chips}</div>',
                    unsafe_allow_html=True)

    friendlies = [m for m in played if m.get("stage") == "friendly"]
    tab_res, tab_fix = st.tabs([f"✅ Results ({len(league_only(played))})",
                                f"📅 Fixtures ({len(league_only(upcoming))})"])
    with tab_res:
        league_played = league_only(played)
        if not league_played:
            st.info("No matches played yet.")
        else:
            html = "".join(_club_match_html(m, club_id, feed) for m in reversed(league_played))
            st.markdown(html, unsafe_allow_html=True)
        if friendlies:
            st.markdown('<div class="eyebrow"><span class="bar" style="background:#7c8595"></span>'
                        'Friendlies</div>', unsafe_allow_html=True)
            st.markdown('<div class="hint">Played outside the league. These don\'t count '
                        'towards points, goals, form or the table.</div>',
                        unsafe_allow_html=True)
            html = "".join(_club_match_html(m, club_id, feed) for m in reversed(friendlies))
            st.markdown(html, unsafe_allow_html=True)
    with tab_fix:
        league_up = league_only(upcoming)
        if not league_up:
            st.info("No upcoming fixtures.")
        else:
            html = "".join(_club_match_html(m, club_id, feed) for m in league_up)
            st.markdown(html, unsafe_allow_html=True)


def _outcome(m, club_id):
    """Return 'W'/'D'/'L' for the given club, or None if not decided."""
    if m["home"]["score"] is None or m["away"]["score"] is None:
        return None
    is_home = m["home"]["id"] == str(club_id)
    mine = m["home"]["score"] if is_home else m["away"]["score"]
    theirs = m["away"]["score"] if is_home else m["home"]["score"]
    return "W" if mine > theirs else ("L" if mine < theirs else "D")


def _form_chip(m, club_id):
    o = _outcome(m, club_id) or "–"
    cls = {"W": "w", "D": "d", "L": "l"}.get(o, "")
    return f'<span class="formchip {cls}">{o}</span>'


def _club_match_html(m, club_id, feed):
    is_home = m["home"]["id"] == str(club_id)
    opp = m["away"] if is_home else m["home"]
    ha = '<span class="ha home">HOME</span>' if is_home else '<span class="ha away">AWAY</span>'
    played = m["state"] in ("in", "post")

    if played:
        mine = m["home"]["score"] if is_home else m["away"]["score"]
        theirs = m["away"]["score"] if is_home else m["home"]["score"]
        o = _outcome(m, club_id)
        ocls = {"W": "w", "D": "d", "L": "l"}.get(o, "")
        right = f'<span class="cm-score">{mine} – {theirs}</span><span class="formchip {ocls}">{o or "–"}</span>'
        when = _when_label(m)
    else:
        wp = datafeed.get_win_probabilities(feed, m["id"])
        if wp:
            pct = wp["home_pct"] if is_home else wp["away_pct"]
            right = f'<span class="cm-pred">Win chance {pct:.0f}%</span>'
        else:
            right = '<span class="cm-pred muted">Prediction soon</span>'
        when = _when_label(m)

    prep = "vs" if is_home else "at"
    friendly = ('<span class="ha friendly">FRIENDLY</span>'
                if m.get("stage") == "friendly" else "")
    return (f'<div class="cmatch" style="border-left-color:{opp["primary"]}">'
            f'<div class="cm-left"><span class="cm-when">{when}</span>{ha}{friendly}'
            f'<span class="cm-opp">{prep} {dot(opp["primary"])}{opp["name"]}</span></div>'
            f'<div class="cm-right">{right}</div></div>')


# --------------------------------------------------------------------------- #
# Playoffs bracket
# --------------------------------------------------------------------------- #
def render_playoffs(feed):
    standings = datafeed.get_standings(feed)
    matches = datafeed.get_matches(feed)
    brk = bracket.build_bracket(standings, matches)

    if brk["has_postseason"]:
        st.markdown('<div class="hint">The bracket fills in game by game — each winner '
                    'moves straight into the next round.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="hint">🔮 Projected bracket. Seeding is provisional until the '
                    'league season ends, then it fills in game by game once the playoffs '
                    'begin.<br><b>Wild Card</b> 4th v 5th · the winner takes the last place, '
                    'then <b>1st v Wild Card winner</b> and <b>2nd v 3rd</b>, and those winners '
                    'meet in the Division Final.</div>', unsafe_allow_html=True)

    for div in brk["divisions"]:
        meta = ISLAND_META.get(div["island"], {"flag": "", "accent": "#888"})
        st.markdown(
            f'<div class="eyebrow"><span class="bar" style="background:{meta["accent"]}"></span>'
            f'{meta["flag"]} {div["name"]}</div>', unsafe_allow_html=True)
        cols = (
            ("Wild Card", [div["wc"]]),
            ("Semi-Finals", div["sf"]),
            ("Division Final", [div["df"]]),
        )
        col_html = "".join(
            f'<div class="brk-col"><div class="brk-h">{title}</div>'
            + "".join(_series_html(x) for x in series) + '</div>'
            for title, series in cols
        )
        st.markdown(f'<div class="brk-cols">{col_html}</div>', unsafe_allow_html=True)

    st.markdown('<div class="eyebrow"><span class="bar" style="background:#f4c800"></span>'
                '🏆 Grand Final</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="brk-final">{_series_html(brk["final"], big=True)}</div>',
                unsafe_allow_html=True)
    if brk["champion"]:
        st.markdown(f'<div class="champline">🏆 <b>{brk["champion"]["name"]}</b> '
                    'are champions of the St. Helena Premier League.</div>',
                    unsafe_allow_html=True)

def _series_html(s, big=False):
    game = s.get("game")

    def team_row(slot, is_winner):
        cls = "steam"
        if s["winner"]:
            cls += " win" if is_winner else " out"
        seed = f'<span class="seed">#{slot["seed"]}</span>' if slot.get("seed") else ""
        if slot["team"]:
            name = f'{dot(slot["team"]["primary"])}{slot["label"]}'
        else:
            name = f'<span class="tbd">{slot["label"]}</span>'
        score = ""
        if game and game["completed"]:
            tid = slot["team"]["id"] if slot["team"] else None
            side = game["home"] if game["home"]["id"] == tid else game["away"]
            score = f'<span class="swins">{side["score"]}</span>'
        chk = " ✓" if (s["winner"] and is_winner) else ""
        return f'<div class="{cls}">{seed}{name}{chk}{score}</div>'

    if game and game["completed"]:
        meta = "Full time"
    elif game:
        meta = "In progress"
    else:
        meta = "Single game"

    cls = "series big" if big else "series"
    return (f'<div class="{cls}">'
            f'{team_row(s["a"], s["winner"] == "A")}'
            f'{team_row(s["b"], s["winner"] == "B")}'
            f'<div class="smeta">{meta}</div></div>')

# --------------------------------------------------------------------------- #
# Ask page — answers written from the same season snapshot the site renders
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=900, show_spinner=False)
def league_context(stamp, _feed):
    """The season brief handed to the assistant. Keyed on the feed's own
    timestamp, so it's rebuilt only when new data lands."""
    return ask.build_context(_feed)


SUGGESTED = [
    "Who's most likely to win each division?",
    "How did the last matchday go?",
    "Who won the last time the Bellboys played?",
    "Which club is in the best form right now?",
]


def _connection_test(expanded=False):
    """A button that actually calls the API and reports what came back.

    Every setup failure used to print the same sentence, which made a missing
    key and a rejected key indistinguishable. This says which one it is.
    """
    with st.expander("🔌 Test the connection", expanded=expanded):
        st.caption("Makes one tiny real call and reports exactly what happened. "
                   "Never shows the key itself.")
        if st.button("Run the test", key="ask_diag", use_container_width=True):
            with st.spinner("Calling the API…"):
                ok, headline, detail = ask.diagnose()
            (st.success if ok else st.error)(headline)
            st.code(detail)
            if ok:
                st.caption("Reload the page and the assistant will answer.")
        st.caption("Set the key under **Manage app → Settings → Secrets**:")
        st.code('ANTHROPIC_API_KEY = "sk-ant-..."', language="toml")
        st.caption("Quotes and the = sign matter, and it has to be saved on "
                   "this app — a key added to a different Streamlit app "
                   "doesn't carry over.")


def render_ask(feed):
    st.markdown('<div class="hint">Ask anything about the season — results, form, '
                'the tables, or who&rsquo;s likely to win. Every answer is written '
                'from the league&rsquo;s own live data.</div>', unsafe_allow_html=True)

    if not ask_ready():
        # Show the question anyway, so it doesn't feel like it vanished.
        waiting = st.session_state.get("ask_pending")
        if waiting:
            with st.chat_message("user"):
                st.markdown(waiting)
        if ask is None:
            st.error("💬 The assistant module didn't load on this server. "
                     "Everything else on the site works as usual.")
            st.code(ASK_IMPORT_ERROR or "unknown import error")
            st.write("Check that `anthropic` is listed in `requirements.txt`, "
                     "then reboot the app so it reinstalls.")
            return
        st.warning("💬 No API key is reaching this app yet, so the assistant "
                   "can't start. Everything else on the site works as usual.")
        _connection_test(expanded=True)
        return

    thread = st.session_state.setdefault("ask_thread", [])
    for msg in thread:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not thread:
        st.caption("Not sure where to start?")
        cols = st.columns(2)
        for i, s in enumerate(SUGGESTED):
            if cols[i % 2].button(s, key=f"sug_{i}", use_container_width=True):
                st.session_state.ask_pending = s
                st.rerun()

    # No question cap and no turn cap — the conversation runs as long as the
    # fan wants it to, and every earlier exchange is replayed for context.
    typed = st.chat_input("Ask about the SHPL…")
    question = st.session_state.pop("ask_pending", None) or typed

    if thread and st.button("🧹 Start a new conversation", key="ask_clear"):
        st.session_state.ask_thread = []
        st.session_state.ask_seen = None
        st.rerun()

    # Available even when a key IS loaded — a key that's present but rejected
    # is a different problem from no key at all, and needs the same button.
    _connection_test()

    if not question:
        return

    with st.chat_message("user"):
        st.markdown(question)

    context = league_context(feed.get("generated_at") or "", feed)
    with st.chat_message("assistant"):
        holder = st.empty()
        # Say something immediately — the first words take a few seconds to
        # arrive, and an empty bubble reads as a broken page.
        holder.markdown("_Reading the season data…_")
        text = ""
        try:
            for piece in ask.stream_answer(question, context, thread):
                text += piece
                holder.markdown(ask.scrub(text) + " ▌")
        except ask.AskError as e:
            holder.warning(str(e))
            return
        answer = ask.scrub(text).strip()
        holder.markdown(answer or "_Nothing came back — try asking that again._")

    thread.extend([{"role": "user", "content": question},
                   {"role": "assistant", "content": answer}])
    st.session_state.ask_thread = thread


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
PAGES = ["🏠 Home", "🏆 Tables", "⚽ Matches", "🛡️ Clubs", "🥇 Playoffs", "💬 Ask"]


def nav_items(playoffs_open):
    """Menu order. Playoffs sits at the bottom while it's still locked, and
    jumps to second — right under Home — the day it opens, because that's what
    everyone is there for once the postseason is in sight."""
    rest = [p for p in PAGES if p != "🥇 Playoffs"]
    if playoffs_open:
        return [rest[0], "🥇 Playoffs"] + rest[1:]
    return rest + ["🥇 Playoffs"]


def _playoff_gate(feed):
    """When does the Playoffs tab open? Returns (is_open, note, None).

    It unlocks as soon as a playoff game exists, or the moment `playoffs_open`
    is switched on in season.json — nothing here depends on a calendar."""
    if not feed:
        return (False, None, None)
    if feed.get("has_playoff_games") or feed.get("playoffs_open"):
        return (True, None, None)
    return (False, "when the league season ends", None)

def _search_box(search_feed):
    """Express route: no stops unless the search is genuinely ambiguous.

    A club goes straight to that club, a matchday straight to that matchday,
    and anything else straight to the assistant — all without an intermediate
    button to click. Buttons appear only when the text matches more than one
    thing, where a choice can't be skipped.
    """
    q = st.text_input("🔎 Search or ask", key="q_widget",
                      placeholder="e.g. Bellboys, matchday 3, or who wins the title?",
                      label_visibility="collapsed")
    ql = (q or "").strip()
    if not ql:
        # Clearing the box re-arms the search, so retyping the same thing works.
        st.session_state.search_seen = None
        return
    low = ql.lower()

    club_hits = [t for t in teams.TEAMS if low in t.name.lower()][:6]

    # Matchday search is token-based, so "matchday 3", "md3" and "ascension 3"
    # all land on the right group of fixtures.
    words = low.replace(",", " ").replace("md", "matchday ").split()
    group_hits, seen = [], set()
    for m in (league_only(datafeed.get_matches(search_feed)) if search_feed else []):
        key = _group_key(m)
        if key in seen:
            continue
        haystack = (_group_label(key) + " matchday " + str(m.get("matchday") or "")).lower()
        if all(w in haystack for w in words):
            group_hits.append(key)
            seen.add(key)
    group_hits = group_hits[:6]

    # `search_seen` stops the same text re-firing on every later rerun, which
    # would otherwise drag the user back here as they browse.
    fresh = st.session_state.get("search_seen") != low

    def _go(**state):
        st.session_state.search_seen = low
        for k, v in state.items():
            st.session_state[k] = v
        st.rerun()

    if len(club_hits) + len(group_hits) == 1 and fresh:
        if club_hits:
            _go(selected_club=club_hits[0].id, page="🛡️ Clubs")
        _go(focus_group=group_hits[0], page="⚽ Matches")

    if club_hits or group_hits:
        for t in club_hits:
            if st.button(f"🛡️ {t.name}", key=f"s_{t.id}", use_container_width=True):
                _go(selected_club=t.id, page="🛡️ Clubs")
        for key in group_hits:
            if st.button(f"📅 {_group_label(key)}", key=f"sd_{key}",
                         use_container_width=True):
                _go(focus_group=key, page="⚽ Matches")
        return

    # Not a club and not a matchday — it's a question. Straight to the
    # assistant, which explains itself even when it isn't connected yet.
    if fresh:
        _go(ask_seen=low, ask_pending=ql, page="💬 Ask")
    st.caption("💬 Answered on the Ask tab.")

def sidebar_nav(seasons, playoffs_open, unlock_date, search_feed):
    """Render the sidebar navigation (button menu). Returns (page, season).

    Device and season live in plain session keys ('device' / 'season_year') that
    survive across reruns; the selectboxes just read/write them. (Widget-keyed
    state gets cleared when a nav-button rerun aborts before the widget renders.)
    """
    st.session_state.setdefault("page", "🏠 Home")
    season = None
    with st.sidebar:
        st.markdown('<div class="side-title">⚽ SHPL</div>', unsafe_allow_html=True)
        st.markdown('<div class="side-sub">St. Helena Premier League</div>', unsafe_allow_html=True)
        st.divider()
        _search_box(search_feed)
        st.divider()
        for item in nav_items(playoffs_open):
            locked = (item == "🥇 Playoffs" and not playoffs_open)
            label = "🔒 Playoffs" if locked else item
            active = (st.session_state.page == item)
            if st.button(label, key=f"nav_{item}", use_container_width=True,
                         disabled=locked, type=("primary" if active else "secondary")):
                st.session_state.page = item
                st.rerun()
        if not playoffs_open and unlock_date:
            st.caption(f"🥇 Playoffs open {unlock_date}")

        st.divider()
        dev_default = st.session_state.get("device", "💻 Laptop")
        if dev_default not in DEVICES:
            dev_default = "💻 Laptop"
        st.session_state["device"] = st.selectbox(
            "Device", DEVICES, index=DEVICES.index(dev_default), key="device_widget")

        if len(seasons) > 1:
            current = max(seasons)
            opts = [str(y) for y in sorted(seasons, reverse=True)]
            labels = {str(y): (f"{y}  ·  current" if y == current else str(y)) for y in seasons}
            sea_default = st.session_state.get("season_year", str(current))
            if sea_default not in opts:
                sea_default = str(current)
            choice = st.selectbox("Season", opts, index=opts.index(sea_default),
                                  format_func=lambda y: labels[y], key="season_widget")
            st.session_state["season_year"] = choice
            yr = int(choice)
            season = None if yr == current else yr

        if st.button("🔄 Refresh data", use_container_width=True, key="refresh"):
            st.cache_data.clear()
            st.rerun()
    return st.session_state.page, season


def device_prompt():
    st.markdown('<p class="hero-title">⚽ St.&nbsp;Helena Premier League</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">First — what are you viewing this on? '
                'This sizes everything to fit your screen.</p>', unsafe_allow_html=True)
    st.write("")
    cols = st.columns(len(DEVICES))
    for c, dev in zip(cols, DEVICES):
        if c.button(dev, use_container_width=True, key=f"pick_{dev}"):
            st.session_state.device = dev
            st.rerun()
    st.caption("You can change this any time in the sidebar.")


def main():
    # First visit each session: ask what device they're on, then size to fit.
    if "device" not in st.session_state:
        device_prompt()
        return
    device = st.session_state.device
    apply_device_css(device)
    ncols = device_cols(device)

    seasons = load_seasons()
    current_year = max(seasons) if seasons else None

    # Which season is selected (persisted in a plain session key)?
    sel = st.session_state.get("season_year")
    selected_year = int(sel) if sel is not None else None
    viewing_archive = (selected_year is not None and current_year is not None
                       and selected_year != current_year)

    # Playoff gate is based on the current/live season; archived seasons are
    # always viewable (their playoffs already happened).
    try:
        current_feed = load_feed(None)
    except datafeed.FeedUnavailable:
        current_feed = None
    gate_open, unlock, _start = _playoff_gate(current_feed)
    playoffs_open = gate_open or viewing_archive

    page, season = sidebar_nav(seasons, playoffs_open, unlock, current_feed)

    # Safety: never land on a locked Playoffs page.
    if page == "🥇 Playoffs" and not playoffs_open:
        page = st.session_state.page = "🏠 Home"

    if season is None:
        feed = current_feed
        if feed is None:
            try:
                feed = load_feed(None)
            except datafeed.FeedUnavailable as e:
                st.error(f"Scores are temporarily unavailable: {e}")
    else:
        try:
            feed = load_feed(season)
        except datafeed.FeedUnavailable as e:
            feed = None
            st.error(f"Scores are temporarily unavailable: {e}")

    # Status line in the sidebar (needs the loaded feed).
    gen = datafeed.generated_at(feed) if feed else None
    if season is not None and feed:
        st.sidebar.caption(f"📚 Viewing the {feed.get('season', '')} season (archived)")
    else:
        stamp = f" · updated {gen.strftime('%B')} {gen.day}, {gen.year}" if gen else ""
        st.sidebar.caption(f"📋 Every table, result and projection on this site is "
                           f"built from the league's own results{stamp}.")

    header(feed["season"] if feed else "")

    if season is not None and feed:
        st.info(f"📚 You're viewing the **{feed.get('season', '')}** season (archived). "
                "Switch back to the current season in the sidebar.")
    st.divider()

    if feed is None:
        st.warning("Data could not be loaded right now. Try the Refresh button in the sidebar in a moment.")
        return

    standings = datafeed.get_standings(feed)

    # Leaving a section clears its drill-in state.
    if page != "🛡️ Clubs":
        st.session_state.selected_club = None
    if page != "⚽ Matches":
        st.session_state.focus_group = None

    if page == "🏠 Home":
        render_home(feed, ncols)
    elif page == "🏆 Tables":
        hint = ("Final standings for this archived season." if season is not None
                else "Both divisions, updated as each matchday is played.")
        st.markdown(f'<div class="hint">{hint}</div>', unsafe_allow_html=True)
        if standings["conferences"]:
            render_standings(standings, ncols, device)
        else:
            st.warning("Standings could not be loaded.")
        render_scorers(feed)
    elif page == "⚽ Matches":
        hint = ("Fixtures & results for this archived season." if season is not None
                else "Live, upcoming and completed matches, grouped by matchday.")
        st.markdown(f'<div class="hint">{hint}</div>', unsafe_allow_html=True)
        render_matches(datafeed.get_matches(feed), feed)
    elif page == "🥇 Playoffs":
        render_playoffs(feed)
    elif page == "💬 Ask":
        render_ask(feed)
    else:  # Clubs
        if st.session_state.get("selected_club"):
            render_club_detail(feed, st.session_state.selected_club)
        else:
            render_clubs(feed)

    st.divider()
    st.markdown(
        '<div class="foot">St. Helena Premier League · St. Helena &amp; Ascension divisions · results published by the league.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
