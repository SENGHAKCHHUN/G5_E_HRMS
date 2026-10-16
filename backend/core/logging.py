"""Logging setup: one consistent format for the app and uvicorn."""
import logging

from .config import config

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging() -> None:
    logging.basicConfig(level=config.log_level.upper(), format=FORMAT)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"hrms.{name}")
