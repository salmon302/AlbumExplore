import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

class ConsolidationMode(Enum):
    """Consolidation operation modes."""
    CONSERVATIVE = "conservative"  # Only high-confidence merges
    BALANCED = "balanced"         # Medium confidence threshold
    AGGRESSIVE = "aggressive"     # Lower confidence threshold
    MANUAL = "manual"            # User approves all merges

class ViewPreference(Enum):
    """UI view preferences."""
    STANDARD = "standard"
    CATEGORY = "category"
    HIERARCHY = "hierarchy"

@dataclass
class ConsolidationSettings:
    """Settings for tag consolidation behavior."""
    mode: ConsolidationMode = ConsolidationMode.BALANCED
    confidence_threshold: float = 0.8
    auto_apply_location_filter: bool = True
    auto_apply_high_confidence: bool = False
    batch_size: int = 100
    preserve_original_tags: bool = True

@dataclass  
class UISettings:
    """Settings for UI behavior and appearance."""
    default_view: ViewPreference = ViewPreference.STANDARD
    show_category_colors: bool = True
    auto_expand_hierarchy: bool = True
    max_suggestions: int = 10
    show_consolidation_preview: bool = True
    enable_real_time_validation: bool = True

@dataclass
class PerformanceSettings:
    """Settings for performance optimization."""
    cache_analysis_results: bool = True
    background_processing: bool = True
    max_cache_size: int = 1000
    analysis_timeout: int = 30
    enable_progress_indicators: bool = True

@dataclass
class FilterSettings:
    """Settings for tag filtering and exclusion."""
    filter_location_tags: bool = True
    filter_single_instance_tags: bool = False
    min_tag_frequency: int = 1
    excluded_patterns: List[str] = None
    included_patterns: List[str] = None
    
    def __post_init__(self):
        if self.excluded_patterns is None:
            self.excluded_patterns = []
        if self.included_patterns is None:
            self.included_patterns = []

@dataclass
class EnhancedTagConfig:
    """Complete configuration for enhanced tag system."""
    consolidation: ConsolidationSettings = None
    ui: UISettings = None
    performance: PerformanceSettings = None
    filters: FilterSettings = None
    version: str = "1.0.0"
    
    def __post_init__(self):
        if self.consolidation is None:
            self.consolidation = ConsolidationSettings()
        if self.ui is None:
            self.ui = UISettings()
        if self.performance is None:
            self.performance = PerformanceSettings()
        if self.filters is None:
            self.filters = FilterSettings()

class ConfigManager:
    """Manager for enhanced tag configuration."""
    
    DEFAULT_CONFIG_FILE = "enhanced_tag_config.json"
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Default to user's home directory
            self.config_dir = Path.home() / ".albumexplore"
        
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE
        
        self._config = None
        self._callbacks = []  # Configuration change callbacks
        
    def load_config(self) -> EnhancedTagConfig:
        """Load configuration from file or create default."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Convert back to dataclass
                config = self._dict_to_config(data)
                self._config = config
                return config
            else:
                # Create default configuration
                config = EnhancedTagConfig()
                self.save_config(config)
                self._config = config
                return config
                
        except Exception as e:
            print(f"Error loading config: {e}")
            # Return default configuration on error
            config = EnhancedTagConfig()
            self._config = config
            return config
    
    def save_config(self, config: EnhancedTagConfig) -> bool:
        """Save configuration to file."""
        try:
            data = self._config_to_dict(config)
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self._config = config
            self._notify_callbacks()
            return True
            
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_config(self) -> EnhancedTagConfig:
        """Get current configuration."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_consolidation_settings(self, **kwargs) -> bool:
        """Update consolidation settings."""
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config.consolidation, key):
                # Handle enum conversions
                if key == 'mode' and isinstance(value, str):
                    value = ConsolidationMode(value)
                setattr(config.consolidation, key, value)
        
        return self.save_config(config)
    
    def update_ui_settings(self, **kwargs) -> bool:
        """Update UI settings."""
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config.ui, key):
                # Handle enum conversions
                if key == 'default_view' and isinstance(value, str):
                    value = ViewPreference(value)
                setattr(config.ui, key, value)
        
        return self.save_config(config)
    
    def update_performance_settings(self, **kwargs) -> bool:
        """Update performance settings."""
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config.performance, key):
                setattr(config.performance, key, value)
        
        return self.save_config(config)
    
    def update_filter_settings(self, **kwargs) -> bool:
        """Update filter settings."""
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config.filters, key):
                setattr(config.filters, key, value)
        
        return self.save_config(config)
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults."""
        config = EnhancedTagConfig()
        return self.save_config(config)
    
    def export_config(self, file_path: str) -> bool:
        """Export configuration to specified file."""
        try:
            config = self.get_config()
            data = self._config_to_dict(config)
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """Import configuration from specified file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            config = self._dict_to_config(data)
            return self.save_config(config)
            
        except Exception as e:
            print(f"Error importing config: {e}")
            return False
    
    def add_change_callback(self, callback):
        """Add callback for configuration changes."""
        self._callbacks.append(callback)
    
    def remove_change_callback(self, callback):
        """Remove callback for configuration changes."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notify all callbacks of configuration changes."""
        for callback in self._callbacks:
            try:
                callback(self._config)
            except Exception as e:
                print(f"Error in config callback: {e}")
    
    def _config_to_dict(self, config: EnhancedTagConfig) -> Dict[str, Any]:
        """Convert configuration to dictionary for JSON serialization."""
        data = asdict(config)
        
        # Convert enums to strings
        if 'consolidation' in data and 'mode' in data['consolidation']:
            data['consolidation']['mode'] = data['consolidation']['mode'].value
        
        if 'ui' in data and 'default_view' in data['ui']:
            data['ui']['default_view'] = data['ui']['default_view'].value
        
        return data
    
    def _dict_to_config(self, data: Dict[str, Any]) -> EnhancedTagConfig:
        """Convert dictionary to configuration object."""
        # Convert enum strings back to enums
        if 'consolidation' in data and 'mode' in data['consolidation']:
            mode_str = data['consolidation']['mode']
            data['consolidation']['mode'] = ConsolidationMode(mode_str)
        
        if 'ui' in data and 'default_view' in data['ui']:
            view_str = data['ui']['default_view']
            data['ui']['default_view'] = ViewPreference(view_str)
        
        # Create dataclass instances
        consolidation = ConsolidationSettings(**data.get('consolidation', {}))
        ui = UISettings(**data.get('ui', {}))
        performance = PerformanceSettings(**data.get('performance', {}))
        filters = FilterSettings(**data.get('filters', {}))
        
        return EnhancedTagConfig(
            consolidation=consolidation,
            ui=ui,
            performance=performance,
            filters=filters,
            version=data.get('version', '1.0.0')
        )


