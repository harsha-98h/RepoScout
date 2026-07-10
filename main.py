"""
RepoScout — GitHub Repository Discovery Agent
Pure Python CLI with rich terminal output.

Usage:
    python main.py              # interactive REPL
    python main.py "query"      # single one-shot query

Commands inside the REPL:
    help     — show available commands
    history  — show queries made this session
    trace    — show last reasoning trace
    clear    — clear the screen
    quit     — exit
"""

from __future__ import annotations

import re
import sys
import os
from datetime import datetime
from typing import Optional

import config
from agent.reposcout_agent import RepoScoutAgent
from tools.github_search import GitHubSearchTool
from tools.repo_evaluator import RepoEvaluator
from utils.exceptions import PromptInjectionDetected
from utils.logger import setup_logger
from utils.sanitizer import sanitize_query

# Rich imports
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# ──────────────────────────────────────────────
# Console setup with custom theme
# ──────────────────────────────────────────────
THEME = Theme(
    {
        "accent":      "bold green",
        "dim_text":    "dim white",
        "user_query":  "bold cyan",
        "answer":      "white",
        "error":       "bold red",
        "warning":     "bold yellow",
        "success":     "bold green",
        "info":        "dim cyan",
        "stars":       "bold yellow",
        "lang":        "bold magenta",
        "url":         "underline cyan",
        "score_high":  "bold green",
        "score_mid":   "bold yellow",
        "score_low":   "bold red",
        "cmd":         "bold white on grey23",
    }
)

console = Console(theme=THEME, highlight=False)
logger  = setup_logger("main")


# ──────────────────────────────────────────────
# Banner
# ──────────────────────────────────────────────
def print_banner() -> None:
    banner = Text()
    banner.append("\n  🔍  ", style="bold green")
    banner.append("RepoScout", style="bold white")
    banner.append("  ·  GitHub Repository Discovery Agent\n", style="dim white")

    info_lines = (
        f"  Model : [accent]{config.OPENAI_MODEL}[/accent]"
        f"   │   GitHub : [accent]{'Authenticated' if config.GITHUB_TOKEN else 'Unauthenticated (60 req/hr)'}[/accent]"
        f"   │   Max iterations : [accent]{config.MAX_ITERATIONS}[/accent]\n"
    )

    console.print(
        Panel(
            banner,
            subtitle=info_lines,
            border_style="green",
            padding=(0, 2),
        )
    )


# ──────────────────────────────────────────────
# Help panel
# ──────────────────────────────────────────────
def print_help() -> None:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Command", style="cmd", no_wrap=True)
    table.add_column("Description", style="dim_text")
    rows = [
        ("help",    "Show this help"),
        ("history", "Show queries made this session"),
        ("trace",   "Show the last reasoning trace"),
        ("clear",   "Clear the terminal screen"),
        ("quit",    "Exit RepoScout  (also: exit, q)"),
    ]
    for cmd, desc in rows:
        table.add_row(cmd, desc)

    console.print(
        Panel(
            table,
            title="[accent]Commands[/accent]",
            border_style="dim white",
            padding=(0, 1),
        )
    )
    console.print(
        "  [dim_text]Example queries:[/dim_text]\n"
        "  [user_query]• Find 10 AI agent frameworks with the most stars[/user_query]\n"
        "  [user_query]• Show me the best Python machine learning repos[/user_query]\n"
        "  [user_query]• Compare top 5 web development frameworks[/user_query]\n"
        "  [user_query]• Read the README of huggingface/transformers[/user_query]\n"
    )


# ──────────────────────────────────────────────
# Repo result renderer
# ──────────────────────────────────────────────
def _score_style(score: int) -> str:
    if score >= 70:
        return "score_high"
    if score >= 40:
        return "score_mid"
    return "score_low"


def render_repo_table(repos: list[dict]) -> Table:
    """Render a list of repo dicts as a rich Table."""
    table = Table(
        box=box.ROUNDED,
        border_style="dim white",
        header_style="bold white",
        show_lines=True,
        expand=True,
    )
    table.add_column("#",           style="dim_text",  width=3,  no_wrap=True)
    table.add_column("Repository",  style="bold white", min_width=24)
    table.add_column("⭐ Stars",    style="stars",     width=10, no_wrap=True, justify="right")
    table.add_column("Language",    style="lang",      width=12, no_wrap=True)
    table.add_column("Score",       width=8,           no_wrap=True, justify="center")
    table.add_column("URL",         style="url",       min_width=30)

    for i, repo in enumerate(repos, 1):
        score = repo.get("quality_score", 0)
        table.add_row(
            str(i),
            repo.get("name", "—"),
            f"{repo.get('stars', 0):,}",
            repo.get("language") or "Unknown",
            Text(f"{score}/100", style=_score_style(score)),
            repo.get("url", "—"),
        )
    return table


def render_answer(answer: str, repos: Optional[list[dict]] = None) -> None:
    """Print the agent's final answer, with an optional repo table above."""
    console.print()
    if repos:
        console.print(render_repo_table(repos))
        console.print()

    console.print(
        Panel(
            Markdown(answer),
            title="[accent]RepoScout[/accent]",
            border_style="green",
            padding=(1, 2),
        )
    )


# ──────────────────────────────────────────────
# History renderer
# ──────────────────────────────────────────────
def print_history(history: list[dict]) -> None:
    user_msgs = [m for m in history if m["role"] == "user"]
    if not user_msgs:
        console.print("[dim_text]No queries yet this session.[/dim_text]")
        return

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("#",     style="dim_text", width=4)
    table.add_column("Query", style="user_query")
    for i, m in enumerate(user_msgs, 1):
        table.add_row(str(i), m["content"])
    console.print(
        Panel(table, title="[accent]Session History[/accent]", border_style="dim white")
    )


