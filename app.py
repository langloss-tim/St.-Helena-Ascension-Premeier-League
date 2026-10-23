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
import hashlib
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
# needs nothing but its code. "gb-sct" style codes cover the UK home nations
# and "us-tx" style codes the US states.
FLAG_DIR = Path(__file__).resolve().parent / "flags"
CDN_ROOT = "https://flagcdn.com/w160"


@lru_cache(maxsize=None)
def flag_src(code):
    code = (code or "").strip().lower()
    if not re.fullmatch(r"[a-z]{2}(-[a-z]{2,3})?", code):
        return ""
    try:
        raw = (FLAG_DIR / f"{code}.png").read_bytes()
    except OSError:
        return f"{CDN_ROOT}/{code}.png"
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{ --panel:#141a26; --panel2:#1a2232; --line:rgba(255,255,255,.08); --ink:#eef1f6;
       --muted:rgba(238,241,246,.58); --accent:#2ecc71; }
html{ font-size:17px; }
html, body, [class*="st-"], .stMarkdown, p, span, div, td, th, button{ font-family:'Inter',-apple-system,"Segoe UI",Roboto,sans-serif; }
.block-container{ padding-top:1.6rem; max-width:1120px; }
.hero{ display:flex; align-items:center; gap:.9rem; margin-bottom:.4rem; }
.hero-mark{ width:52px; height:52px; border-radius:14px; display:flex; align-items:center; justify-content:center;
            font-size:28px; background:linear-gradient(135deg,#1f8f4e,#0f5132); box-shadow:0 6px 18px rgba(31,143,78,.35); }
.hero-title{ font-size:2.4rem; font-weight:900; letter-spacing:-1px; line-height:1; margin:0; }
.hero-sub{ font-size:1rem; color:var(--muted); margin:.3rem 0 0; }
.hint{ font-size:.95rem; color:var(--muted); margin:.1rem 0 1rem; }
button[data-baseweb="tab"] p{ font-size:1.02rem !important; font-weight:700 !important; }

/* League header */
.lhead{ display:flex; align-items:center; gap:1rem; background:linear-gradient(135deg,#18263a,#121826);
        border:1px solid var(--line); border-radius:16px; padding:1rem 1.2rem; margin:.4rem 0 1rem; }
.lhead img{ width:58px; height:40px; object-fit:cover; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,.4); }
.lhead .nm{ font-size:1.45rem; font-weight:800; line-height:1.15; }
.lhead .chips{ margin-top:.35rem; display:flex; flex-wrap:wrap; gap:.4rem; }
.chip{ font-size:.72rem; font-weight:700; letter-spacing:.4px; text-transform:uppercase; padding:.2rem .55rem;
       border-radius:99px; background:rgba(255,255,255,.08); color:var(--muted); }
.chip.live{ background:rgba(46,204,113,.16); color:#2ecc71; }

/* Standings */
.card{ background:var(--panel); border:1px solid var(--line); border-radius:14px; overflow:hidden; margin-bottom:1rem; }
.card h4{ margin:0; padding:.7rem 1rem; font-size:.95rem; font-weight:800; border-bottom:1px solid var(--line); }
.tblwrap{ overflow-x:auto; -webkit-overflow-scrolling:touch; }
.tbl{ width:100%; border-collapse:collapse; font-size:.95rem; }
.tbl th{ text-transform:uppercase; font-size:.7rem; letter-spacing:.6px; color:var(--muted); font-weight:700;
         padding:.6rem .45rem; background:var(--panel2); text-align:center; }
.tbl td{ padding:.55rem .45rem; border-top:1px solid var(--line); text-align:center; white-space:nowrap;
         font-variant-numeric:tabular-nums; }
.tbl tbody tr:hover td{ background:rgba(255,255,255,.03); }
.tbl td.team, .tbl th.team{ text-align:left; }
.tbl td.team{ font-weight:600; }
.tbl td.pos{ font-weight:800; width:2.2rem; box-shadow:inset 4px 0 0 var(--band, transparent); }
.tbl td.pts{ font-weight:900; font-size:1.02rem; }
.tbl td.gdp{ color:#2ecc71; } .tbl td.gdn{ color:#ef5350; }
.crest{ width:24px; height:24px; object-fit:contain; vertical-align:middle; margin-right:.55rem; }
.ini{ display:inline-flex; width:24px; height:24px; border-radius:50%; align-items:center; justify-content:center;
      font-size:.62rem; font-weight:800; color:#fff; vertical-align:middle; margin-right:.55rem; }
.legend{ font-size:.8rem; color:var(--muted); padding:.6rem 1rem .75rem; border-top:1px solid var(--line); }
.legend span{ display:inline-flex; align-items:center; margin:.15rem 1.1rem .15rem 0; }
.legend i{ display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:.4rem; }

/* Matches */
.mday{ font-size:.78rem; font-weight:800; letter-spacing:.6px; text-transform:uppercase; color:var(--muted);
       margin:1.1rem 0 .45rem; }
.match{ display:grid; grid-template-columns:1fr 5.4rem 1fr; gap:.6rem; align-items:center; background:var(--panel);
        border:1px solid var(--line); border-radius:12px; padding:.65rem .9rem; margin-bottom:.45rem; }
.match .h, .match .a{ display:flex; align-items:center; gap:.5rem; min-width:0; font-weight:600; }
.match .h{ justify-content:flex-end; text-align:right; } .match .a{ justify-content:flex-start; }
.match .h .crest, .match .h .ini{ margin:0; } .match .a .crest, .match .a .ini{ margin:0; }
.match .tn{ overflow:hidden; text-overflow:ellipsis; }
.match .sc{ font-weight:900; font-size:1.15rem; text-align:center; background:var(--panel2); border-radius:8px;
            padding:.25rem 0; font-variant-numeric:tabular-nums; }
.match .sc.pre{ font-size:.85rem; font-weight:700; color:var(--muted); }
.match .st{ font-size:.68rem; color:var(--muted); text-align:center; font-weight:700; margin-top:.2rem;
            text-transform:uppercase; letter-spacing:.4px; }
.match .live{ color:#2ecc71; }
.match .lose{ color:var(--muted); font-weight:500; }
@media (max-width:640px){
  html{ font-size:15px; }
  .hero-title{ font-size:1.8rem; }
  .match{ grid-template-columns:1fr 4.4rem 1fr; padding:.55rem .6rem; gap:.35rem; font-size:.88rem; }
  .lhead{ padding:.8rem; } .lhead .nm{ font-size:1.15rem; }
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


# Bump when wiki_league's result changes shape: the cache is keyed on this
# wrapper, not on leagues.py, so old results would otherwise outlive a deploy.
WIKI_SHAPE = 2


@st.cache_data(ttl=3600, show_spinner=False)
def _wiki(query, shape=WIKI_SHAPE):
    found = leagues.wiki_league(query)
    if found:
        for k in ("standings", "matches", "facts"):
            found.setdefault(k, [])
    return found


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _crest(url, name):
    """The club badge when the source has one; otherwise its initials on a
    colour picked from the name, so every club always looks the same."""
    if url:
        return f'<img class="crest" src="{_e(url)}" alt="" loading="lazy">'
    words = [w for w in re.findall(r"[^\W_]+", str(name)) if w[0].isalnum()]
    ini = "".join(w[0] for w in words[:2]).upper() or "?"
    hue = int(hashlib.md5(str(name).encode()).hexdigest()[:4], 16) % 360
    return f'<span class="ini" style="background:hsl({hue},45%,38%)">{_e(ini)}</span>'


def _gd_class(gd):
    gd = str(gd)
    return "gdp" if gd.startswith("+") and gd != "+0" else "gdn" if gd.startswith("-") else ""


def _standings_html(group, title=""):
    head = ("<tr><th>#</th><th class='team'>Team</th><th>P</th><th>W</th><th>D</th>"
            "<th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th></tr>")
    body = []
    for r in group["rows"]:
        band = f' style="--band:{_e(r["color"])}"' if r["color"] else ""
        body.append(
            f"<tr><td class='pos'{band} title='{_e(r['note'])}'>{_e(r['rank'])}</td>"
            f"<td class='team'>{_crest(r['logo'], r['team'])}{_e(r['team'])}</td>"
            f"<td>{_e(r['gp'])}</td><td>{_e(r['w'])}</td><td>{_e(r['d'])}</td><td>{_e(r['l'])}</td>"
            f"<td>{_e(r['gf'])}</td><td>{_e(r['ga'])}</td>"
            f"<td class='{_gd_class(r['gd'])}'>{_e(r['gd'])}</td>"
            f"<td class='pts'>{_e(r['pts'])}</td></tr>")
    notes = {}
    for r in group["rows"]:
        if r["color"] and r["note"]:
            notes.setdefault(r["note"], r["color"])
    legend = "".join(f'<span><i style="background:{_e(c)}"></i>{_e(n)}</span>'
                     for n, c in notes.items())
    return (f'<div class="card">' + (f"<h4>{_e(title)}</h4>" if title else "")
            + f'<div class="tblwrap"><table class="tbl"><thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>'
            + (f'<div class="legend">{legend}</div>' if legend else "") + "</div>")


def _when(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
    except (ValueError, AttributeError):
        return None


def _match_html(m):
    hs, as_ = m["hs"], m["as"]
    hc = ac = ""
    if m["state"] == "post" and str(hs).isdigit() and str(as_).isdigit():
        hc = " lose" if int(hs) < int(as_) else ""
        ac = " lose" if int(as_) < int(hs) else ""
    dt = _when(m["date"])
    if m["state"] != "pre":
        sc = f'<div class="sc">{_e(hs)} – {_e(as_)}</div>'
        cls = "st live" if m["state"] == "in" else "st"
        status = m["detail"] or ("FT" if m["state"] == "post" else "Live")
    else:
        timed = dt and m["date"][11:16] != "12:00"
        sc = f'<div class="sc pre">{dt.strftime("%-I:%M %p") if timed else "vs"}</div>'
        cls, status = "st", ("ET" if timed else "Upcoming")
    return (f'<div class="match"><div class="h{hc}"><span class="tn">{_e(m["home"])}</span>'
            f'{_crest(m["home_logo"], m["home"])}</div>'
            f'<div>{sc}<div class="{cls}">{_e(status)}</div></div>'
            f'<div class="a{ac}">{_crest(m["away_logo"], m["away"])}'
            f'<span class="tn">{_e(m["away"])}</span></div></div>')


def _group_of(m):
    dt = _when(m["date"])
    if dt:
        return (0, dt.strftime("%Y-%m-%d"), dt.strftime("%A, %B %-d, %Y"))
    if m.get("label"):
        return (1, m["label"], re.sub(r"\s*\(\d{4}-\d\d-\d\d\)", "", m["label"]))
    return (2, m["home"], f"{m['home']} · home games")


def _matches_html(ms, newest_first):
    """Dated games by day; games with no date (from a season results grid)
    by home club, so every club's fixtures sit together."""
    groups = {}
    for m in ms:
        groups.setdefault(_group_of(m), []).append(m)
    dated = sorted((k for k in groups if k[0] == 0), key=lambda k: k[1], reverse=newest_first)
    rest = sorted((k for k in groups if k[0] != 0), key=lambda k: (k[0], k[1].casefold()))
    out = []
    for k in dated + rest:
        out.append(f'<div class="mday">{_e(k[2])}</div>')
        out.extend(_match_html(m) for m in sorted(groups[k], key=lambda m: m["date"]))
    return "".join(out)


def _league_head(name, code, chips):
    flag = flag_src(code)
    img = f'<img src="{flag}" alt="">' if flag else ""
    chip_html = "".join(f'<span class="chip{" live" if live else ""}">{_e(c)}</span>'
                        for c, live in chips)
    st.markdown(f'<div class="lhead">{img}<div><div class="nm">{_e(name)}</div>'
                f'<div class="chips">{chip_html}</div></div></div>', unsafe_allow_html=True)


def _render_tables(groups):
    for g in groups:
        st.markdown(_standings_html(g, g["name"] if len(groups) > 1 else ""),
                    unsafe_allow_html=True)


def _render_match_tabs(ms, note):
    live = [m for m in ms if m["state"] == "in"]
    done = [m for m in ms if m["state"] == "post"]
    todo = [m for m in ms if m["state"] == "pre"]
    labels = [f"✅ Results ({len(done)})", f"📅 Fixtures ({len(todo)})"]
    if live:
        labels.insert(0, f"🔴 Live ({len(live)})")
    tabs = st.tabs(labels)
    if live:
        with tabs[0]:
            st.markdown(_matches_html(live, False), unsafe_allow_html=True)
    with tabs[-2]:
        st.markdown(_matches_html(done, True) or '<div class="hint">No results yet.</div>',
                    unsafe_allow_html=True)
    with tabs[-1]:
        st.markdown(_matches_html(todo, False) or '<div class="hint">No fixtures to come.</div>',
                    unsafe_allow_html=True)
    if note:
        st.caption(note)


# ESPN slug prefix -> flag, for the league header.
ESPN_FLAGS = dict(arg="ar", aus="au", aut="at", bel="be", bol="bo", bra="br", can="ca", chi="cl",
                  chn="cn", col="co", crc="cr", den="dk", ecu="ec", eng="gb-eng", esp="es",
                  fra="fr", ger="de", gre="gr", gua="gt", hon="hn", ind="in", ita="it", jpn="jp",
                  ksa="sa", mex="mx", ned="nl", nor="no", par="py", per="pe", por="pt", rsa="za",
                  rus="ru", sco="gb-sct", slv="sv", swe="se", tur="tr", uru="uy", usa="us", ven="ve")


def render_espn_league(slug, name):
    try:
        groups = _espn_standings(slug)
    except leagues.Unavailable:
        groups = None
    try:
        ms = _espn_matches(slug)
    except leagues.Unavailable:
        ms = None
    teams = sum(len(g["rows"]) for g in groups or [])
    chips = [("Live", True)] + ([(f"{teams} teams", False)] if teams else [])
    _league_head(name, ESPN_FLAGS.get(slug.split(".")[0], ""), chips)
    tab_table, tab_matches = st.tabs(["📊 Table", "⚽ Matches"])
    with tab_table:
        if groups is None:
            st.error("The table couldn't be loaded right now. Try again in a minute.")
        elif not groups:
            st.info(f"{name} has no league table — it's a knockout competition. "
                    "See Matches for its games.")
        _render_tables(groups or [])
    with tab_matches:
        if ms is None:
            st.error("Matches couldn't be loaded right now. Try again in a minute.")
        else:
            _render_match_tabs(ms, "Results from the last two weeks and fixtures for the "
                                   "next two. Times are US Eastern.")


def render_wiki_league(query, name=None, code=""):
    with st.spinner(f"Loading {name or query}…"):
        try:
            found = _wiki(query)
        except leagues.Unavailable:
            st.error("The league couldn't be loaded right now. Try again in a minute.")
            return
    if not found:
        st.warning(f"No league found for “{query}”. Try the league's full name, "
                   "e.g. “Faroe Islands Premier League” or “Gibraltar Football League”.")
        return
    season = re.match(r"^\d{4}(?:–\d{2,4})?", found["title"])
    if not found["standings"]:
        _league_head(name or found["title"], code, [("League facts", False)])
        st.info("This league doesn't publish a table or results online, "
                "so here is what is known about it.")
        rows = "".join(f"<tr><td class='team'>{_e(a)}</td><td class='team'>{_e(b)}</td></tr>"
                       for a, b in found["facts"])
        st.markdown(f'<div class="card"><table class="tbl"><tbody>{rows}</tbody></table></div>',
                    unsafe_allow_html=True)
        st.caption(f"Source: [{found['title']}]({found['url']}) on Wikipedia")
        return
    teams = len(found["standings"][0]["rows"])
    chips = [(f"{season.group(0)} season", False) if season else ("Latest season", False),
             (f"{teams} teams", False), (f"{len(found['matches'])} games", False)]
    _league_head(name or found["title"], code, chips)
    tab_table, tab_matches = st.tabs(["📊 Table", "⚽ Matches"])
    with tab_table:
        _render_tables(found["standings"])
    with tab_matches:
        if found["matches"]:
            _render_match_tabs(found["matches"], "")
        else:
            st.info("This season's page lists the table but not the individual games.")
    st.caption(f"Source: [{found['title']}]({found['url']}) on Wikipedia")


def render_leagues():
    st.markdown('<div class="hint">Every country\'s top league is here — the Caribbean, '
                'Africa, Asia, Oceania, Europe and the Island Games — plus the big leagues '
                'and cups. Type a country or a league. Not listed? Type any league name '
                'and press Enter.</div>', unsafe_allow_html=True)
    # label -> ("espn", slug, name, code) or ("wiki", query, name, code)
    choices = {n: ("espn", s, n, "") for s, n in leagues.espn_leagues()}
    # getattr: Streamlit Cloud can keep an older leagues module loaded for a
    # moment after a deploy; the big list still works without the extras.
    for region, country, code, query in getattr(leagues, "world_leagues", list)():
        shown = query.lstrip("=")      # "=" marks an exact-title entry
        choices.setdefault(f"{country} — {shown} ({region})",
                           ("wiki", query, f"{country} — {shown}", code))
    pick = st.selectbox("League", sorted(choices, key=str.casefold), index=None,
                        accept_new_options=True, placeholder="Type a country or league…",
                        label_visibility="collapsed", key="league_pick")
    if not pick:
        return
    src, ref, name, code = choices.get(pick, ("wiki", pick, None, ""))
    if src == "espn":
        render_espn_league(ref, name)
    else:
        render_wiki_league(ref, name, code)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<div class="hero"><div class="hero-mark">⚽</div><div>'
                '<div class="hero-title">Match Simulator</div>'
                '<div class="hero-sub">Any club. Any nation. Every league.</div></div></div>',
                unsafe_allow_html=True)
    t_sim, t_leagues = st.tabs(["⚽ Simulator", "📊 Leagues"])
    with t_sim:
        render_simulator()
    with t_leagues:
        render_leagues()


if __name__ == "__main__":
    main()
