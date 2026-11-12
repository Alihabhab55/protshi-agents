"""W06-D2 - one logging setup for every stage.

Two audiences, two handlers on the same records:
  screen  readable lines, no timestamps - you are watching it live
  file    logs/run.log, EVERYTHING, with timestamps - the record you quote later

Each module says `log = logging.getLogger(__name__)` and calls log.info / log.warning
/ log.error / log.debug. Nothing in the modules knows or cares where the lines go;
only this file decides that. That is the whole point of logging over print.

Levels, as used in this project:
  DEBUG    detail only the file needs: per-attempt token counts, rejected tool
           input, tracebacks, the command line that started the run
  INFO     one readable line per event: a bag skipped, extracted, pushed; totals
  WARNING  something odd but handled: a photo skipped, a retry, Shopify throttling
  ERROR    a bag failed (the run goes on - that is W04-D5's job)
"""

import logging
import sys
from pathlib import Path

LOG_FILE = Path("logs") / "run.log"
# Libraries that log every HTTP request at INFO/DEBUG. Useful never, noisy always.
# Matched by PREFIX: the Anthropic SDK ships its copies as "httpx2"/"httpcore2", and
# W07 adds OpenAI and Google clients. Their WARNINGs and ERRORs still get through.
NOISY_PREFIXES = ("httpx", "httpcore", "anthropic", "urllib3", "openai", "google")


class QuietLibraries(logging.Filter):
    """Drop INFO/DEBUG chatter from HTTP libraries; keep everything of ours."""

    def filter(self, record):
        if record.levelno >= logging.WARNING:
            return True
        return not record.name.startswith(NOISY_PREFIXES)


class ScreenFormatter(logging.Formatter):
    """INFO lines as they are; WARNING and above get a prefix so they stand out."""

    def format(self, record):
        message = record.getMessage()
        if record.levelno >= logging.WARNING:
            return f"{record.levelname}: {message}"
        return message


def setup_logging(log_file=LOG_FILE, screen_level=logging.INFO):
    """Install the screen and file handlers once. Safe to call more than once."""
    root = logging.getLogger()
    if getattr(root, "protshi_handlers", False):
        return                      # already set up (tests call main() several times)
    root.protshi_handlers = True
    # The root lets everything through; each HANDLER decides what it keeps.
    root.setLevel(logging.DEBUG)

    screen = logging.StreamHandler(sys.stdout)
    screen.setLevel(screen_level)
    screen.setFormatter(ScreenFormatter())
    screen.addFilter(QuietLibraries())
    root.addHandler(screen)

    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    # utf-8, or the first em dash or Arabic title in a description crashes the handler
    # on Windows (the terminal's cp1252 problem from W05-D2, this time on disk).
    to_file = logging.FileHandler(log_file, encoding="utf-8")
    to_file.setLevel(logging.DEBUG)
    to_file.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    to_file.addFilter(QuietLibraries())
    root.addHandler(to_file)

    # File only: a marker line per run, so you can find "the last run" in run.log.
    logging.getLogger("session").debug("---- %s", " ".join(sys.argv))