# ──────────────────────────────────────────────
# Trace renderer
# ──────────────────────────────────────────────
def print_trace(agent: RepoScoutAgent) -> None:
    if not agent.trace:
        console.print("[dim_text]No trace available yet.[/dim_text]")
        return

    icons = {"thought": "💭", "action": "⚡", "observation": "📊", "final_answer": "✅"}
    colors = {"thought": "cyan", "action": "yellow", "observation": "blue", "final_answer": "green"}

    console.print(Rule("[accent]Reasoning Trace[/accent]"))
    for step in agent.trace:
        stype   = step["type"]
        icon    = icons.get(stype, "•")
        color   = colors.get(stype, "white")
        preview = step["content"][:400] + ("…" if len(step["content"]) > 400 else "")
        console.print(
            Panel(
                preview,
                title=f"[{color}]{icon} {stype.upper()}[/{color}]",
                border_style=color,
                padding=(0, 1),
            )
        )
    console.print(Rule())


# ──────────────────────────────────────────────
# Agent initialisation
# ──────────────────────────────────────────────
def build_agent() -> RepoScoutAgent:
    """Wire up the RepoScoutAgent with all tools and return it."""
    agent       = RepoScoutAgent()
    github_tool = GitHubSearchTool()
    evaluator   = RepoEvaluator()

    def search_github_wrapper(query: str) -> str:
        numbers     = re.findall(r"\b(\d+)\b", query)
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

        parts = []
        for r in quality[:max_results]:
            short = r["name"].split("/")[-1] if "/" in r["name"] else r["name"]
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


# ──────────────────────────────────────────────
# Query runner
# ──────────────────────────────────────────────
def run_query(agent: RepoScoutAgent, question: str, history: list[dict]) -> str:
    """Run a single query through the agent with a live spinner. Returns the answer."""
    steps: list[str] = []

    def on_step(step_type: str, content: str) -> None:
        icons = {
            "thought":      "💭 Reasoning…",
            "action":       f"⚡ Calling tool: {content[:60]}",
            "observation":  "📊 Processing results…",
            "final_answer": "✅ Finalising answer…",
        }
        steps.append(icons.get(step_type, step_type))

    answer = ""
    with Progress(
        SpinnerColumn(spinner_name="dots", style="green"),
        TextColumn("[green]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("🔍 Searching and analysing…", total=None)

        def patched_callback(step_type: str, content: str) -> None:
            on_step(step_type, content)
            label = steps[-1] if steps else "Working…"
            progress.update(task, description=label)

        answer = agent.search(question, step_callback=patched_callback, history=history)

    return answer


# ──────────────────────────────────────────────
# Interactive REPL
# ──────────────────────────────────────────────
def repl(agent: RepoScoutAgent) -> None:
    """Run the interactive prompt loop."""
    history: list[dict] = []

    print_help()
    console.print(Rule("[dim_text]Session started[/dim_text]"))

    while True:
        try:
            console.print()
            question = Prompt.ask("[bold green]You[/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim_text]👋 Goodbye![/dim_text]")
            break

        if not question:
            continue

        cmd = question.lower()

        if cmd in {"quit", "exit", "q"}:
            console.print("[dim_text]👋 Goodbye![/dim_text]")
            break

        if cmd == "help":
            print_help()
            continue

        if cmd == "history":
            print_history(history)
            continue

        if cmd == "trace":
            print_trace(agent)
            continue

        if cmd == "clear":
            console.clear()
            print_banner()
            continue

        # Sanitize
        try:
            clean = sanitize_query(question)
        except PromptInjectionDetected as exc:
            console.print(f"[error]🛡️  Blocked:[/error] {exc}")
            continue
        except ValueError as exc:
            console.print(f"[warning]⚠️  {exc}[/warning]")
            continue

        # Record user message
        history.append({"role": "user", "content": clean})

        # Run query
        try:
            answer = run_query(agent, clean, history[:-1])
        except Exception as exc:
            console.print(f"[error]❌ Error:[/error] {exc}")
            history.pop()   # remove failed query from history
            continue

        # Record assistant message
        history.append({"role": "assistant", "content": answer})

        render_answer(answer)


# ──────────────────────────────────────────────
# One-shot mode
# ──────────────────────────────────────────────
def one_shot(agent: RepoScoutAgent, question: str) -> None:
    """Run a single non-interactive query and print the result."""
    try:
        clean = sanitize_query(question)
    except (PromptInjectionDetected, ValueError) as exc:
        console.print(f"[error]❌ {exc}[/error]")
        sys.exit(1)

    answer = run_query(agent, clean, [])
    render_answer(answer)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
def main() -> None:
    print_banner()

    if not config.OPENAI_API_KEY:
        console.print(
            Panel(
                "[error]OPENAI_API_KEY not found in .env![/error]\n"
                "Add your key:  [cmd]OPENAI_API_KEY=sk-...[/cmd]",
                title="[error]Configuration Error[/error]",
                border_style="red",
            )
        )
        sys.exit(1)

    with console.status("[green]Initialising agent…[/green]", spinner="dots"):
        agent = build_agent()

    console.print("[success]✅ Agent ready.[/success]  5 tools registered.\n")

    # One-shot if a query was passed on the command line
    if len(sys.argv) > 1:
        one_shot(agent, " ".join(sys.argv[1:]))
    else:
        repl(agent)


if __name__ == "__main__":
    main()