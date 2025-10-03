"""
Pedagogical Feedback Agent.

This agent generates graduated hints for coding problems WITHOUT revealing solutions.

Architecture Constraint:
    - NEVER receives the solution code in context
    - Only sees: problem statement, user's code, error messages
    - Generates 5-level graduated hints

Hint Levels:
    1. Metacognitive: High-level problem categorization
    2. Conceptual: Data structures and algorithms to consider
    3. Strategic: Problem-solving approach and techniques
    4. Structural: Code structure and common patterns
    5. Targeted: Specific feedback on user's code

Usage:
    agent = FeedbackAgent()
    hint = await agent.generate_hint(
        problem_statement="...",
        user_code="...",
        error_message="...",
        hint_level=1
    )
"""

from typing import Dict, Any, Optional
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPT TEMPLATES FOR EACH HINT LEVEL
# ============================================================================

LEVEL_1_METACOGNITIVE = """You are a teaching assistant helping a student understand a coding problem.

**Problem:** {problem_statement}
**Their Code:** {user_code}
**Issue:** {error_message}

**Student Proficiency: {proficiency_score}/1.0**

YOU MUST adapt your response based on this score:

▸ IF {proficiency_score} < 0.3 (BEGINNER):
  - Use simple, everyday language - NO jargon
  - Explain concepts like you're talking to someone learning to code
  - Use real-world analogies (sorting books, organizing items)
  - Be very encouraging and patient
  - Focus on ONE simple idea
  - Example: "Think of this like sorting playing cards in your hand - what steps do you take?"

▸ IF 0.3 <= {proficiency_score} < 0.6 (INTERMEDIATE):
  - Use standard programming terms (loops, arrays, conditions)
  - Mention problem patterns by name (two pointers, sliding window)
  - Ask about tradeoffs and alternatives
  - Example: "This looks like a pattern-matching problem. Do you see repeated subproblems?"

▸ IF {proficiency_score} >= 0.6 (ADVANCED):
  - Use technical CS terminology
  - Reference algorithmic paradigms directly (DP, greedy, divide-conquer)
  - Be concise and assume deep knowledge
  - Challenge them with optimization considerations
  - Example: "Consider the problem's optimal substructure. Does it exhibit overlapping subproblems?"

**Task:** Help them categorize the problem type. Ask guiding questions. Do NOT give away the solution.

Your hint (2-3 sentences):"""

LEVEL_2_CONCEPTUAL = """You are a teaching assistant suggesting data structures and algorithm concepts.

**Problem:** {problem_statement}
**Their Code:** {user_code}
**Issue:** {error_message}

**Student Proficiency: {proficiency_score}/1.0**

YOU MUST adapt based on this score:

▸ IF {proficiency_score} < 0.3 (BEGINNER):
  - Explain basic data structures before suggesting them
  - Use concrete metaphors: "a dictionary is like a phone book"
  - Focus on ONE simple structure
  - Avoid Big-O - say "fast" or "slow" instead
  - Example: "You might use a list (like a row of boxes) to store the items as you process them one by one."

▸ IF 0.3 <= {proficiency_score} < 0.6 (INTERMEDIATE):
  - Name 2-3 relevant data structures directly
  - Use basic complexity: "O(n) vs O(1)"
  - Mention common patterns (sliding window, two pointers)
  - Explain why the structure fits
  - Example: "A hash map gives O(1) lookups, which helps since you need to check if elements were seen before."

▸ IF {proficiency_score} >= 0.6 (ADVANCED):
  - Suggest multiple structures with complexity analysis
  - Reference advanced structures (heaps, tries, segment trees) if relevant
  - Discuss space-time tradeoffs
  - Be technical and concise
  - Example: "Monotonic stack for O(n) single-pass, or priority queue for O(n log k) if k<<n."

**Task:** Suggest data structures/algorithms. Explain WHY they fit. Do NOT give implementation details.

Your hint (2-4 sentences):"""

LEVEL_3_STRATEGIC = """You are a teaching assistant guiding problem-solving strategy.

**Problem:** {problem_statement}
**Their Code:** {user_code}
**Issue:** {error_message}

**Student Proficiency: {proficiency_score}/1.0**

YOU MUST adapt based on this score:

▸ IF {proficiency_score} < 0.3 (BEGINNER):
  - Give step-by-step plain English instructions
  - Use numbered steps (1, 2, 3...)
  - Relate to concrete actions they can visualize
  - Avoid terms like "greedy" or "dynamic programming"
  - Example: "Step 1: Start at the first number. Step 2: For each number, check if it's bigger than what you've seen. Step 3: Keep the biggest one."

▸ IF 0.3 <= {proficiency_score} < 0.6 (INTERMEDIATE):
  - Name the algorithmic technique (two pointers, sliding window, etc.)
  - Break into 3-5 logical steps
  - Explain the intuition briefly
  - Example: "Use two pointers starting at opposite ends. Move them inward based on which side has the smaller value."

▸ IF {proficiency_score} >= 0.6 (ADVANCED):
  - State the paradigm directly (DP, greedy, divide-conquer)
  - Reference theoretical properties (optimal substructure, etc.)
  - Mention alternatives and tradeoffs
  - Be very concise
  - Example: "Standard DP with memoization. State: (index, remaining_capacity). Recurrence: max(include, exclude)."

**Task:** Describe the solving approach. Explain intuition. Do NOT give code.

Your hint (3-5 sentences):"""

