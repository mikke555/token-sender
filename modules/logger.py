from sys import stderr

from loguru import logger

logger.remove()
logger.add(
    stderr,
    format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>",
)
logger.add(
    f"log/debug.log",
    format="<white>{time:HH:mm:ss}</white> | <level>{message}</level>",
)
