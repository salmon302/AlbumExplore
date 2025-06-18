"""
Tag validation system to catch edge cases and ensure data quality during import.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from albumexplore.gui.gui_logging import db_logger

class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Block import
    WARNING = "warning"  # Log but continue
    INFO = "info"       # Informational only

@dataclass
class ValidationResult:
    """Result of tag validation."""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    suggested_fix: Optional[str] = None
    category: Optional[str] = None

class TagValidator:
    """Comprehensive tag validation system."""
    
    # Configuration constants
    MAX_TAG_LENGTH = 100
    MIN_TAG_LENGTH = 1
    MAX_TAGS_PER_ALBUM = 20
    
    # Problematic patterns
    INVALID_PATTERNS = [
        r'^[\s\-_]+$',          # Only whitespace, hyphens, underscores
        r'^\d+$',               # Only numbers
        r'^[^\w\s\-]+$',        # Only special characters (except hyphens)
        r'.*\b(fuck|shit|damn)\b.*',  # Profanity (basic check)
    ]
    
    # Format strings that should not be tags
    FORMAT_STRINGS = {
        'lp', 'ep', 'single', 'album', 'cd', 'vinyl', 'digital', 'cassette',
        '2xlp', '3xlp', '4xlp', '2xcd', '3xcd', 'double album', 'triple album'
    }
    
    # Date-like strings that shouldn't be tags
    DATE_PATTERNS = [
        r'^\d{4}$',                    # Just year
        r'^\d{1,2}/\d{1,2}/\d{4}$',    # MM/DD/YYYY
        r'^\d{4}-\d{2}-\d{2}$',        # YYYY-MM-DD
        r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}$',  # Month Day
    ]
    
    # Common non-genre terms that often get misclassified as tags
    NON_GENRE_TERMS = {
        'album', 'ep', 'single', 'lp', 'cd', 'vinyl', 'digital', 'release',
        'new', 'old', 'classic', 'modern', 'contemporary', 'traditional',
        'good', 'bad', 'excellent', 'amazing', 'terrible', 'awesome',
        'music', 'song', 'track', 'sound', 'audio', 'band', 'artist',
        'male', 'female', 'vocals', 'instrumental', 'acoustic', 'electric',
        '2023', '2024', '2025', '2026', '2027', '2028', '2029', '2030'
    }
    
    # Suspicious short tags that might be typos or abbreviations
    SUSPICIOUS_SHORT_TAGS = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'is', 'was', 'are', 'were',
        'be', 'been', 'have', 'has', 'had', 'do', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'must', 'shall', 'to', 'of', 'in', 'on',
        'at', 'by', 'for', 'with', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'among', 'against', 'x', 'y', 'z'
    }
    
    def __init__(self):
        self.validation_stats = {
            'total_validated': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'fixed': 0
        }
        
    def validate_tag(self, tag: str, context: Optional[Dict] = None) -> List[ValidationResult]:
        """
        Validate a single tag and return list of validation results.
        
        Args:
            tag: The tag to validate
            context: Optional context information (album, artist, etc.)
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        self.validation_stats['total_validated'] += 1
        
        if not tag:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Empty tag",
                category="empty"
            ))
            return results
        
        # Clean tag for validation
        clean_tag = tag.strip()
        
        # Check basic constraints
        results.extend(self._validate_basic_constraints(clean_tag))
        
        # Check for problematic patterns
        results.extend(self._validate_patterns(clean_tag))
        
        # Check for format strings
        results.extend(self._validate_format_strings(clean_tag))
        
        # Check for date-like patterns
        results.extend(self._validate_date_patterns(clean_tag))
        
        # Check for non-genre terms
        results.extend(self._validate_genre_relevance(clean_tag))
        
        # Check for suspicious short tags
        results.extend(self._validate_suspicious_short_tags(clean_tag))
        
        # Check encoding and character issues
        results.extend(self._validate_encoding(clean_tag))
        
        # Update statistics
        for result in results:
            if result.severity == ValidationSeverity.ERROR:
                self.validation_stats['errors'] += 1
            elif result.severity == ValidationSeverity.WARNING:
                self.validation_stats['warnings'] += 1
            else:
                self.validation_stats['info'] += 1
        
        return results
    
    def validate_tag_list(self, tags: List[str], context: Optional[Dict] = None) -> Dict:
        """
        Validate a list of tags and return comprehensive results.
        
        Args:
            tags: List of tags to validate
            context: Optional context information
            
        Returns:
            Dictionary with validation results and statistics
        """
        all_results = []
        valid_tags = []
        invalid_tags = []
        warnings = []
        
        # Check list-level constraints
        if len(tags) > self.MAX_TAGS_PER_ALBUM:
            all_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Too many tags ({len(tags)}), maximum recommended: {self.MAX_TAGS_PER_ALBUM}",
                category="list_size"
            ))
        
        # Validate each tag
        for tag in tags:
            tag_results = self.validate_tag(tag, context)
            all_results.extend(tag_results)
            
            # Categorize tag based on validation results
            has_errors = any(r.severity == ValidationSeverity.ERROR for r in tag_results)
            has_warnings = any(r.severity == ValidationSeverity.WARNING for r in tag_results)
            
            if has_errors:
                invalid_tags.append(tag)
            elif has_warnings:
                warnings.append(tag)
            else:
                valid_tags.append(tag)
        
        # Check for duplicates
        seen_tags = set()
        duplicates = []
        for tag in tags:
            if tag.lower() in seen_tags:
                duplicates.append(tag)
            else:
                seen_tags.add(tag.lower())
        
        if duplicates:
            all_results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Duplicate tags found: {', '.join(duplicates)}",
                category="duplicates"
            ))
        
        return {
            'results': all_results,
            'valid_tags': valid_tags,
            'invalid_tags': invalid_tags,
            'warning_tags': warnings,
            'duplicates': duplicates,
            'summary': {
                'total_tags': len(tags),
                'valid_count': len(valid_tags),
                'invalid_count': len(invalid_tags),
                'warning_count': len(warnings),
                'duplicate_count': len(duplicates)
            }
        }
    
    def _validate_basic_constraints(self, tag: str) -> List[ValidationResult]:
        """Validate basic constraints like length."""
        results = []
        
        if len(tag) < self.MIN_TAG_LENGTH:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Tag too short (minimum {self.MIN_TAG_LENGTH} characters)",
                category="length"
            ))
        elif len(tag) > self.MAX_TAG_LENGTH:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Tag very long ({len(tag)} characters, maximum recommended {self.MAX_TAG_LENGTH})",
                suggested_fix=tag[:self.MAX_TAG_LENGTH] + "...",
                category="length"
            ))
        
        return results
    
    def _validate_patterns(self, tag: str) -> List[ValidationResult]:
        """Validate against problematic patterns."""
        results = []
        
        for pattern in self.INVALID_PATTERNS:
            if re.match(pattern, tag, re.IGNORECASE):
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Tag matches invalid pattern: {pattern}",
                    category="pattern"
                ))
        
        return results
    
    def _validate_format_strings(self, tag: str) -> List[ValidationResult]:
        """Check if tag is a format string rather than a genre."""
        results = []
        
        if tag.lower() in self.FORMAT_STRINGS:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="Tag appears to be a format descriptor rather than a genre",
                category="format"
            ))
        
        return results
    
    def _validate_date_patterns(self, tag: str) -> List[ValidationResult]:
        """Check if tag looks like a date."""
        results = []
        
        for pattern in self.DATE_PATTERNS:
            if re.match(pattern, tag):
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message="Tag appears to be a date rather than a genre",
                    category="date"
                ))
                break
        
        return results
    
    def _validate_genre_relevance(self, tag: str) -> List[ValidationResult]:
        """Check if tag is relevant to music genres."""
        results = []
        
        if tag.lower() in self.NON_GENRE_TERMS:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="Tag appears to be a general music term rather than a specific genre",
                category="relevance"
            ))
        
        return results
    
    def _validate_suspicious_short_tags(self, tag: str) -> List[ValidationResult]:
        """Check for suspicious short tags that might be typos."""
        results = []
        
        if len(tag) <= 3 and tag.lower() in self.SUSPICIOUS_SHORT_TAGS:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.INFO,
                message="Very short tag that might be a common word rather than a genre",
                category="suspicious"
            ))
        
        return results
    
    def _validate_encoding(self, tag: str) -> List[ValidationResult]:
        """Check for encoding and character issues."""
        results = []
        
        # Check for non-printable characters
        if any(ord(c) < 32 or ord(c) > 126 for c in tag if c not in 'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'):
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="Tag contains unusual characters that might cause encoding issues",
                category="encoding"
            ))
        
        # Check for multiple consecutive spaces
        if '  ' in tag:
            suggested_fix = re.sub(r'\s+', ' ', tag).strip()
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.INFO,
                message="Tag contains multiple consecutive spaces",
                suggested_fix=suggested_fix,
                category="spacing"
            ))
        
        # Check for leading/trailing special characters
        if tag.startswith(('-', '_', '.', ',')) or tag.endswith(('-', '_', '.', ',')):
            suggested_fix = tag.strip('-_.,')
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.INFO,
                message="Tag has leading or trailing special characters",
                suggested_fix=suggested_fix,
                category="formatting"
            ))
        
        return results
    
    def get_validation_statistics(self) -> Dict:
        """Get current validation statistics."""
        return self.validation_stats.copy()
    
    def reset_statistics(self):
        """Reset validation statistics."""
        self.validation_stats = {
            'total_validated': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'fixed': 0
        }


