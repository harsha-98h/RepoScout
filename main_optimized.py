"""
Optimized RepoScout with all performance enhancements
"""

import config
from agent.optimized_reposcout import OptimizedRepoScoutAgent
from tools.github_search import GitHubSearchTool
from tools.repo_evaluator import RepoEvaluator
from utils.logger import setup_logger

logger = setup_logger("main")

def format_repositories_for_llm(repositories):
    """Format repos for LLM"""
    if not repositories:
        return "No repositories found."
    
    if isinstance(repositories, dict) and repositories.get("error"):
        return repositories.get("message", "Error occurred")
    
    evaluator = RepoEvaluator()
    quality_repos = evaluator.filter_quality_repos(repositories, min_score=40)
    
    if not quality_repos:
        return "No high-quality repositories found."
    
    formatted = []
    for repo in quality_repos[:5]:
        formatted.append(
            f"Repository: {repo['name']}\n"
            f"Description: {repo['description']}\n"
            f"Stars: {repo['stars']:,}\n"
            f"Language: {repo['language']}\n"
            f"URL: {repo['url']}\n"
            f"Quality Score: {repo['quality_score']}/100"
        )
    
    return "\n\n".join(formatted)

def main():
    """Main function"""
    
    print("\n" + "="*60)
    print(f"🚀 {config.AGENT_NAME} - OPTIMIZED VERSION")
    print("="*60)
    
    if not config.OPENAI_API_KEY:
        print("\n❌ Error: OPENAI_API_KEY not found!")
        return
    
    # Initialize
    print("\n🔧 Initializing optimized agent...")
    agent = OptimizedRepoScoutAgent()
    github_tool = GitHubSearchTool()
    
    # Register tools
    def search_github_wrapper(query):
        repos = github_tool.search_repositories(query, max_results=10)
        return format_repositories_for_llm(repos)
    
    agent.register_tool(
        "search_github",
        search_github_wrapper,
        "Search GitHub repositories"
    )
    
    print("✅ Agent ready!\n")
    
    # Interactive mode
    print("="*60)
    print("🔍 Optimized RepoScout - Lightning Fast!")
    print("Commands: 'quit', 'stats', 'trace'")
    print("="*60)
    
    while True:
        question = input("\n🔍 What are you looking for? ").strip()
        
        if not question:
            continue
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if question.lower() == 'stats':
            agent.print_performance_stats()
            continue
        
        if question.lower() == 'trace':
            agent.print_trace() if hasattr(agent, 'print_trace') else print("No trace available")
            continue
        
        try:
            answer = agent.search(question)
            print(f"\n{'='*60}")
            print(answer)
            print(f"{'='*60}")
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()