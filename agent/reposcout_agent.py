"""
RepoScout Agent — GitHub Repository Discovery using the ReAct Pattern.

Key improvements over the original:
- Robust regex-based ReAct parser (not brittle string splitting)
- Typed return values and full type hints
- Custom exception hierarchy instead of generic ``Exception``
- Consistent ``logger`` usage (no bare ``print``)
"""

from __future__ import annotations

import re
from typing import Any

from openai import OpenAI
from openai import APIError as OpenAIAPIError

import config
from agent.prompts import REPOSCOUT_SYSTEM_PROMPT, REPOSCOUT_USER_PROMPT
from utils.exceptions import MaxIterationsExceeded, ToolExecutionError, ToolNotFoundError
from utils.logger import setup_logger

logger = setup_logger(__name__)
_ENV_DEBUG = config.DEBUG

# ---------------------------------------------------------------------------
# Regex patterns for ReAct parsing
# ---------------------------------------------------------------------------
_ACTION_RE = re.compile(r"ACTION\s*:\s*(.+)", re.IGNORECASE)
_FINAL_ANSWER_RE = re.compile(r"FINAL\s+ANSWER\s*:\s*(.*)", re.IGNORECASE | re.DOTALL)
# Tool invocations look like  search_github: some query text
_TOOL_CALL_RE = re.compile(r"^(\w+)\s*:\s*(.*)", re.DOTALL)


