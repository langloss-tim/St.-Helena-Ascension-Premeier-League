"""
Ask-the-league assistant.

The sidebar search still answers club and match-day lookups itself (instant, no
API call). Anything that isn't one of those — "who won last night", "who's most
likely to win the title", "how are the Bellboys doing since June" — is routed
here and answered by Claude, grounded in the exact same season snapshot the rest
of the site renders from. No web access, no guessing: if it isn't in the
snapshot, the assistant says so.

Two rules this module exists to protect:
  * the model is only ever shown SHPL names (never the source league's, never a
    venue, never a roster), and
  * every answer is scrubbed on the way out, in case something slips through.

Configuration: an `ANTHROPIC_API_KEY` in Streamlit secrets (or the environment).
Without one the Ask tab politely says the assistant is switched off; nothing
else in the app changes.
"""

import os
import re
from zoneinfo import ZoneInfo

import teams

MODEL = "claude-opus-5"
MAX_TOKENS = 4000
# The season brief is already handed over on a plate, so the work here is
# reading and explaining rather than hard reasoning. Low effort keeps answers
# quick — a fan waiting on a phone notices every second.
EFFORT = "low"

# How much of the back-and-forth to replay on a follow-up question.
MAX_TURNS = 6
# Per-visitor guard rail — this is a public site paying for its own tokens.
MAX_QUESTIONS = 25

LOCAL_TZ = ZoneInfo("America/New_York")


class AskError(RuntimeError):
    """Something went wrong talking to the model; message is fan-friendly."""


# --------------------------------------------------------------------------- #
# Key / availability
# --------------------------------------------------------------------------- #
def api_key():
    """Streamlit secrets first, then the environment. Never raises."""
    try:
        import streamlit as st
        key = st.secrets.get("ANTHROPIC_API_KEY")
        if key:
            return str(key).strip()
    except Exception:
        pass  # no secrets file configured — fall through to the environment
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip() or None


def available():
    return api_key() is not None


def looks_like_question(text):
    """Is this search worth sending to the assistant?

    Deliberately loose — it only runs after the club and match-day lookups have
    both come up empty, so anything with a bit of substance qualifies.
    """
    t = (text or "").strip()
    if len(t) < 4:
        return False
    return t.endswith("?") or len(t.split()) >= 2 or len(t) >= 6


# --------------------------------------------------------------------------- #
# Leak guard: real names never go in, and never come out
# --------------------------------------------------------------------------- #
def _aliases(real_name):
    """Every spelling of a real club name we want to catch in output."""
    out = {real_name}
    flat = real_name.replace(".", "")
    out.add(flat)
    for name in (real_name, flat):
        core = [w for w in name.split() if w.upper() not in ("FC", "SC", "CF", "CITY")]
        joined = " ".join(core)
        if len(joined) >= 4:
            out.add(joined)
    return {a.replace("é", "e") for a in out} | out


def _scrub_map():
    m = {}
    for t in teams.TEAMS:
        for alias in _aliases(t.mls_name):
            m[alias.lower()] = t.shpl_name
    for league in ("Major League Soccer", "M.L.S", "MLS"):
        m[league.lower()] = "the SHPL"
    return m


