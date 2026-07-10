# 🔍 RepoScout — AI-Powered GitHub Discovery Agent

RepoScout is an intelligent repository search agent that uses the **ReAct (Reasoning and Acting)** pattern to discover, evaluate, and detail GitHub repositories. It features both a **Streamlit web UI** and a rich **CLI**.

## ✨ Features

*   **ReAct Agentic Logic**: Uses an LLM to reason through search results and decide follow-up actions (reading READMEs, commits, or issues).
*   **Intelligent evaluation**: Automatically filters and scores repositories based on activity, stars, and description quality.
*   **Premium Streamlit UI**: Dark neon glassmorphism aesthetic with live reasoning trace, animated hero, and repo cards.
*   **Rich CLI**: Full-featured terminal REPL with `rich` formatting.
*   **Double-Search Architecture**: Fetches 2× the requested results, then filters for quality.
*   **Advanced Tools**: Read READMEs, analyze recent commits, check open issues/PRs.
*   **Security**: Prompt injection detection, environment-based secrets.
*   **Production-Ready**: Docker + AWS App Runner deployment included.

## 🚀 Quick Start

### 1. Prerequisites
*   Python 3.11+
*   OpenAI API Key
*   GitHub Personal Access Token (optional but recommended)

### 2. Installation
```bash
git clone https://github.com/yourusername/reposcout.git
cd reposcout

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configuration
```bash
cp .env.example .env
# Edit .env and fill in OPENAI_API_KEY and GITHUB_TOKEN
```

### 4. Run — Web UI (Streamlit)
```bash
streamlit run app.py
# Open http://localhost:8501
```

### 5. Run — CLI
```bash
python main.py              # interactive REPL
python main.py "Find 5 Python AI agents"  # one-shot
```

## 🧠 How it Works

RepoScout follows the **ReAct** pattern:
1.  **Thought**: Analyses the user request.
2.  **Action**: Calls a tool (e.g., `search_github`, `read_readme`, `analyze_commits`).
3.  **Observation**: Processes the tool result.
4.  **Final Answer**: Presents the best curated repositories.

## 🐳 Docker

```bash
docker build -t reposcout .
docker run -p 8501:8501 \
  -e OPENAI_API_KEY="sk-..." \
  -e GITHUB_TOKEN="ghp_..." \
  reposcout
```

## ☁️ AWS Deployment

See **[deploy/DEPLOY.md](deploy/DEPLOY.md)** for full step-by-step instructions.

**Recommended: AWS App Runner** (fully managed, auto-HTTPS, ~$5–12/month)

```bash
# Build → push to Amazon ECR → deploy on App Runner
# Environment variables are set in App Runner console (never in files)
```

## 🛡️ Security

*   Prompt sanitization blocks injection attempts.
*   Secrets loaded via environment variables only (never committed).
*   `.dockerignore` ensures `.env` is never baked into Docker images.

## 🧪 Tests

```bash
pytest tests/ -v   # 62 tests, all passing
```

## 📜 License
MIT License.
