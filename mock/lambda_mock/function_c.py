import logging
import time

logger = logging.getLogger(__name__)


def run(event):
    """Simulate heavy processing that exceeds the Lambda timeout.

    BUG: Sleeps for 2 seconds, but Lambda timeout is configured at 1 second.
    """
    duration = event.get("duration", 2)
    logger.info("Starting heavy processing for %s seconds...", duration)
    time.sleep(duration)
    return {"status": "completed"}