_SCRUB = _scrub_map()
_SCRUB_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in sorted(_SCRUB, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def scrub(text):
    """Rewrite any real-world club or league name back into SHPL language.

    Belt and braces: the model is never shown these names in the first place.
    Safe to call repeatedly on a growing string while streaming.
    """
    if not text:
        return text
    return _SCRUB_RE.sub(lambda mo: _SCRUB.get(mo.group(0).lower(), "the SHPL"), text)


# --------------------------------------------------------------------------- #
# Season context (SHPL names only — no venues, no rosters, no real names)
# --------------------------------------------------------------------------- #
def _amdate(dt):
    d = dt.astimezone(LOCAL_TZ)
    return f"{d.strftime('%a')}, {d.strftime('%B')} {d.day}, {d.year}"


def _amtime(dt):
    return dt.astimezone(LOCAL_TZ).strftime("%I:%M %p ET").lstrip("0")


def _shortdate(dt):
    """'Sat Feb 21' — the fixture list is long, so every character counts."""
    d = dt.astimezone(LOCAL_TZ)
    return f"{d.strftime('%a')} {d.strftime('%b')} {d.day}"


def _parse(s):
    from datetime import datetime
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _form_strings(matches):
    """Last five results per club, oldest to newest, e.g. 'W W D L W'."""
    seq = {}
    for m in sorted((x for x in matches if x["done"]), key=lambda x: x["when"]):
        for side, other in ((m["home"], m["away"]), (m["away"], m["home"])):
            if side["score"] is None or other["score"] is None:
                continue
            if side["score"] > other["score"]:
                r = "W"
            elif side["score"] < other["score"]:
                r = "L"
            else:
                r = "D"
            seq.setdefault(side["name"], []).append(r)
    return {name: " ".join(v[-5:]) for name, v in seq.items()}


def _rows(feed):
    """Flatten the feed's matches into the small shape this module needs."""
    out = []
    for m in feed.get("matches") or []:
        when = m["start"] if hasattr(m.get("start"), "tzinfo") else _parse(m.get("start"))
        home, away = m.get("home") or {}, m.get("away") or {}
        out.append({
            "id": str(m.get("id")),
            "when": when,
            "state": m.get("state"),
            "done": bool(m.get("completed")),
            "detail": m.get("status_detail") or "",
            "playoff": (m.get("season_slug") or "regular-season") != "regular-season",
            "home": {"name": home.get("shpl_name") or "?", "score": home.get("score")},
            "away": {"name": away.get("shpl_name") or "?", "score": away.get("score")},
        })
    return [r for r in out if r["when"] is not None]


def build_context(feed):
    """A compact, plain-text brief on the whole season. Deterministic, so it
    caches cleanly across questions until the feed itself refreshes."""
    season = feed.get("season") or ""
    matches = _rows(feed)
    winprobs = feed.get("winprobs") or {}
    forms = _form_strings(matches)

    L = [f"ST. HELENA PREMIER LEAGUE — {season} SEASON"]
    gen = _parse(feed.get("generated_at"))
    if gen:
        L.append(f"Data current as of {_amdate(gen)} at {_amtime(gen)}.")
    L.append("Thirty clubs, split between two islands and two conferences. "
             "Rosters and venues are not published, so no player or stadium "
             "information exists in this data.")

    L.append("")
    L.append("=== CONFERENCE TABLES ===")
    for conf in (feed.get("standings") or {}).get("conferences") or []:
        L.append(f"-- {conf.get('name', '')} ({conf.get('island', '')}) --")
        for row in conf.get("table") or []:
            name = row.get("shpl_name", "?")
            form = forms.get(name)
            L.append(
                f"{row.get('rank', '?')}. {name}: {row.get('points', 0)} pts, "
                f"{row.get('played', 0)} played, {row.get('wins', 0)}W-"
                f"{row.get('draws', 0)}D-{row.get('losses', 0)}L, "
                f"{row.get('gf', 0)} scored, {row.get('ga', 0)} conceded, "
                f"goal difference {row.get('gd', 0):+d}"
                + (f", last 5: {form}" if form else "")
            )
        L.append("")

    live = [m for m in matches if m["state"] == "in"]
    if live:
        L.append("=== IN PROGRESS RIGHT NOW ===")
        for m in live:
            L.append(f"{m['home']['name']} {m['home']['score']}-{m['away']['score']} "
                     f"{m['away']['name']} ({m['detail']}) — {m['home']['name']} hosting")
        L.append("")

    played = sorted((m for m in matches if m["done"]), key=lambda m: m["when"])
    L.append(f"=== COMPLETED MATCHES ({len(played)}, oldest first) ===")
    L.append(f"All dates are in {season}. Format: date — home team score-score away team")
    for m in played:
        tag = " [playoff]" if m["playoff"] else ""
        L.append(f"{_shortdate(m['when'])} — {m['home']['name']} "
                 f"{m['home']['score']}-{m['away']['score']} {m['away']['name']}{tag}")
    L.append("")

    upcoming = sorted((m for m in matches if m["state"] == "pre"), key=lambda m: m["when"])
    L.append(f"=== UPCOMING FIXTURES ({len(upcoming)}, soonest first) ===")
    L.append("Format: date, kickoff — home team vs away team, then win chances "
             "where a forecast exists. The home team hosts.")
    for m in upcoming:
        line = (f"{_shortdate(m['when'])}, {_amtime(m['when'])} — "
                f"{m['home']['name']} vs {m['away']['name']}")
        wp = winprobs.get(m["id"])
        if wp:
            line += (f" — win chance: {m['home']['name']} {wp.get('home_pct')}%, "
                     f"draw {wp.get('draw_pct')}%, {m['away']['name']} {wp.get('away_pct')}%")
        L.append(line)

    return "\n".join(L)


# --------------------------------------------------------------------------- #
# The model call
# --------------------------------------------------------------------------- #
SYSTEM = """\
You are the resident match analyst for the St. Helena Premier League (SHPL), a \
30-club league played across the islands of St. Helena and Ascension. You answer \
questions from fans on the league's own website — most often the son or brother \
of the person who built it, so keep it warm and plain-spoken.

Everything you know about this season is in the SEASON DATA below. Ground every \
factual claim in it: results, tables, form, kickoff times and win chances all \
come from there. If the data doesn't cover something, say so in a sentence \
rather than guessing — and never invent a score, a date, or a fixture.

For "who will win" questions, give a real opinion and show your reasoning from \
the numbers you have: points, games in hand, goal difference, recent form, and \
the published win chances for upcoming fixtures. A confident answer with the \
evidence beside it beats a hedge.

The SHPL is the only league that exists in your world. Never mention any other \
league, club, city, stadium, or competition, real or otherwise, and never name a \
player — rosters aren't published, so you don't know any. Refer to clubs only by \
their SHPL names.

Write for a fan reading on a phone: two or three short paragraphs, or a short \
list when you're comparing clubs. No headings. Dates in American format \
("Sunday, August 16, 2026") and times in ET. Keep it focused — answer what was \
asked, then stop."""


def _client():
    key = api_key()
    if not key:
        raise AskError("The assistant isn't switched on right now.")
    try:
        import anthropic
    except ImportError:
        raise AskError("The assistant isn't installed on this server yet.")
    # Bounded so a stalled call fails visibly instead of spinning for minutes.
    return anthropic, anthropic.Anthropic(api_key=key, timeout=90.0, max_retries=1)


def stream_answer(question, context, history=None):
    """Yield the answer in pieces as it's written.

    `history` is a list of {"role", "content"} dicts from earlier in this
    conversation so follow-up questions ("what about the other one?") work.
    """
    anthropic, client = _client()

    messages = list(history or [])[-(MAX_TURNS * 2):]
    messages.append({"role": "user", "content": question.strip()})

    system = [
        {"type": "text", "text": SYSTEM},
        {"type": "text",
         "text": "SEASON DATA\n" + context,
         "cache_control": {"type": "ephemeral"}},
    ]

    base = dict(model=MODEL, max_tokens=MAX_TOKENS, system=system, messages=messages)

    def open_stream():
        """Ask for medium effort, but never let that be the reason we fail.

        Older SDK builds don't type `output_config`, so it rides in extra_body;
        if the request is rejected for it, fall back to the model's default.
        """
        try:
            return client.messages.stream(
                **base, extra_body={"output_config": {"effort": EFFORT}})
        except TypeError:
            return client.messages.stream(**base)

    try:
        manager = open_stream()
        try:
            stream = manager.__enter__()          # this is where the request goes out
        except anthropic.BadRequestError:
            manager = client.messages.stream(**base)
            stream = manager.__enter__()
        try:
            for chunk in stream.text_stream:
                yield chunk
            final = stream.get_final_message()
        finally:
            manager.__exit__(None, None, None)
        if final.stop_reason == "refusal":
            raise AskError("The assistant would rather not answer that one — "
                           "try asking about the league.")
    except AskError:
        raise
    except anthropic.RateLimitError:
        raise AskError("The assistant is busy right now. Give it a minute and ask again.")
    except anthropic.AuthenticationError:
        raise AskError("The assistant isn't switched on right now.")
    except anthropic.APIConnectionError:
        raise AskError("Couldn't reach the assistant. Check the connection and try again.")
    except anthropic.APIStatusError as e:
        raise AskError(f"The assistant hit a snag (error {e.status_code}). Try again shortly.")
