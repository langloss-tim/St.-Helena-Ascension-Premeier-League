"""
Match Simulator -- Streamlit app.

Two things on one site:
  * Simulator: pick (or type) any two clubs, or any two nations from FIFA and
    the Island Games, and watch the game play out from 1' to 90' in about
    ninety seconds.
  * Leagues: look up any league's table and matches. ESPN covers 216 leagues
    and cups live; every other country's top league (world_leagues.json), and
    anything typed in, is read from Wikipedia's latest season page.

sim.py holds the sides and the match engine; leagues.py fetches the data.

Run locally:  streamlit run app.py
"""

import base64
import html
import json
import random
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

import leagues
import sim

st.set_page_config(page_title="Match Simulator", page_icon="⚽", layout="wide")

LOCAL_TZ = ZoneInfo("America/New_York")

# Flags are vendored into flags/ where a file exists (they can't 404 or be
# rate-limited) and fall back to flagcdn for every other code, so any country
# needs nothing but its code. "gb-sct" style codes cover the UK home nations.
FLAG_DIR = Path(__file__).resolve().parent / "flags"
CDN_ROOT = "https://flagcdn.com/w160"


@lru_cache(maxsize=None)
def flag_src(code):
    code = (code or "").strip().lower()
    if not re.fullmatch(r"[a-z]{2}(-[a-z]{3})?", code):
        return ""
    try:
        raw = (FLAG_DIR / f"{code}.png").read_bytes()
    except OSError:
        return f"{CDN_ROOT}/{code}.png"
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


CSS = """
<style>
html{ font-size:18px; }
.block-container{ padding-top:2rem; max-width:1100px; }
.hero-title{ font-size:3rem; font-weight:800; letter-spacing:-1px; line-height:1.05; margin:0; }
.hero-sub{ font-size:1.15rem; color:rgba(238,241,246,.6); margin:.4rem 0 1rem; }
.hint{ font-size:1rem; color:rgba(238,241,246,.6); margin:-.2rem 0 1rem; }
button[data-baseweb="tab"] p{ font-size:1.1rem !important; font-weight:700 !important; }

.tblwrap{ overflow-x:auto; -webkit-overflow-scrolling:touch; margin-bottom:1.2rem; }
.tbl{ width:100%; border-collapse:collapse; font-size:1rem; }
.tbl th{ text-transform:uppercase; font-size:.75rem; letter-spacing:.5px; color:rgba(238,241,246,.55);
         padding:.45rem .4rem; border-bottom:1px solid rgba(255,255,255,.12); text-align:center; }
.tbl td{ padding:.45rem .4rem; border-bottom:1px solid rgba(255,255,255,.06); text-align:center;
         white-space:nowrap; }
.tbl td.team, .tbl th.team{ text-align:left; }
.tbl td.pts{ font-weight:800; }
.tbl img{ width:22px; height:22px; object-fit:contain; vertical-align:middle; margin-right:.45rem; }
.tbl .mark{ display:inline-block; width:4px; height:1.2rem; border-radius:2px; vertical-align:middle; }
.legend{ font-size:.85rem; color:rgba(238,241,246,.6); margin:-.6rem 0 1.2rem; }
.legend span{ display:inline-block; margin-right:1rem; }
.legend i{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:.35rem; }

.mday{ font-weight:800; margin:1rem 0 .4rem; color:rgba(238,241,246,.75); }
.match{ display:grid; grid-template-columns:1fr auto 1fr; gap:.6rem; align-items:center;
        background:#161b26; border:1px solid rgba(255,255,255,.07); border-radius:12px;
        padding:.6rem .8rem; margin-bottom:.45rem; }
.match .h{ text-align:right; } .match .a{ text-align:left; }
.match img{ width:22px; height:22px; object-fit:contain; vertical-align:middle; margin:0 .4rem; }
.match .sc{ font-weight:800; font-size:1.15rem; min-width:4.2rem; text-align:center; }
.match .st{ font-size:.75rem; color:rgba(238,241,246,.55); text-align:center; font-weight:600; }
.match .live{ color:#2ecc71; }
.match .win{ font-weight:800; }
@media (max-width:640px){
  html{ font-size:16px; }
  .hero-title{ font-size:2.1rem; }
  .match{ padding:.5rem; gap:.3rem; font-size:.9rem; }
  .match img{ width:18px; height:18px; margin:0 .25rem; }
}
</style>
"""