class TagValidationFilter:
    """Filter for automatically handling validation results."""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validator = TagValidator()
    
    def filter_tags(self, tags: List[str], context: Optional[Dict] = None) -> Tuple[List[str], List[str], Dict]:
        """
        Filter tags based on validation results.
        
        Args:
            tags: List of tags to filter
            context: Optional context information
            strict_mode: If True, remove tags with warnings as well as errors
            
        Returns:
            Tuple of (valid_tags, rejected_tags, validation_info)
        """
        validation_result = self.validator.validate_tag_list(tags, context)
        
        valid_tags = []
        rejected_tags = []
        
        for tag in tags:
            tag_results = self.validator.validate_tag(tag, context)
            
            # Determine if tag should be rejected
            should_reject = False
            
            for result in tag_results:
                if result.severity == ValidationSeverity.ERROR:
                    should_reject = True
                    break
                elif self.strict_mode and result.severity == ValidationSeverity.WARNING:
                    should_reject = True
                    break
            
            if should_reject:
                rejected_tags.append(tag)
            else:
                # Apply suggested fixes if available
                fixed_tag = tag
                for result in tag_results:
                    if result.suggested_fix:
                        fixed_tag = result.suggested_fix
                        self.validator.validation_stats['fixed'] += 1
                        break
                valid_tags.append(fixed_tag)
        
        return valid_tags, rejected_tags, validation_result 