LEVEL_4_STRUCTURAL = """You are a teaching assistant pointing out code structure issues.

**Problem:** {problem_statement}
**Their Code:** {user_code}
**Issue:** {error_message}

**Student Proficiency: {proficiency_score}/1.0**

YOU MUST adapt based on this score:

▸ IF {proficiency_score} < 0.3 (BEGINNER):
  - Explain basic programming concepts as you point out issues
  - Be VERY specific about where the problem is
  - Explain what each part of their code does
  - Use simple vocabulary
  - Example: "Your loop starts here on line 3, but before the loop, you need to create a variable to store your answer. Right now there's nowhere to save the results."

▸ IF 0.3 <= {proficiency_score} < 0.6 (INTERMEDIATE):
  - Point out structural patterns (initialization, accumulation, termination)
  - Name common mistakes (off-by-one, missing base case)
  - Explain what's wrong and why
  - Example: "Missing base case for recursion. When n==0, your function will keep calling itself infinitely."

▸ IF {proficiency_score} >= 0.6 (ADVANCED):
  - Be direct about the structural flaw
  - Reference design patterns and best practices
  - Mention edge cases and invariants
  - Assume they can debug themselves
  - Example: "Missing memoization - recomputing overlapping subproblems. Add a cache dict keyed by (i, remaining)."

**Task:** Point out what's WRONG or MISSING in structure. Do NOT write the fix.

Your hint (3-5 sentences):"""

LEVEL_5_TARGETED = """You are a teaching assistant giving SPECIFIC code feedback.

**Problem:** {problem_statement}
**Their Code:** {user_code}
**Issue:** {error_message}

**Student Proficiency: {proficiency_score}/1.0**

YOU MUST adapt based on this score:

▸ IF {proficiency_score} < 0.3 (BEGINNER):
  - Quote their exact code and walk through what it does
  - Use a concrete example with real numbers
  - Show what SHOULD happen vs what IS happening
  - Be very patient and detailed
  - Example: "This line `digit = n % 10` gets the last digit (if n=123, digit becomes 3). Good! But then you need to ADD that digit to your result. Right now you're just storing it but not using it."

▸ IF 0.3 <= {proficiency_score} < 0.6 (INTERMEDIATE):
  - Point to the specific line/section
  - Explain the logical error
  - Give an example showing the failure
  - Example: "Line 7: you update `result` before checking for overflow. If result is already at INT_MAX/10, multiplying by 10 will overflow. Check BEFORE updating."

▸ IF {proficiency_score} >= 0.6 (ADVANCED):
  - Be direct and concise
  - Point out edge cases and constraints
  - Reference algorithmic properties
  - Mention subtle bugs
  - Example: "L12: Integer overflow unchecked. Add guard: `if result > INT_MAX//10 or (result == INT_MAX//10 and digit > 7): return 0`"

**Task:** Point to SPECIFIC lines/issues. Explain what's wrong. Do NOT give the complete solution.

Your hint (3-5 sentences):"""


# ============================================================================
# FEEDBACK AGENT CLASS
# ============================================================================

