import logging
from logging.handlers import RotatingFileHandler

format_str = (
    "[%(levelname)s] [%(name)s] %(asctime)s %(filename)s %(lineno)s %(message)s"
)
logging.basicConfig(
    level=logging.INFO,
    format=format_str,
)

logger = logging.getLogger("tg-signer")
formatter = logging.Formatter(format_str)


def configure_logger(
    log_level: str = "INFO",
    filename: str = "tg-signer.log",
    max_bytes: int = 1024 * 1024 * 3,
):
    logger.setLevel(log_level.strip().upper())
    file_handler = RotatingFileHandler(
        filename,
        maxBytes=max_bytes,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
