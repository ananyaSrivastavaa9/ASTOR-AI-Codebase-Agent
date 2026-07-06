import re
import gradio as gr
import markdown

from agent import run_agent_stream
from indexer import rebuild_index

# ----------------------------------------------------------------------------
# Source extraction
# ----------------------------------------------------------------------------

def extract_sources(text):
    """Pull repo-aware Repo/File citation pairs out of an agent answer.
    Only the exact 'Repo: X\\nFile: Y' pairs emitted by the backend count —
    no fallback scanning of markdown/code snippets, since that's what was
    producing noisy, non-repo-aware chips."""
    if not text:
        return []

    sources = set()

    repo_matches = re.findall(
        r"Repo:\s*([^\n]+)\nFile:\s*([^\n]+)",
        text,
    )

    for repo, file in repo_matches:
        sources.add(f"{repo.strip()} · {file.strip()}")

    return sorted(sources)


def render_answer(content, sources):
    """Build the final answer card with source chips (cream premium card).
    Returns an empty string when there's nothing to show — the card itself
    is hidden by the caller until a real answer exists."""
    if not content or not content.strip():
        return ""

    body = content.strip()
    body_html = markdown.markdown(
      body,
      extensions=["fenced_code", "tables", "nl2br"],
    )

    sources_block = ""
    if sources:
        chips = "".join(f"<span class='chip'>{s}</span>" for s in sources)
        sources_block = (
            "<div class='answer-card__rule'></div>"
            "<div class='sources-label'>Sources</div>"
            f"<div class='chip-row'>{chips}</div>"
        )

    return (
        "<div class='answer-card'>"
        "<div class='answer-card__head'>"
        "<span class='spark-ico'></span><span class='answer-card__title'>Answer</span>"
        "</div>"
        "<div class='answer-card__rule'></div>"
        f"<div class='answer-card__body'>{body_html}</div>"
        f"{sources_block}"
        "</div>"
    )


def render_index_status(state, title, subtitle):
    """Nested status card in the sidebar (Ready / Indexing / Indexed / Failed)."""
    return (
        f"<div class='status-card status-card--{state}'>"
        f"<div class='status-card__row'><span class='status-dot'></span>"
        f"<span class='status-card__title'>{title}</span></div>"
        f"<div class='status-card__sub'>{subtitle}</div>"
        "</div>"
    )


def render_thinking(text, active):
    """Compact single-line thinking status shown only while streaming."""
    if not text:
        return ""
    safe = text.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    state = "active" if active else "idle"
    return (
        f"<div class='think-line think-line--{state}'>"
        "<span class='think-dot'></span>"
        f"<span class='think-text' title='{safe}'>{safe}</span>"
        "</div>"
    )


# ----------------------------------------------------------------------------
# Backend handlers
# ----------------------------------------------------------------------------

def handle_index(repo_path_val, repo_path2_val):
    if not repo_path_val.strip():
      return "⚠ Enter at least one repository path."

    repo_paths = [repo_path_val.strip()]

    if repo_path2_val.strip():
      repo_paths.append(repo_path2_val.strip())

    try:
      rebuild_index(repo_paths)
      return f"✓ Indexed {len(repo_paths)} repositories."
    except Exception as exc:
      return f"✗ Indexing failed: {exc}"


def handle_ask(question_val, current_trace):
    if not question_val or not question_val.strip():
        yield gr.update(value="", visible=False), gr.update(value="", visible=False)
        return

    trace_lines = []
    last_chunk = ""

    for chunk in run_agent_stream(question_val):
        last_chunk = chunk
        trace_lines.append(chunk)
        yield (
            gr.update(value=render_thinking(chunk, True), visible=True),
            gr.update(value="", visible=False),
        )

    sources = extract_sources(last_chunk)
    yield (
        gr.update(value="", visible=False),
        gr.update(value=render_answer(last_chunk, sources), visible=True),
    )


