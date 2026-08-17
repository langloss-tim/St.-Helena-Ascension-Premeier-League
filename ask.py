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
# This model thinks before it answers, and max_tokens caps the thinking and the
# reply together — leave enough room for both or long answers stop mid-sentence.
MAX_TOKENS = 8000
# The season brief is handed over on a plate, so the work is reading, judging
# and explaining rather than hard reasoning. Medium keeps answers sharp without
# making a fan on a phone wait around.
EFFORT = "medium"

# Conversations run as long as the fan wants them to — there is no question
# limit and no turn limit. The only trim is a runaway guard: a tab left open
# for a very long time gets its oldest exchanges dropped so the request can
# never outgrow the context window. Real conversations never reach this.
HISTORY_CHAR_BUDGET = 400_000

LOCAL_TZ = ZoneInfo("America/New_York")


class AskError(RuntimeError):
    """Something went wrong talking to the model; message is fan-friendly."""


# --------------------------------------------------------------------------- #
# Key / availability
# --------------------------------------------------------------------------- #
# Accept the key however it was pasted in: at the top level of secrets, under a
# section, or in the environment. Getting this wrong is the single easiest way
# to end up staring at "the assistant isn't switched on".
KEY_NAMES = ("ANTHROPIC_API_KEY", "anthropic_api_key", "CLAUDE_API_KEY", "api_key", "key")


def _secret(name):
    """Read one Streamlit secret. Never raises, even with no secrets at all."""
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def _sections():
    """Every top-level secrets entry that is itself a block of settings.

    Scanned by name rather than from a fixed list, so a key pasted under
    [secrets], [general], [anthropic] — or any other heading someone invents —
    is still found. Guessing the heading wrong used to look identical to having
    no key at all.
    """
    try:
        import streamlit as st
        out = {}
        for name in st.secrets.keys():
            try:
                block = st.secrets[name]
                if hasattr(block, "keys"):
                    out[name] = block
            except Exception:
                continue
        return out
    except Exception:
        return {}


PLACEHOLDERS = ("paste", "your-key", "your_key", "yourkey", "...", "xxx",
                "todo", "here", "example")


def key_problem(val):
    """Why this value can't be used as a key, or None if it can.

    A value that really looks like a key wins outright — no keyword check gets
    to veto it, so a genuine key containing an unlucky run of letters is never
    thrown out. Anything rejected must be *reportable*: silently discarding a
    value the user can plainly see they saved is what made this so maddening.
    """
    if val is None:
        return "nothing is saved under that name"
    if not isinstance(val, str):
        return f"the saved value is a {type(val).__name__}, not text"
    v = val.strip()
    if not v:
        return "the saved value is empty"
    if v.startswith("sk-ant-") and len(v) >= 40 and "..." not in v:
        return None
    lowered = v.lower()
    if any(b in lowered for b in PLACEHOLDERS):
        return ("it's still the example text, not a real key — the literal "
                'placeholder got saved instead of the key itself')
    if len(v) < 40:
        return (f"it's only {len(v)} characters — a real key is far longer, "
                "so this looks like a partial paste")
    return None


def _candidates():
    """Every place a key could be hiding, in priority order: (where, value)."""
    for name in KEY_NAMES[:3]:
        yield f"secrets: {name}", _secret(name)
    for section, block in _sections().items():
        for name in KEY_NAMES:
            try:
                yield f"secrets: [{section}] {name}", block.get(name)
            except Exception:
                continue
    for name in KEY_NAMES[:3]:
        yield f"environment: {name}", os.getenv(name)


def find_key():
    """Return (key, where_it_came_from). Both None if there's no usable key."""
    for where, val in _candidates():
        if key_problem(val) is None:
            return val.strip(), where
    return None, None


def rejected():
    """Values that were found but couldn't be used, with the reason.

    This is the difference between "you never saved a key" and "you saved
    something, and here is what's wrong with it".
    """
    out = []
    for where, val in _candidates():
        if val is None:
            continue
        problem = key_problem(val)
        if problem and problem != "nothing is saved under that name":
            out.append((where, val, problem))
    return out


