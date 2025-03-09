"""Tag management and analysis system."""
from .normalizer import TagNormalizer
from .config import TagRulesConfig
from .analysis import TagAnalyzer, TagSimilarity, SingleInstanceHandler
from .relationships import TagRelationships

__all__ = [
    'TagNormalizer',
    'TagRulesConfig',
    'TagAnalyzer',
    'TagSimilarity',
    'SingleInstanceHandler',
    'TagRelationships'
]