def _fill(template):
    def inner(repo_path_val):
        repo = repo_path_val.strip() if repo_path_val and repo_path_val.strip() else "the repo"
        return template.format(repo=repo)
    return inner


# ----------------------------------------------------------------------------
# Inline icon library (Feather-style, embedded as CSS data-URIs)
# ----------------------------------------------------------------------------

def _svg(inner, color, size=24):
    raw = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
        f"viewBox='0 0 24 24' fill='none' stroke='{color}' stroke-width='2' "
        f"stroke-linecap='round' stroke-linejoin='round'>{inner}</svg>"
    )
    return raw.replace("#", "%23").replace("\n", "")


ICON_PATHS = {
    "folder": "<path d='M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'/>",
    "search": "<circle cx='11' cy='11' r='8'/><line x1='21' y1='21' x2='16.65' y2='16.65'/>",
    "database": "<ellipse cx='12' cy='5' rx='9' ry='3'/><path d='M21 12c0 1.66-4 3-9 3s-9-1.34-9-3'/><path d='M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5'/>",
    "book": "<path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/><path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/>",
    "route": "<line x1='6' y1='3' x2='6' y2='15'/><circle cx='18' cy='6' r='3'/><circle cx='6' cy='18' r='3'/><path d='M18 9a9 9 0 0 1-9 9'/>",
    "shield": "<path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/>",
    "bug": "<circle cx='12' cy='13' r='6'/><line x1='12' y1='7' x2='12' y2='4'/><line x1='8' y1='9' x2='5' y2='6'/><line x1='16' y1='9' x2='19' y2='6'/><line x1='6' y1='14' x2='3' y2='14'/><line x1='18' y1='14' x2='21' y2='14'/><line x1='7' y1='18' x2='4' y2='20'/><line x1='17' y1='18' x2='20' y2='20'/>",
}

MUTED = "%238a7fa0"
LAVENDER = "%23cdb8ff"

ICON_FOLDER = _svg(ICON_PATHS["folder"], MUTED, 18)
ICON_SEARCH = _svg(ICON_PATHS["search"], MUTED, 18)
ICON_DATABASE = _svg(ICON_PATHS["database"], LAVENDER, 18)
ICON_BOOK = _svg(ICON_PATHS["book"], LAVENDER, 18)
ICON_BUG = _svg(ICON_PATHS["bug"], LAVENDER, 18)
ICON_ROUTE = _svg(ICON_PATHS["route"], LAVENDER, 18)
ICON_SHIELD = _svg(ICON_PATHS["shield"], LAVENDER, 18)


# ----------------------------------------------------------------------------
# Visual assets (inline, no external files)
# ----------------------------------------------------------------------------

ROBOT_BADGE = """
<div class="robot-badge">
  <svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="eye" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#d8c3ff"/>
        <stop offset="100%" stop-color="#8f6ef2"/>
      </linearGradient>
    </defs>
    <line x1="20" y1="4" x2="20" y2="9" stroke="#5a4a80" stroke-width="2" stroke-linecap="round"/>
    <circle cx="20" cy="3.5" r="2.2" fill="#c9a7ff"/>
    <rect x="8" y="9" width="24" height="22" rx="9" fill="#241a3a" stroke="#4a3b73" stroke-width="1.4"/>
    <rect x="13" y="17" width="14" height="8" rx="4" fill="url(#eye)"/>
    <circle cx="17.6" cy="21" r="1.5" fill="#241a3a"/>
    <circle cx="22.4" cy="21" r="1.5" fill="#241a3a"/>
  </svg>
</div>
"""

SPLASH_HTML = """
<div class="splash" id="astor-splash">
  <div class="splash__mark">A S T O R</div>
  <div class="splash__sub">codebase intelligence</div>
</div>
"""

SHIELD_CARD = """
<div class="trust-note">
  <div class="trust-note__title">Your code stays local</div>
  <div class="trust-note__sub">Nothing is stored or shared.</div>
</div>
"""

