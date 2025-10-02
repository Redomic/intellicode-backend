"""
Topic normalization and mapping utilities for consistent skill tracking.

This module provides functions to normalize topic names and map various tags
to a standardized taxonomy, ensuring consistency in learner_state.mastery keys.
"""

from typing import List, Dict, Set
import re


# Standardized topic taxonomy (lowercase, hyphenated)
TOPIC_TAXONOMY = {
    # Core data structures
    "array": ["array", "arrays"],
    "string": ["string", "strings", "string-matching"],
    "linked-list": ["linked-list", "linkedlist", "linked list"],
    "stack": ["stack", "stacks"],
    "queue": ["queue", "queues"],
    "hash-table": ["hash-table", "hash table", "hashtable", "hash map", "hashmap", "dictionary"],
    "tree": ["tree", "trees", "binary-tree", "binary tree"],
    "graph": ["graph", "graphs"],
    "heap": ["heap", "heaps", "priority-queue", "priority queue"],
    "trie": ["trie", "tries", "prefix-tree"],
    
    # Algorithms
    "sorting": ["sorting", "sort", "merge-sort", "quick-sort", "heap-sort"],
    "searching": ["searching", "search", "binary-search", "binary search"],
    "two-pointers": ["two-pointers", "two pointers", "sliding-window", "sliding window"],
    "dynamic-programming": ["dynamic-programming", "dp", "dynamic programming"],
    "greedy": ["greedy", "greedy-algorithm"],
    "divide-and-conquer": ["divide-and-conquer", "divide and conquer"],
    "backtracking": ["backtracking", "backtrack"],
    "recursion": ["recursion", "recursive"],
    "bit-manipulation": ["bit-manipulation", "bit manipulation", "bitwise"],
    
    # Graph algorithms
    "dfs": ["dfs", "depth-first-search", "depth first search"],
    "bfs": ["bfs", "breadth-first-search", "breadth first search"],
    "union-find": ["union-find", "disjoint-set", "disjoint set"],
    "topological-sort": ["topological-sort", "topological sort"],
    
    # Mathematical
    "math": ["math", "mathematics", "mathematical"],
    "geometry": ["geometry", "geometric"],
    "combinatorics": ["combinatorics", "permutation", "combination"],
    "number-theory": ["number-theory", "number theory"],
    
    # Design patterns
    "design": ["design", "system-design", "oop"],
    "simulation": ["simulation", "simulator"],
    
    # Other
    "matrix": ["matrix", "matrices", "2d-array"],
    "prefix-sum": ["prefix-sum", "prefix sum"],
    "monotonic-stack": ["monotonic-stack", "monotonic stack"],
    "binary-search": ["binary-search", "binary search"],
}


def normalize_topic(topic_name: str) -> str:
    """
    Normalize a topic name to a standardized format.
    
    Args:
        topic_name: Raw topic name (e.g., "Dynamic Programming", "Hash Table")
    
    Returns:
        Normalized topic (e.g., "dynamic-programming", "hash-table")
    
    Examples:
        >>> normalize_topic("Dynamic Programming")
        'dynamic-programming'
        >>> normalize_topic("HASH_TABLE")
        'hash-table'
        >>> normalize_topic("Two Pointers")
        'two-pointers'
    """
    if not topic_name:
        return "general"
    
    # Convert to lowercase and replace underscores/spaces with hyphens
    normalized = topic_name.lower()
    normalized = re.sub(r'[_\s]+', '-', normalized)
    
    # Remove special characters except hyphens
    normalized = re.sub(r'[^a-z0-9-]', '', normalized)
    
    # Remove multiple consecutive hyphens
    normalized = re.sub(r'-+', '-', normalized)
    
    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')
    
    return normalized or "general"


def map_tag_to_topic(tag: str) -> str:
    """
    Map a tag to its primary standardized topic.
    
    Args:
        tag: Tag from question metadata
    
    Returns:
        Standardized topic name
    
    Examples:
        >>> map_tag_to_topic("Array")
        'array'
        >>> map_tag_to_topic("Hash Map")
        'hash-table'
        >>> map_tag_to_topic("DFS")
        'dfs'
    """
    normalized_tag = normalize_topic(tag)
    
    # Check if it matches a standardized topic
    for primary_topic, aliases in TOPIC_TAXONOMY.items():
        if normalized_tag in aliases or normalized_tag == primary_topic:
            return primary_topic
    
    # If no match found, return the normalized version
    return normalized_tag


def get_normalized_topics_from_question(question_data: Dict) -> List[str]:
    """
    Extract and normalize all topics from a question document.
    
    Args:
        question_data: Question document from database
    
    Returns:
        List of unique normalized topics
    
    Examples:
        >>> question = {"tags": ["Array", "Two Pointers"], "difficulty": "easy"}
        >>> get_normalized_topics_from_question(question)
        ['array', 'two-pointers']
    """
    topics: Set[str] = set()
    
    # Extract from 'tags' field
    if "tags" in question_data and question_data["tags"]:
        for tag in question_data["tags"]:
            if isinstance(tag, str):
                topics.add(map_tag_to_topic(tag))
    
    # Extract from 'topic_tags' field (alternative field name)
    if "topic_tags" in question_data and question_data["topic_tags"]:
        for tag in question_data["topic_tags"]:
            if isinstance(tag, str):
                topics.add(map_tag_to_topic(tag))
    
    # If no topics found, return a default
    if not topics:
        topics.add("general")
    
    return sorted(list(topics))


def normalize_topics(topics: List[str]) -> List[str]:
    """
    Normalize a list of topic names.
    
    Args:
        topics: List of raw topic names
    
    Returns:
        List of normalized, unique topics
    
    Examples:
        >>> normalize_topics(["Dynamic Programming", "array", "HASH_TABLE"])
        ['array', 'dynamic-programming', 'hash-table']
    """
    if not topics:
        return ["general"]
    
    normalized_set: Set[str] = set()
    for topic in topics:
        if isinstance(topic, str) and topic.strip():
            normalized_set.add(map_tag_to_topic(topic))
    
    return sorted(list(normalized_set)) if normalized_set else ["general"]


def get_topic_display_name(normalized_topic: str) -> str:
    """
    Convert a normalized topic back to a human-readable display name.
    
    Args:
        normalized_topic: Normalized topic (e.g., "dynamic-programming")
    
    Returns:
        Display name (e.g., "Dynamic Programming")
    
    Examples:
        >>> get_topic_display_name("dynamic-programming")
        'Dynamic Programming'
        >>> get_topic_display_name("hash-table")
        'Hash Table'
    """
    # Split by hyphens and capitalize each word
    words = normalized_topic.split('-')
    return ' '.join(word.capitalize() for word in words)