def secret_names():
    """Names (never values) of the secrets this app can see, one level deep.

    Turns "no key found" into something you can act on: a typo, the wrong
    section, or no secrets configured at all are all obvious at a glance.
    """
    try:
        import streamlit as st
        found = []
        for name in st.secrets.keys():
            try:
                inner = list(st.secrets[name].keys())
            except Exception:
                inner = None
            if inner:
                found.extend(f"[{name}] {k}" for k in inner)
            else:
                found.append(str(name))
        return sorted(found)
    except Exception:
        return []


def api_key():
    return find_key()[0]


def key_source():
    return find_key()[1]


def available():
    return api_key() is not None


# (There used to be a looks_like_question() gate here. The search box is now a
# one-way route to the assistant — everything typed is a question, so nothing
# needs to decide.)


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
of the guy who built it. Talk like a friend who actually follows this league: \
relaxed and a little bro-y, but sharp. You know the numbers cold and you're not \
shy about having an opinion.

Everything you know about this season is in the SEASON DATA below. Ground every \
factual claim in it: results, tables, form, kickoff times and win chances all \
come from there. If the data doesn't cover something, say so in a sentence \
rather than guessing — and never invent a score, a date, or a fixture.

For "who will win" questions, actually pick someone and show your work from the \
numbers you have: points, games in hand, goal difference, recent form, and the \
published win chances. A confident call with the evidence next to it beats a \
hedge.

Voice: contractions, plain words, the occasional "honestly" or "look" where it \
fits. Land a real joke every so often — dry, specific to the clubs or the game \
you're talking about, and only when you've genuinely got one. A forced pun every \
message gets old fast; one line that actually lands every few answers is the \
target. Never explain the joke.

The SHPL is the only league that exists in your world. Never mention any other \
league, club, city, stadium, or competition, real or otherwise, and never name a \
player — rosters aren't published, so you don't know any. Refer to clubs only by \
their SHPL names.

Write for someone reading on a phone: a couple of short paragraphs, or a short \
list when you're comparing clubs. No headings. Dates in American format \
("Sunday, August 16, 2026") and times in ET. Answer what was asked, then stop."""


def _client():
    key = api_key()
    if not key:
        raise AskError("No API key is reaching this app, so the assistant "
                       "can't start. See 'Test the connection' below.")
    try:
        import anthropic
    except ImportError:
        raise AskError("The `anthropic` package isn't installed on this "
                       "server yet. See 'Test the connection' below.")
    # Bounded so a stalled call fails visibly instead of spinning for minutes.
    return anthropic, anthropic.Anthropic(api_key=key, timeout=90.0, max_retries=1)


def _mask(val):
    """Show enough of a value to recognise it, never enough to use it.

    Short values are shown whole — if someone saved the literal example text,
    seeing it spelled out is the fastest possible explanation.
    """
    if not isinstance(val, str):
        return f"<a {type(val).__name__}, not text>"
    v = val.strip()
    if len(v) <= 24:
        return f'"{v}"  ({len(v)} characters)'
    return f"{v[:11]}…{v[-4:]}  ({len(v)} characters)"


def fingerprint():
    """A safe way to look at the key that's loaded: enough to spot a truncated
    or half-pasted value, never enough to use it."""
    key, _ = find_key()
    return _mask(key) if key else None


