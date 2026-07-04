"""
RepoScout AI — Real Chatbot UI
A ChatGPT-style conversational interface for GitHub repository discovery.
"""

import streamlit as st
import re
import config
from agent.reposcout_agent import RepoScoutAgent
from tools.github_search import GitHubSearchTool
from tools.repo_evaluator import RepoEvaluator
from utils.sanitizer import sanitize_query
from utils.exceptions import PromptInjectionDetected

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="RepoScout AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "query_count" not in st.session_state:
    st.session_state.query_count = 0

# ──────────────────────────────────────────────
# CSS — ChatGPT-style chatbot
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-main: #0d0d0d;
    --bg-sidebar: #171717;
    --bg-user-msg: #2f2f2f;
    --bg-assistant-msg: transparent;
    --text-main: #ececec;
    --text-dim: #9a9a9a;
    --accent: #10a37f;
    --accent-light: #19c37d;
    --border-subtle: rgba(255,255,255,0.08);
}

/* ── Global ── */
html, body, [data-testid="stAppViewContainer"], .main,
[data-testid="stApp"], [data-testid="stMainBlockContainer"] {
    background: var(--bg-main) !important;
    color: var(--text-main) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 1.5rem 0 !important;
    max-width: 780px;
    margin: 0 auto !important;
}
/* User messages get a subtle bg like ChatGPT */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--bg-user-msg) !important;
    border-radius: 16px !important;
    padding: 1.2rem 1.5rem !important;
    margin-bottom: 0.5rem !important;
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] td,
[data-testid="stChatMessage"] th {
    color: var(--text-main) !important;
    font-size: 0.95rem !important;
    line-height: 1.7 !important;
}
[data-testid="stChatMessage"] strong {
    color: #fff !important;
}
[data-testid="stChatMessage"] a {
    color: var(--accent-light) !important;
}
[data-testid="stChatMessage"] code {
    background: rgba(255,255,255,0.06) !important;
    color: #e8e8e8 !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
}

/* ── Chat input bar — fixed at bottom ── */
[data-testid="stChatInput"] {
    background: var(--bg-main) !important;
    border-top: 1px solid var(--border-subtle) !important;
    padding-top: 12px !important;
}
[data-testid="stChatInput"] textarea {
    background: #2f2f2f !important;
    color: var(--text-main) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 16px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 12px 16px !important;
    max-width: 780px !important;
    margin: 0 auto !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
}
[data-testid="stChatInput"] button {
    color: var(--text-dim) !important;
}
[data-testid="stChatInput"] button:hover {
    color: var(--accent-light) !important;
}

/* ── Status widget ── */
[data-testid="stStatusWidget"] {
    background: rgba(16, 163, 127, 0.05) !important;
    border: 1px solid rgba(16, 163, 127, 0.2) !important;
    border-radius: 12px !important;
}

/* ── Expander (trace) ── */
[data-testid="stExpander"] {
    border: 1px solid var(--border-subtle) !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,0.02) !important;
    margin-top: 0.5rem !important;
}
[data-testid="stExpander"] summary span {
    color: var(--text-dim) !important;
    font-size: 0.85rem !important;
}

/* ── Buttons ── */
.stButton > button {
    background: transparent !important;
    color: var(--text-dim) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 10px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.05) !important;
    color: var(--text-main) !important;
    border-color: rgba(255,255,255,0.2) !important;
}

/* ── Welcome cards ── */
.welcome-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 1.2rem;
    cursor: default;
    transition: border-color 0.2s ease;
    height: 100%;
}
.welcome-card:hover {
    border-color: var(--accent);
}
.welcome-icon { font-size: 1.5rem; margin-bottom: 8px; }
.welcome-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-main);
    margin-bottom: 4px;
}
.welcome-desc {
    font-size: 0.8rem;
    color: var(--text-dim);
    line-height: 1.4;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)



# ──────────────────────────────────────────────
# Agent initialization
# ──────────────────────────────────────────────
def initialize_agent():
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
        if isinstance(repos, list) and len(repos) == 1 and isinstance(repos[0], dict) and repos[0].get("error"):
            return repos[0].get("message", "Search failed.")

        quality_repos = evaluator.filter_quality_repos(repos, min_score=40)
        if not quality_repos:
            return "No high-quality repositories found matching your criteria."

        parts = []
        for r in quality_repos[:max_results]:
            repo_short = r['name'].split('/')[-1] if '/' in r['name'] else r['name']
            parts.append(
                f"**{r['name']}** - {r['description']}\n\n"
                f"⭐ Stars: {r['stars']:,}+\n\n"
                f"💻 Language: {r['language']}\n\n"
                f"🔗 GitHub: [{repo_short}]({r['url']})\n\n"
                f"Why useful: {evaluator.explain_why_useful(r)}"
            )
        return "\n\n---\n\n".join(parts)

    agent.register_tool("search_github", search_github_wrapper,
        "Search GitHub repositories. Supports count in query like 'Find 10 repos' (default 10, max 20).")
    agent.register_tool("get_repo_details", github_tool.get_repository_details,
        "Get detailed information about a specific repository (format: owner/repo).")
    agent.register_tool("read_readme", github_tool.get_readme,
        "Read the README.md file of a repository (format: owner/repo).")
    agent.register_tool("analyze_commits", lambda r: github_tool.get_recent_commits(r.strip(), 5),
        "Get the 5 most recent commits for a repository (format: owner/repo).")
    agent.register_tool("read_issues", lambda r: github_tool.get_open_issues(r.strip(), 5),
        "Get the 5 most recent open issues/PRs for a repository (format: owner/repo).")
    return agent