class RepoScoutAgent:
    """ReAct agent for discovering GitHub repositories.

    Implements the Thought → Action → Observation loop using an LLM
    (GPT-4o-mini by default) and a set of registered callable tools.
    """

    def __init__(self) -> None:
        logger.info("🤖 Initialising RepoScout Agent…")
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.tools: dict[str, dict[str, Any]] = {}
        self.max_iterations: int = config.MAX_ITERATIONS
        self.trace: list[dict[str, str]] = []
        logger.info("✅ RepoScout ready.")

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register_tool(
        self, name: str, function: Any, description: str
    ) -> None:
        """Register a callable tool that the ReAct loop can invoke.

        Args:
            name:        Unique tool identifier used in ``ACTION: name: args``.
            function:    Callable that accepts a single string argument.
            description: Short description shown to the LLM.
        """
        self.tools[name] = {"function": function, "description": description}
        logger.info("🔧 Registered tool: %s", name)

    # ------------------------------------------------------------------
    # Main ReAct loop
    # ------------------------------------------------------------------

    def search(self, question: str, step_callback: Any = None, history: list[dict[str, str]] | None = None) -> str:
        """Run the ReAct loop and return the final answer.

        Args:
            question: Natural-language repository search request.
            step_callback: Optional callable(step_type, content) for progress tracking.
            history: Optional list of previous messages ``[{"role": "user"/"assistant", "content": "..."}]``

        Returns:
            The agent's final formatted answer string.
        """
        logger.info("=" * 60)
        logger.info("🔍 USER REQUEST: %s", question)
        if history:
            logger.info("🧠 Using conversational memory (%d prior messages)", len(history))
        logger.info("=" * 60)

        self.trace = []

        for iteration in range(1, self.max_iterations + 1):
            # THOUGHT
            thought = self._generate_thought(question, history)
            self._add_trace("thought", thought)
            if step_callback:
                step_callback("thought", thought)

            # Check for FINAL ANSWER
            final = self._extract_final_answer(thought)
            if final is not None:
                if step_callback:
                    step_callback("final_answer", final)
                return final

            # ACTION
            action_line = self._extract_action(thought)
            if action_line:
                self._add_trace("action", action_line)
                if step_callback:
                    step_callback("action", action_line)

                # OBSERVATION
                observation = self._execute_action(action_line)
                self._add_trace("observation", observation)
                if step_callback:
                    step_callback("observation", observation)
            else:
                # No action extracted – ask LLM to continue
                msg = "No action found. Please provide an ACTION."
                self._add_trace("observation", msg)
                if step_callback:
                    step_callback("observation", msg)

        logger.warning("⚠️  Max iterations reached.")
        return "I couldn't complete the search. Please try rephrasing your request."

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    def _generate_thought(self, question: str, history: list[dict[str, str]] | None = None) -> str:
        """Call the LLM and return its next reasoning step.

        Args:
            question: The user's original question.
            history: Optional conversational history.

        Returns:
            Raw LLM output string.
        """
        tools_desc = "\n".join(
            f"- {name}: {info['description']}" for name, info in self.tools.items()
        )
        system_prompt = REPOSCOUT_SYSTEM_PROMPT.format(tools_description=tools_desc)
        user_prompt = REPOSCOUT_USER_PROMPT.format(
            question=question, context=self._trace_text()
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        # Inject conversational history if provided
        if history:
            # We only send the text content to save tokens, removing huge repo UI cards if they exist.
            for msg in history:
                # Basic safety check to ensure standard keys
                if "role" in msg and "content" in msg:
                    # Optional: We could truncate very long past assistant messages 
                    # but for now we just pass them in.
                    messages.append({"role": msg["role"], "content": msg["content"]})
                    
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=config.TEMPERATURE,
                max_tokens=1000,
            )
            return response.choices[0].message.content.strip()

        except OpenAIAPIError as exc:
            logger.error("❌ OpenAI API error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # ReAct parsing helpers (robust regex-based)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_action(thought: str) -> str | None:
        """Extract the ACTION line from an LLM thought string.

        Uses a regex so that minor formatting differences (extra spaces,
        different capitalisation, markdown bold, etc.) don't break parsing.

        Args:
            thought: Raw LLM output.

        Returns:
            The action string, or ``None`` if not found.
        """
        match = _ACTION_RE.search(thought)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _extract_final_answer(thought: str) -> str | None:
        """Extract the FINAL ANSWER section from *thought*, if present.

        Args:
            thought: Raw LLM output.

        Returns:
            The final answer text, or ``None`` when not yet complete.
        """
        match = _FINAL_ANSWER_RE.search(thought)
        if match:
            return match.group(1).strip()
        return None

    def _execute_action(self, action_line: str) -> str:
        """Parse and execute a tool invocation line.

        Expected format: ``tool_name: argument text``

        Args:
            action_line: Action string extracted from the LLM output.

        Returns:
            String observation to feed back into the next thought.
        """
        match = _TOOL_CALL_RE.match(action_line)
        if not match:
            return (
                f"Could not parse action '{action_line}'. "
                "Expected format: tool_name: arguments"
            )

        tool_name = match.group(1).strip()
        arguments = match.group(2).strip()

        if tool_name not in self.tools:
            try:
                raise ToolNotFoundError(tool_name, list(self.tools.keys()))
            except ToolNotFoundError as exc:
                return str(exc)

        tool_fn = self.tools[tool_name]["function"]
        try:
            result = tool_fn(arguments) if arguments else tool_fn()
            return str(result)
        except Exception as exc:
            try:
                raise ToolExecutionError(tool_name, exc) from exc
            except ToolExecutionError as tex:
                logger.error("❌ %s", tex)
                return str(tex)

    # ------------------------------------------------------------------
    # Trace helpers
    # ------------------------------------------------------------------

    def _add_trace(self, step_type: str, content: str) -> None:
        self.trace.append({"type": step_type, "content": content})

    def _trace_text(self) -> str:
        """Return the accumulated trace formatted for the LLM prompt."""
        lines: list[str] = []
        for step in self.trace:
            label = step["type"].upper()
            lines.append(f"\n{label}: {step['content']}\n")
        return "".join(lines)

    def print_trace(self) -> None:
        """Log the full reasoning trace at INFO level."""
        logger.info("=" * 60)
        logger.info("REPOSCOUT TRACE")
        logger.info("=" * 60)
        logger.info(self._trace_text())
        logger.info("=" * 60)