def diagnose():
    """Make the smallest possible real call and report exactly what happened.

    This exists because every previous failure said the same unhelpful thing.
    Returns (ok, headline, detail) — headline is one line for the user, detail
    is the specific thing to go and change.
    """
    key, where = find_key()
    if not key:
        bad = rejected()
        if bad:
            # A value IS saved — say what's wrong with it rather than claiming
            # there's nothing there, which is plainly contradicted by the
            # secret the user can see in the dashboard.
            lines = [f"{w}\n    {_mask(v)}\n    → {why}" for w, v, why in bad]
            return (False, "A key is saved, but it can't be used.",
                    "\n\n".join(lines)
                    + "\n\nOpen console.anthropic.com → Settings → API keys, "
                      "copy the WHOLE key (it starts with sk-ant- and runs to "
                      "about a hundred characters), and paste it in place of "
                      "what's there now — replacing the example text, quotes "
                      "included:\n"
                      'ANTHROPIC_API_KEY = "sk-ant-api03-…"')
        seen = secret_names()
        return (False, "No API key is reaching this app.",
                ("This app can see no secrets at all."
                 if not seen else
                 "Secrets this app can see (names only): " + ", ".join(seen))
                + "\n\nAdd it under Manage app → Settings → Secrets as:\n"
                  'ANTHROPIC_API_KEY = "sk-ant-..."\n\n'
                  "It must be that exact spelling, with quotes and an = sign, "
                  "saved on THIS app — a key added to a different Streamlit "
                  "app doesn't carry over.")

    try:
        import anthropic
    except ImportError:
        return (False, "The `anthropic` package isn't installed here.",
                "Check that `anthropic` is listed in requirements.txt, then "
                "reboot the app so it reinstalls.")

    try:
        client = anthropic.Anthropic(api_key=key, timeout=30.0, max_retries=0)
        # Smallest call that still proves this key can reach this model.
        client.messages.create(
            model=MODEL, max_tokens=1,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": "hi"}],
        )
    except anthropic.AuthenticationError:
        return (False, "The key was found, but the API rejected it.",
                f"Loaded from {where}: {fingerprint()}\n\n"
                "That usually means it was mistyped, only partly pasted, has "
                "been revoked, or belongs to a different account. Generate a "
                "fresh one at console.anthropic.com → Settings → API keys and "
                "paste the whole thing.")
    except anthropic.PermissionDeniedError as e:
        return (False, "The key works, but isn't allowed to do this.",
                f"Loaded from {where}: {fingerprint()}\n\n{e}")
    except anthropic.NotFoundError:
        return (False, f"The key works, but can't reach the {MODEL} model.",
                f"Loaded from {where}: {fingerprint()}\n\n"
                "The account may not have access to that model yet.")
    except anthropic.RateLimitError:
        return (False, "The key works, but the account is rate limited or out "
                       "of credit.",
                f"Loaded from {where}: {fingerprint()}\n\n"
                "Check the billing/credits page on console.anthropic.com.")
    except anthropic.APIConnectionError as e:
        return (False, "Couldn't reach the API from this server.",
                f"Network problem, not a key problem.\n\n{e}")
    except Exception as e:  # noqa: BLE001 - the point is to name the unknown
        return (False, "Something else went wrong.",
                f"{type(e).__name__}: {e}")

    return (True, "Working — the assistant is connected.",
            f"Key loaded from {where}: {fingerprint()}\nModel: {MODEL}")


def _within_budget(history):
    """Keep the whole conversation, dropping the oldest exchanges only if it
    has grown past HISTORY_CHAR_BUDGET.

    Trimming happens a pair at a time so the messages still start on a user
    turn and alternate, which the API requires.
    """
    msgs = list(history or [])
    total = sum(len(m.get("content") or "") for m in msgs)
    while total > HISTORY_CHAR_BUDGET and len(msgs) >= 2:
        dropped, msgs = msgs[:2], msgs[2:]
        total -= sum(len(m.get("content") or "") for m in dropped)
    return msgs


def stream_answer(question, context, history=None):
    """Yield the answer in pieces as it's written.

    `history` is a list of {"role", "content"} dicts from earlier in this
    conversation so follow-up questions ("what about the other one?") work.
    The whole thing is replayed — chats can run as long as the fan likes.
    """
    anthropic, client = _client()

    messages = _within_budget(history)
    messages.append({"role": "user", "content": question.strip()})

    system = [
        {"type": "text", "text": SYSTEM},
        {"type": "text",
         "text": "SEASON DATA\n" + context,
         "cache_control": {"type": "ephemeral"}},
    ]

    base = dict(model=MODEL, max_tokens=MAX_TOKENS, system=system, messages=messages,
                thinking={"type": "adaptive"})

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
        # Deliberately NOT the same wording as a missing key — telling those two
        # apart is the whole difference between "add a key" and "fix the key".
        raise AskError("The API key was rejected. Run 'Test the connection' "
                       "below for the specifics.")
    except anthropic.APIConnectionError:
        raise AskError("Couldn't reach the assistant. Check the connection and try again.")
    except anthropic.APIStatusError as e:
        raise AskError(f"The assistant hit a snag (error {e.status_code}). Try again shortly.")