class FeedbackAgent:
    """
    Generates graduated pedagogical hints for coding problems.
    
    Ensures hints never reveal the solution while providing
    progressively more specific guidance.
    """
    
    def __init__(self):
        """Initialize the feedback agent with Gemini model."""
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not configured. Set it in .env or environment variables."
            )
        
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7,  # Some creativity for varied hints
            max_output_tokens=2048  # Increased from 500 to avoid MAX_TOKENS error
        )
        
        logger.info(f"✅ FeedbackAgent initialized with model: {settings.GEMINI_MODEL}")
        
        # Map hint levels to their prompt templates
        self.hint_templates = {
            1: LEVEL_1_METACOGNITIVE,
            2: LEVEL_2_CONCEPTUAL,
            3: LEVEL_3_STRATEGIC,
            4: LEVEL_4_STRUCTURAL,
            5: LEVEL_5_TARGETED
        }
        
        logger.info("✅ Feedback Agent initialized with Gemini")
    
    async def generate_hint(
        self,
        problem_statement: str,
        user_code: str,
        error_message: Optional[str],
        hint_level: int,
        topics: Optional[list] = None,
        proficiency_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate a hint at the specified level.
        
        Args:
            problem_statement: The problem description
            user_code: User's current code attempt
            error_message: Error message from last submission (if any)
            hint_level: 1-5 (metacognitive to targeted)
            topics: Optional list of topics for context
            proficiency_score: User proficiency (0.0-1.0) to adjust hint difficulty
            
        Returns:
            Dict containing hint text and metadata
            
        Raises:
            ValueError: If hint_level is not 1-5
        """
        if hint_level not in range(1, 6):
            raise ValueError(f"Hint level must be 1-5, got {hint_level}")
        
        # Use proficiency score or default to 0.5 (intermediate)
        proficiency = proficiency_score if proficiency_score is not None else 0.5
        
        logger.info(f"🤔 Generating Level {hint_level} hint (proficiency: {proficiency:.2f})")
        logger.info(f"🔍 DEBUG - FeedbackAgent inputs: problem_length={len(problem_statement)}, code_length={len(user_code or '')}, hint_level={hint_level}")
        
        # Get appropriate prompt template
        template_str = self.hint_templates[hint_level]
        prompt = ChatPromptTemplate.from_template(template_str)
        
        # Prepare context
        error_text = error_message or "No error yet - user is asking for guidance"
        
        # Format prompt with proficiency score
        formatted_prompt = prompt.format_messages(
            problem_statement=problem_statement,
            user_code=user_code or "# No code written yet",
            error_message=error_text,
            proficiency_score=f"{proficiency:.2f}"
        )
        
        logger.info(f"🔍 DEBUG - Sending prompt to LLM (level {hint_level})...")
        print(f"\n{'='*80}")
        print(f"📤 SENDING TO GEMINI (Level {hint_level})")
        print(f"Prompt preview (first 500 chars):")
        prompt_str = str(formatted_prompt[0].content) if formatted_prompt else "No prompt"
        print(f"{prompt_str[:500]}...")
        print(f"{'='*80}\n")
        
        try:
            # Generate hint
            response = await self.llm.ainvoke(formatted_prompt)
            
            print(f"\n{'='*80}")
            print(f"📥 RECEIVED FROM GEMINI (Level {hint_level})")
            print(f"Response type: {type(response)}")
            print(f"Response content length: {len(response.content) if response.content else 0}")
            print(f"Response preview: {response.content[:200] if response.content else 'EMPTY'}...")
            print(f"Full response object attributes: {dir(response)}")
            print(f"Response metadata: {response.response_metadata if hasattr(response, 'response_metadata') else 'No metadata'}")
            print(f"{'='*80}\n")
            hint_text = response.content.strip() if response.content else ""
            
            # Validate that we actually got a hint
            if not hint_text or len(hint_text) < 10:
                logger.error(f"❌ LLM returned empty or too short hint (length: {len(hint_text)})")
                logger.error(f"❌ Response object: {response}")
                return {
                    "hint_text": "I apologize, but I couldn't generate a helpful hint at this moment. Please try again.",
                    "hint_level": hint_level,
                    "level_name": self._get_level_name(hint_level),
                    "success": False,
                    "error": "LLM returned empty response"
                }
            
            logger.info(f"✅ Generated Level {hint_level} hint ({len(hint_text)} chars)")
            logger.info(f"🔍 DEBUG - Hint preview: {hint_text[:100]}...")
            
            return {
                "hint_text": hint_text,
                "hint_level": hint_level,
                "level_name": self._get_level_name(hint_level),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate hint: {e}")
            return {
                "hint_text": "Sorry, I couldn't generate a hint right now. Please try again.",
                "hint_level": hint_level,
                "level_name": self._get_level_name(hint_level),
                "success": False,
                "error": str(e)
            }
    
    def _get_level_name(self, level: int) -> str:
        """Get descriptive name for hint level."""
        names = {
            1: "Metacognitive",
            2: "Conceptual",
            3: "Strategic",
            4: "Structural",
            5: "Targeted"
        }
        return names.get(level, "Unknown")


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

_feedback_agent_instance: Optional[FeedbackAgent] = None


def get_feedback_agent() -> FeedbackAgent:
    """
    Get or create the global feedback agent instance.
    
    Returns:
        Configured FeedbackAgent
    """
    global _feedback_agent_instance
    
    if _feedback_agent_instance is None:
        _feedback_agent_instance = FeedbackAgent()
    
    return _feedback_agent_instance