# ----------------------------------------------------------------------------
# Stylesheet
# ----------------------------------------------------------------------------

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap');

:root{{
  --ink:#f2ece0;
  --ink-dim:#9a92ab;
  --ink-faint:#726b85;
  --accent:#8f6ef2;
  --accent-soft:#c9a7ff;
  --accent-line:rgba(157,124,242,0.35);
  --line:rgba(255,255,255,0.07);
  --line-soft:rgba(255,255,255,0.045);
}}

*, *::before, *::after{{ box-sizing:border-box !important; }}

html, body{{ height:100%; margin:0; padding:0; overflow:hidden; }}

.gradio-container{{
  background:
    radial-gradient(ellipse 900px 620px at 88% 2%, rgba(255,196,148,0.30), transparent 60%),
    radial-gradient(ellipse 700px 560px at 95% 14%, rgba(255,140,120,0.14), transparent 55%),
    linear-gradient(165deg, #140e21 0%, #0d0916 55%, #0a0712 100%) !important;
  font-family:'Manrope', sans-serif !important;
  color: var(--ink) !important;
  height:100vh !important;
  max-height:100vh !important;
  overflow:hidden !important;
  padding:0 !important;
  margin:0 !important;
}}

/* Gradio wraps our content in its own layout div(s) before .app-shell —
   make sure every link in that chain actually stretches to full height,
   otherwise our panel's height:100% resolves against a collapsed parent
   and its bottom border ends up clipped by the shell's overflow:hidden. */
.gradio-container > .main,
.gradio-container > div{{ height:100%; min-height:0; }}

footer{{display:none !important;}}

/* thin, unobtrusive scrollbars everywhere a scroll region is needed */
*{{ scrollbar-width: thin; scrollbar-color: rgba(157,124,242,0.28) transparent; }}
*::-webkit-scrollbar{{ width:6px; height:6px; }}
*::-webkit-scrollbar-thumb{{ background: rgba(157,124,242,0.28); border-radius:10px; }}
*::-webkit-scrollbar-track{{ background: transparent; }}

/* ---------- Splash intro (unchanged) ---------- */
.splash{{
  position:fixed; inset:0; z-index:9999;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  background: radial-gradient(circle at 50% 45%, #2a1f44 0%, #120c1d 70%);
  animation: splash-fade 3.6s ease forwards;
  pointer-events:none;
}}
.splash__mark{{
  font-family:'Fraunces', serif;
  font-size:3.4rem; letter-spacing:0.55rem; font-weight:600;
  color: var(--accent-soft);
  opacity:0; transform: translateY(14px) scale(0.97);
  animation: splash-rise 1.1s ease-out 0.15s forwards;
  text-shadow: 0 0 36px rgba(157,124,242,0.55);
}}
.splash__sub{{
  margin-top:0.7rem; font-size:0.78rem; letter-spacing:0.32rem; text-transform:uppercase;
  color: var(--ink-dim); opacity:0;
  animation: splash-rise 1.1s ease-out 0.5s forwards;
}}
@keyframes splash-rise{{ to{{ opacity:1; transform: translateY(0) scale(1); }} }}
@keyframes splash-fade{{
  0%{{opacity:1; visibility:visible;}}
  82%{{opacity:1; visibility:visible;}}
  100%{{opacity:0; visibility:hidden;}}
}}

/* ---------- Shell (fixed viewport, no page scroll) ---------- */
.app-shell{{ padding: 14px 6px 12px 6px; height:100vh; max-height:100vh; overflow:hidden; display:flex; flex-direction:column; }}
.app-shell > div{{ min-height:0; }}
.main-row{{ flex:1; min-height:0; display:flex; align-items:stretch; }}
.main-row > div{{ height:100%; min-height:0; }}

/* ---------- Sidebar ---------- */
.sidebar-col{{ height:100%; min-height:0; display:flex; }}
.sidebar-col > div{{ height:100%; min-height:0; display:flex; flex-direction:column; flex:1; }}
.sidebar-panel{{
  background: rgba(255,255,255,0.018);
  border:1px solid var(--line);
  border-radius:22px;
  padding:18px 16px 16px 16px;
  height:100%;
  overflow-y:auto;
  display:flex;
  flex-direction:column;
  gap:0 !important;
}}

.brand{{ display:flex; align-items:center; gap:0.6rem; margin-bottom:1rem; flex-shrink:0; }}
.brand__mark{{
  width:34px; height:34px; border-radius:10px; flex-shrink:0;
  background: linear-gradient(135deg, var(--accent) 0%, #5b3fb0 100%);
  display:flex; align-items:center; justify-content:center;
  font-family:'Fraunces', serif; font-weight:600; color:#fff; font-size:1.05rem;
  box-shadow: 0 0 22px rgba(157,124,242,0.4);
}}
.brand__text{{ font-family:'Fraunces', serif; font-size:1.18rem; letter-spacing:0.05rem; color:var(--ink); line-height:1.1; }}
.brand__tag{{ font-size:0.58rem; color: var(--accent-soft); letter-spacing:0.13rem; text-transform:uppercase; margin-top:1px; font-weight:600; }}

.section-label{{
  font-size:0.63rem; letter-spacing:0.15rem; text-transform:uppercase;
  color: var(--ink-faint); margin: 2px 0 6px 2px; font-weight:700;
}}

/* kill browser-injected autofill icons (Chrome password/contact suggestions)
   that were rendering as stray icons inside the search bar */
input::-webkit-contacts-auto-fill-button,
input::-webkit-credentials-auto-fill-button,
input::-webkit-caps-lock-indicator,
input::-webkit-search-cancel-button,
input::-webkit-search-decoration{{
  visibility:hidden !important;
  display:none !important;
  pointer-events:none !important;
  position:absolute !important;
  right:0 !important;
}}
/* hide any auto-injected Gradio icon buttons (copy/clear) on our custom inputs */
#repo-path-input .icon-button-wrapper,
#question-input .icon-button-wrapper,
#repo-path-input button.icon-button,
#question-input button.icon-button{{
  display:none !important;
}}
/* consistent, subtle motion on every interactive element */
.gradio-container button,
.gradio-container input,
.gradio-container textarea{{
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease, filter 0.15s ease !important;
}}

/* text inputs (dark theme, generic) */
.gradio-container input, .gradio-container textarea{{
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important;
  border-radius: 13px !important;
}}
.gradio-container input:focus, .gradio-container textarea:focus{{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(157,124,242,0.14) !important;
}}
.gradio-container label span{{ color: var(--ink-dim) !important; font-size:0.78rem !important; }}

/* Gradio's Base theme wraps every input in its own container div with a
   default border/background — that outer wrapper is the "second border"
   sitting behind our own rounded <input> border. Strip it on every
   wrapper layer for these three inputs, leaving only the input's own
   rounded border visible. */
#repo-path-input,
#repo-path-input > *,
#repo-path2-input,
#repo-path2-input > *,
#question-input,
#question-input > *{{
  border:none !important;
  background:transparent !important;
  box-shadow:none !important;
  padding:0 !important;
}}