# --------------------------------------------------------------------------- #
# Simulator
# --------------------------------------------------------------------------- #
# The whole game is decided in Python the moment Kick off is pressed; the
# browser only reveals it a minute at a time, so a rerun can't change a score.
MATCH_HTML = r"""
<div id="sim">
  <div class="board">
    <div class="side home"><div class="badge" id="hb"></div><div class="nm" id="hn"></div></div>
    <div class="mid">
      <div class="score"><span id="hs">0</span><span class="dash">–</span><span id="as">0</span></div>
      <div class="clock" id="clock">KO</div>
    </div>
    <div class="side away"><div class="badge" id="ab"></div><div class="nm" id="an"></div></div>
  </div>
  <div class="bar"><div id="fill"></div><div class="ht"></div></div>
  <div class="ctl"><button id="skip">Skip to full time ⏭</button></div>
  <div class="feed" id="feed"></div>
</div>
<style>
  *{ box-sizing:border-box; }
  body{ margin:0; font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#eef1f6; }
  #sim{ background:linear-gradient(180deg,#15402a,#0f2b1d); border-radius:18px; padding:18px 16px 14px;
        border:1px solid rgba(255,255,255,.08); }
  .board{ display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:10px; }
  .side{ display:flex; flex-direction:column; align-items:center; gap:8px; text-align:center; min-width:0; }
  .badge{ width:84px; height:56px; display:flex; align-items:center; justify-content:center; }
  .badge img{ max-width:84px; max-height:56px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,.4); }
  .badge .init{ width:56px; height:56px; border-radius:50%; background:#24314a; display:flex;
                align-items:center; justify-content:center; font-weight:800; font-size:20px; }
  .nm{ font-weight:800; font-size:19px; line-height:1.15; overflow-wrap:anywhere; }
  .mid{ text-align:center; }
  .score{ font-size:56px; font-weight:900; letter-spacing:2px; line-height:1; font-variant-numeric:tabular-nums; }
  .dash{ opacity:.6; margin:0 8px; }
  .clock{ margin-top:8px; display:inline-block; background:#0b1a12; border-radius:99px; padding:4px 14px;
          font-weight:800; font-size:18px; color:#2ecc71; font-variant-numeric:tabular-nums; }
  .clock.done{ color:#eef1f6; background:#e4572e; }
  .bar{ position:relative; height:6px; background:rgba(255,255,255,.12); border-radius:99px; margin:16px 0 10px; }
  #fill{ height:100%; width:0; background:#2ecc71; border-radius:99px; transition:width .9s linear; }
  .ht{ position:absolute; left:50%; top:-3px; width:2px; height:12px; background:rgba(255,255,255,.5); }
  .ctl{ text-align:right; }
  #skip{ background:transparent; color:rgba(238,241,246,.75); border:1px solid rgba(255,255,255,.25);
         border-radius:8px; padding:4px 10px; font-size:13px; cursor:pointer; }
  .feed{ margin-top:10px; max-height:230px; overflow-y:auto; }
  .ev{ display:flex; gap:10px; align-items:center; padding:7px 10px; border-radius:10px;
       background:rgba(0,0,0,.22); margin-bottom:6px; font-size:15px; animation:pop .35s ease-out; }
  .ev.away{ flex-direction:row-reverse; text-align:right; }
  .ev .m{ font-weight:800; min-width:34px; color:#2ecc71; }
  .ev.goal{ background:rgba(46,204,113,.22); font-weight:700; }
  .ev.note{ justify-content:center; background:rgba(255,255,255,.08); font-weight:700; }
  .card{ display:inline-block; width:11px; height:15px; border-radius:2px; }
  @keyframes pop{ from{ transform:scale(.96); opacity:0 } to{ transform:none; opacity:1 } }
  @media (max-width:520px){
    .score{ font-size:40px; } .nm{ font-size:15px; } .badge{ width:60px; height:40px; }
    .badge img{ max-width:60px; max-height:40px; }
  }
</style>
<script>
const M = __MATCH__;
const $ = id => document.getElementById(id);
const esc = t => String(t).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
M.home.name = esc(M.home.name); M.away.name = esc(M.away.name);
function badge(el, side){
  if (side.flag){ el.innerHTML = `<img src="${side.flag}" alt="">`; }
  else {
    const ini = side.name.split(/\s+/).filter(w => /^[\p{L}\d]/u.test(w)).slice(0,2).map(w => w[0]).join("").toUpperCase();
    el.innerHTML = `<div class="init">${ini || "?"}</div>`;
  }
}
$("hn").innerHTML = M.home.name; $("an").innerHTML = M.away.name;
badge($("hb"), M.home); badge($("ab"), M.away);
const score = {home:0, away:0};
function row(cls, html){ const d = document.createElement("div"); d.className = "ev " + cls;
  d.innerHTML = html; $("feed").prepend(d); }
function show(ev){
  const name = (ev.side === "home" ? M.home : M.away).name;
  if (ev.type === "goal"){
    score[ev.side]++; $("hs").textContent = score.home; $("as").textContent = score.away;
    row(ev.side + " goal", `<span class="m">${ev.min}'</span><span>⚽ GOAL — ${name}</span>`);
  } else {
    const c = ev.type === "red" ? "#e53935" : "#fdd835";
    const word = ev.type === "red" ? "Red card" : "Yellow card";
    row(ev.side, `<span class="m">${ev.min}'</span><span><i class="card" style="background:${c}"></i> ${word} — ${name}</span>`);
  }
}
let minute = 0, timer = null;
const STEP = 1000;            // one match minute per second -> about 90 seconds
function tick(){
  minute++;
  $("clock").textContent = minute + "'";
  $("fill").style.width = (minute / 90 * 100) + "%";
  M.events.filter(e => e.min === minute).forEach(show);
  if (minute === 45){
    row("note", `Half time · ${M.home.name} ${score.home}–${score.away} ${M.away.name}`);
    $("clock").textContent = "HT"; clearInterval(timer);
    setTimeout(() => { timer = setInterval(tick, STEP); }, 2500);
    return;
  }
  if (minute >= 90) finish();
}
function finish(){
  clearInterval(timer); timer = null;
  $("clock").textContent = "FT"; $("clock").classList.add("done");
  $("fill").style.width = "100%";
  const [h, a] = [score.home, score.away];
  const res = h > a ? M.home.name + " win" : a > h ? M.away.name + " win" : "Draw";
  row("note", `Full time · ${M.home.name} ${h}–${a} ${M.away.name} · ${res}`);
  $("skip").style.display = "none";
}
$("skip").onclick = () => {
  if (!timer) return;
  clearInterval(timer);
  while (minute < 90){ minute++; M.events.filter(e => e.min === minute).forEach(show); }
  finish();
};
$("clock").textContent = "KO";
setTimeout(() => { timer = setInterval(tick, STEP); }, 900);
</script>
"""