# ──────────────────────────────────────────────
# Sidebar (minimal)
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 1.5rem 0; text-align: center;">
        <span style="font-size: 2rem;">🔍</span>
        <h2 style="color: #ececec; font-weight: 800; margin: 8px 0 2px 0;">RepoScout</h2>
        <p style="color: #9a9a9a; font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase;">AI Discovery Agent</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.query_count = 0
        st.session_state.agent = None
        st.rerun()

    st.divider()

    # Show past queries as "chat history"
    if st.session_state.messages:
        st.markdown(f"<p style='color:#9a9a9a; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; padding: 0 0 4px 0;'>History</p>", unsafe_allow_html=True)
        user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
        for i, m in enumerate(user_msgs[-5:]): # show last 5
            label = m["content"][:35] + ("..." if len(m["content"]) > 35 else "")
            st.markdown(f"<div style='color:#9a9a9a; font-size:0.82rem; padding:6px 0; border-bottom: 1px solid rgba(255,255,255,0.04);'>💬 {label}</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="position: fixed; bottom: 16px; left: 16px; width: 220px;">
        <div style="font-size: 0.72rem; color: #555;">
            Model: {config.OPENAI_MODEL}<br>
            Queries: {st.session_state.query_count}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Main chat area
# ──────────────────────────────────────────────
if not config.OPENAI_API_KEY:
    st.error("⚠️ `OPENAI_API_KEY` not found in your `.env` file. Please add it to continue.")
    st.stop()

if st.session_state.agent is None:
    st.session_state.agent = initialize_agent()

# Welcome screen when no messages
if not st.session_state.messages:
    st.markdown("""
    <div style="max-width: 680px; margin: 6rem auto 2rem; text-align: center;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
        <h1 style="font-size: 2rem; font-weight: 800; color: #ececec; margin-bottom: 0.5rem;">
            What repos are you looking for?
        </h1>
        <p style="color: #9a9a9a; font-size: 1rem;">
            Ask me anything about GitHub repositories. I'll search, evaluate, and recommend the best ones for you.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Suggestion cards
    cols = st.columns(3)
    suggestions = [
        ("🤖", "AI Agents", "Find 10 AI agent frameworks with the most stars"),
        ("🐍", "Python ML", "Show me the best Python machine learning repositories"),
        ("🌐", "Web Frameworks", "Compare top 5 web development frameworks"),
    ]
    for col, (icon, title, desc) in zip(cols, suggestions):
        with col:
            st.markdown(f"""
            <div class="welcome-card">
                <div class="welcome-icon">{icon}</div>
                <div class="welcome-title">{title}</div>
                <div class="welcome-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

# Chat history display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Show reasoning trace
        if msg.get("trace"):
            with st.expander("View reasoning steps"):
                for step in msg["trace"]:
                    icon = {"thought": "💭", "action": "⚡", "observation": "📊"}.get(step["type"], "•")
                    label = step["type"].upper()
                    content_preview = step["content"][:300] + ("..." if len(step["content"]) > 300 else "")
                    st.markdown(f"**{icon} {label}**\n\n{content_preview}")
                    st.divider()


# ──────────────────────────────────────────────
# Chat input and processing
# ──────────────────────────────────────────────
if prompt := st.chat_input("Message RepoScout..."):
    # Add and display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process with agent
    with st.chat_message("assistant"):
        # Real-time status
        with st.status("🔍 Searching and analyzing...", expanded=True) as status:
            step_container = st.container()

            def on_step(step_type, content):
                icons = {"thought": "💭 Reasoning", "action": "⚡ Acting", "observation": "📊 Observing", "final_answer": "✅ Done"}
                label = icons.get(step_type, step_type)
                status.update(label=label, state="running" if step_type != "final_answer" else "complete")
                with step_container:
                    if step_type == "thought":
                        st.markdown(f"💭 *Thinking: {content[:80]}...*")
                    elif step_type == "action":
                        st.markdown(f"⚡ Running: `{content}`")
                    elif step_type == "observation":
                        st.markdown(f"📊 Got results.")

            try:
                clean = sanitize_query(prompt)
                
                # Pass previous messages (excluding the current one we just added) as history
                history = st.session_state.messages[:-1]
                
                answer = st.session_state.agent.search(
                    clean, 
                    step_callback=on_step,
                    history=history
                )
                trace = list(getattr(st.session_state.agent, "trace", []))
            except PromptInjectionDetected as e:
                answer = f"🛡️ **Blocked:** {e}"
                trace = []
            except ValueError as e:
                answer = f"⚠️ {e}"
                trace = []
            except Exception as e:
                answer = f"❌ An error occurred: {e}"
                trace = []

            status.update(label="✅ Complete", state="complete", expanded=False)

        # Render the final answer
        st.markdown(answer)

        # Show trace in expander
        if trace:
            with st.expander("View reasoning steps"):
                for step in trace:
                    icon = {"thought": "💭", "action": "⚡", "observation": "📊"}.get(step["type"], "•")
                    label = step["type"].upper()
                    content_preview = step["content"][:300] + ("..." if len(step["content"]) > 300 else "")
                    st.markdown(f"**{icon} {label}**\n\n{content_preview}")
                    st.divider()

        # Save to history
        st.session_state.query_count += 1
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "trace": trace,
        })