class ConfigurationValidator:
    """Validator for configuration settings."""
    
    @staticmethod
    def validate_config(config: EnhancedTagConfig) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate consolidation settings
        if config.consolidation.confidence_threshold < 0 or config.consolidation.confidence_threshold > 1:
            errors.append("Confidence threshold must be between 0 and 1")
        
        if config.consolidation.batch_size < 1:
            errors.append("Batch size must be at least 1")
        
        # Validate UI settings
        if config.ui.max_suggestions < 1:
            errors.append("Max suggestions must be at least 1")
        
        # Validate performance settings
        if config.performance.max_cache_size < 0:
            errors.append("Max cache size cannot be negative")
        
        if config.performance.analysis_timeout < 1:
            errors.append("Analysis timeout must be at least 1 second")
        
        # Validate filter settings
        if config.filters.min_tag_frequency < 1:
            errors.append("Minimum tag frequency must be at least 1")
        
        return errors
    
    @staticmethod
    def validate_and_fix_config(config: EnhancedTagConfig) -> EnhancedTagConfig:
        """Validate and automatically fix configuration issues."""
        # Fix consolidation settings
        config.consolidation.confidence_threshold = max(0, min(1, config.consolidation.confidence_threshold))
        config.consolidation.batch_size = max(1, config.consolidation.batch_size)
        
        # Fix UI settings
        config.ui.max_suggestions = max(1, config.ui.max_suggestions)
        
        # Fix performance settings
        config.performance.max_cache_size = max(0, config.performance.max_cache_size)
        config.performance.analysis_timeout = max(1, config.performance.analysis_timeout)
        
        # Fix filter settings
        config.filters.min_tag_frequency = max(1, config.filters.min_tag_frequency)
        
        return config


# Global configuration instance
_global_config_manager = None

def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance."""
    global _global_config_manager
    
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_dir)
    
    return _global_config_manager

def get_config() -> EnhancedTagConfig:
    """Get current configuration."""
    return get_config_manager().get_config()

def save_config(config: EnhancedTagConfig) -> bool:
    """Save configuration."""
    return get_config_manager().save_config(config)

def reset_config() -> bool:
    """Reset configuration to defaults."""
    return get_config_manager().reset_to_defaults()


# Configuration presets
class ConfigPresets:
    """Predefined configuration presets."""
    
    @staticmethod
    def conservative() -> EnhancedTagConfig:
        """Conservative preset - minimal automatic changes."""
        config = EnhancedTagConfig()
        config.consolidation.mode = ConsolidationMode.CONSERVATIVE
        config.consolidation.confidence_threshold = 0.95
        config.consolidation.auto_apply_high_confidence = False
        config.filters.filter_location_tags = True
        config.filters.filter_single_instance_tags = False
        return config
    
    @staticmethod
    def balanced() -> EnhancedTagConfig:
        """Balanced preset - good balance of automation and control."""
        config = EnhancedTagConfig()
        config.consolidation.mode = ConsolidationMode.BALANCED
        config.consolidation.confidence_threshold = 0.8
        config.consolidation.auto_apply_high_confidence = True
        config.filters.filter_location_tags = True
        config.filters.filter_single_instance_tags = True
        return config
    
    @staticmethod
    def aggressive() -> EnhancedTagConfig:
        """Aggressive preset - maximum automation."""
        config = EnhancedTagConfig()
        config.consolidation.mode = ConsolidationMode.AGGRESSIVE
        config.consolidation.confidence_threshold = 0.6
        config.consolidation.auto_apply_high_confidence = True
        config.filters.filter_location_tags = True
        config.filters.filter_single_instance_tags = True
        config.filters.min_tag_frequency = 2
        return config
    
    @staticmethod
    def manual() -> EnhancedTagConfig:
        """Manual preset - user controls everything."""
        config = EnhancedTagConfig()
        config.consolidation.mode = ConsolidationMode.MANUAL
        config.consolidation.auto_apply_high_confidence = False
        config.consolidation.auto_apply_location_filter = False
        config.ui.show_consolidation_preview = True
        return config 