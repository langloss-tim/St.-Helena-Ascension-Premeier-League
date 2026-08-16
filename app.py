"""
St. Helena Premier League — Streamlit app.

A fan site for a South Atlantic island league (St. Helena + Ascension). Live
standings, fixtures, scores and win probabilities update in real time.

The underlying club data is fetched from a live sports feed and re-branded via
teams.py. NOTE: the real-world source league is never surfaced anywhere in the
UI — the site stands entirely on its own as the St. Helena Premier League.

Run locally:  streamlit run app.py
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

import bracket
import facts
import feed as datafeed
import teams

st.set_page_config(
    page_title="St. Helena Premier League",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# St. Helena is UTC+0 all year.
LOCAL_TZ = ZoneInfo("Atlantic/St_Helena")

ISLAND_META = {
    teams.ST_HELENA: {"flag": "🇸🇭", "accent": "#e4572e"},
    teams.ASCENSION: {"flag": "🇦🇨", "accent": "#3d9be0"},
}


# --------------------------------------------------------------------------- #
# Cached data (one snapshot powers every page)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=120, show_spinner=False)
def load_feed(season=None):
    return datafeed.load_feed(season)


@st.cache_data(ttl=600, show_spinner=False)
def load_seasons():
    return datafeed.load_seasons()


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
.tbl{ width:100%; border-collapse:collapse; font-size:1.28rem; }
.tbl thead th{ text-transform:uppercase; font-size:.9rem; letter-spacing:.6px;
   color:var(--muted); font-weight:700; padding:.55rem .5rem; border-bottom:1px solid var(--line);
   text-align:center; }
.tbl thead th.l{ text-align:left; }
.tbl td{ padding:.85rem .5rem; border-bottom:1px solid rgba(255,255,255,.05); text-align:center; }
.tbl td.club{ text-align:left; font-weight:600; }
.tbl td.club .dot{ margin-right:.65rem; }
.tbl td.rank{ color:var(--muted); font-variant-numeric:tabular-nums; width:2.6rem; }
.tbl td.pts{ font-weight:800; font-size:1.4rem; }
.tbl tr:hover td{ background:rgba(255,255,255,.03); }
.tbl tr.cutoff td{ border-bottom:2px solid rgba(255,255,255,.22); }
.tbl tr.qual td.rank{ color:#57c66a; font-weight:700; }
.legend{ font-size:1.05rem; color:var(--muted); margin-top:.9rem; }
.legend b{ color:#57c66a; }

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
def render_standings(standings, ncols=2):
    def one(conf):
        meta = ISLAND_META.get(conf["island"], {"flag": "", "accent": "#888"})
        st.markdown(
            f'<div class="eyebrow"><span class="bar" style="background:{meta["accent"]}"></span>'
            f'{meta["flag"]} {conf["island"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_standings_html(conf["table"]), unsafe_allow_html=True)

    confs = standings["conferences"]
    if ncols == 1:
        for conf in confs:
            one(conf)
    else:
        cols = st.columns(len(confs), gap="large")
        for col, conf in zip(cols, confs):
            with col:
                one(conf)


def _standings_html(rows):
    head = (
        '<table class="tbl"><thead><tr>'
        '<th class="l">#</th><th class="l">Club</th>'
        '<th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th><th>Pts</th>'
        '</tr></thead><tbody>'
    )
    body = []
    for r in rows:
        classes = []
        if r["rank"] <= 9:
            classes.append("qual")
        if r["rank"] == 9:
            classes.append("cutoff")  # divider line under the last playoff spot
        cls = f' class="{" ".join(classes)}"' if classes else ""
        body.append(
            f'<tr{cls}>'
            f'<td class="rank">{r["rank"]}</td>'
            f'<td class="club">{dot(r["primary"])}{r["shpl_name"]}</td>'
            f'<td>{r["played"]}</td><td>{r["wins"]}</td><td>{r["draws"]}</td>'
            f'<td>{r["losses"]}</td><td>{r["gd"]:+d}</td>'
            f'<td class="pts">{r["points"]}</td>'
            f'</tr>'
        )
    legend = '<div class="legend"><b>Green</b> = top 9 qualify for the playoffs</div>'
    return '<div class="tblwrap">' + head + "".join(body) + "</tbody></table></div>" + legend


# --------------------------------------------------------------------------- #
# Matches page
# --------------------------------------------------------------------------- #
def render_matches(matches, feed):
    live = [m for m in matches if m["state"] == "in"]
    upcoming = [m for m in matches if m["state"] == "pre"]
    past = [m for m in matches if m["state"] == "post"]

    tab_live, tab_up, tab_past = st.tabs(
        [f"🔴 Live ({len(live)})", f"📅 Upcoming ({len(upcoming)})", f"✅ Results ({len(past)})"]
    )
    with tab_live:
        if not live:
            st.info("No matches are being played right now — check the Upcoming tab for what's next.")
        else:
            _render_day_groups(live, feed, show_prob=False, newest_first=False)
    with tab_up:
        if not upcoming:
            st.info("No upcoming fixtures.")
        else:
            st.caption(f"{len(upcoming)} fixtures remaining this season")
            _render_day_groups(upcoming, feed, show_prob=True, newest_first=False)
    with tab_past:
        if not past:
            st.info("No results yet this season.")
        else:
            days = len({_day_key(m) for m in past})
            st.caption(f"{len(past)} matches played across {days} match days this season")
            _render_day_groups(past, feed, show_prob=False, newest_first=True)


def _day_key(m):
    return m["start"].astimezone(LOCAL_TZ).date() if m["start"] else None


def _day_label(d):
    if d is None:
        return "Date to be confirmed"
    return f"{d.strftime('%A')} · {d.day} {d.strftime('%B %Y')}"


def _render_day_groups(matches, feed, show_prob, newest_first):
    """Group matches by calendar day and render each day in a single call."""
    groups = {}
    for m in matches:
        groups.setdefault(_day_key(m), []).append(m)

    days = sorted((d for d in groups if d is not None), reverse=newest_first)
    if None in groups:  # undated fixtures go last
        days = days + [None]

    for d in days:
        day_matches = groups[d]
        n = len(day_matches)
        header = (f'<div class="dayhdr"><span>{_day_label(d)}</span>'
                  f'<span class="daycount">{n} {"match" if n == 1 else "matches"}</span></div>')
        cards = "".join(_match_html(m, feed, show_prob) for m in day_matches)
        st.markdown(f'<div class="daygroup">{header}{cards}</div>', unsafe_allow_html=True)


def _fmt_kickoff(dt):
    if not dt:
        return "TBD"
    return dt.astimezone(LOCAL_TZ).strftime("%a %d %b · %H:%M")


def _is_draw(m):
    hs, as_ = m["home"]["score"], m["away"]["score"]
    return hs is not None and hs == as_


def _match_html(m, feed, show_prob):
    live = m["state"] == "in"
    home, away = m["home"], m["away"]
    show_score = m["state"] in ("in", "post")

    top_left = (f'<span class="live">● LIVE · {m["status_detail"]}</span>' if live
                else f'<span class="status">{m["status_detail"] or _fmt_kickoff(m["start"])}</span>')
    hosting = f'<span class="status">{home["shpl_name"]} hosting</span>'

    def row(side, is_home):
        s = side["score"] if side["score"] is not None else "–"
        score = f'<span class="score">{s}</span>' if show_score else '<span class="score"></span>'
        cls = "tname"
        if show_score and m["completed"]:
            cls += " win" if side.get("winner") else (" lose" if not _is_draw(m) else "")
        tag = '<span class="ha home">HOME</span>' if is_home else '<span class="ha away">AWAY</span>'
        return (f'<div class="mrow"><span class="{cls}">{dot(side["primary"])}{side["shpl_name"]}'
                f'{tag}</span>{score}</div>')

    kick = "" if show_score else f'<div class="kick">🕓 {_fmt_kickoff(m["start"])}</div>'
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
        f'<span>{m["home"]["shpl_name"]} · {h}%</span>'
        f'<span class="mid">Draw {d}%</span>'
        f'<span>{a}% · {m["away"]["shpl_name"]}</span></div>'
        '<div class="note">Pre-match win probability</div></div>'
    )


# --------------------------------------------------------------------------- #
# Home page
# --------------------------------------------------------------------------- #
def render_home(feed, ncols=2):
    day = datetime.now(LOCAL_TZ).timetuple().tm_yday
    st.markdown(
        '<div class="factrow">'
        f'<div class="factcard"><div class="factlabel">⚽ Soccer fact of the day</div>'
        f'<div class="facttext">{facts.soccer_fact(day)}</div></div>'
        f'<div class="factcard sh"><div class="factlabel sh">🇸🇭 St. Helena fact of the day</div>'
        f'<div class="facttext">{facts.sthelena_fact(day)}</div></div>'
        '</div>',
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
                    f'<div class="leader-isl">{meta["flag"]} {conf["island"]}</div>'
                    f'<div class="leader-name">{dot(top["primary"])}{top["shpl_name"]}</div>'
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

    # Next few fixtures
    matches = datafeed.get_matches(feed)
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
            f'{meta["flag"]} {island}</div>',
            unsafe_allow_html=True,
        )
        club_list = [t for t in teams.TEAMS if t.island == island]
        cols = st.columns(3)
        for i, t in enumerate(club_list):
            if cols[i % 3].button(t.shpl_name, key=f"club_{t.espn_id}", use_container_width=True):
                st.session_state.selected_club = t.espn_id
                st.rerun()
        st.write("")


def render_club_detail(feed, espn_id):
    team = teams.BY_ESPN_ID.get(str(espn_id))
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
        f'<div class="club-hero-name">{dot(team.primary)}{team.shpl_name}</div>'
        f'<div class="club-hero-isl">{meta["flag"]} {team.island}</div></div>',
        unsafe_allow_html=True,
    )

    # Standings summary
    standings = datafeed.get_standings(feed)
    row = None
    for conf in standings["conferences"]:
        for r in conf["table"]:
            if r["espn_id"] == str(espn_id):
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
               if m["home"]["espn_id"] == str(espn_id) or m["away"]["espn_id"] == str(espn_id)]
    played = [m for m in matches if m["state"] in ("in", "post")]
    upcoming = [m for m in matches if m["state"] == "pre"]

    # Form (last 5 completed)
    last5 = [m for m in played if m["state"] == "post"][-5:]
    if last5:
        chips = "".join(_form_chip(m, espn_id) for m in last5)
        st.markdown(f'<div class="formline"><span class="formlabel">Recent form</span>{chips}</div>',
                    unsafe_allow_html=True)

    tab_res, tab_fix = st.tabs([f"✅ Results ({len(played)})", f"📅 Fixtures ({len(upcoming)})"])
    with tab_res:
        if not played:
            st.info("No matches played yet.")
        else:
            html = "".join(_club_match_html(m, espn_id, feed) for m in reversed(played))
            st.markdown(html, unsafe_allow_html=True)
    with tab_fix:
        if not upcoming:
            st.info("No upcoming fixtures.")
        else:
            html = "".join(_club_match_html(m, espn_id, feed) for m in upcoming)
            st.markdown(html, unsafe_allow_html=True)


def _outcome(m, espn_id):
    """Return 'W'/'D'/'L' for the given club, or None if not decided."""
    if m["home"]["score"] is None or m["away"]["score"] is None:
        return None
    is_home = m["home"]["espn_id"] == str(espn_id)
    mine = m["home"]["score"] if is_home else m["away"]["score"]
    theirs = m["away"]["score"] if is_home else m["home"]["score"]
    return "W" if mine > theirs else ("L" if mine < theirs else "D")


def _form_chip(m, espn_id):
    o = _outcome(m, espn_id) or "–"
    cls = {"W": "w", "D": "d", "L": "l"}.get(o, "")
    return f'<span class="formchip {cls}">{o}</span>'


def _club_match_html(m, espn_id, feed):
    is_home = m["home"]["espn_id"] == str(espn_id)
    opp = m["away"] if is_home else m["home"]
    ha = '<span class="ha home">HOME</span>' if is_home else '<span class="ha away">AWAY</span>'
    played = m["state"] in ("in", "post")

    if played:
        mine = m["home"]["score"] if is_home else m["away"]["score"]
        theirs = m["away"]["score"] if is_home else m["home"]["score"]
        o = _outcome(m, espn_id)
        ocls = {"W": "w", "D": "d", "L": "l"}.get(o, "")
        right = f'<span class="cm-score">{mine} – {theirs}</span><span class="formchip {ocls}">{o or "–"}</span>'
        when = _fmt_kickoff(m["start"]).split(" · ")[0]
    else:
        wp = datafeed.get_win_probabilities(feed, m["id"])
        if wp:
            pct = wp["home_pct"] if is_home else wp["away_pct"]
            right = f'<span class="cm-pred">Win chance {pct:.0f}%</span>'
        else:
            right = '<span class="cm-pred muted">Prediction soon</span>'
        when = _fmt_kickoff(m["start"])

    prep = "vs" if is_home else "at"
    return (f'<div class="cmatch" style="border-left-color:{opp["primary"]}">'
            f'<div class="cm-left"><span class="cm-when">{when}</span>{ha}'
            f'<span class="cm-opp">{prep} {dot(opp["primary"])}{opp["shpl_name"]}</span></div>'
            f'<div class="cm-right">{right}</div></div>')


# --------------------------------------------------------------------------- #
# Playoffs bracket
# --------------------------------------------------------------------------- #
def render_playoffs(feed):
    standings = datafeed.get_standings(feed)
    matches = datafeed.get_matches(feed)
    brk = bracket.build_bracket(standings, matches)

    if brk["has_postseason"]:
        st.markdown('<div class="hint">The bracket updates automatically as playoff games are played — '
                    'winners advance to the next round.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="hint">🔮 Projected bracket. Seeding is provisional until the end of the '
                    'regular season, then fills in game-by-game once the playoffs begin.</div>',
                    unsafe_allow_html=True)

    for conf in brk["conferences"]:
        meta = ISLAND_META.get(conf["island"], {"flag": "", "accent": "#888"})
        st.markdown(
            f'<div class="eyebrow"><span class="bar" style="background:{meta["accent"]}"></span>'
            f'{meta["flag"]} {conf["island"]}</div>', unsafe_allow_html=True)
        cols = (
            ('Wild Card', [conf["wc"]]),
            ('Round One', conf["r1"]),
            ('Semifinals', conf["sf"]),
            ('Conference Final', [conf["cf"]]),
        )
        col_html = "".join(
            f'<div class="brk-col"><div class="brk-h">{title}</div>'
            + "".join(_series_html(s) for s in series) + '</div>'
            for title, series in cols
        )
        st.markdown(f'<div class="brk-cols">{col_html}</div>', unsafe_allow_html=True)

    if brk["final"]:
        st.markdown('<div class="eyebrow"><span class="bar" style="background:#f4c800"></span>'
                    '🏆 Cup Final</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="brk-final">{_series_html(brk["final"], big=True)}</div>',
                    unsafe_allow_html=True)


def _series_html(s, big=False):
    def team_row(slot, is_winner, wins):
        cls = "steam"
        if s["winner"]:
            cls += " win" if is_winner else " out"
        seed = f'<span class="seed">#{slot["seed"]}</span>' if slot.get("seed") else ""
        if slot["team"]:
            name = f'{dot(slot["team"]["primary"])}{slot["label"]}'
        else:
            name = f'<span class="tbd">{slot["label"]}</span>'
        w = f'<span class="swins">{wins}</span>' if (s["best_of"] == 3 and s["games"]) else ""
        chk = ' ✓' if (s["winner"] and is_winner) else ""
        return f'<div class="{cls}">{seed}{name}{chk}{w}</div>'

    if s["best_of"] == 3:
        meta = f'Best of 3 · {s["awins"]}–{s["bwins"]}' if s["games"] else 'Best of 3'
    else:
        if s["games"]:
            g = s["games"][-1]
            meta = f'{g["home"]["score"]}–{g["away"]["score"]}'
        else:
            meta = 'Single game'

    cls = "series big" if big else "series"
    return (f'<div class="{cls}">'
            f'{team_row(s["a"], s["winner"] == "A", s["awins"])}'
            f'{team_row(s["b"], s["winner"] == "B", s["bwins"])}'
            f'<div class="smeta">{meta}</div></div>')


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
NAV_ITEMS = ["🏠 Home", "🏆 Tables", "⚽ Matches", "🛡️ Clubs", "🥇 Playoffs"]


def _playoff_gate(feed):
    """When should the Playoffs tab open? Returns (is_open, unlock_date, start_date).

    Opens ~21 days before the playoffs start. The start is the first postseason
    game once ESPN schedules them, otherwise estimated a few days after the last
    regular-season game (Decision Day)."""
    if not feed:
        return (False, None, None)
    matches = datafeed.get_matches(feed)
    today = datetime.now(LOCAL_TZ).date()

    post = [m["start"] for m in matches
            if (m.get("season_slug") or "regular-season") not in
            ("regular-season", "", "pre-season", "preseason") and m["start"]]
    if post:
        start = min(post).astimezone(LOCAL_TZ).date()
    else:
        reg = [m["start"] for m in matches if m["start"]]
        if not reg:
            return (False, None, None)
        start = max(reg).astimezone(LOCAL_TZ).date() + timedelta(days=5)

    unlock = start - timedelta(days=21)
    return (today >= unlock, unlock, start)


def sidebar_nav(seasons, playoffs_open, unlock_date):
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
        for item in NAV_ITEMS:
            locked = (item == "🥇 Playoffs" and not playoffs_open)
            label = "🔒 Playoffs" if locked else item
            active = (st.session_state.page == item)
            if st.button(label, key=f"nav_{item}", use_container_width=True,
                         disabled=locked, type=("primary" if active else "secondary")):
                st.session_state.page = item
                st.rerun()
        if not playoffs_open and unlock_date:
            st.caption(f"🥇 Playoffs open ~{unlock_date.strftime('%d %b')}")

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

    page, season = sidebar_nav(seasons, playoffs_open, unlock)

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
    elif gen:
        st.sidebar.caption(f"Scores updated\n\n**{gen.astimezone(LOCAL_TZ).strftime('%a %d %b · %H:%M')}** (St. Helena time)")
    else:
        st.sidebar.caption(f"Loaded {datetime.now(LOCAL_TZ).strftime('%d %b · %H:%M')}")

    header(feed["season"] if feed else "")

    if season is not None and feed:
        st.info(f"📚 You're viewing the **{feed.get('season', '')}** season (archived). "
                "Switch back to the current season in the sidebar.")
    st.divider()

    if feed is None:
        st.warning("Data could not be loaded right now. Try the Refresh button in the sidebar in a moment.")
        return

    standings = datafeed.get_standings(feed)

    # Leaving the Clubs section clears any drilled-in club.
    if page != "🛡️ Clubs":
        st.session_state.selected_club = None

    if page == "🏠 Home":
        render_home(feed, ncols)
    elif page == "🏆 Tables":
        st.markdown('<div class="hint">Standings for each island, updating as results come in.</div>',
                    unsafe_allow_html=True)
        if standings["conferences"]:
            render_standings(standings, ncols)
        else:
            st.warning("Standings could not be loaded. Try the Refresh button.")
    elif page == "⚽ Matches":
        st.markdown('<div class="hint">Live, upcoming and recent fixtures — times shown in St. Helena time.</div>',
                    unsafe_allow_html=True)
        render_matches(datafeed.get_matches(feed), feed)
    elif page == "🥇 Playoffs":
        render_playoffs(feed)
    else:  # Clubs
        if st.session_state.get("selected_club"):
            render_club_detail(feed, st.session_state.selected_club)
        else:
            render_clubs(feed)

    st.divider()
    st.markdown(
        '<div class="foot">St. Helena Premier League · an unofficial fan project · scores update automatically.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
