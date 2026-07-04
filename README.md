# 🔍 RepoScout — AI-Powered GitHub Discovery Agent

RepoScout is an intelligent repository search agent that uses the **ReAct (Reasoning and Acting)** pattern to discover, evaluate, and detail GitHub repositories. It features a premium, web-based UI built with Streamlit.

![RepoScout UI Preview](https://github.com/user-attachments/assets/your-screenshot-id)

## ✨ Features

*   **ReAct Agentic Logic**: Uses an LLM to reason through search results and decide follow-up actions (reading READMEs, commits, or issues).
*   **Intelligent evaluation**: Automatically filters and scores repositories based on activity, stars, and description quality.
*   **Premium UI**: Built with Streamlit, featuring a dark neon glassmorphism aesthetic with animated hero sections and live session stats.
*   **Double-Search Architecture**: Optimized to fetch ample results to ensure quality filters return exactly the count you requested.
*   **Advanced Tools**: The agent can read repository READMEs, analyze recent commit history, and check open issues/PRs to provide expert advice.

## 🚀 Quick Start

### 1. Prerequisites
*   Python 3.11+
*   OpenAI API Key
*   GitHub Personal Access Token (Optional but recommended to avoid rate limits)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/reposcout.git
cd reposcout

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
pip install streamlit
```

### 3. Configuration
Copy the template and add your keys:
```bash
cp .env.example .env
```
Edit `.env` and add:
*   `OPENAI_API_KEY`: Your OpenAI key.
*   `GITHUB_TOKEN`: Your GitHub token.

### 4. Run the App
```bash
streamlit run app.py
```
Or run the CLI version:
```bash
python main.py
```

## 🧠 How it Works

RepoScout follows the **ReAct** pattern:
1.  **Thought**: Analyzes the user request (e.g., "Find 5 Python AI agents").
2.  **Action**: Searches GitHub using the `search_github` tool.
3.  **Observation**: Filters results for quality and presents them.
4.  **Thought**: Decides if it needs to dig deeper into a specific repo.
5.  **Final Answer**: Presents the best curated list to the user.

## 🛡️ Security

*   **Prompt Sanitization**: Includes logic to detect and block prompt injection attempts.
*   **Environment Protection**: Securely loads keys via `python-dotenv`.
*   **Filtering**: Ensures only active and high-quality repositories reach the final output.

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
# RepoScout
