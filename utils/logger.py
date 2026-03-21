import logging
import sys

# configura el logger principal del proyecto
def setup_logger(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("yalex")
    if logger.handlers:
        return logger   # ya configurado

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger

logger = setup_logger()
