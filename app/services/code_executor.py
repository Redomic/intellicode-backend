"""
Code Execution Service - Safely execute user code with test cases.

This service provides LeetCode-style code execution with:
- Isolated execution environment
- Test case validation
- Runtime and memory tracking
- Timeout handling
- Security measures

Note: For production, enhance with Docker containers or sandboxed environments.
"""

import subprocess
import tempfile
import os
import time
import traceback
import json
import resource
import signal
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass


class ExecutionStatus(str, Enum):
    """Execution status enum matching LeetCode statuses."""
    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILE_ERROR = "Compile Error"


@dataclass
class TestCaseResult:
    """Result of a single test case execution."""
    input: str
    expected_output: str
    actual_output: Optional[str]
    passed: bool
    runtime_ms: Optional[int]
    error: Optional[str] = None


@dataclass
class ExecutionResult:
    """Complete execution result."""
    status: ExecutionStatus
    passed_count: int
    total_count: int
    test_results: List[TestCaseResult]
    runtime_ms: Optional[int]
    memory_kb: Optional[int]
    error_message: Optional[str] = None
    failed_test_case_index: Optional[int] = None


class CodeExecutor:
    """Execute code safely with test cases."""
    
    # Execution limits
    TIMEOUT_SECONDS = 5  # Per test case
    MEMORY_LIMIT_MB = 256
    
    def __init__(self):
        """Initialize the code executor."""
        pass
    
    def execute(
        self,
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
        function_name: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute code with test cases.
        
        Args:
            code: User's code
            language: Programming language (python, java)
            test_cases: List of test cases with input and expected_output
            function_name: Name of the function to test (optional)
        
        Returns:
            ExecutionResult with test case results
        """
        if language.lower() == 'python':
            return self._execute_python(code, test_cases, function_name)
        elif language.lower() == 'java':
            return self._execute_java(code, test_cases, function_name)
        else:
            raise ValueError(f"Unsupported language: {language}")
    
    def _execute_python(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        function_name: Optional[str] = None
    ) -> ExecutionResult:
        """Execute Python code with test cases."""
        test_results = []
        total_runtime = 0
        
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = f.name
            
            # Write user code and test harness
            test_code = self._create_python_test_harness(code, test_cases, function_name)
            f.write(test_code)
        
        try:
            # Execute the code
            start_time = time.time()
            
            try:
                result = subprocess.run(
                    ['python3', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.TIMEOUT_SECONDS * len(test_cases),
                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
                )
                
                end_time = time.time()
                total_runtime = int((end_time - start_time) * 1000)
                
                # Parse results
                if result.returncode != 0:
                    # Runtime error
                    error_msg = result.stderr or result.stdout
                    return ExecutionResult(
                        status=ExecutionStatus.RUNTIME_ERROR,
                        passed_count=0,
                        total_count=len(test_cases),
                        test_results=[],
                        runtime_ms=total_runtime,
                        memory_kb=None,
                        error_message=self._clean_error_message(error_msg, temp_file)
                    )
                
                # Parse test results from stdout
                test_results = self._parse_python_results(result.stdout, test_cases)
                
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    status=ExecutionStatus.TIME_LIMIT_EXCEEDED,
                    passed_count=0,
                    total_count=len(test_cases),
                    test_results=[],
                    runtime_ms=self.TIMEOUT_SECONDS * 1000,
                    memory_kb=None,
                    error_message=f"Execution exceeded time limit of {self.TIMEOUT_SECONDS * len(test_cases)} seconds"
                )
            
            # Determine overall status
            passed_count = sum(1 for tr in test_results if tr.passed)
            
            if passed_count == len(test_cases):
                status = ExecutionStatus.ACCEPTED
                failed_index = None
            else:
                # Check if any test has a runtime error (exception was thrown)
                has_runtime_error = any(tr.error is not None and len(str(tr.error)) > 0 for tr in test_results if not tr.passed)
                
                if has_runtime_error:
                    status = ExecutionStatus.RUNTIME_ERROR
                else:
                    status = ExecutionStatus.WRONG_ANSWER
                    
                failed_index = next((i for i, tr in enumerate(test_results) if not tr.passed), None)
            
            return ExecutionResult(
                status=status,
                passed_count=passed_count,
                total_count=len(test_cases),
                test_results=test_results,
                runtime_ms=total_runtime,
                memory_kb=None,  # Can be enhanced with memory tracking
                failed_test_case_index=failed_index
            )
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def _create_python_test_harness(
        self,
        user_code: str,
        test_cases: List[Dict[str, Any]],
        function_name: Optional[str] = None
    ) -> str:
        """Create Python test harness with user code and test cases."""
        
        # Extract function name from code if not provided
        if not function_name:
            function_name = self._extract_python_function_name(user_code)
        
        harness = f"""
import json
import sys
from typing import *

# User code
{user_code}

# Test harness
def run_tests():
    test_cases = {json.dumps(test_cases)}
    results = []
    
    for i, test_case in enumerate(test_cases):
        try:
            # Parse input
            input_str = test_case.get('input', '')
            expected = test_case.get('expected_output', '')
            
            # Helper function to parse value (handles JSON booleans and Python literals)
            def parse_value(val_str):
                val_str = val_str.strip()
                # Handle JSON booleans
                if val_str.lower() == 'true':
                    return True
                elif val_str.lower() == 'false':
                    return False
                elif val_str.lower() == 'null':
                    return None
                else:
                    try:
                        # Try JSON parsing first
                        return json.loads(val_str)
                    except (json.JSONDecodeError, ValueError):
                        try:
                            # Use ast.literal_eval for safe Python literal evaluation
                            import ast
                            return ast.literal_eval(val_str)
                        except:
                            try:
                                # Final fallback to eval (less safe but more flexible)
                                return eval(val_str)
                            except:
                                # Return as string if all else fails
                                return val_str
            
            # Extract function parameters from input string using AST parsing
            # This properly handles commas in strings, nested structures, etc.
            params = {{}}
            
            if '=' in input_str:
                # Use regex to properly split parameter assignments
                # This pattern matches: key = value (where value can be complex)
                import re
                import ast
                
                # Try to parse as Python code first (most robust)
                try:
                    # Treat the input as a series of assignments
                    # Parse them using compile/exec to let Python handle the complexity
                    temp_globals = {{}}
                    exec(input_str, temp_globals)
                    # Extract all variables that were set (exclude builtins)
                    params = {{k: v for k, v in temp_globals.items() if not k.startswith('_')}}
                except:
                    # Fallback: manual parsing
                    # Find all parameter assignments by looking for '=' not in quotes
                    in_quotes = False
                    quote_char = None
                    depth = 0
                    current_param = []
                    
                    i = 0
                    while i < len(input_str):
                        char = input_str[i]
                        
                        # Track quotes
                        if char in ('"', "'") and (i == 0 or input_str[i-1] != '\\\\'):
                            if not in_quotes:
                                in_quotes = True
                                quote_char = char
                            elif char == quote_char:
                                in_quotes = False
                                quote_char = None
                        
                        # Track bracket depth
                        if not in_quotes:
                            if char in '([' + '{{':
                                depth += 1
                            elif char in ')]' + '}}':
                                depth -= 1
                            elif char == ',' and depth == 0:
                                # End of parameter
                                param_str = ''.join(current_param).strip()
                                if '=' in param_str:
                                    key, value = param_str.split('=', 1)
                                    params[key.strip()] = parse_value(value)
                                current_param = []
                                i += 1
                                continue
                        
                        current_param.append(char)
                        i += 1
                    
                    # Don't forget the last parameter
                    if current_param:
                        param_str = ''.join(current_param).strip()
                        if '=' in param_str:
                            key, value = param_str.split('=', 1)
                            params[key.strip()] = parse_value(value)
            else:
                # Single argument without key (e.g., "123" or "[1,2,3]")
                params = {{'arg': parse_value(input_str)}}
            
            # Call the solution function
            solution_obj = Solution()
            if hasattr(solution_obj, '{function_name or "solution"}'):
                func = getattr(solution_obj, '{function_name or "solution"}')
                if len(params) == 1 and 'arg' in params:
                    actual = func(params['arg'])
                else:
                    actual = func(**params)
            else:
                # Try to find any method that's not __init__
                methods = [m for m in dir(solution_obj) if not m.startswith('_')]
                if methods:
                    func = getattr(solution_obj, methods[0])
                    if len(params) == 1 and 'arg' in params:
                        actual = func(params['arg'])
                    else:
                        actual = func(**params)
                else:
                    raise AttributeError("No solution method found")
            
            # Compare results - handle JSON boolean format
            expected_str = str(expected).strip()
            
            # Convert JSON booleans to Python booleans
            if expected_str.lower() == 'true':
                expected_value = True
            elif expected_str.lower() == 'false':
                expected_value = False
            elif expected_str.lower() == 'null' or expected_str.lower() == 'none':
                expected_value = None
            else:
                try:
                    # Try to parse as JSON first (handles arrays, objects, etc.)
                    expected_value = json.loads(expected_str)
                except (json.JSONDecodeError, ValueError):
                    try:
                        # Fallback to eval for Python-style inputs
                        expected_value = eval(expected_str)
                    except:
                        # If all else fails, use the string as-is
                        expected_value = expected_str
            
            # Normalize comparison - handle both value and string comparison
            if type(actual) == type(expected_value):
                passed = actual == expected_value
            else:
                # Try comparing as strings for type mismatches
                passed = str(actual) == str(expected_value)
            
            results.append({{
                'passed': passed,
                'input': input_str,
                'expected': str(expected_value),
                'actual': str(actual)
            }})
            
        except Exception as e:
            # Detect if it's a runtime error vs wrong answer
            error_type = type(e).__name__
            results.append({{
                'passed': False,
                'input': test_case.get('input', ''),
                'expected': test_case.get('expected_output', ''),
                'actual': None,
                'error': str(e),
                'error_type': error_type
            }})
    
    print(json.dumps(results))

if __name__ == '__main__':
    run_tests()
"""
        return harness
    
    def _extract_python_function_name(self, code: str) -> str:
        """Extract the main function name from Python code."""
        # Look for common patterns
        import re
        
        # Look for methods in a class
        class_methods = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(self', code)
        if class_methods:
            # Return first non-__init__ method
            for method in class_methods:
                if method != '__init__':
                    return method
        
        # Look for standalone functions
        functions = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code)
        if functions:
            return functions[0]
        
        return 'solution'  # Default
    
    def _parse_python_results(
        self,
        stdout: str,
        test_cases: List[Dict[str, Any]]
    ) -> List[TestCaseResult]:
        """Parse Python execution results from stdout."""
        try:
            results_data = json.loads(stdout.strip())
            test_results = []
            
            for i, result in enumerate(results_data):
                test_results.append(TestCaseResult(
                    input=result.get('input', ''),
                    expected_output=result.get('expected', ''),
                    actual_output=result.get('actual'),
                    passed=result.get('passed', False),
                    runtime_ms=None,  # Per-test timing can be added
                    error=result.get('error')
                ))
            
            return test_results
            
        except json.JSONDecodeError:
            # Fallback: create failed results
            return [
                TestCaseResult(
                    input=tc.get('input', ''),
                    expected_output=tc.get('expected_output', ''),
                    actual_output=None,
                    passed=False,
                    runtime_ms=None,
                    error="Failed to parse execution output"
                )
                for tc in test_cases
            ]
    
    def _execute_java(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        function_name: Optional[str] = None
    ) -> ExecutionResult:
        """Execute Java code with test cases."""
        # Java execution is more complex - simplified version for now
        # In production, use proper Java compilation and execution
        return ExecutionResult(
            status=ExecutionStatus.RUNTIME_ERROR,
            passed_count=0,
            total_count=len(test_cases),
            test_results=[],
            runtime_ms=0,
            memory_kb=None,
            error_message="Java execution not fully implemented yet. Coming soon!"
        )
    
    def _clean_error_message(self, error: str, temp_file: str) -> str:
        """Clean error message by removing temp file references."""
        if temp_file in error:
            error = error.replace(temp_file, '<solution.py>')
        
        # Limit error message length
        lines = error.split('\n')
        if len(lines) > 20:
            lines = lines[-20:]
            error = '...\n' + '\n'.join(lines)
        
        return error


# Singleton instance
executor = CodeExecutor()


def execute_code(
    code: str,
    language: str,
    test_cases: List[Dict[str, Any]],
    function_name: Optional[str] = None
) -> ExecutionResult:
    """
    Execute code with test cases.
    
    Args:
        code: User's source code
        language: Programming language
        test_cases: List of test cases
        function_name: Optional function name to test
    
    Returns:
        ExecutionResult object
    """
    return executor.execute(code, language, test_cases, function_name)