/* repo path input with folder icon — renders as a textarea (via
   lines/max_lines) so it can grow with the text instead of being a
   single-line <input> that's forced to truncate. */
#repo-path-input textarea,
#repo-path2-input textarea{{
  border:1px solid var(--line) !important;
  background-color: rgba(255,255,255,0.03) !important;
  background-image: url("data:image/svg+xml,{ICON_FOLDER}") !important;
  background-repeat:no-repeat !important;
  background-position: 14px 10px !important;
  background-size:16px 16px !important;
  padding:9px 14px 9px 40px !important;
  min-height:38px !important;
  max-height:96px !important;
  border-radius:13px !important;
  white-space:pre-wrap !important;
  word-break:break-all !important;
  overflow-y:auto !important;
  resize:none !important;
  line-height:1.4 !important;
}}
#repo-path-input{{ margin-bottom:8px !important; }}

/* question input with search icon */
#question-input input{{
  background-color: transparent !important;
  border:none !important;
  border-radius:13px !important;
  background-image: url("data:image/svg+xml,{ICON_SEARCH}") !important;
  background-repeat:no-repeat !important;
  background-position: 4px center !important;
  background-size:18px 18px !important;
  padding-left:30px !important;
  height:48px !important;
  font-size:0.95rem !important;
  box-shadow:none !important;
  white-space:nowrap !important;
  text-overflow:ellipsis !important;
  overflow:hidden !important;
}}
#question-input input:focus{{ box-shadow:none !important; }}

