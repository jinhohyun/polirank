"""
Rank Core Platform Engine
-------------------------
A modular, configuration-driven white-label ranking platform core for Polirank, Krank, and future domain-specific ranking products.
"""

__version__ = "1.0.0"

from .config import PlatformConfig, ScoringWeightConfig
from .scoring import BaseScoringEngine, WeightedScoringEngine
from .database import BaseDatabaseManager
from .factory import create_ranking_app
from .i18n import I18nManager

__all__ = [
    "PlatformConfig",
    "ScoringWeightConfig",
    "BaseScoringEngine",
    "WeightedScoringEngine",
    "BaseDatabaseManager",
    "create_ranking_app",
    "I18nManager",
]
