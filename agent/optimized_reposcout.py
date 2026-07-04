"""
Optimized RepoScout Agent with all performance enhancements
"""

from openai import OpenAI
import config
from agent.prompts import REPOSCOUT_SYSTEM_PROMPT, REPOSCOUT_USER_PROMPT
from agent.optimized_prompts import get_optimized_query
from utils.logger import setup_logger
from utils.performance_monitor import PerformanceMonitor
from utils.streaming import StreamingOutput

logger = setup_logger(__name__)

class OptimizedRepoScoutAgent:
    """
    High-performance ReAct agent with caching and optimization
    """
    
    def __init__(self):
        logger.info("🚀 Initializing Optimized RepoScout...")
        
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.tools = {}
        self.max_iterations = config.MAX_ITERATIONS
        self.trace = []
        
        # Performance monitoring
        self.monitor = PerformanceMonitor()
        self.streaming = StreamingOutput()
        
        logger.info("✅ Optimized RepoScout ready!")
    
    def register_tool(self, name, function, description):
        """Register a tool"""
        self.tools[name] = {
            "function": function,
            "description": description
        }
        logger.info(f"🔧 Registered tool: {name}")
    
    def _add_to_trace(self, step_type, content):
        """Add to trace"""
        self.trace.append({
            "type": step_type,
            "content": content
        })
    
    def _get_trace_text(self):
        """Get trace text"""
        trace_text = ""
        for step in self.trace:
            if step["type"] == "thought":
                trace_text += f"\nTHOUGHT: {step['content']}\n"
            elif step["type"] == "action":
                trace_text += f"ACTION: {step['content']}\n"
            elif step["type"] == "observation":
                trace_text += f"OBSERVATION: {step['content']}\n"
        return trace_text
    
    @PerformanceMonitor().track_query
    def search(self, question):
        """
        Optimized search with performance tracking
        """
        logger.info("\n" + "="*60)
        logger.info(f"🔍 USER REQUEST: {question}")
        logger.info("="*60)
        
        # Clear trace
        self.trace = []
        
        # Show thinking indicator
        self.streaming.stream_thinking("Analyzing your request")
        
        # Check for optimized query patterns
        optimized = get_optimized_query(question)
        
        if optimized:
            logger.info(f"⚡ Using optimized query template")
            # Fast path - skip LLM reasoning for common queries
            return self._fast_search(question, optimized)
        
        # Standard ReAct loop
        return self._react_search(question)
    
    def _fast_search(self, question, template):
        """
        Fast path for common queries using templates
        """
        logger.info(f"🚀 Fast path execution")
        
        # Use pre-defined search query
        search_tool = self.tools.get("search_github")
        
        if search_tool:
            import re
            numbers = re.findall(r"\b(\d+)\b", question)
            req_count = int(numbers[0]) if numbers else template.get('expected_results', 5)
            
            # Pass the requested count to the search tool wrapper
            query_with_count = f"{template['search_query']} {req_count} repos"
            result = search_tool["function"](query_with_count)
            
            # Format response
            answer = f"Here are the top {req_count} {template['description']}:\n\n"
            
            if isinstance(result, list):
                for i, repo in enumerate(result[:req_count], 1):
                    answer += f"{i}. **{repo['name']}**\n"
                    answer += f"   {repo['description']}\n"
                    answer += f"   ⭐ {repo['stars']:,} stars\n"
                    answer += f"   🔗 {repo['url']}\n\n"
            else:
                answer += str(result)
            
            return answer
        
        # Fallback to standard search
        return self._react_search(question)
    
    @PerformanceMonitor().track_llm_call
    def _generate_thought(self, question):
        """Generate thought with performance tracking"""
        tools_desc = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])
        
        system_prompt = REPOSCOUT_SYSTEM_PROMPT.format(
            tools_description=tools_desc
        )
        
        context = self._get_trace_text()
        
        user_prompt = REPOSCOUT_USER_PROMPT.format(
            question=question,
            context=context
        )
        
        response = self.client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config.TEMPERATURE,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    def _react_search(self, question):
        """Standard ReAct search"""
        for iteration in range(self.max_iterations):
            logger.info(f"\n--- Iteration {iteration + 1}/{self.max_iterations} ---")
            
            # THOUGHT
            thought = self._generate_thought(question)
            logger.info(f"\n💭 {thought[:150]}...")
            self._add_to_trace("thought", thought)
            
            # Check final answer
            if self._is_final_answer(thought):
                answer = self._extract_final_answer(thought)
                logger.info(f"\n✅ COMPLETE!")
                return answer
            
            # ACTION
            action = self._generate_action(thought)
            logger.info(f"\n⚡ ACTION: {action}")
            self._add_to_trace("action", action)
            
            # OBSERVATION
            observation = self._execute_action(action)
            logger.info(f"\n📊 OBSERVATION: {observation[:150]}...")
            self._add_to_trace("observation", observation)
        
        return "Search incomplete. Please try again."
    
    def _is_final_answer(self, thought):
        """Check if final answer"""
        return "FINAL ANSWER:" in thought
    
    def _extract_final_answer(self, thought):
        """Extract final answer"""
        if "FINAL ANSWER:" in thought:
            parts = thought.split("FINAL ANSWER:")
            if len(parts) > 1:
                return parts[1].strip()
        return thought
    
    def _generate_action(self, thought):
        """Extract action"""
        if "ACTION:" in thought:
            lines = thought.split("\n")
            for line in lines:
                if line.strip().startswith("ACTION:"):
                    return line.replace("ACTION:", "").strip()
        return None
    
    @PerformanceMonitor().track_tool_call
    def _execute_action(self, action):
        """Execute action with performance tracking"""
        if not action:
            return "No action specified"
        
        try:
            if ":" in action:
                parts = action.split(":", 1)
                tool_name = parts[0].strip()
                arguments = parts[1].strip() if len(parts) > 1 else ""
            else:
                tool_name = action.strip()
                arguments = ""
            
            if tool_name not in self.tools:
                available = ", ".join(self.tools.keys())
                return f"Error: Tool '{tool_name}' not found. Available: {available}"
            
            tool_function = self.tools[tool_name]["function"]
            
            if arguments:
                result = tool_function(arguments)
            else:
                result = tool_function()
            
            return str(result)
        
        except Exception as e:
            return f"Error executing action: {str(e)}"
    
    def get_performance_stats(self):
        """Get performance statistics"""
        return self.monitor.get_stats()
    
    def print_performance_stats(self):
        """Print performance statistics"""
        self.monitor.print_stats()