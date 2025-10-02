"""
Memory Manager for Multi-Agent System.

This module provides utilities to safely manage the user.memory field,
which stores long-term learning insights from AI agents.

Key Features:
- Initialize memory for new users
- Append observations without overwriting
- Retrieve specific sections
- Auto-trim when size limit exceeded

Memory Format (Plain Text):
    === MASTERY TRENDS ===
    2025-01-15: DP mastery improved 0.50 → 0.65 after coin-change variants
    
    === MISCONCEPTIONS ===
    Off-by-one errors: Frequent in binary search (detected 3 times)
    
    === BEHAVIORAL INSIGHTS ===
    Flow state: Best performance 8-10 AM (WPM: 45, low pauses)
    
    === RECOMMENDATIONS ===
    Prioritize DP practice in morning sessions
"""

from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Memory configuration
MAX_MEMORY_SIZE = 50_000  # 50KB character limit
SECTION_SEPARATOR = "==="
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"

# Memory sections
SECTION_MASTERY = "MASTERY TRENDS"
SECTION_MISCONCEPTIONS = "MISCONCEPTIONS"
SECTION_BEHAVIORAL = "BEHAVIORAL INSIGHTS"
SECTION_RECOMMENDATIONS = "RECOMMENDATIONS"


class MemoryManager:
    """
    Manages the user.memory field for AI agents.
    
    Ensures thread-safe appending, size limits, and structured format.
    """
    
    @staticmethod
    def initialize_memory() -> str:
        """
        Create empty memory template for new users.
        
        Returns:
            Empty memory string with section headers
            
        Example:
            >>> memory = MemoryManager.initialize_memory()
            >>> print(memory)
            === MASTERY TRENDS ===
            
            === MISCONCEPTIONS ===
            ...
        """
        sections = [
            SECTION_MASTERY,
            SECTION_MISCONCEPTIONS,
            SECTION_BEHAVIORAL,
            SECTION_RECOMMENDATIONS
        ]
        
        memory_parts = []
        for section in sections:
            memory_parts.append(f"{SECTION_SEPARATOR} {section} {SECTION_SEPARATOR}")
            memory_parts.append("")  # Empty line after header
        
        return "\n".join(memory_parts)
    
    @staticmethod
    def append_to_section(
        current_memory: Optional[str],
        section: str,
        observation: str,
        include_timestamp: bool = True
    ) -> str:
        """
        Append an observation to a specific section.
        
        Args:
            current_memory: Current memory string (None for new users)
            section: Section name (e.g., "MASTERY TRENDS")
            observation: Text to append
            include_timestamp: Whether to prefix with timestamp
            
        Returns:
            Updated memory string
            
        Example:
            >>> memory = MemoryManager.append_to_section(
            ...     current_memory="=== MASTERY TRENDS ===\\n",
            ...     section="MASTERY TRENDS",
            ...     observation="DP mastery improved 0.5 → 0.65"
            ... )
        
        Note:
            If memory exceeds MAX_MEMORY_SIZE, oldest entries are trimmed.
        """
        # Initialize if None
        if current_memory is None or current_memory.strip() == "":
            current_memory = MemoryManager.initialize_memory()
        
        # Format observation
        timestamp_prefix = ""
        if include_timestamp:
            timestamp_prefix = f"{datetime.utcnow().strftime(TIMESTAMP_FORMAT)}: "
        
        formatted_observation = f"{timestamp_prefix}{observation}"
        
        # Find section and append
        section_header = f"{SECTION_SEPARATOR} {section} {SECTION_SEPARATOR}"
        
        if section_header not in current_memory:
            # Section doesn't exist, create it
            current_memory += f"\n\n{section_header}\n{formatted_observation}"
        else:
            # Insert after section header
            lines = current_memory.split("\n")
            new_lines = []
            section_found = False
            
            for i, line in enumerate(lines):
                new_lines.append(line)
                
                # Found the section, insert after it
                if line == section_header and not section_found:
                    section_found = True
                    # Find next section or end
                    next_section_idx = None
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith(SECTION_SEPARATOR):
                            next_section_idx = j
                            break
                    
                    # Insert before next section
                    if next_section_idx:
                        # Add to end of current section
                        insert_idx = i + 1
                        # Skip to last non-empty line in section
                        while insert_idx < next_section_idx and lines[insert_idx].strip():
                            insert_idx += 1
                        new_lines.append(formatted_observation)
                    else:
                        # This is the last section
                        new_lines.append(formatted_observation)
            
            current_memory = "\n".join(new_lines)
        
        # Check size and trim if needed
        if len(current_memory) > MAX_MEMORY_SIZE:
            current_memory = MemoryManager._trim_memory(current_memory)
            logger.warning(
                f"Memory exceeded {MAX_MEMORY_SIZE} characters, trimmed oldest entries"
            )
        
        return current_memory
    
    @staticmethod
    def get_section(memory: Optional[str], section: str) -> List[str]:
        """
        Retrieve all entries from a specific section.
        
        Args:
            memory: Current memory string
            section: Section name to retrieve
            
        Returns:
            List of observation strings in that section
            
        Example:
            >>> observations = MemoryManager.get_section(memory, "MISCONCEPTIONS")
            >>> print(observations)
            ['Off-by-one errors: Frequent in binary search', ...]
        """
        if not memory:
            return []
        
        section_header = f"{SECTION_SEPARATOR} {section} {SECTION_SEPARATOR}"
        
        if section_header not in memory:
            return []
        
        lines = memory.split("\n")
        observations = []
        in_section = False
        
        for line in lines:
            if line == section_header:
                in_section = True
                continue
            
            # Hit next section
            if in_section and line.startswith(SECTION_SEPARATOR):
                break
            
            # Collect non-empty lines
            if in_section and line.strip():
                observations.append(line.strip())
        
        return observations
    
    @staticmethod
    def _trim_memory(memory: str, target_size: int = int(MAX_MEMORY_SIZE * 0.8)) -> str:
        """
        Trim oldest entries to bring memory under size limit.
        
        Strategy: Keep most recent entries from each section.
        
        Args:
            memory: Current memory string
            target_size: Target size after trimming (default: 80% of max)
            
        Returns:
            Trimmed memory string
        """
        if len(memory) <= target_size:
            return memory
        
        # Parse sections
        sections_data: Dict[str, List[str]] = {}
        current_section = None
        
        lines = memory.split("\n")
        for line in lines:
            # Section header
            if line.startswith(SECTION_SEPARATOR):
                section_name = line.replace(SECTION_SEPARATOR, "").strip()
                current_section = section_name
                sections_data[section_name] = []
            elif current_section and line.strip():
                sections_data[current_section].append(line)
        
        # Keep most recent entries (last 50% of each section)
        trimmed_sections = {}
        for section_name, entries in sections_data.items():
            if len(entries) > 5:  # Only trim if more than 5 entries
                keep_count = max(5, len(entries) // 2)
                trimmed_sections[section_name] = entries[-keep_count:]
            else:
                trimmed_sections[section_name] = entries
        
        # Rebuild memory
        rebuilt = []
        for section_name, entries in trimmed_sections.items():
            rebuilt.append(f"{SECTION_SEPARATOR} {section_name} {SECTION_SEPARATOR}")
            for entry in entries:
                rebuilt.append(entry)
            rebuilt.append("")  # Empty line after section
        
        return "\n".join(rebuilt)
    
    @staticmethod
    def get_memory_stats(memory: Optional[str]) -> Dict[str, int]:
        """
        Get statistics about memory usage.
        
        Args:
            memory: Current memory string
            
        Returns:
            Dict with stats: size, entry_count, sections
            
        Example:
            >>> stats = MemoryManager.get_memory_stats(memory)
            >>> print(stats)
            {'size_bytes': 1234, 'entry_count': 15, 'sections': 4}
        """
        if not memory:
            return {"size_bytes": 0, "entry_count": 0, "sections": 0}
        
        # Count entries (non-empty lines that aren't section headers)
        lines = memory.split("\n")
        entry_count = sum(
            1 for line in lines 
            if line.strip() and not line.startswith(SECTION_SEPARATOR)
        )
        
        # Count sections
        section_count = sum(1 for line in lines if line.startswith(SECTION_SEPARATOR))
        
        return {
            "size_bytes": len(memory),
            "entry_count": entry_count,
            "sections": section_count // 2  # Each section has 2 separators
        }


# Convenience functions for common operations

def add_mastery_trend(memory: Optional[str], trend: str) -> str:
    """Add a mastery trend observation."""
    return MemoryManager.append_to_section(memory, SECTION_MASTERY, trend)


def add_misconception(memory: Optional[str], misconception: str) -> str:
    """Add a misconception observation."""
    return MemoryManager.append_to_section(memory, SECTION_MISCONCEPTIONS, misconception)


def add_behavioral_insight(memory: Optional[str], insight: str) -> str:
    """Add a behavioral insight."""
    return MemoryManager.append_to_section(memory, SECTION_BEHAVIORAL, insight)


def add_recommendation(memory: Optional[str], recommendation: str) -> str:
    """Add a strategic recommendation."""
    return MemoryManager.append_to_section(memory, SECTION_RECOMMENDATIONS, recommendation)

