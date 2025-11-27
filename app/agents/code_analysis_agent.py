
"""
Code Analysis Agent - Provides code quality improvement suggestions.

This agent analyzes user's code AFTER it passes all tests and suggests:
- Time complexity optimizations
- Space complexity improvements
- Code readability enhancements
- Edge case considerations
- Best practices and patterns

Architecture:
    - Only runs on SUCCESSFUL submissions (all tests pass)
    - Never reveals complete solutions
    - Provides actionable, line-specific feedback
    - Adapts suggestions based on user proficiency level

Usage:
    agent = CodeAnalysisAgent()
    analysis = await agent.analyze_code(
        problem_statement="...",
        user_code="...",
        test_results=[...],
        proficiency_score=0.7
    )
"""

from typing import Dict, Any, Optional, List
import logging
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# RESPONSE VALIDATION & PARSING
# ============================================================================

def validate_and_parse_analysis(analysis_text: str) -> Dict[str, Any]:
    """
    Validate and parse the structured analysis response.
    
    Expected format:
        SUCCESS_MESSAGE: Message here
        
        SUGGESTION|TYPE|Line X|Title|Explanation
        SUGGESTION|TYPE|Line Y|Title|Explanation
        
        OVERALL: Assessment here
    
    Or for optimal code with no suggestions:
        SUCCESS_MESSAGE: Message here
        
        NO_SUGGESTIONS: Reason why code is already optimal
        
        OVERALL: Assessment here
    
    Args:
        analysis_text: Raw text from LLM
        
    Returns:
        Dict with parsed components and validation status
        
    Note:
        If validation fails, returns a structured fallback response.
        Case added to handle when LLM doesn't follow format (2025-01-29).
        Updated to handle NO_SUGGESTIONS case for already-optimal code (2025-10-29).
    """
    lines = [line.strip() for line in analysis_text.split('\n') if line.strip()]
    
    parsed = {
        'success_message': '',
        'suggestions': [],
        'no_suggestions_reason': None,  # New field for optimal code case
        'overall': '',
        'is_valid': True,
        'validation_errors': []
    }
    
    # Extract components
    success_message_found = False
    overall_found = False
    no_suggestions_found = False
    
    for line in lines:
        # Parse SUCCESS_MESSAGE
        if line.startswith('SUCCESS_MESSAGE:'):
            parsed['success_message'] = line.replace('SUCCESS_MESSAGE:', '').strip()
            success_message_found = True
            
        # Parse NO_SUGGESTIONS (code is already optimal)
        elif line.startswith('NO_SUGGESTIONS:'):
            parsed['no_suggestions_reason'] = line.replace('NO_SUGGESTIONS:', '').strip()
            no_suggestions_found = True
            
        # Parse SUGGESTION
        elif line.startswith('SUGGESTION|'):
            suggestion_parts = line.replace('SUGGESTION|', '').split('|')
            
            if len(suggestion_parts) >= 4:
                suggestion_type = suggestion_parts[0].strip()
                line_ref = suggestion_parts[1].strip()
                title = suggestion_parts[2].strip()
                explanation = '|'.join(suggestion_parts[3:]).strip()  # Handle pipes in explanation
                
                # Validate suggestion type
                valid_types = ['TIME', 'SPACE', 'READABILITY', 'EDGE_CASE']
                if suggestion_type not in valid_types:
                    parsed['validation_errors'].append(
                        f"Invalid suggestion type '{suggestion_type}' - must be one of {valid_types}"
                    )
                    parsed['is_valid'] = False
                
                parsed['suggestions'].append({
                    'type': suggestion_type,
                    'line': line_ref,
                    'title': title,
                    'explanation': explanation
                })
            else:
                parsed['validation_errors'].append(
                    f"Malformed SUGGESTION line: {line} (expected 4+ fields)"
                )
                parsed['is_valid'] = False
                
        # Parse OVERALL
        elif line.startswith('OVERALL:'):
            parsed['overall'] = line.replace('OVERALL:', '').strip()
            overall_found = True
    
    # Validate required components
    if not success_message_found:
        parsed['validation_errors'].append("Missing SUCCESS_MESSAGE")
        parsed['is_valid'] = False
        parsed['success_message'] = "Your code passed all tests!"
    
    # If NO_SUGGESTIONS was provided, that's valid (code is optimal)
    if no_suggestions_found:
        logger.info("✅ Code is already optimal - no suggestions needed")
    # If no suggestions AND no NO_SUGGESTIONS marker, that's an error
    elif len(parsed['suggestions']) == 0:
        parsed['validation_errors'].append("No SUGGESTION entries or NO_SUGGESTIONS marker found")
        parsed['is_valid'] = False
        # Don't add fallback - let frontend handle this
    
    if not overall_found:
        parsed['validation_errors'].append("Missing OVERALL assessment")
        parsed['is_valid'] = False
        parsed['overall'] = "Great job completing this problem!"
    
    # Log validation results
    if not parsed['is_valid']:
        logger.warning(f"⚠️ Analysis validation failed: {parsed['validation_errors']}")
        logger.warning(f"📄 Original text: {analysis_text[:200]}...")
    else:
        if no_suggestions_found:
            logger.info("✅ Analysis validated: Code is already optimal (no suggestions)")
        else:
            logger.info(f"✅ Analysis validated: {len(parsed['suggestions'])} suggestions found")
    
    return parsed


