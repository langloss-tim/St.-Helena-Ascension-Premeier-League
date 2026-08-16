"""
St. Helena Premier League — Streamlit app.

A fan site for a fictional island league (St. Helena + Ascension) that mirrors
the real MLS 2026 season in real time. Standings, fixtures, scores and win
probabilities are pulled live from ESPN and re-branded via teams.py, so the
site updates itself as matches are played and new seasons begin.

Run locally:  streamlit run app.py
"""

from datetime import datetime, timezone
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

# Show times in a fixed island-friendly zone. St. Helena is UTC+0 year round.
LOCAL_TZ = ZoneInfo("Atlantic/St_Helena")


# --------------------------------------------------------------------------- #
# Cached data fetchers (TTL keeps live scores fresh without hammering ESPN)
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
:root { --card-bg: rgba(255,255,255,0.03); --line: rgba(255,255,255,0.10); }
.shpl-title { font-size: 2.5rem; font-weight: 800; letter-spacing:-.5px; margin:0; }
.shpl-sub { opacity:.7; margin:.2rem 0 0; font-size:1rem; }

.chip { display:inline-flex; align-items:center; gap:.55rem; }
.dot { width:14px; height:14px; border-radius:50%; flex:0 0 auto;
       box-shadow: inset 0 0 0 2px rgba(255,255,255,.25); }
.mls { opacity:.5; font-size:.8rem; }

/* match cards */
.match { border:1px solid var(--line); border-radius:14px; padding:.9rem 1.1rem;
         margin-bottom:.7rem; background:var(--card-bg); }
