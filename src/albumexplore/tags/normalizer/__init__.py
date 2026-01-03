"""Tag normalization package."""
from .enhanced_normalizer import EnhancedTagNormalizer as TagNormalizer
from .tag_normalizer import TagNormalizer as BaseTagNormalizer

__all__ = ['TagNormalizer', 'BaseTagNormalizer']