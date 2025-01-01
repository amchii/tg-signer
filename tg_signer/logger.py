import logging
import os
from logging.handlers import RotatingFileHandler

format_str = (
    "[%(levelname)s] [%(name)s] %(asctime)s %(filename)s %(lineno)s %(message)s"
)
formatter = logging.Formatter(format_str)


def configure_logger(
    log_level: str = "INFO",
    filename: str = "tg-signer.log",
    max_bytes: int = 1024 * 1024 * 3,
):
    level = log_level.strip().upper()
    logger = logging.getLogger("tg-signer")
    logger.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        filename,
        maxBytes=max_bytes,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    if os.environ.get("PYROGRAM_LOG_ON", "0") == "1":
        pyrogram_logger = logging.getLogger("pyrogram")
        pyrogram_logger.setLevel(level)
        pyrogram_logger.addHandler(console_handler)
    return logger