def _side_payload(s):
    return {"name": s["name"], "flag": flag_src(s.get("code"))}


def render_match(m):
    payload = {"home": _side_payload(m["home"]), "away": _side_payload(m["away"]),
               "events": m["result"]["events"]}
    # One extra key per kick-off so pressing Kick off again with the same two
    # sides always restarts the animation instead of reusing the old frame.
    page = MATCH_HTML.replace("__MATCH__", json.dumps(payload).replace("</", "<\\/")) + f"<!-- {m['id']} -->"
    components.html(page, height=600, scrolling=False)


def render_simulator():
    st.markdown('<div class="hint">Pick two sides and press Kick off. The game runs '
                'from 1\' to 90\' in about 90 seconds.</div>', unsafe_allow_html=True)
    kind = st.radio("Mode", ["🛡️ Clubs", "🌍 Nations"], horizontal=True,
                    label_visibility="collapsed", key="sim_kind")
    is_club = kind.startswith("🛡️")
    if is_club:
        options = sim.club_names()
        help_ = (f"{len(options):,} clubs listed. Not in the list? Type its name "
                 "and press Enter — every club can play.")
        ph = "Type any club…"
    else:
        options = sim.nation_names()
        help_ = "All 211 FIFA member nations plus every Island Games (IIGA) member."
        ph = "Type a nation…"
    st.caption(help_)

    c1, c2 = st.columns(2)
    sel = {}
    for col, which in ((c1, "home"), (c2, "away")):
        with col:
            sel[which] = st.selectbox(
                "Home" if which == "home" else "Away", options, index=None,
                placeholder=ph, accept_new_options=is_club,
                key=f"sim_{which}_{'club' if is_club else 'nation'}")
    neutral = st.checkbox("Neutral venue (no home advantage)", key="sim_neutral")

    ready = sel["home"] and sel["away"]
    same = ready and sel["home"].strip().casefold() == sel["away"].strip().casefold()
    if same:
        st.warning("A side can't play itself — pick two different teams.")
    if st.button("⚽ Kick off", type="primary", disabled=not ready or same,
                 width="stretch"):
        k = "club" if is_club else "nation"
        home, away = sim.side(sel["home"], k), sim.side(sel["away"], k)
        mid = random.getrandbits(48)
        st.session_state.match = {"home": home, "away": away, "id": mid,
                                  "result": sim.simulate(home, away, neutral, seed=mid)}

    m = st.session_state.get("match")
    if m:
        render_match(m)


