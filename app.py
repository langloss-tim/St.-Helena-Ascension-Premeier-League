"""
St. Helena Premier League — Streamlit app.

A fan site for a South Atlantic island league (St. Helena + Ascension). Live
standings, fixtures, scores and win probabilities update in real time.

The underlying club data is fetched from a live sports feed and re-branded via
teams.py. NOTE: the real-world source league is never surfaced anywhere in the
UI — the site stands entirely on its own as the St. Helena Premier League.

Run locally:  streamlit run app.py
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

import espn
import teams

st.set_page_config(
    page_title="St. Helena Premier League",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# St. Helena is UTC+0 all year.
LOCAL_TZ = ZoneInfo("Atlantic/St_Helena")

ISLAND_META = {
    teams.ST_HELENA: {"flag": "🇸🇭", "accent": "#e4572e"},
    teams.ASCENSION: {"flag": "🇦🇨", "accent": "#3d9be0"},
}


# --------------------------------------------------------------------------- #
# Cached data fetchers
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=300, show_spinner=False)
def load_standings():
    return espn.get_standings()


@st.cache_data(ttl=60, show_spinner=False)
def load_matches(days_back=10, days_ahead=21):
    return espn.get_matches(days_back=days_back, days_ahead=days_ahead)


@st.cache_data(ttl=600, show_spinner=False)
def load_win_prob(event_id):
    return espn.get_win_probabilities(event_id)


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
html, body, [class*="st-"], .stMarkdown, p, span, div { font-family: var(--font); }

/* nudge Streamlit's native controls up in size */
.stRadio label p { font-size: 1.08rem !important; }
button[data-baseweb="tab"]{ font-size:1.06rem !important; font-weight:600 !important; }
.block-container{ padding-top:2.2rem; max-width:1150px; }

/* Header */
.hero-title{ font-size:3rem; font-weight:800; letter-spacing:-1px; line-height:1.05; margin:0; }
.hero-sub{ font-size:1.15rem; color:var(--muted); margin:.45rem 0 0; }

/* Section eyebrow */
.eyebrow{ font-size:1.5rem; font-weight:800; letter-spacing:.2px; margin:.2rem 0 1rem;
          display:flex; align-items:center; gap:.6rem; }
.eyebrow .bar{ width:34px; height:4px; border-radius:99px; display:inline-block; }
.hint{ font-size:1rem; color:var(--muted); margin:-.4rem 0 1.2rem; }

.dot{ width:15px; height:15px; border-radius:50%; display:inline-block; flex:0 0 auto;
      box-shadow: inset 0 0 0 2px rgba(255,255,255,.22); vertical-align:middle; }

/* Standings table */
.tbl{ width:100%; border-collapse:collapse; font-size:1.08rem; }
.tbl thead th{ text-transform:uppercase; font-size:.78rem; letter-spacing:.6px;
   color:var(--muted); font-weight:700; padding:.5rem .5rem; border-bottom:1px solid var(--line);
   text-align:center; }
.tbl thead th.l{ text-align:left; }
.tbl td{ padding:.72rem .5rem; border-bottom:1px solid rgba(255,255,255,.05); text-align:center; }
.tbl td.club{ text-align:left; font-weight:600; }
.tbl td.club .dot{ margin-right:.6rem; }
.tbl td.rank{ color:var(--muted); font-variant-numeric:tabular-nums; width:2.4rem; }
.tbl td.pts{ font-weight:800; font-size:1.15rem; }
.tbl tr:hover td{ background:rgba(255,255,255,.03); }
.tbl tr.cutoff td{ border-bottom:2px solid rgba(255,255,255,.22); }
.tbl tr.qual td.rank{ color:#57c66a; font-weight:700; }
.legend{ font-size:.92rem; color:var(--muted); margin-top:.7rem; }
.legend b{ color:#57c66a; }

/* Match cards */
.match{ border:1px solid var(--line); border-left-width:5px; border-radius:16px;
   padding:1.05rem 1.25rem; margin-bottom:.9rem; background:var(--panel); }
.match .top{ display:flex; justify-content:space-between; align-items:center; margin-bottom:.55rem; }
.mrow{ display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.18rem 0; }
.tname{ display:flex; align-items:center; gap:.7rem; font-size:1.35rem; font-weight:600; }
.tname .dot{ width:17px; height:17px; }
.tname.win{ font-weight:800; }
.tname.lose{ color:var(--muted); }
.score{ font-size:1.7rem; font-weight:800; min-width:1.8rem; text-align:center;
        font-variant-numeric:tabular-nums; }
.status{ font-size:.98rem; color:var(--muted); }
.kick{ font-size:1rem; color:var(--muted); margin-top:.5rem; }
.live{ color:#fff; background:var(--accent); padding:.18rem .6rem; border-radius:99px;
       font-size:.82rem; font-weight:800; letter-spacing:.4px; }
.match.islive{ border-color:var(--accent); }

/* Win probability bar */
.wp{ margin:.7rem 0 .2rem; }
.wp .bar{ height:12px; border-radius:99px; overflow:hidden; display:flex; }
.wp .bar > div{ height:100%; }
.wp .labels{ display:flex; justify-content:space-between; font-size:.95rem; margin-top:.45rem; color:var(--ink); }
.wp .labels .mid{ color:var(--muted); }
.wp .note{ font-size:.9rem; color:var(--muted); margin-top:.35rem; }

/* Club cards */
.clubgrid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:.8rem; }
.club{ border:1px solid var(--line); border-left-width:5px; border-radius:14px;
   padding:.95rem 1.1rem; background:var(--panel); font-size:1.2rem; font-weight:600;
   display:flex; align-items:center; gap:.7rem; }

.foot{ color:var(--muted); font-size:.95rem; margin-top:.5rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def dot(color):
    return f'<span class="dot" style="background:{color}"></span>'


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
def header(season):
    left, right = st.columns([4, 1])
    with left:
        st.markdown('<p class="hero-title">St.&nbsp;Helena Premier League</p>', unsafe_allow_html=True)
        sub = "St. Helena &amp; Ascension · South Atlantic football"
        if season:
            sub += f" · {season} season"
        st.markdown(f'<p class="hero-sub">{sub}</p>', unsafe_allow_html=True)
    with right:
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        now = datetime.now(LOCAL_TZ).strftime("%d %b · %H:%M")
        st.caption(f"Updated {now}")


# --------------------------------------------------------------------------- #
# Tables page
# --------------------------------------------------------------------------- #
def render_standings(standings):
    cols = st.columns(len(standings["conferences"]), gap="large")
    for col, conf in zip(cols, standings["conferences"]):
        with col:
            meta = ISLAND_META.get(conf["island"], {"flag": "", "accent": "#888"})
            st.markdown(
                f'<div class="eyebrow"><span class="bar" style="background:{meta["accent"]}"></span>'
                f'{meta["flag"]} {conf["island"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_standings_html(conf["table"]), unsafe_allow_html=True)


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
    return head + "".join(body) + "</tbody></table>" + legend


# --------------------------------------------------------------------------- #
# Matches page
# --------------------------------------------------------------------------- #
def render_matches(matches):
    live = [m for m in matches if m["state"] == "in"]
    upcoming = [m for m in matches if m["state"] == "pre"]
    past = [m for m in matches if m["state"] == "post"]
    past.reverse()

    tab_live, tab_up, tab_past = st.tabs(
        [f"🔴 Live ({len(live)})", f"📅 Upcoming ({len(upcoming)})", f"✅ Results ({len(past)})"]
    )
    with tab_live:
        if not live:
            st.info("No matches are being played right now — check the Upcoming tab for what's next.")
        for m in live:
            match_card(m, show_prob=False)
    with tab_up:
        if not upcoming:
            st.info("No upcoming fixtures in the current window.")
        for m in upcoming:
            match_card(m, show_prob=True)
    with tab_past:
        if not past:
            st.info("No recent results in the current window.")
        for m in past:
            match_card(m, show_prob=False)


def _fmt_kickoff(dt):
    if not dt:
        return "TBD"
    return dt.astimezone(LOCAL_TZ).strftime("%a %d %b · %H:%M")


def match_card(m, show_prob):
    live = m["state"] == "in"
    home, away = m["home"], m["away"]
    show_score = m["state"] in ("in", "post")

    top_left = (f'<span class="live">● LIVE · {m["status_detail"]}</span>' if live
                else f'<span class="status">{m["status_detail"] or _fmt_kickoff(m["start"])}</span>')
    venue = f'<span class="status">📍 {m["venue"]}</span>' if m["venue"] else "<span></span>"

    def row(side):
        s = side["score"] if side["score"] is not None else "–"
        score = f'<span class="score">{s}</span>' if show_score else '<span class="score"></span>'
        cls = "tname"
        if show_score and m["completed"]:
            cls += " win" if side.get("winner") else (" lose" if not _is_draw(m) else "")
        return f'<div class="mrow"><span class="{cls}">{dot(side["primary"])}{side["shpl_name"]}</span>{score}</div>'

    kick = "" if show_score else f'<div class="kick">🕓 {_fmt_kickoff(m["start"])}</div>'
    border = f'border-left-color:{home["primary"]};'
    card_cls = "match islive" if live else "match"

    html = (f'<div class="{card_cls}" style="{border}">'
            f'<div class="top">{top_left}{venue}</div>'
            f'{row(home)}{row(away)}{kick}</div>')
    st.markdown(html, unsafe_allow_html=True)

    if show_prob:
        _win_prob_block(m)


def _is_draw(m):
    hs, as_ = m["home"]["score"], m["away"]["score"]
    return hs is not None and hs == as_


def _win_prob_block(m):
    wp = load_win_prob(m["id"])
    if not wp:
        st.markdown(
            '<div class="wp"><div class="note">Win probability not published yet '
            '(usually appears a few days before kick-off).</div></div>',
            unsafe_allow_html=True,
        )
        return
    h, d, a = wp["home_pct"], wp["draw_pct"], wp["away_pct"]
    hc, ac = m["home"]["primary"], m["away"]["primary"]
    html = (
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
    st.markdown(html, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Clubs page
# --------------------------------------------------------------------------- #
def render_clubs():
    for island in teams.ISLANDS:
        meta = ISLAND_META.get(island, {"flag": "", "accent": "#888"})
        st.markdown(
            f'<div class="eyebrow"><span class="bar" style="background:{meta["accent"]}"></span>'
            f'{meta["flag"]} {island}</div>',
            unsafe_allow_html=True,
        )
        cards = "".join(
            f'<div class="club" style="border-left-color:{t.primary}">{dot(t.primary)}{t.shpl_name}</div>'
            for t in teams.TEAMS if t.island == island
        )
        st.markdown(f'<div class="clubgrid">{cards}</div>', unsafe_allow_html=True)
        st.write("")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    try:
        standings = load_standings()
    except espn.ESPNError as e:
        standings = {"season": "", "conferences": []}
        st.error(f"Live data is temporarily unavailable: {e}")

    header(standings.get("season", ""))
    st.divider()

    page = st.radio(
        "Section", ["🏆 Tables", "⚽ Matches", "🛡️ Clubs"],
        horizontal=True, label_visibility="collapsed",
    )

    if page == "🏆 Tables":
        st.markdown('<div class="hint">Standings for each island, updating live as results come in.</div>',
                    unsafe_allow_html=True)
        if standings["conferences"]:
            render_standings(standings)
        else:
            st.warning("Standings could not be loaded. Try the Refresh button.")
    elif page == "⚽ Matches":
        st.markdown('<div class="hint">Live, upcoming and recent fixtures — times shown in St. Helena time.</div>',
                    unsafe_allow_html=True)
        try:
            render_matches(load_matches())
        except espn.ESPNError as e:
            st.error(f"Could not load matches: {e}")
    else:
        st.markdown('<div class="hint">The fifteen clubs of each island.</div>', unsafe_allow_html=True)
        render_clubs()

    st.divider()
    st.markdown(
        '<div class="foot">St. Helena Premier League · an unofficial fan project · scores update automatically.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
