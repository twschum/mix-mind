import logging
from flask.logging import default_handler
import os

def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(default_handler)
    if os.getenv("FLASK_DEBUG"):
        logger.setLevel(logging.DEBUG)
        logger.debug("FLASK_DEBUG detected, setting to DEBUG level")
    else:
        logger.setLevel(logging.INFO)
    return logger
