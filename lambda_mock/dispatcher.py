"""Dispatcher module for routing Lambda function calls."""

from lambda_mock.function_a import run as function_a_run
from lambda_mock.function_b import run as function_b_run

FUNCTIONS = {
    "function_a": function_a_run,
    "function_b": function_b_run,
}


def handler(event):
    """Main Lambda handler that dispatches to the appropriate function."""
    func_name = event.get("function_name")
    
    if func_name not in FUNCTIONS:
        raise ValueError(f"Unknown function: {func_name}")
    
    result = FUNCTIONS[func_name](event)
    return result
