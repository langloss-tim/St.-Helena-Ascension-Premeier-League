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
def load_feed():
    return datafeed.load_feed()


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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


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
def render_matches(matches, feed):
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
            match_card(m, show_prob=False, feed=feed)
    with tab_up:
        if not upcoming:
            st.info("No upcoming fixtures in the current window.")
        for m in upcoming:
            match_card(m, show_prob=True, feed=feed)
    with tab_past:
        if not past:
            st.info("No recent results in the current window.")
        for m in past:
            match_card(m, show_prob=False, feed=feed)


def _fmt_kickoff(dt):
    if not dt:
        return "TBD"
    return dt.astimezone(LOCAL_TZ).strftime("%a %d %b · %H:%M")


def match_card(m, show_prob, feed):
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
        _win_prob_block(m, feed)


def _is_draw(m):
    hs, as_ = m["home"]["score"], m["away"]["score"]
    return hs is not None and hs == as_


def _win_prob_block(m, feed):
    wp = datafeed.get_win_probabilities(feed, m["id"])
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
def sidebar(feed):
    """Navigation + status. Returns the selected page."""
    with st.sidebar:
        st.markdown('<div class="side-title">⚽ SHPL</div>', unsafe_allow_html=True)
        st.markdown('<div class="side-sub">St. Helena Premier League</div>', unsafe_allow_html=True)
        st.divider()
        page = st.radio(
            "Go to", ["🏆 Tables", "⚽ Matches", "🛡️ Clubs"],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("🔄 Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        gen = datafeed.generated_at(feed) if feed else None
        if gen:
            st.caption(f"Scores updated\n\n**{gen.astimezone(LOCAL_TZ).strftime('%a %d %b · %H:%M')}** (St. Helena time)")
        else:
            st.caption(f"Loaded {datetime.now(LOCAL_TZ).strftime('%d %b · %H:%M')}")
    return page


def main():
    try:
        feed = load_feed()
    except datafeed.FeedUnavailable as e:
        feed = None
        st.error(f"Scores are temporarily unavailable: {e}")

    season = feed["season"] if feed else ""
    page = sidebar(feed)

    header(season)
    st.divider()

    if feed is None:
        st.warning("Data could not be loaded right now. Try the Refresh button in the sidebar in a moment.")
        return

    standings = datafeed.get_standings(feed)

    if page == "🏆 Tables":
        st.markdown('<div class="hint">Standings for each island, updating as results come in.</div>',
                    unsafe_allow_html=True)
        if standings["conferences"]:
            render_standings(standings)
        else:
            st.warning("Standings could not be loaded. Try the Refresh button.")
    elif page == "⚽ Matches":
        st.markdown('<div class="hint">Live, upcoming and recent fixtures — times shown in St. Helena time.</div>',
                    unsafe_allow_html=True)
        render_matches(datafeed.get_matches(feed), feed)
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
