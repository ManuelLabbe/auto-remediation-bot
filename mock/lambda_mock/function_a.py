import logging

logger = logging.getLogger(__name__)


def run(event):
    """Calculate average of a list of numbers.

    Returns None for empty lists to avoid division by zero.
    """
    items = event.get("items", [])
    if not items:
        return {"average": None}
    total = sum(items)
    average = total / len(items)
    return {"average": average}
