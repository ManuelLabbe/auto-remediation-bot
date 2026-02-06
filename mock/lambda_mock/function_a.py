import logging

logger = logging.getLogger(__name__)


def run(event):
    """Calculate average of a list of numbers.

    BUG: When the list is empty, divides by zero.
    """
    items = event.get("items", [])
    total = sum(items)
    average = total / len(items)
    return {"average": average}
