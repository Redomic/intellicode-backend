"""
Assessment questions for onboarding and skill evaluation.
These questions are designed to assess different skill levels.
"""

from app.models.question import (
    QuestionCreate, DifficultyLevel, QuestionType, SkillCategory,
    MultipleChoiceOption, QuestionExampda
# Beginner Level Questions (Basic Concepts & Simple Data Structures)
BEGINNER_QUESTIONS = [
    QuestionCreate(
        title="What is a variable?",
        description="Choose the best definition of a variable in programming.",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.BASIC_PROGRAMMING],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="A container for storing data values", is_correct=True),
            MultipleChoiceOption(key="B", text="A type of loop in programming", is_correct=False),
            MultipleChoiceOption(key="C", text="A way to comment code", is_correct=False),
            MultipleChoiceOption(key="D", text="A programming language", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="A variable is a container that stores data values. It can hold different types of data like numbers, text, or boolean values."
    ),
    
    QuestionCreate(
        title="Array Index",
        description="In most programming languages, what is the index of the first element in an array?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.ARRAYS],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="1", is_correct=False),
            MultipleChoiceOption(key="B", text="0", is_correct=True),
            MultipleChoiceOption(key="C", text="-1", is_correct=False),
            MultipleChoiceOption(key="D", text="It depends on the array size", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="In most programming languages, arrays use zero-based indexing, meaning the first element is at index 0."
    ),
    
    QuestionCreate(
        title="String Length",
        description="Which of the following best describes how to find the length of a string?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.STRINGS],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="Count each character manually", is_correct=False),
            MultipleChoiceOption(key="B", text="Use a built-in length function or property", is_correct=True),
            MultipleChoiceOption(key="C", text="Convert it to an array first", is_correct=False),
            MultipleChoiceOption(key="D", text="Use a loop to iterate through all characters", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Most programming languages provide built-in functions or properties (like .length, len(), or .size()) to get the length of a string."
    ),
    
    QuestionCreate(
        title="Basic Loop Purpose",
        description="What is the primary purpose of a loop in programming?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.BASIC_PROGRAMMING],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="To make code run faster", is_correct=False),
            MultipleChoiceOption(key="B", text="To repeat a block of code multiple times", is_correct=True),
            MultipleChoiceOption(key="C", text="To store multiple values", is_correct=False),
            MultipleChoiceOption(key="D", text="To handle errors in code", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="A loop is used to repeat a block of code multiple times, either for a specific number of iterations or until a certain condition is met."
    ),
    
    QuestionCreate(
        title="Simple Array Access",
        description="If you have an array arr = [10, 20, 30, 40], what is arr[2]?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.ARRAYS],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="10", is_correct=False),
            MultipleChoiceOption(key="B", text="20", is_correct=False),
            MultipleChoiceOption(key="C", text="30", is_correct=True),
            MultipleChoiceOption(key="D", text="40", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="Array indexing starts at 0, so arr[2] refers to the third element, which is 30."
    ),
    
    QuestionCreate(
        title="Boolean Values",
        description="Which of the following are valid boolean values?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.BASIC_PROGRAMMING],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="true and false", is_correct=True),
            MultipleChoiceOption(key="B", text="yes and no", is_correct=False),
            MultipleChoiceOption(key="C", text="1 and 0 only", is_correct=False),
            MultipleChoiceOption(key="D", text="on and off", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="Boolean values are true and false. While some languages may convert 1/0 to boolean, the actual boolean values are true and false."
    ),
    
    QuestionCreate(
        title="Simple Condition",
        description="What does an if statement do?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.BASIC_PROGRAMMING],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="Always executes code", is_correct=False),
            MultipleChoiceOption(key="B", text="Executes code only if a condition is true", is_correct=True),
            MultipleChoiceOption(key="C", text="Repeats code multiple times", is_correct=False),
            MultipleChoiceOption(key="D", text="Defines a function", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="An if statement executes a block of code only when the specified condition evaluates to true."
    ),
    
    QuestionCreate(
        title="String Concatenation",
        description="What does string concatenation mean?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.STRINGS],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="Breaking a string into parts", is_correct=False),
            MultipleChoiceOption(key="B", text="Joining two or more strings together", is_correct=True),
            MultipleChoiceOption(key="C", text="Converting string to uppercase", is_correct=False),
            MultipleChoiceOption(key="D", text="Finding a character in a string", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="String concatenation is the process of joining two or more strings together to form a single string."
    ),
    
    QuestionCreate(
        title="Array Size",
        description="How do you typically find the number of elements in an array?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.ARRAYS],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="Count manually", is_correct=False),
            MultipleChoiceOption(key="B", text="Use length property or function", is_correct=True),
            MultipleChoiceOption(key="C", text="Loop through all elements", is_correct=False),
            MultipleChoiceOption(key="D", text="Check the last index", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Most programming languages provide a length property or function to get the number of elements in an array."
    ),
    
    QuestionCreate(
        title="Basic Function Purpose",
        description="What is the main purpose of functions in programming?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.BASIC_PROGRAMMING],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="To make programs slower", is_correct=False),
            MultipleChoiceOption(key="B", text="To organize code into reusable blocks", is_correct=True),
            MultipleChoiceOption(key="C", text="To store data", is_correct=False),
            MultipleChoiceOption(key="D", text="To display output only", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Functions allow you to organize code into reusable blocks that can be called multiple times with different inputs."
    ),
    
    QuestionCreate(
        title="What is an Algorithm?",
        description="What best describes an algorithm?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.BASIC_PROGRAMMING],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="A programming language", is_correct=False),
            MultipleChoiceOption(key="B", text="A step-by-step procedure to solve a problem", is_correct=True),
            MultipleChoiceOption(key="C", text="A type of data structure", is_correct=False),
            MultipleChoiceOption(key="D", text="A debugging tool", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="An algorithm is a finite sequence of well-defined instructions to solve a specific problem or perform a computation."
    ),
    
    QuestionCreate(
        title="Simple Linear Search",
        description="In linear search, how do you find an element in an array?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.SORTING_SEARCHING],
        estimated_time_minutes=3,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="Check each element one by one from start to end", is_correct=True),
            MultipleChoiceOption(key="B", text="Jump to the middle and search from there", is_correct=False),
            MultipleChoiceOption(key="C", text="Search from the end to the beginning only", is_correct=False),
            MultipleChoiceOption(key="D", text="Randomly check elements", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="Linear search examines each element in the array sequentially from the beginning until the target element is found or the end is reached."
    ),
    
    QuestionCreate(
        title="Basic Time Complexity",
        description="What does O(1) time complexity mean?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.BASIC_PROGRAMMING],
        estimated_time_minutes=3,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="The operation takes 1 second", is_correct=False),
            MultipleChoiceOption(key="B", text="The operation takes constant time regardless of input size", is_correct=True),
            MultipleChoiceOption(key="C", text="The operation processes 1 element", is_correct=False),
            MultipleChoiceOption(key="D", text="The operation runs once", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="O(1) means constant time complexity - the operation takes the same amount of time regardless of the input size."
    ),
    
    QuestionCreate(
        title="What is a Stack?",
        description="Which analogy best describes a stack data structure?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.STACKS_QUEUES],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="A line of people waiting", is_correct=False),
            MultipleChoiceOption(key="B", text="A pile of plates", is_correct=True),
            MultipleChoiceOption(key="C", text="A parking lot", is_correct=False),
            MultipleChoiceOption(key="D", text="A bookshelf", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="A stack is like a pile of plates - you can only add or remove items from the top (Last In, First Out - LIFO)."
    ),
    
    QuestionCreate(
        title="Simple Queue Concept",
        description="Which analogy best describes a queue data structure?",
        difficulty=DifficultyLevel.BEGINNER,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.STACKS_QUEUES],
        estimated_time_minutes=2,
        points=10,
        options=[
            MultipleChoiceOption(key="A", text="A pile of books", is_correct=False),
            MultipleChoiceOption(key="B", text="A line of people waiting for service", is_correct=True),
            MultipleChoiceOption(key="C", text="A stack of papers", is_correct=False),
            MultipleChoiceOption(key="D", text="A deck of cards", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="A queue is like a line of people waiting - the first person in line is the first to be served (First In, First Out - FIFO)."
    )
]

# Intermediate Level Questions (Data Structures & Algorithms)
INTERMEDIATE_QUESTIONS = [
    QuestionCreate(
        title="Time Complexity of Binary Search",
        description="What is the time complexity of binary search in a sorted array?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.SORTING_SEARCHING],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="O(n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(log n)", is_correct=True),
            MultipleChoiceOption(key="C", text="O(n log n)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(n²)", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Binary search has O(log n) time complexity because it eliminates half of the remaining elements in each step."
    ),
    
    QuestionCreate(
        title="Stack vs Queue",
        description="What is the main difference between a stack and a queue?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.STACKS_QUEUES],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="Stack uses LIFO, Queue uses FIFO", is_correct=True),
            MultipleChoiceOption(key="B", text="Stack is faster than Queue", is_correct=False),
            MultipleChoiceOption(key="C", text="Stack stores numbers, Queue stores strings", is_correct=False),
            MultipleChoiceOption(key="D", text="There is no difference", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="Stack follows Last In, First Out (LIFO) principle, while Queue follows First In, First Out (FIFO) principle."
    ),
    
    QuestionCreate(
        title="Hash Table Collision",
        description="What happens when two different keys hash to the same index in a hash table?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.HASH_TABLES],
        estimated_time_minutes=4,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="The program crashes", is_correct=False),
            MultipleChoiceOption(key="B", text="One key overwrites the other", is_correct=False),
            MultipleChoiceOption(key="C", text="A collision resolution strategy is used", is_correct=True),
            MultipleChoiceOption(key="D", text="The hash table becomes invalid", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="When a collision occurs, collision resolution strategies like chaining or open addressing are used to handle multiple keys hashing to the same index."
    ),
    
    QuestionCreate(
        title="Recursion Base Case",
        description="What is a base case in recursion?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.RECURSION],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="The first function call", is_correct=False),
            MultipleChoiceOption(key="B", text="The condition that stops the recursion", is_correct=True),
            MultipleChoiceOption(key="C", text="The most complex part of the algorithm", is_correct=False),
            MultipleChoiceOption(key="D", text="The return statement", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="A base case is the condition that stops the recursive calls, preventing infinite recursion and providing a way to return a result."
    ),
    
    QuestionCreate(
        title="Bubble Sort Complexity",
        description="What is the worst-case time complexity of bubble sort?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.SORTING_SEARCHING],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="O(n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(n log n)", is_correct=False),
            MultipleChoiceOption(key="C", text="O(n²)", is_correct=True),
            MultipleChoiceOption(key="D", text="O(2^n)", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="Bubble sort has O(n²) worst-case time complexity because it compares every pair of elements, resulting in nested loops."
    ),
    
    QuestionCreate(
        title="Linked List Insertion",
        description="What is the time complexity of inserting an element at the beginning of a linked list?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="O(1)", is_correct=True),
            MultipleChoiceOption(key="B", text="O(n)", is_correct=False),
            MultipleChoiceOption(key="C", text="O(log n)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(n²)", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="Inserting at the beginning of a linked list is O(1) because you only need to update the head pointer and the new node's next pointer."
    ),
    
    QuestionCreate(
        title="Binary Tree Height",
        description="What is the maximum height of a binary tree with n nodes?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=4,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="log n", is_correct=False),
            MultipleChoiceOption(key="B", text="n", is_correct=False),
            MultipleChoiceOption(key="C", text="n - 1", is_correct=True),
            MultipleChoiceOption(key="D", text="2n", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="The maximum height occurs when the tree is completely unbalanced (like a linked list), giving a height of n-1."
    ),
    
    QuestionCreate(
        title="Queue Implementation",
        description="Which data structure is commonly used to implement a queue efficiently?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.STACKS_QUEUES],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="Array with two pointers", is_correct=True),
            MultipleChoiceOption(key="B", text="Single pointer array", is_correct=False),
            MultipleChoiceOption(key="C", text="Hash table", is_correct=False),
            MultipleChoiceOption(key="D", text="Binary tree", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="A queue is efficiently implemented using an array with two pointers (front and rear) or a linked list."
    ),
    
    QuestionCreate(
        title="Hash Function Properties",
        description="What is a desirable property of a good hash function?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.HASH_TABLES],
        estimated_time_minutes=4,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="Always returns the same value", is_correct=False),
            MultipleChoiceOption(key="B", text="Distributes keys uniformly across the hash table", is_correct=True),
            MultipleChoiceOption(key="C", text="Only works with strings", is_correct=False),
            MultipleChoiceOption(key="D", text="Maximizes collisions", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="A good hash function should distribute keys uniformly across the hash table to minimize collisions and ensure good performance."
    ),
    
    QuestionCreate(
        title="Array vs Linked List Access",
        description="What is the main advantage of arrays over linked lists for accessing elements?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.ARRAYS, SkillCategory.TREES],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="Arrays use less memory", is_correct=False),
            MultipleChoiceOption(key="B", text="Arrays provide O(1) random access", is_correct=True),
            MultipleChoiceOption(key="C", text="Arrays are always sorted", is_correct=False),
            MultipleChoiceOption(key="D", text="Arrays can grow dynamically", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Arrays provide O(1) random access to elements using indices, while linked lists require O(n) traversal to reach a specific position."
    ),
    
    QuestionCreate(
        title="Depth-First Search",
        description="Which data structure is typically used to implement depth-first search (DFS)?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.GRAPHS],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="Queue", is_correct=False),
            MultipleChoiceOption(key="B", text="Stack or recursion", is_correct=True),
            MultipleChoiceOption(key="C", text="Hash table", is_correct=False),
            MultipleChoiceOption(key="D", text="Heap", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="DFS uses a stack (either explicitly or implicitly through recursion) to keep track of vertices to visit."
    ),
    
    QuestionCreate(
        title="Binary Search Tree Property",
        description="What property must a binary search tree maintain?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=4,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="All nodes have exactly two children", is_correct=False),
            MultipleChoiceOption(key="B", text="Left subtree values < root < right subtree values", is_correct=True),
            MultipleChoiceOption(key="C", text="The tree is always balanced", is_correct=False),
            MultipleChoiceOption(key="D", text="All leaves are at the same level", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="A BST maintains the property that all values in the left subtree are less than the root, and all values in the right subtree are greater than the root."
    ),
    
    QuestionCreate(
        title="Merge Sort Complexity",
        description="What is the time complexity of merge sort in all cases?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.SORTING_SEARCHING],
        estimated_time_minutes=4,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="O(n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(n log n)", is_correct=True),
            MultipleChoiceOption(key="C", text="O(n²)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(log n)", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Merge sort consistently has O(n log n) time complexity in best, average, and worst cases due to its divide-and-conquer approach."
    ),
    
    QuestionCreate(
        title="String Pattern Matching",
        description="What is the time complexity of the naive string pattern matching algorithm?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.STRINGS],
        estimated_time_minutes=4,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="O(n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(m)", is_correct=False),
            MultipleChoiceOption(key="C", text="O(m * n)", is_correct=True),
            MultipleChoiceOption(key="D", text="O(m + n)", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="The naive pattern matching algorithm has O(m*n) complexity where m is pattern length and n is text length, as it may check every position."
    ),
    
    QuestionCreate(
        title="Breadth-First Search",
        description="Which data structure is typically used to implement breadth-first search (BFS)?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.GRAPHS],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="Stack", is_correct=False),
            MultipleChoiceOption(key="B", text="Queue", is_correct=True),
            MultipleChoiceOption(key="C", text="Hash table", is_correct=False),
            MultipleChoiceOption(key="D", text="Array", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="BFS uses a queue to process vertices level by level, ensuring that all vertices at distance k are processed before vertices at distance k+1."
    ),
    
    QuestionCreate(
        title="Recursive Factorial",
        description="What is the space complexity of a recursive factorial function?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.RECURSION],
        estimated_time_minutes=3,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="O(1)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(n)", is_correct=True),
            MultipleChoiceOption(key="C", text="O(log n)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(n²)", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Recursive factorial has O(n) space complexity due to the call stack storing n function calls."
    ),
    
    QuestionCreate(
        title="Heap Property",
        description="In a max heap, what property must be maintained?",
        difficulty=DifficultyLevel.INTERMEDIATE,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=4,
        points=15,
        options=[
            MultipleChoiceOption(key="A", text="Parent node ≥ child nodes", is_correct=True),
            MultipleChoiceOption(key="B", text="Parent node ≤ child nodes", is_correct=False),
            MultipleChoiceOption(key="C", text="Left child < right child", is_correct=False),
            MultipleChoiceOption(key="D", text="All nodes are equal", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="In a max heap, every parent node must have a value greater than or equal to its children."
    )
]

# Advanced Level Questions (Complex Algorithms & Advanced Data Structures)
ADVANCED_QUESTIONS = [
    QuestionCreate(
        title="Dynamic Programming Principle",
        description="What is the key principle behind dynamic programming?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.DYNAMIC_PROGRAMMING],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Divide and conquer", is_correct=False),
            MultipleChoiceOption(key="B", text="Greedy choice", is_correct=False),
            MultipleChoiceOption(key="C", text="Optimal substructure and overlapping subproblems", is_correct=True),
            MultipleChoiceOption(key="D", text="Breadth-first search", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="Dynamic programming relies on optimal substructure (optimal solution contains optimal solutions to subproblems) and overlapping subproblems (same subproblems are solved multiple times)."
    ),
    
    QuestionCreate(
        title="Graph Traversal Difference",
        description="What is the main difference between DFS and BFS in terms of memory usage?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.GRAPHS],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="DFS uses O(V) space, BFS uses O(V) space", is_correct=False),
            MultipleChoiceOption(key="B", text="DFS uses O(h) space, BFS uses O(w) space", is_correct=True),
            MultipleChoiceOption(key="C", text="DFS uses more memory than BFS always", is_correct=False),
            MultipleChoiceOption(key="D", text="Both use the same amount of memory", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="DFS uses O(h) space where h is the height of the tree/depth of recursion, while BFS uses O(w) space where w is the maximum width of the tree/graph level."
    ),
    
    QuestionCreate(
        title="Tree Balancing",
        description="What is the primary benefit of keeping a binary search tree balanced?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Easier to implement", is_correct=False),
            MultipleChoiceOption(key="B", text="Uses less memory", is_correct=False),
            MultipleChoiceOption(key="C", text="Maintains O(log n) time complexity for operations", is_correct=True),
            MultipleChoiceOption(key="D", text="Allows duplicate values", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="A balanced BST ensures that the height remains O(log n), which maintains O(log n) time complexity for search, insert, and delete operations."
    ),
    
    QuestionCreate(
        title="Space-Time Tradeoff",
        description="In algorithm design, what does 'space-time tradeoff' typically refer to?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.DYNAMIC_PROGRAMMING],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Using more time to save space", is_correct=False),
            MultipleChoiceOption(key="B", text="Using more space to save time", is_correct=False),
            MultipleChoiceOption(key="C", text="Trading off between memory usage and execution time", is_correct=True),
            MultipleChoiceOption(key="D", text="The physical space needed to run algorithms", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="Space-time tradeoff refers to the balance between memory usage and execution time - often you can make an algorithm faster by using more memory, or use less memory but take more time."
    ),
    
    QuestionCreate(
        title="AVL Tree Rotation",
        description="When is a double rotation needed in an AVL tree?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="When the balance factor is ±2", is_correct=False),
            MultipleChoiceOption(key="B", text="When the imbalance forms a zig-zag pattern", is_correct=True),
            MultipleChoiceOption(key="C", text="When inserting into an empty tree", is_correct=False),
            MultipleChoiceOption(key="D", text="When deleting the root node", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="A double rotation (left-right or right-left) is needed when the imbalance forms a zig-zag pattern, where single rotation would not fix the imbalance."
    ),
    
    QuestionCreate(
        title="Dijkstra's Algorithm Complexity",
        description="What is the time complexity of Dijkstra's algorithm using a binary heap?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.GRAPHS],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="O(V²)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(E log V)", is_correct=True),
            MultipleChoiceOption(key="C", text="O(V log E)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(E + V)", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Using a binary heap, Dijkstra's algorithm has O(E log V) complexity, where E is the number of edges and V is the number of vertices."
    ),
    
    QuestionCreate(
        title="Red-Black Tree Properties",
        description="How many properties must a red-black tree satisfy?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="3", is_correct=False),
            MultipleChoiceOption(key="B", text="4", is_correct=False),
            MultipleChoiceOption(key="C", text="5", is_correct=True),
            MultipleChoiceOption(key="D", text="6", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="A red-black tree must satisfy 5 properties: root is black, leaves are black, red nodes have black children, all paths have same black height, and new insertions are red."
    ),
    
    QuestionCreate(
        title="Fibonacci Dynamic Programming",
        description="What is the time complexity of computing Fibonacci numbers using dynamic programming?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.DYNAMIC_PROGRAMMING],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="O(2^n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(n)", is_correct=True),
            MultipleChoiceOption(key="C", text="O(log n)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(n²)", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Dynamic programming reduces Fibonacci computation from O(2^n) to O(n) by storing previously computed values and avoiding redundant calculations."
    ),
    
    QuestionCreate(
        title="Topological Sort Requirement",
        description="What type of graph is required for topological sorting?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.GRAPHS],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Undirected graph", is_correct=False),
            MultipleChoiceOption(key="B", text="Directed acyclic graph (DAG)", is_correct=True),
            MultipleChoiceOption(key="C", text="Directed cyclic graph", is_correct=False),
            MultipleChoiceOption(key="D", text="Complete graph", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Topological sorting is only possible on directed acyclic graphs (DAGs) because cycles would create impossible ordering dependencies."
    ),
    
    QuestionCreate(
        title="Quick Sort Worst Case",
        description="When does Quick Sort perform worst with O(n²) complexity?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.SORTING_SEARCHING],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="When the array is already sorted", is_correct=True),
            MultipleChoiceOption(key="B", text="When the array is randomly shuffled", is_correct=False),
            MultipleChoiceOption(key="C", text="When all elements are equal", is_correct=False),
            MultipleChoiceOption(key="D", text="When the array has duplicate elements", is_correct=False)
        ],
        correct_answer_key="A",
        explanation="Quick Sort performs worst when the pivot is always the smallest or largest element, which happens with sorted arrays using simple pivot selection."
    ),
    
    QuestionCreate(
        title="Knapsack Problem Type",
        description="What type of algorithm optimization problem is the 0/1 Knapsack problem?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.DYNAMIC_PROGRAMMING],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Greedy algorithm", is_correct=False),
            MultipleChoiceOption(key="B", text="Dynamic programming", is_correct=True),
            MultipleChoiceOption(key="C", text="Divide and conquer", is_correct=False),
            MultipleChoiceOption(key="D", text="Backtracking only", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="The 0/1 Knapsack problem is solved optimally using dynamic programming due to its optimal substructure and overlapping subproblems."
    ),
    
    QuestionCreate(
        title="B-Tree Properties",
        description="What is the minimum number of keys in a non-root node of a B-tree of order m?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="m/2", is_correct=False),
            MultipleChoiceOption(key="B", text="⌈m/2⌉ - 1", is_correct=True),
            MultipleChoiceOption(key="C", text="m - 1", is_correct=False),
            MultipleChoiceOption(key="D", text="m", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="In a B-tree of order m, each non-root node must have at least ⌈m/2⌉ - 1 keys to maintain the B-tree properties."
    ),
    
    QuestionCreate(
        title="Minimum Spanning Tree",
        description="Which algorithm is NOT used to find minimum spanning trees?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.GRAPHS],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Kruskal's algorithm", is_correct=False),
            MultipleChoiceOption(key="B", text="Prim's algorithm", is_correct=False),
            MultipleChoiceOption(key="C", text="Dijkstra's algorithm", is_correct=True),
            MultipleChoiceOption(key="D", text="Borůvka's algorithm", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="Dijkstra's algorithm finds shortest paths from a source vertex, not minimum spanning trees. Kruskal's, Prim's, and Borůvka's algorithms find MSTs."
    ),
    
    QuestionCreate(
        title="Heap Sort Stability",
        description="Is Heap Sort a stable sorting algorithm?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.SORTING_SEARCHING, SkillCategory.TREES],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Yes, it always maintains relative order", is_correct=False),
            MultipleChoiceOption(key="B", text="No, it can change relative order of equal elements", is_correct=True),
            MultipleChoiceOption(key="C", text="It depends on the input", is_correct=False),
            MultipleChoiceOption(key="D", text="It depends on the heap implementation", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Heap Sort is not stable because the heap operations can change the relative order of equal elements during the sorting process."
    ),
    
    QuestionCreate(
        title="Longest Common Subsequence",
        description="What is the time complexity of finding the LCS of two strings of length m and n using dynamic programming?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.DYNAMIC_PROGRAMMING, SkillCategory.STRINGS],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="O(m + n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(m * n)", is_correct=True),
            MultipleChoiceOption(key="C", text="O(m² * n²)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(2^min(m,n))", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="The LCS dynamic programming solution uses a 2D table of size m×n, resulting in O(m*n) time complexity."
    ),
    
    QuestionCreate(
        title="Trie Space Complexity",
        description="What is the worst-case space complexity of a Trie storing n strings of maximum length m?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES, SkillCategory.STRINGS],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="O(n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(m)", is_correct=False),
            MultipleChoiceOption(key="C", text="O(n * m)", is_correct=True),
            MultipleChoiceOption(key="D", text="O(n * m * alphabet_size)", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="In the worst case, a Trie storing n strings of length m can have O(n*m) nodes when there's minimal prefix sharing between strings."
    ),
    
    QuestionCreate(
        title="Union-Find Optimization",
        description="What optimization technique improves Union-Find operations to nearly O(1) amortized time?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.GRAPHS],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Path compression only", is_correct=False),
            MultipleChoiceOption(key="B", text="Union by rank only", is_correct=False),
            MultipleChoiceOption(key="C", text="Path compression and union by rank", is_correct=True),
            MultipleChoiceOption(key="D", text="Randomization", is_correct=False)
        ],
        correct_answer_key="C",
        explanation="Combining path compression with union by rank gives Union-Find operations O(α(n)) amortized time, where α is the inverse Ackermann function."
    ),
    
    QuestionCreate(
        title="NP-Complete Problem",
        description="Which of the following is an NP-Complete problem?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.DYNAMIC_PROGRAMMING],
        estimated_time_minutes=5,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="Shortest path in unweighted graph", is_correct=False),
            MultipleChoiceOption(key="B", text="Traveling Salesman Problem", is_correct=True),
            MultipleChoiceOption(key="C", text="Finding minimum spanning tree", is_correct=False),
            MultipleChoiceOption(key="D", text="Binary search", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="The Traveling Salesman Problem is NP-Complete, meaning no known polynomial-time algorithm exists to solve it optimally."
    ),
    
    QuestionCreate(
        title="Skip List Operations",
        description="What is the expected time complexity of search operations in a Skip List?",
        difficulty=DifficultyLevel.ADVANCED,
        question_type=QuestionType.MULTIPLE_CHOICE,
        skill_categories=[SkillCategory.TREES],
        estimated_time_minutes=4,
        points=20,
        options=[
            MultipleChoiceOption(key="A", text="O(n)", is_correct=False),
            MultipleChoiceOption(key="B", text="O(log n)", is_correct=True),
            MultipleChoiceOption(key="C", text="O(√n)", is_correct=False),
            MultipleChoiceOption(key="D", text="O(1)", is_correct=False)
        ],
        correct_answer_key="B",
        explanation="Skip Lists provide O(log n) expected time complexity for search, insert, and delete operations through their probabilistic layered structure."
    )
]

# All questions combined
ALL_ASSESSMENT_QUESTIONS = BEGINNER_QUESTIONS + INTERMEDIATE_QUESTIONS + ADVANCED_QUESTIONS

def get_questions_by_difficulty(difficulty: DifficultyLevel) -> list:
    """Get questions filtered by difficulty level."""
    if difficulty == DifficultyLevel.BEGINNER:
        return BEGINNER_QUESTIONS
    elif difficulty == DifficultyLevel.INTERMEDIATE:
        return INTERMEDIATE_QUESTIONS
    elif difficulty == DifficultyLevel.ADVANCED:
        return ADVANCED_QUESTIONS
    else:
        return ALL_ASSESSMENT_QUESTIONS
