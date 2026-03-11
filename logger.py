"""
logger.py - Event logging. Writes to tracking_log.txt and memory buffer for the GUI.
"""

import logging
import os
from datetime import datetime
from collections import deque
import threading

MAX_CONSOLE_LINES = 500
_log_queue = deque(maxlen=MAX_CONSOLE_LINES)
_queue_lock = threading.Lock()
_callbacks = []


def _setup_file_logger():
    logger = logging.getLogger("tracking_system")
    logger.setLevel(logging.DEBUG)
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracking_log.txt")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                             datefmt="%Y-%m-%d %H:%M:%S")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


_logger = _setup_file_logger()


def _emit(level: str, message: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {message}"
    getattr(_logger, level.lower(), _logger.info)(message)
    with _queue_lock:
        _log_queue.append(line)
        for cb in _callbacks:
            try:
                cb(line)
            except Exception:
                pass


def register_callback(fn):
    _callbacks.append(fn)

def info(msg):    _emit("INFO",    msg)
def warning(msg): _emit("WARNING", msg)
def error(msg):   _emit("ERROR",   msg)
def debug(msg):   _emit("DEBUG",   msg)

def get_recent_lines():
    with _queue_lock:
        return list(_log_queue)