def format_parsed_analysis(parsed: Dict[str, Any]) -> str:
    """
    Convert parsed analysis back to structured text format.
    
    This ensures the frontend always receives properly formatted data,
    even if we had to add fallback content.
    
    Args:
        parsed: Dictionary from validate_and_parse_analysis()
        
    Returns:
        Properly formatted analysis text
    """
    lines = [f"SUCCESS_MESSAGE: {parsed['success_message']}", ""]
    
    # Handle NO_SUGGESTIONS case (code is already optimal)
    if parsed.get('no_suggestions_reason'):
        lines.append(f"NO_SUGGESTIONS: {parsed['no_suggestions_reason']}")
    else:
        # Add suggestions
        for suggestion in parsed['suggestions']:
            lines.append(
                f"SUGGESTION|{suggestion['type']}|{suggestion['line']}|"
                f"{suggestion['title']}|{suggestion['explanation']}"
            )
    
    lines.extend(["", f"OVERALL: {parsed['overall']}"])
    
    return '\n'.join(lines)


# ============================================================================
# ANALYSIS PROMPT TEMPLATE
# ============================================================================

CODE_ANALYSIS_PROMPT = """You are an expert code reviewer helping a student improve their code quality.

<Problem>
{problem_statement}
</Problem>

<StudentCode>
{user_code}
</StudentCode>

<TestResults>
✅ All {test_count} test cases passed successfully!
</TestResults>

<StudentProficiency>
{proficiency_score}/1.0
</StudentProficiency>

<AdaptationRules>
YOU MUST adapt your feedback based on proficiency:

▸ IF proficiency < 0.3 (BEGINNER):
  - Use simple, encouraging language
  - Focus on ONE main improvement
  - Explain concepts clearly with analogies
  - Celebrate their success first
  - Keep suggestions actionable and not overwhelming
  - Example: "Great job! Your code works perfectly. One way to make it faster: instead of checking every item twice (nested loops), you could remember which items you've seen using a dictionary. This would make your code run much faster on large lists!"

▸ IF proficiency >= 0.3 AND < 0.6 (INTERMEDIATE):
  - Point out 2-3 key improvements
  - Reference specific algorithmic concepts
  - Mention time/space complexity with Big-O notation
  - Suggest concrete refactoring opportunities
  - Example: "Nice work! Here are some optimizations: 1) Line 8: Nested loop creates O(n²) time - consider using a hash map for O(n) lookup. 2) Line 12: Magic number '100' should be a named constant. 3) Consider edge case: empty array handling."

▸ IF proficiency >= 0.6 (ADVANCED):
  - Provide detailed complexity analysis
  - Suggest advanced optimizations and patterns
  - Point out subtle edge cases and corner cases
  - Reference industry best practices
  - Be concise and technical
  - Example: "Solid implementation. Optimizations: 1) O(n²) brute force at L15-20 → monotonic stack for O(n) single pass. 2) Space: O(n) auxiliary storage avoidable with two-pointer in-place approach. 3) Edge: Integer overflow unchecked at L25. 4) Style: Extract magic constants, add type hints."
</AdaptationRules>

<CRITICAL_FORMATTING_INSTRUCTIONS>
YOU MUST FOLLOW THIS EXACT FORMAT. DO NOT DEVIATE. NO BRACKETS, NO MARKDOWN, NO NUMBERING.

Your response MUST use this structure with pipe delimiters (|):

SUCCESS_MESSAGE: Your code passed all tests!

SUGGESTION|TYPE|Line X|Short title here|Detailed explanation here.
SUGGESTION|TYPE|Line Y|Another title here|Another explanation here.

OVERALL: One sentence overall assessment.

REQUIRED FORMAT RULES:
1. Start with "SUCCESS_MESSAGE:" followed by a congratulatory message
2. Each suggestion MUST start with "SUGGESTION|" (uppercase, followed by pipe)
3. Use pipe character "|" to separate fields (NOT brackets, NOT colons)
4. Field order: SUGGESTION|TYPE|Line|Title|Explanation
5. TYPE must be exactly: TIME or SPACE or READABILITY or EDGE_CASE
6. Line format: "Line 8" or "Line 8-12" or "General"
7. Title: 4-8 words describing the optimization
8. Explanation: 1-2 sentences, clear and actionable
9. End with "OVERALL:" followed by one encouraging sentence

IMPORTANT - BE HONEST ABOUT CODE QUALITY:
- If the code is ALREADY well-optimized with good time/space complexity, readability, and edge case handling, provide 0 suggestions
- ONLY suggest improvements if there are REAL, MEANINGFUL optimizations to make
- DO NOT make up generic suggestions just to fill space
- DO NOT suggest changes that wouldn't actually improve the code
- If there are no real improvements needed, use this format:

SUCCESS_MESSAGE: Excellent work! Your solution passed all tests.

NO_SUGGESTIONS: Your code is already well-optimized with efficient time complexity, clean structure, and proper edge case handling.

OVERALL: Your solution demonstrates excellent problem-solving and coding practices!

DO NOT USE:
- Brackets like [Title] or [Explanation]
- Numbered lists like 1., 2., 3.
- Markdown formatting like **, __, etc.
- Multiple paragraphs
- Code blocks
- Any format other than the pipe-delimited structure
- Generic suggestions when code is already optimal

EXAMPLE WITH REAL SUGGESTIONS:
SUCCESS_MESSAGE: Excellent work! Your solution passed all tests.

SUGGESTION|TIME|Line 15|Optimize nested loop with hash map|Your current O(n²) nested loop can be reduced to O(n) by using a hash map to store seen values.
SUGGESTION|READABILITY|Line 8|Extract magic number to constant|The hardcoded value 100 should be a named constant like MAX_SIZE for better maintainability.

OVERALL: Your solution demonstrates solid problem-solving skills—keep refining your approach!

EXAMPLE WITH NO SUGGESTIONS (ALREADY OPTIMAL):
SUCCESS_MESSAGE: Excellent work! Your solution passed all tests.

NO_SUGGESTIONS: Your code demonstrates optimal O(n) time complexity, efficient space usage, excellent readability with clear variable names, and comprehensive edge case handling.

OVERALL: This is production-quality code—outstanding work!
</CRITICAL_FORMATTING_INSTRUCTIONS>

Your analysis:"""