/* Index this repo — highlighted primary sidebar button */
#index-btn{{
  background: linear-gradient(135deg, rgba(157,124,242,0.30), rgba(157,124,242,0.12)) !important;
  border:1px solid rgba(157,124,242,0.4) !important;
  color: var(--ink) !important;
  font-weight:600 !important;
  font-size:0.85rem !important;
  border-radius:12px !important;
  text-align:left !important;
  justify-content:flex-start !important;
  position:relative !important;
  padding:9px 30px 9px 36px !important;
  margin-top:8px !important;
  height:auto !important;
  flex-shrink:0;
}}
#index-btn::before{{
  content:''; position:absolute; left:14px; top:50%; transform:translateY(-50%);
  width:16px; height:16px; background-repeat:no-repeat; background-size:contain;
  background-image:url("data:image/svg+xml,{ICON_DATABASE}");
}}
#index-btn::after{{
  content:'\\203A'; position:absolute; right:14px; top:50%; transform:translateY(-58%);
  font-size:1.1rem; color: var(--accent-soft);
}}
#index-btn:hover{{ filter:brightness(1.1); }}

/* status card (Ready / Indexed / Failed) */
.status-card{{
  background: rgba(255,255,255,0.025);
  border:1px solid var(--line);
  border-radius:13px;
  padding:10px 12px;
  margin:10px 0 2px 0;
  flex-shrink:0;
}}
.status-card__row{{ display:flex; align-items:center; gap:8px; }}
.status-dot{{ width:7px; height:7px; border-radius:50%; background:#4ADE80; box-shadow:0 0 8px rgba(74,222,128,0.7); flex-shrink:0; }}
.status-card--warn .status-dot{{ background:#FBBF24; box-shadow:0 0 8px rgba(251,191,36,0.7); }}
.status-card--error .status-dot{{ background:#F87171; box-shadow:0 0 8px rgba(248,113,113,0.7); }}
.status-card__title{{ font-weight:700; font-size:0.82rem; color: var(--ink); }}
.status-card__sub{{ font-size:0.73rem; color: var(--ink-faint); margin-top:3px; margin-left:15px; line-height:1.35; }}

/* quick start rows */
.starter-btn{{
  background: rgba(255,255,255,0.022) !important;
  border:1px solid var(--line) !important;
  color: var(--ink) !important;
  border-radius:12px !important;
  font-size:0.83rem !important;
  font-weight:500 !important;
  text-align:left !important;
  justify-content:flex-start !important;
  position:relative !important;
  padding:10px 30px 10px 34px !important;
  margin-bottom:7px !important;
  height:auto !important;
  flex-shrink:0;
}}
.starter-btn::after{{
  content:'\\203A'; position:absolute; right:14px; top:50%; transform:translateY(-58%);
  font-size:1.05rem; color: var(--ink-faint);
}}
.starter-btn:hover{{ background: rgba(157,124,242,0.10) !important; border-color: var(--accent-line) !important; }}

#q1-btn::before{{
  content:''; position:absolute; left:14px; top:50%; transform:translateY(-50%);
  width:16px; height:16px; background-repeat:no-repeat; background-size:contain;
  background-image:url("data:image/svg+xml,{ICON_BOOK}");
}}
#q2-btn::before{{
  content:''; position:absolute; left:14px; top:50%; transform:translateY(-50%);
  width:16px; height:16px; background-repeat:no-repeat; background-size:contain;
  background-image:url("data:image/svg+xml,{ICON_BUG}");
}}
#q3-btn::before{{
  content:''; position:absolute; left:14px; top:50%; transform:translateY(-50%);
  width:16px; height:16px; background-repeat:no-repeat; background-size:contain;
  background-image:url("data:image/svg+xml,{ICON_ROUTE}");
}}

