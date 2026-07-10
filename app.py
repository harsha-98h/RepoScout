"""
RepoScout — Streamlit Web UI
Dark neon glassmorphism aesthetic with live agent reasoning trace.

Run locally:
    streamlit run app.py

On AWS (App Runner / EC2):
    Set OPENAI_API_KEY and GITHUB_TOKEN as environment variables.
"""

from __future__ import annotations

import re
import time
from typing import Optional

import streamlit as st

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="RepoScout — AI GitHub Discovery",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

import config
from agent.reposcout_agent import RepoScoutAgent
from tools.github_search import GitHubSearchTool
from tools.repo_evaluator import RepoEvaluator
from utils.exceptions import PromptInjectionDetected
from utils.sanitizer import sanitize_query

# ── Custom CSS — dark neon glassmorphism ─────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Global reset ── */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #050b14; color: #e2e8f0; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1628 0%, #0d1f3c 100%);
        border-right: 1px solid rgba(0, 255, 163, 0.15);
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    /* ── Hero banner ── */
    .hero {
        background: linear-gradient(135deg, #0a1628 0%, #0d2244 50%, #0a1628 100%);
        border: 1px solid rgba(0, 255, 163, 0.2);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -50%;  left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(0,255,163,0.05) 0%, transparent 60%),
                    radial-gradient(circle at 70% 50%, rgba(56,189,248,0.05) 0%, transparent 60%);
        pointer-events: none;
    }
    .hero-title {
        font-size: 2.8rem; font-weight: 800; margin: 0; line-height: 1.1;
        background: linear-gradient(135deg, #00ffa3, #38bdf8, #818cf8);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero-sub {
        font-size: 1.05rem; color: #64748b; margin-top: 0.6rem;
        font-weight: 400;
    }
    .hero-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(0,255,163,0.1); border: 1px solid rgba(0,255,163,0.3);
        color: #00ffa3; border-radius: 20px; padding: 4px 14px;
        font-size: 0.78rem; font-weight: 500; margin-top: 1rem; margin-right: 0.5rem;
    }

    /* ── Search box ── */
    .stTextInput > div > div > input {
        background: rgba(15, 28, 50, 0.8) !important;
        border: 1px solid rgba(0, 255, 163, 0.3) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-size: 1rem !important;
        padding: 0.75rem 1.1rem !important;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .stTextInput > div > div > input:focus {
        border-color: #00ffa3 !important;
        box-shadow: 0 0 0 3px rgba(0,255,163,0.12) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #00ffa3, #00d4aa) !important;
        color: #050b14 !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.6rem 1.8rem !important;
        transition: transform 0.15s, box-shadow 0.15s !important;
        letter-spacing: 0.02em;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(0,255,163,0.35) !important;
    }

    /* ── Repo cards ── */
    .repo-card {
        background: linear-gradient(135deg, rgba(10,22,40,0.9), rgba(13,31,60,0.9));
        border: 1px solid rgba(0, 255, 163, 0.12);
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
        position: relative; overflow: hidden;
    }
    .repo-card:hover {
        border-color: rgba(0, 255, 163, 0.4);
        transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(0,255,163,0.12);
    }
    .repo-card::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, #00ffa3, #38bdf8, #818cf8);
        opacity: 0; transition: opacity 0.2s;
    }
    .repo-card:hover::before { opacity: 1; }
    .repo-name {
        font-size: 1.15rem; font-weight: 700; color: #e2e8f0;
        text-decoration: none;
    }
    .repo-desc { color: #94a3b8; font-size: 0.9rem; margin: 0.5rem 0; line-height: 1.5; }
    .repo-meta { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.8rem; }
    .badge {
        display: inline-flex; align-items: center; gap: 4px;
        border-radius: 8px; padding: 3px 10px;
        font-size: 0.78rem; font-weight: 500;
    }
    .badge-stars { background: rgba(251,191,36,0.15); color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
    .badge-lang  { background: rgba(129,140,248,0.15); color: #818cf8; border: 1px solid rgba(129,140,248,0.25); }
    .badge-score-high { background: rgba(0,255,163,0.12); color: #00ffa3; border: 1px solid rgba(0,255,163,0.3); }
    .badge-score-mid  { background: rgba(251,191,36,0.12); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }
    .badge-score-low  { background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.3); }
    .repo-url { color: #38bdf8; font-size: 0.82rem; margin-top: 0.4rem; word-break: break-all; }

    /* ── Trace panel ── */
    .trace-step {
        border-radius: 10px; padding: 0.8rem 1rem;
        margin-bottom: 0.6rem; font-size: 0.87rem;
        border-left: 3px solid;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.6;
    }
    .trace-thought    { background: rgba(56,189,248,0.07);  border-color: #38bdf8; color: #93c5fd; }
    .trace-action     { background: rgba(251,191,36,0.07);  border-color: #fbbf24; color: #fcd34d; }
    .trace-observation{ background: rgba(129,140,248,0.07); border-color: #818cf8; color: #a5b4fc; }
    .trace-final      { background: rgba(0,255,163,0.07);   border-color: #00ffa3; color: #6ee7b7; }

    /* ── Section headers ── */
    .section-header {
        font-size: 1rem; font-weight: 600; color: #00ffa3;
        text-transform: uppercase; letter-spacing: 0.1em;
        margin: 1.5rem 0 0.8rem;
        display: flex; align-items: center; gap: 8px;
    }

    /* ── Hide default Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session state init ────────────────────────────────────────────────────────
def _init_state() -> None:
    defaults = {
        "agent": None,
        "history": [],
        "results": [],
        "trace_steps": [],
        "query_count": 0,
        "repo_count": 0,
        "elapsed": 0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ── Agent builder (cached) ────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def build_agent() -> RepoScoutAgent:
    agent = RepoScoutAgent()
    github_tool = GitHubSearchTool()
    evaluator = RepoEvaluator()

    def search_github_wrapper(query: str) -> str:
        numbers = re.findall(r"\b(\d+)\b", query)
        max_results = min(max(int(numbers[0]), 5), 20) if numbers else 10
        fetch_count = min(max_results * 2, 30)
        repos = github_tool.search_repositories(query, max_results=fetch_count)
        if not repos:
            return "No repositories found."
        if isinstance(repos, list) and len(repos) == 1 and repos[0].get("error"):
            return repos[0].get("message", "Search failed.")
        quality = evaluator.filter_quality_repos(repos, min_score=40)
        if not quality:
            return "No high-quality repositories found matching your criteria."
        st.session_state["results"] = quality[:max_results]
        parts = []
        for r in quality[:max_results]:
            parts.append(
                f"**{r['name']}** — {r['description']}\n\n"
                f"⭐ Stars: {r['stars']:,}  |  💻 Language: {r['language']}  "
                f"|  Score: {r.get('quality_score', 0)}/100\n\n"
                f"🔗 {r['url']}\n\n"
                f"Why useful: {evaluator.explain_why_useful(r)}"
            )
        return "\n\n---\n\n".join(parts)

    agent.register_tool(
        "search_github", search_github_wrapper,
        "Search GitHub repositories. Embed the count in the query e.g. 'Find 10 AI repos' (default 10, max 20).",
    )
    agent.register_tool(
        "get_repo_details", github_tool.get_repository_details,
        "Get detailed info for a single repository (format: owner/repo).",
    )
    agent.register_tool(
        "read_readme", github_tool.get_readme,
        "Read the README.md of a repository (format: owner/repo).",
    )
    agent.register_tool(
        "analyze_commits", lambda r: github_tool.get_recent_commits(r.strip(), 5),
        "Get the 5 most recent commits for a repository (format: owner/repo).",
    )
    agent.register_tool(
        "read_issues", lambda r: github_tool.get_open_issues(r.strip(), 5),
        "Get the 5 most recent open issues/PRs for a repository (format: owner/repo).",
    )
    return agent


# ── Helpers ───────────────────────────────────────────────────────────────────
def _score_badge(score: int) -> str:
    cls = "score-high" if score >= 70 else ("score-mid" if score >= 40 else "score-low")
    return f'<span class="badge badge-{cls}">⚡ {score}/100</span>'


def _stars_fmt(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def render_repo_cards(repos: list[dict]) -> None:
    for repo in repos:
        score = repo.get("quality_score", 0)
        name = repo.get("name", "—")
        desc = repo.get("description", "No description")
        url = repo.get("url", "#")
        stars = repo.get("stars", 0)
        lang = repo.get("language") or "Unknown"
        st.markdown(
            f"""
            <div class="repo-card">
                <div><a class="repo-name" href="{url}" target="_blank">{name}</a></div>
                <div class="repo-desc">{desc}</div>
                <div class="repo-meta">
                    <span class="badge badge-stars">⭐ {_stars_fmt(stars)}</span>
                    <span class="badge badge-lang">💻 {lang}</span>
                    {_score_badge(score)}
                </div>
                <div class="repo-url">🔗 {url}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_trace(steps: list[dict]) -> None:
    icons = {"thought": "💭", "action": "⚡", "observation": "📊", "final_answer": "✅"}
    css_map = {
        "thought": "trace-thought",
        "action": "trace-action",
        "observation": "trace-observation",
        "final_answer": "trace-final",
    }
    for step in steps:
        stype = step["type"]
        icon = icons.get(stype, "•")
        css = css_map.get(stype, "trace-thought")
        preview = step["content"][:500] + ("…" if len(step["content"]) > 500 else "")
        label = stype.replace("_", " ").upper()
        st.markdown(
            f'<div class="trace-step {css}"><strong>{icon} {label}</strong><br>{preview}</div>',
            unsafe_allow_html=True,
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:1rem 0 1.5rem;">
            <div style="font-size:2.5rem;">🔍</div>
            <div style="font-weight:800;font-size:1.3rem;color:#e2e8f0;">RepoScout</div>
            <div style="color:#64748b;font-size:0.8rem;margin-top:4px;">AI GitHub Discovery</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("**⚙️ Settings**")
    num_results = st.slider("Max results", min_value=3, max_value=20, value=5, step=1)
    min_score = st.slider("Min quality score", min_value=0, max_value=80, value=40, step=5)
    show_trace = st.checkbox("Show reasoning trace", value=True)
    show_history = st.checkbox("Show session history", value=False)
    st.markdown("---")
    st.markdown("**📊 Session Stats**")
    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;gap:0.6rem;margin-top:0.5rem;">
            <div><span style="color:#00ffa3;font-weight:700;font-size:1.2rem;">{st.session_state.query_count}</span>
                 <span style="color:#64748b;font-size:0.8rem;margin-left:6px;">Queries</span></div>
            <div><span style="color:#38bdf8;font-weight:700;font-size:1.2rem;">{st.session_state.repo_count}</span>
                 <span style="color:#64748b;font-size:0.8rem;margin-left:6px;">Repos Found</span></div>
            <div><span style="color:#818cf8;font-weight:700;font-size:1.2rem;">{st.session_state.elapsed:.1f}s</span>
                 <span style="color:#64748b;font-size:0.8rem;margin-left:6px;">Last Query Time</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    api_ok = bool(config.OPENAI_API_KEY)
    gh_ok = bool(config.GITHUB_TOKEN)
    st.markdown(
        f"""
        <div style="font-size:0.82rem;">
            <div style="margin-bottom:4px;">
                {'🟢' if api_ok else '🔴'} OpenAI API {'Connected' if api_ok else 'Missing key!'}
            </div>
            <div>
                {'🟢' if gh_ok else '🟡'} GitHub {'Authenticated' if gh_ok else 'Unauthenticated (60 req/hr)'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not api_ok:
        st.error("⚠️ OPENAI_API_KEY not set.")


# ── Main content ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🔍 RepoScout</div>
        <div class="hero-sub">AI-powered GitHub repository discovery using the ReAct reasoning pattern</div>
        <div>
            <span class="hero-badge">⚡ ReAct Agent</span>
            <span class="hero-badge">🔥 GPT-4o-mini</span>
            <span class="hero-badge">🛡️ Injection-Proof</span>
            <span class="hero-badge">⚡ Cached Results</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_input, col_btn = st.columns([5, 1])
with col_input:
    query = st.text_input(
        label="search_query",
        placeholder='e.g. "Find 8 Python AI agent frameworks" or "Top Rust web servers"',
        label_visibility="collapsed",
        key="query_input",
    )
with col_btn:
    search_clicked = st.button("Search 🔍", use_container_width=True)

st.markdown(
    """
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin:0.5rem 0 1.5rem;">
        <span style="font-size:0.78rem;color:#64748b;">Try:</span>
        <span style="font-size:0.78rem;color:#38bdf8;">Find 5 Python AI agents</span> ·
        <span style="font-size:0.78rem;color:#38bdf8;">Top Rust web frameworks</span> ·
        <span style="font-size:0.78rem;color:#38bdf8;">Best LLM fine-tuning repos</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Run search ────────────────────────────────────────────────────────────────
if search_clicked and query.strip():
    if not config.OPENAI_API_KEY:
        st.error("❌ OPENAI_API_KEY is not configured.")
        st.stop()

    try:
        clean_query = sanitize_query(query)
    except PromptInjectionDetected as e:
        st.error(f"🛡️ **Query blocked (prompt injection detected):** {e}")
        st.stop()
    except ValueError as e:
        st.warning(f"⚠️ {e}")
        st.stop()

    st.session_state["results"] = []
    st.session_state["trace_steps"] = []

    with st.spinner("🤖 Initialising agent…"):
        agent: RepoScoutAgent = build_agent()

    live_steps: list[dict] = []
    trace_placeholder = st.empty()

    def on_step(step_type: str, content: str) -> None:
        live_steps.append({"type": step_type, "content": content})
        if show_trace:
            with trace_placeholder.container():
                st.markdown('<div class="section-header">🧠 Live Reasoning</div>', unsafe_allow_html=True)
                render_trace(live_steps)

    t0 = time.time()
    with st.spinner("🔍 Searching and reasoning…"):
        answer = agent.search(clean_query, step_callback=on_step, history=st.session_state["history"][:])

    elapsed = time.time() - t0
    trace_placeholder.empty()

    st.session_state["history"].append({"role": "user", "content": clean_query})
    st.session_state["history"].append({"role": "assistant", "content": answer})
    st.session_state["trace_steps"] = live_steps
    st.session_state["query_count"] += 1
    st.session_state["repo_count"] += len(st.session_state["results"])
    st.session_state["elapsed"] = elapsed

# ── Display results ───────────────────────────────────────────────────────────
if st.session_state["history"]:
    last_answer = next(
        (m["content"] for m in reversed(st.session_state["history"]) if m["role"] == "assistant"),
        None,
    )

    if st.session_state["results"]:
        st.markdown('<div class="section-header">📦 Repositories Found</div>', unsafe_allow_html=True)
        render_repo_cards(st.session_state["results"])

    if last_answer:
        st.markdown('<div class="section-header">💬 Agent Answer</div>', unsafe_allow_html=True)
        with st.expander("View full agent response", expanded=True):
            st.markdown(last_answer)

    if show_trace and st.session_state["trace_steps"]:
        st.markdown('<div class="section-header">🧠 Reasoning Trace</div>', unsafe_allow_html=True)
        with st.expander("View reasoning steps", expanded=False):
            render_trace(st.session_state["trace_steps"])

    if show_history:
        user_queries = [m for m in st.session_state["history"] if m["role"] == "user"]
        if user_queries:
            st.markdown('<div class="section-header">🕘 Session History</div>', unsafe_allow_html=True)
            with st.expander(f"{len(user_queries)} queries this session", expanded=False):
                for i, m in enumerate(user_queries, 1):
                    st.markdown(
                        f'<div style="color:#94a3b8;font-size:0.85rem;margin-bottom:4px;">'
                        f'<strong style="color:#00ffa3;">#{i}</strong> {m["content"]}</div>',
                        unsafe_allow_html=True,
                    )

    if st.button("🗑️ Clear Session"):
        for k in ["history", "results", "trace_steps"]:
            st.session_state[k] = []
        st.session_state["query_count"] = 0
        st.session_state["repo_count"] = 0
        st.session_state["elapsed"] = 0.0
        st.rerun()

else:
    st.markdown(
        """
        <div style="text-align:center;padding:4rem 2rem;color:#334155;">
            <div style="font-size:4rem;margin-bottom:1rem;">🔭</div>
            <div style="font-size:1.2rem;font-weight:600;color:#475569;">Ready to discover repositories</div>
            <div style="font-size:0.9rem;color:#334155;margin-top:0.5rem;">
                Enter a query above and hit <strong>Search</strong> to find the best GitHub repos using AI reasoning.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