# --------------------------------------------------------------------------- #
# Leagues
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=120, show_spinner=False)
def _espn_standings(slug):
    return leagues.espn_standings(slug)


@st.cache_data(ttl=60, show_spinner=False)
def _espn_matches(slug):
    return leagues.espn_matches(slug)


@st.cache_data(ttl=3600, show_spinner=False)
def _wiki(query):
    return leagues.wiki_league(query)


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _img(url):
    return f'<img src="{_e(url)}" alt="" loading="lazy">' if url else ""


def _standings_html(group):
    head = ("<tr><th></th><th>#</th><th class='team'>Team</th><th>P</th><th>W</th><th>D</th>"
            "<th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th></tr>")
    body = []
    for r in group["rows"]:
        mark = (f'<span class="mark" style="background:{_e(r["color"])}" title="{_e(r["note"])}"></span>'
                if r["color"] else "")
        body.append(
            f"<tr><td>{mark}</td><td>{_e(r['rank'])}</td>"
            f"<td class='team'>{_img(r['logo'])}{_e(r['team'])}</td>"
            f"<td>{_e(r['gp'])}</td><td>{_e(r['w'])}</td><td>{_e(r['d'])}</td><td>{_e(r['l'])}</td>"
            f"<td>{_e(r['gf'])}</td><td>{_e(r['ga'])}</td><td>{_e(r['gd'])}</td>"
            f"<td class='pts'>{_e(r['pts'])}</td></tr>")
    notes = {}
    for r in group["rows"]:
        if r["color"] and r["note"]:
            notes.setdefault(r["note"], r["color"])
    legend = "".join(f'<span><i style="background:{_e(c)}"></i>{_e(n)}</span>'
                     for n, c in notes.items())
    return (f'<div class="tblwrap"><table class="tbl"><thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>'
            + (f'<div class="legend">{legend}</div>' if legend else ""))