# ============================================================================
# CODE ANALYSIS AGENT CLASS
# ============================================================================

class CodeAnalysisAgent:
    """
    Analyzes code quality and suggests optimizations.
    
    Only runs on successful submissions (all tests pass).
    Provides actionable feedback on time/space complexity,
    readability, and edge cases.
    """
    
    def __init__(self):
        """Initialize the code analysis agent with Gemini model."""
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not configured. Set it in .env or environment variables."
            )
        
        # Configure for code analysis with optimal settings
        # Research: Gemini 2.5 Flash supports up to 65,535 output tokens
        # Adaptive thinking uses internal reasoning budget automatically
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.4,  # Lower temp (0.2-0.4) for focused, consistent code review
            max_output_tokens=12288  # Doubled from 4096
        )
        
        logger.info(f"✅ CodeAnalysisAgent initialized with model: {settings.GEMINI_MODEL}")
    
    async def analyze_code(
        self,
        problem_statement: str,
        user_code: str,
        test_results: Optional[List[Dict[str, Any]]] = None,
        proficiency_score: Optional[float] = None,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Analyze code and provide optimization suggestions.
        
        Args:
            problem_statement: The problem description
            user_code: User's code that passed all tests
            test_results: Optional list of test results (all should be passed)
            proficiency_score: User proficiency (0.0-1.0) to adjust feedback complexity
            language: Programming language of the code
            
        Returns:
            Dict containing analysis feedback and metadata
            
        Note:
            This should ONLY be called for code that passed ALL tests.
        """
        # Use proficiency score or default to intermediate (0.5)
        proficiency = proficiency_score if proficiency_score is not None else 0.5
        
        # Count passed tests
        test_count = len(test_results) if test_results else 0
        
        logger.info(f"🔍 Analyzing code (proficiency: {proficiency:.2f}, language: {language}, tests: {test_count})")
        
        # Get prompt template
        prompt = ChatPromptTemplate.from_template(CODE_ANALYSIS_PROMPT)
        
        # Format prompt
        formatted_prompt = prompt.format_messages(
            problem_statement=problem_statement,
            user_code=user_code,
            test_count=test_count,
            proficiency_score=f"{proficiency:.2f}"
        )
        
        logger.info(f"📤 Sending code analysis request to LLM...")
        
        try:
            # Generate analysis
            response = await self.llm.ainvoke(formatted_prompt)
            
            raw_analysis_text = response.content.strip() if response.content else ""
            
            # Log token usage for monitoring
            if hasattr(response, 'usage_metadata'):
                logger.info(f"📊 Token usage: {response.usage_metadata}")
            
            # Validate response length
            if not raw_analysis_text or len(raw_analysis_text) < 20:
                logger.error(f"❌ LLM returned empty or too short analysis (length: {len(raw_analysis_text)})")
                logger.error(f"❌ Full response object: {response}")
                return self._create_fallback_analysis(proficiency, language)
            
            logger.info(f"✅ Code analysis generated ({len(raw_analysis_text)} chars)")
            logger.debug(f"📄 Raw analysis:\n{raw_analysis_text}")
            
            # Validate and parse the structured response
            parsed = validate_and_parse_analysis(raw_analysis_text)
            
            # If validation failed, reformat with parsed components (including fallbacks)
            if not parsed['is_valid']:
                logger.warning("⚠️ LLM response didn't follow format - applying fallbacks")
                analysis_text = format_parsed_analysis(parsed)
            else:
                # Use original text if valid
                analysis_text = raw_analysis_text
            
            return {
                "analysis_text": analysis_text,
                "suggestion_count": len(parsed['suggestions']),
                "proficiency_level": self._get_proficiency_level(proficiency),
                "language": language,
                "success": True,
                "validation_warnings": parsed['validation_errors'] if not parsed['is_valid'] else []
            }
            
        except Exception as e:
            logger.exception(f"❌ Failed to generate code analysis: {e}")
            return self._create_fallback_analysis(proficiency, language, error=str(e))
    
    def _get_proficiency_level(self, score: float) -> str:
        """Get descriptive proficiency level."""
        if score < 0.3:
            return "Beginner"
        elif score < 0.6:
            return "Intermediate"
        else:
            return "Advanced"
    
    def _create_fallback_analysis(
        self, 
        proficiency: float, 
        language: str, 
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a structured fallback analysis when LLM fails.
        
        Returns a "no suggestions" message since we can't reliably analyze without the LLM.
        It's more honest to say "analysis unavailable" than to provide generic suggestions.
        
        Args:
            proficiency: User's proficiency score
            language: Programming language
            error: Optional error message
            
        Returns:
            Structured analysis response
            
        Note:
            Updated to return NO_SUGGESTIONS on error rather than generic advice (2025-10-29).
        """
        fallback_parsed = {
            'success_message': "Excellent work! Your code passed all tests.",
            'suggestions': [],
            'no_suggestions_reason': 'Code analysis temporarily unavailable, but your solution is working correctly.',
            'overall': 'Your solution successfully solves the problem. Keep up the great work!',
            'is_valid': True,
            'validation_errors': []
        }
        
        analysis_text = format_parsed_analysis(fallback_parsed)
        
        return {
            "analysis_text": analysis_text,
            "suggestion_count": 0,
            "proficiency_level": self._get_proficiency_level(proficiency),
            "language": language,
            "success": False,
            "error": error or "Analysis generation failed"
        }


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

_code_analysis_agent_instance: Optional[CodeAnalysisAgent] = None


def get_code_analysis_agent() -> CodeAnalysisAgent:
    """
    Get or create the global code analysis agent instance.
    
    Returns:
        Configured CodeAnalysisAgent
    """
    global _code_analysis_agent_instance
    
    if _code_analysis_agent_instance is None:
        _code_analysis_agent_instance = CodeAnalysisAgent()
    
    return _code_analysis_agent_instance