/* trust note — plain centered text at the bottom of the sidebar, no box */
.trust-note{{
  text-align:center;
  margin-top:auto;
  padding:14px 8px 2px 8px;
  flex-shrink:0;
}}
.trust-note__title{{ font-size:0.82rem; font-weight:700; color:var(--ink); }}
.trust-note__sub{{ font-size:0.74rem; color:var(--ink-faint); margin-top:2px; }}

/* ---------- Center / robot ---------- */
.center-stage{{ display:flex; flex-direction:column; align-items:center; padding: 32px 0 6px 0; flex-shrink:0; }}
.robot-badge{{
  width:64px; height:64px; border-radius:18px;
  background: linear-gradient(160deg, #201638, #130c20);
  display:flex; align-items:center; justify-content:center;
  box-shadow: 0 0 34px rgba(190,150,255,0.32), inset 0 0 0 1px rgba(255,255,255,0.05);
  animation: float 5s ease-in-out infinite;
}}
.robot-badge svg{{ width:30px; height:30px; }}
@keyframes float{{ 0%,100%{{ transform: translateY(0);}} 50%{{ transform: translateY(-5px);}} }}

.headline{{
  font-family:'Fraunces', serif; font-weight:500; font-size:1.7rem;
  color: var(--ink); margin: 14px 0 5px 0; text-align:center;
}}
.subhead{{ color: var(--ink-dim); font-size:0.88rem; margin-bottom:16px; text-align:center; }}

/* search row */
.main-col{{ display:flex; flex-direction:column; height:100%; min-height:0; }}
.search-row{{
  background: rgba(255,255,255,0.035);
  border:1px solid rgba(255,214,170,0.22);
  border-radius:16px;
  padding:6px 6px 6px 16px;
  box-shadow: 0 0 34px rgba(255,196,148,0.06), 0 18px 40px rgba(0,0,0,0.30);
  display:flex; align-items:center; gap:10px;
  flex-shrink:0;
}}
.search-row > *:first-child{{ flex:1; min-width:0; }}
#ask-btn{{ flex:0 0 auto !important; }}

#ask-btn{{
  background: linear-gradient(135deg, var(--accent) 0%, #6c4fd6 100%) !important;
  border:none !important;
  color:#fff !important;
  font-weight:600 !important;
  font-size:0.86rem !important;
  border-radius:11px !important;
  width:auto !important;
  min-width:0 !important;
  padding:0 22px !important;
  height:36px !important;
  box-shadow: 0 8px 20px rgba(124,92,255,0.30) !important;
}}
#ask-btn:hover{{ filter: brightness(1.08); transform: translateY(-1px); }}

/* the scrollable body: thinking line + answer card */
.main-scroll{{ flex:1; min-height:0; overflow-y:auto; padding-right:4px; }}