def _when(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
    except ValueError:
        return None
    return dt


def _match_html(m):
    played = m["state"] != "pre"
    hs, as_ = m["hs"], m["as"]
    hw = aw = ""
    if m["state"] == "post" and str(hs).isdigit() and str(as_).isdigit():
        hw = " win" if int(hs) > int(as_) else ""
        aw = " win" if int(as_) > int(hs) else ""
    dt = _when(m["date"])
    if played:
        sc = f"{_e(hs)} – {_e(as_)}"
        status = m["detail"] or ("FT" if m["state"] == "post" else "Live")
        cls = "st live" if m["state"] == "in" else "st"
    else:
        sc = dt.strftime("%-I:%M %p") if dt else "vs"
        status, cls = "ET", "st"
    return (f'<div class="match"><div class="h{hw}">{_e(m["home"])}{_img(m["home_logo"])}</div>'
            f'<div><div class="sc">{sc}</div><div class="{cls}">{_e(status)}</div></div>'
            f'<div class="a{aw}">{_img(m["away_logo"])}{_e(m["away"])}</div></div>')


def _matches_by_day(ms, newest_first):
    ms = sorted(ms, key=lambda m: m["date"], reverse=newest_first)
    out, last = [], None
    for m in ms:
        dt = _when(m["date"])
        day = dt.strftime("%A, %B %-d") if dt else ""
        if day != last:
            out.append(f'<div class="mday">{_e(day)}</div>')
            last = day
        out.append(_match_html(m))
    return "".join(out)


def render_espn_league(slug, name):
    tab_table, tab_matches = st.tabs(["📊 Table", "⚽ Matches"])
    with tab_table:
        try:
            groups = _espn_standings(slug)
        except leagues.Unavailable:
            groups = None
            st.error("The table couldn't be loaded right now. Try again in a minute.")
        if groups == []:
            st.info(f"{name} has no league table — it's a knockout competition. "
                    "See Matches for its games.")
        for g in groups or []:
            if len(groups) > 1 and g["name"]:
                st.markdown(f"**{_e(g['name'])}**")
            st.markdown(_standings_html(g), unsafe_allow_html=True)
    with tab_matches:
        try:
            ms = _espn_matches(slug)
        except leagues.Unavailable:
            st.error("Matches couldn't be loaded right now. Try again in a minute.")
            return
        live = [m for m in ms if m["state"] == "in"]
        done = [m for m in ms if m["state"] == "post"]
        todo = [m for m in ms if m["state"] == "pre"]
        st.caption("The last two weeks of results and the next two weeks of fixtures. "
                   "Times are US Eastern.")
        t_live, t_res, t_fix = st.tabs([f"🔴 Live ({len(live)})", f"✅ Results ({len(done)})",
                                        f"📅 Fixtures ({len(todo)})"])
        with t_live:
            st.markdown(_matches_by_day(live, False) or "No games being played right now.",
                        unsafe_allow_html=True)
        with t_res:
            st.markdown(_matches_by_day(done, True) or "No results in the last two weeks.",
                        unsafe_allow_html=True)
        with t_fix:
            st.markdown(_matches_by_day(todo, False) or "No fixtures in the next two weeks.",
                        unsafe_allow_html=True)


def render_wiki_league(query):
    with st.spinner(f"Looking up {query}…"):
        try:
            found = _wiki(query)
        except leagues.Unavailable:
            st.error("Wikipedia couldn't be reached right now. Try again in a minute.")
            return
    if not found:
        st.warning(f"No league table found for “{query}”. Try the league's full name, "
                   "e.g. “Faroe Islands Premier League” or “Gibraltar Football League”.")
        return
    if not found["tables"]:
        st.caption(f"From Wikipedia: [{found['title']}]({found['url']})")
        st.info("This league doesn't publish a table or results anywhere online, "
                "so here is what is known about it.")
        rows = "".join(f"<tr><td class='team'>{_e(a)}</td><td class='team'>{_e(b)}</td></tr>"
                       for a, b in found["facts"])
        st.markdown(f'<div class="tblwrap"><table class="tbl"><tbody>{rows}</tbody></table></div>',
                    unsafe_allow_html=True)
        return
    st.caption(f"From Wikipedia: [{found['title']}]({found['url']}) — the newest season "
               "page with a table. Leagues outside the live list update when Wikipedia does.")
    tab_table, tab_matches = st.tabs(["📊 Table", "⚽ Matches"])
    with tab_table:
        for t in found["tables"][:4]:
            st.dataframe(t, hide_index=True, width="stretch")
    with tab_matches:
        if found["grid"] is not None:
            st.caption("Results grid — home team down the left, away team across the top.")
            st.dataframe(found["grid"], hide_index=True, width="stretch")
        else:
            st.info("That season page has no match-by-match results.")


def render_leagues():
    st.markdown('<div class="hint">Every country\'s top league is in the list — the '
                'Caribbean, Africa, Asia, Oceania, Europe and the Island Games — along '
                'with the big leagues and cups. Type a country or a league to find it. '
                'Not listed? Type any league name and press Enter.</div>',
                unsafe_allow_html=True)
    # label -> ("espn", slug) or ("wiki", query)
    choices = {n: ("espn", s) for s, n in leagues.espn_leagues()}
    # getattr: Streamlit Cloud can keep an older leagues module loaded for a
    # moment after a deploy; the big list still works without the extras.
    for region, country, _code, query in getattr(leagues, "world_leagues", list)():
        choices.setdefault(f"{country} — {query} ({region})", ("wiki", query))
    pick = st.selectbox("League", sorted(choices, key=str.casefold), index=None,
                        accept_new_options=True, placeholder="Type a country or league…",
                        label_visibility="collapsed", key="league_pick")
    if not pick:
        return
    src, ref = choices.get(pick, ("wiki", pick))
    st.subheader(pick.split(" (")[0] if src == "wiki" and pick in choices else pick)
    if src == "espn":
        render_espn_league(ref, pick)
    else:
        render_wiki_league(ref)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<div class="hero-title">⚽ Match Simulator</div>'
                '<div class="hero-sub">Any club. Any nation. Ninety minutes.</div>',
                unsafe_allow_html=True)
    t_sim, t_leagues = st.tabs(["⚽ Simulator", "📊 Leagues"])
    with t_sim:
        render_simulator()
    with t_leagues:
        render_leagues()


if __name__ == "__main__":
    main()
