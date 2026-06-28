from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app_main.config import LoggingConfig

_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_RUN_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
_DETAIL_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_ROTATE_KW = {
    "encoding": "utf-8",
    "maxBytes": 10 * 1024 * 1024,
    "backupCount": 5,
}


class _ExactLevelFilter(logging.Filter):
    def __init__(self, level: int) -> None:
        super().__init__()
        self._level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self._level


class _MinLevelFilter(logging.Filter):
    def __init__(self, level: int) -> None:
        super().__init__()
        self._level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self._level


class PerModuleDebugHandler(logging.Handler):
    def __init__(self, session_dir: Path, formatter: logging.Formatter) -> None:
        super().__init__(logging.DEBUG)
        self._session_dir = session_dir
        self._formatter = formatter
        self._handlers: dict[str, RotatingFileHandler] = {}
        self.addFilter(_ExactLevelFilter(logging.DEBUG))

    def emit(self, record: logging.LogRecord) -> None:
        safe_name = _safe_log_name(record.name or "root")
        handler = self._handlers.get(safe_name)
        if handler is None:
            path = self._session_dir / f"{safe_name}.log"
            handler = RotatingFileHandler(path, **_ROTATE_KW)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(self._formatter)
            self._handlers[safe_name] = handler
        handler.emit(record)

    def close(self) -> None:
        for handler in self._handlers.values():
            handler.close()
        self._handlers.clear()
        super().close()


def setup_logging(config: LoggingConfig) -> Path | None:
    level = _level(config.level)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(_DETAIL_FORMAT, datefmt=_DATE_FORMAT))
    root_logger.addHandler(console_handler)

    if not config.enabled:
        return None

    now = datetime.now()
    session_dir = Path(config.root_dir) / now.strftime("%Y-%m-%d") / now.strftime("%H-%M-%S")
    modules_dir = session_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    run_handler = RotatingFileHandler(session_dir / "run.log", **_ROTATE_KW)
    run_handler.setLevel(level)
    run_handler.addFilter(_MinLevelFilter(level))
    run_handler.setFormatter(logging.Formatter(_RUN_FORMAT, datefmt=_DATE_FORMAT))
    root_logger.addHandler(run_handler)

    error_handler = RotatingFileHandler(session_dir / "error.log", **_ROTATE_KW)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(_DETAIL_FORMAT, datefmt=_DATE_FORMAT))
    root_logger.addHandler(error_handler)

    module_handler = PerModuleDebugHandler(
        modules_dir,
        logging.Formatter(_DETAIL_FORMAT, datefmt=_DATE_FORMAT),
    )
    root_logger.addHandler(module_handler)

    return session_dir


def _level(value: str) -> int:
    level = logging.getLevelName(value.upper())
    if isinstance(level, int):
        return level
    raise ValueError(f"Invalid logging level: {value}")


def _safe_log_name(name: str) -> str:
    safe = []
    for char in name:
        if char.isalnum() or char in {".", "_", "-"}:
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("._") or "root"
