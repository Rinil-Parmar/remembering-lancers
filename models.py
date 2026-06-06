"""Backward-compatible model imports.

New code should import models from remembering_lancers.models.
"""

from remembering_lancers.extensions import db
from remembering_lancers.models import DistinctObituary, Obituary

__all__ = ["db", "Obituary", "DistinctObituary"]