.match.live { border-color:#e4572e; box-shadow:0 0 0 1px #e4572e33; }
.mrow { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.team-line { display:flex; align-items:center; gap:.55rem; font-size:1.08rem; font-weight:600; }
.score { font-size:1.35rem; font-weight:800; min-width:1.6rem; text-align:center; }
.meta { font-size:.8rem; opacity:.65; }
.livebadge { color:#fff; background:#e4572e; padding:.12rem .5rem; border-radius:999px;
             font-size:.72rem; font-weight:700; letter-spacing:.4px; }
.winbar { height:8px; border-radius:999px; overflow:hidden; display:flex; margin-top:.5rem; }
.winbar > div { height:100%; }
.winlabels { display:flex; justify-content:space-between; font-size:.74rem; opacity:.8; margin-top:.25rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def dot(color):
    return f'<span class="dot" style="background:{color}"></span>'


def team_chip(side_or_row, show_mls=True):
    name = side_or_row["shpl_name"]
    mls = side_or_row.get("mls_name", "")
    html = f'<span class="chip">{dot(side_or_row["primary"])}<span>{name}</span>'
    if show_mls and mls:
        html += f' <span class="mls">· {mls}</span>'
    html += "</span>"
    return html


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
def header(season):
    left, right = st.columns([4, 1])
    with left:
        st.markdown('<p class="shpl-title">⚽ St. Helena Premier League</p>', unsafe_allow_html=True)
        sub = "St. Helena & Ascension · a South Atlantic league mirroring the MLS"
        if season:
            sub += f" · {season} season"
        st.markdown(f'<p class="shpl-sub">{sub}</p>', unsafe_allow_html=True)
    with right:
        st.write("")
        if st.button("🔄 Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        now = datetime.now(LOCAL_TZ).strftime("%d %b %H:%M")
        st.caption(f"Updated {now} (St. Helena time)")


# --------------------------------------------------------------------------- #
# Tables page
# --------------------------------------------------------------------------- #
def render_standings(standings):
    st.markdown("#### League Tables")
    st.caption(
        "St. Helena clubs play in the MLS Eastern Conference; Ascension clubs in "
        "the Western Conference. Points, results and goal difference update live."
    )
    cols = st.columns(len(standings["conferences"]))
    for col, conf in zip(cols, standings["conferences"]):
        with col:
            flag = "🇸🇭" if conf["island"] == teams.ST_HELENA else "🌋"
            st.markdown(f"##### {flag} {conf['island']}")
            _standings_table(conf["table"])


def _standings_table(rows):
    header_cols = st.columns([0.6, 4, 0.7, 0.7, 0.7, 0.7, 0.9, 0.9])
    labels = ["#", "Club", "P", "W", "D", "L", "GD", "Pts"]
    for c, lab in zip(header_cols, labels):
        c.markdown(f"**{lab}**")
    # A simple playoff line: top 9 of each conference qualify in MLS.
    for r in rows:
        cs = st.columns([0.6, 4, 0.7, 0.7, 0.7, 0.7, 0.9, 0.9])
        rank_badge = f"{r['rank']}"
        if r["rank"] <= 9:
            rank_badge = f"<span style='color:#4caf50;font-weight:700'>{r['rank']}</span>"
        cs[0].markdown(rank_badge, unsafe_allow_html=True)
        cs[1].markdown(team_chip(r), unsafe_allow_html=True)
        cs[2].write(r["played"])
        cs[3].write(r["wins"])
        cs[4].write(r["draws"])
        cs[5].write(r["losses"])
        cs[6].write(f"{r['gd']:+d}")
        cs[7].markdown(f"**{r['points']}**")
    st.caption("🟢 Top 9 = playoff places")


# --------------------------------------------------------------------------- #
# Matches page
# --------------------------------------------------------------------------- #
def render_matches(matches):
    st.markdown("#### Matches")

    live = [m for m in matches if m["state"] == "in"]
    upcoming = [m for m in matches if m["state"] == "pre"]
    past = [m for m in matches if m["state"] == "post"]
    past.reverse()  # most recent first

    tab_live, tab_up, tab_past = st.tabs(
        [f"🔴 Live ({len(live)})", f"📅 Upcoming ({len(upcoming)})", f"✅ Results ({len(past)})"]
    )

    with tab_live:
        if not live:
            st.info("No matches are being played right now. Check the Upcoming tab for the next fixtures.")
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
    css_class = "match live" if live else "match"

    status_html = f'<span class="livebadge">● LIVE · {m["status_detail"]}</span>' if live \
        else f'<span class="meta">{m["status_detail"] or _fmt_kickoff(m["start"])}</span>'

    def score_or_dash(side):
        return side["score"] if side["score"] is not None else "–"

    show_score = m["state"] in ("in", "post")

    def line(side):
        score = f'<span class="score">{score_or_dash(side)}</span>' if show_score else '<span class="score"></span>'
        win = "font-weight:800" if side.get("winner") else ""
        return (f'<div class="mrow"><span class="team-line" style="{win}">'
                f'{dot(side["primary"])}{side["shpl_name"]} '
                f'<span class="mls">· {side["mls_name"]}</span></span>{score}</div>')

    kickoff = "" if show_score else f'<div class="meta">🕓 {_fmt_kickoff(m["start"])}</div>'
    venue = f'<div class="meta">📍 {m["venue"]}</div>' if m["venue"] else ""

    html = (f'<div class="{css_class}">'
            f'<div class="mrow"><div>{status_html}</div>{venue}</div>'
            f'{line(home)}{line(away)}{kickoff}'
            f'</div>')
    st.markdown(html, unsafe_allow_html=True)

    if show_prob:
        _win_prob_block(m)


def _win_prob_block(m):
    wp = load_win_prob(m["id"])
    if not wp:
        st.caption("Win probability not published yet (odds usually appear a few days before kick-off).")
        return
    h, d, a = wp["home_pct"], wp["draw_pct"], wp["away_pct"]
    hc, ac = m["home"]["primary"], m["away"]["primary"]
    bar = (f'<div class="winbar">'
           f'<div style="width:{h}%;background:{hc}"></div>'
           f'<div style="width:{d}%;background:#9e9e9e"></div>'
           f'<div style="width:{a}%;background:{ac}"></div></div>'
           f'<div class="winlabels">'
           f'<span>{m["home"]["shpl_name"]} {h}%</span>'
           f'<span>Draw {d}%</span>'
           f'<span>{a}% {m["away"]["shpl_name"]}</span></div>')
    st.markdown(bar, unsafe_allow_html=True)
    st.caption(f"Win % from {wp['source']} match preview odds (de-vigged).")


# --------------------------------------------------------------------------- #
# Teams page
# --------------------------------------------------------------------------- #
def render_teams():
    st.markdown("#### Clubs")
    st.caption("Every SHPL club and the MLS side it mirrors.")
    for island in teams.ISLANDS:
        flag = "🇸🇭" if island == teams.ST_HELENA else "🌋"
        st.markdown(f"##### {flag} {island}")
        club_rows = [t for t in teams.TEAMS if t.island == island]
        cols = st.columns(3)
        for i, t in enumerate(club_rows):
            with cols[i % 3]:
                st.markdown(
                    f'<div class="match"><div class="team-line">{dot(t.primary)}{t.shpl_name}</div>'
                    f'<div class="mls">mirrors {t.mls_name}</div></div>',
                    unsafe_allow_html=True,
                )


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
        if standings["conferences"]:
            render_standings(standings)
        else:
            st.warning("Standings could not be loaded. Try the Refresh button.")
    elif page == "⚽ Matches":
        try:
            matches = load_matches()
            render_matches(matches)
        except espn.ESPNError as e:
            st.error(f"Could not load matches: {e}")
    else:
        render_teams()

    st.divider()
    st.caption(
        "Unofficial fan project. Live data via ESPN's public MLS feed. "
        "SHPL is a fictional re-brand of MLS clubs for St. Helena & Ascension."
    )


if __name__ == "__main__":
    main()
