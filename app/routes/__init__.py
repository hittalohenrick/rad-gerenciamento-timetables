from flask import Blueprint

bp = Blueprint("main", __name__)

# Re-export helpers used by tests/importers.
from .helpers import find_timetable_conflict, times_overlap

# Register route modules.
from . import admin  # noqa: E402,F401
from . import auth  # noqa: E402,F401
from . import professor  # noqa: E402,F401

__all__ = ["bp", "find_timetable_conflict", "times_overlap"]
