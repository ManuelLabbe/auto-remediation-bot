import json
import logging
import traceback

from . import function_a, function_b, function_c

logger = logging.getLogger(__name__)

FUNCTIONS = {
    "a": function_a.run,
    "b": function_b.run,
    "c": function_c.run,
}


def handler(event, context):
    func_name = event.get("function")

    if func_name not in FUNCTIONS:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Invalid function '{func_name}'. Must be one of: a, b, c"
            }),
        }

    try:
        result = FUNCTIONS[func_name](event)
        return {
            "statusCode": 200,
            "body": json.dumps(result),
        }
    except Exception:
        logger.error("Error in function_%s:\n%s", func_name, traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": traceback.format_exc(),
            }),
        }
