"""Function A module - calculates average of items."""


def run(event):
    """Calculate the average of items in the event."""
    items = event.get("items", [])
    total = sum(items)
    
    # Handle empty list to prevent ZeroDivisionError
    if len(items) == 0:
        return {"average": 0, "count": 0, "total": 0}
    
    average = total / len(items)
    return {"average": average, "count": len(items), "total": total}
