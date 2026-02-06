import logging

logger = logging.getLogger(__name__)


def run(event):
    """Build a greeting message from name and age.

    BUG: Concatenates str + int directly, causing TypeError.
    """
    name = event.get("name", "World")
    age = event.get("age", 0)
    message = "Hello " + name + " age: " + str(age)
    return {"message": message}