/* thinking status line */
.think-line{{ display:flex; align-items:center; gap:9px; margin:14px 4px 14px 4px; animation: card-in 0.3s ease; }}
.think-dot{{ width:7px; height:7px; border-radius:50%; background: var(--accent-soft); flex-shrink:0; }}
.think-line--active .think-dot{{ animation: pulse 1.1s ease-in-out infinite; }}
@keyframes pulse{{ 0%,100%{{ opacity:1; transform:scale(1);}} 50%{{ opacity:0.35; transform:scale(0.7);}} }}
.think-text{{
  font-size:0.86rem; color: var(--ink-dim);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:640px;
}}

/* ---------- Answer card (cream, premium) ---------- */
.answer-card{{
  background: linear-gradient(175deg, #f8ecd8 0%, #f1ddbf 100%);
  border-radius:24px;
  padding: 6px 30px 22px 30px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.35);
  animation: card-in 0.45s cubic-bezier(0.2,0.8,0.2,1);
}}
.answer-card__body > *:first-child{{ margin-top:0 !important; }}
@keyframes card-in{{
  from{{ opacity:0; transform: translateY(10px); }}
  to{{ opacity:1; transform: translateY(0); }}
}}
.answer-card__head{{ display:flex; align-items:center; gap:9px; margin-bottom:2px; margin-left:0; }}
.answer-card__head .spark-ico{{ display:none; }}
.spark-ico{{
  width:16px; height:16px; display:inline-block;
  background-repeat:no-repeat; background-size:contain;
  background-image:url("data:image/svg+xml,{_svg('<path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8z"/>', '%237c5cff', 16)}");
}}
.answer-card__title{{ font-family:'Fraunces', serif; font-weight:700; font-size:1.42rem; letter-spacing:0.01rem; color:#4a3018; }}
.answer-card__rule{{ height:1px; background: rgba(90,66,30,0.14); margin:14px 0; }}
.answer-card__body,
.answer-card__body *{{
  font-size:0.98rem;
  line-height:1.7;
  color:#4a3b28 !important;
}}
.answer-card__body h1,
.answer-card__body h2,
.answer-card__body h3,
.answer-card__body h4{{
  font-family:'Fraunces', serif !important;
  font-weight:600 !important;
  font-size:1.08rem !important;
  letter-spacing:0.01rem !important;
  color:#5b3fb0 !important;
  margin:22px 0 8px 0 !important;
  line-height:1.3 !important;
}}
.answer-card__body h1:first-child,
.answer-card__body h2:first-child,
.answer-card__body h3:first-child,
.answer-card__body h4:first-child{{
  margin-top:0 !important;
}}

.answer-card__body p,
.answer-card__body ul,
.answer-card__body ol,
.answer-card__body li{{
  margin:0 0 10px 0 !important;
}}

.answer-card__body hr{{
  border:none !important;
  border-top:1px solid rgba(90,66,30,0.14) !important;
  margin:10px 0 !important;
}}
.sources-label{{ font-size:0.68rem; letter-spacing:0.16rem; text-transform:uppercase; color:#8a7658; font-weight:700; margin-bottom:2px; }}
.chip-row{{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }}
.chip{{
  font-family:'Manrope', monospace; font-size:0.74rem;
  background: rgba(124,92,255,0.12); border:1px solid rgba(124,92,255,0.28);
  color:#5b3fb0; padding: 4px 11px; border-radius:999px;
}}

.astor-footer{{
  text-align:center; color: var(--ink-faint); font-size:0.74rem; letter-spacing:0.05rem;
  padding:10px 0 2px 0; flex-shrink:0; width:100%;
}}

/* ---------- Responsive: stack on narrow / mobile viewports ---------- */
@media (max-width: 860px){{
  html, body{{ overflow:auto; }}
  .gradio-container{{ height:auto !important; max-height:none !important; overflow:auto !important; }}
  .app-shell{{ height:auto; max-height:none; overflow:visible; }}
  .main-row{{ flex-direction:column; }}
  .main-row > div{{ height:auto; }}
  .sidebar-col{{ height:auto; }}
  .sidebar-panel{{ height:auto; overflow-y:visible; }}
  .main-col{{ height:auto; }}
  .main-scroll{{ overflow-y:visible; }}
}}
"""


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------

with gr.Blocks(css=CSS, title="ASTOR — Codebase Agent", theme=gr.themes.Base()) as demo:
    gr.HTML(SPLASH_HTML)

    with gr.Column(elem_classes=["app-shell"]):
        with gr.Row(elem_classes=["main-row"]):
            # ---------------- Sidebar ----------------
            with gr.Column(scale=2, min_width=280, elem_classes=["sidebar-col"]):
                with gr.Column(elem_classes=["sidebar-panel"]):
                    gr.HTML(
                        "<div class='brand'>"
                        "<div class='brand__mark'>A</div>"
                        "<div><div class='brand__text'>ASTOR</div>"
                        "<div class='brand__tag'>codebase agent</div></div>"
                        "</div>"
                    )

                    gr.HTML("<div class='section-label'>Repository</div>")
                    repo_path = gr.Textbox(
                        placeholder="/path/to/your/repo",
                        label="Repository path",
                        show_label=False,
                        container=False,
                        elem_id="repo-path-input",
                        lines=1,
                        max_lines=4,
                    )
                    repo_path2 = gr.Textbox(
                      placeholder="Second repository (optional)",
                      show_label=False,
                      container=False,
                      elem_id="repo-path2-input",
                      lines=1,
                      max_lines=4,
                    )
                    index_btn = gr.Button("Index this repo", elem_id="index-btn")
                    index_status = gr.HTML(
                        render_index_status("ok", "Ready", "Index a repository to get started.")
                    )

                    gr.HTML("<div class='section-label' style='margin-top:14px;'>Quick starts</div>")
                    q1 = gr.Button("Explain this repo", elem_id="q1-btn", elem_classes=["starter-btn"])
                    q2 = gr.Button("Find bugs in app.py", elem_id="q2-btn", elem_classes=["starter-btn"])
                    q3 = gr.Button("Review the routing code", elem_id="q3-btn", elem_classes=["starter-btn"])

                    gr.HTML(SHIELD_CARD)

            # ---------------- Main ----------------
            with gr.Column(scale=5, elem_classes=["main-col"]):
                gr.HTML(
                    "<div class='center-stage'>"
                    f"{ROBOT_BADGE}"
                    "<div class='headline'>Ask ASTOR about your codebase</div>"
                    "<div class='subhead'>Index a repository, then ask anything — architecture, bugs, routing, anything in between.</div>"
                    "</div>"
                )

                with gr.Row(elem_classes=["search-row"]):
                    question = gr.Textbox(
                        placeholder="e.g. explain this repository",
                        label="Ask a question about your codebase",
                        show_label=False,
                        container=False,
                        elem_id="question-input",
                    )
                    ask_btn = gr.Button("Ask", elem_id="ask-btn", scale=0, min_width=76)

                with gr.Column(elem_classes=["main-scroll"]):
                    thinking = gr.HTML(value="", visible=False)
                    answer_html = gr.HTML(value="", visible=False)

        gr.HTML("<div class='astor-footer'>ASTOR · reads your code so you don't have to</div>")

    # ---------------- Wiring ----------------
    index_btn.click(
      fn=handle_index,
      inputs=[repo_path, repo_path2],
      outputs=[index_status],
    )

    ask_btn.click(fn=handle_ask, inputs=[question, thinking], outputs=[thinking, answer_html])
    question.submit(fn=handle_ask, inputs=[question, thinking], outputs=[thinking, answer_html])

    q1.click(fn=_fill("explain this repository {repo}"), inputs=[repo_path], outputs=[question])
    q2.click(fn=_fill("find bugs in {repo}/app.py"), inputs=[repo_path], outputs=[question])
    q3.click(fn=_fill("review {repo}/app.py"), inputs=[repo_path], outputs=[question])


if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
    )