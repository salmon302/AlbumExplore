"""Similarity bar chart visualization view."""
from typing import Dict, Any, List, Tuple, Optional
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                               QSlider, QPushButton, QWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QMenu, QToolTip, QFileDialog, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent, QPoint
from PyQt6.QtGui import QColor, QAction
from .base_view import BaseView
from .album_header_widget import AlbumHeaderWidget
from albumexplore.visualization.state import ViewType
from albumexplore.database.models import Album
from albumexplore.database.similarity import calculate_album_similarity_optimized
from albumexplore.gui.gui_logging import graphics_logger
from albumexplore.gui.favorites import get_favorites_manager
from PyQt6.QtWidgets import QDialog, QFormLayout, QSpinBox
from albumexplore.similarity import manual as manual_mod
from albumexplore.database.models import Tag
from PyQt6.QtWidgets import QMessageBox, QTextEdit
import os
from .manual_mappings_editor import ManualMappingsEditor
from .manual_suggester_dialog import ManualSuggestionDialog


class SimilarityBarChartView(BaseView):
    """Similarity bar chart visualization view."""
    
    # Signal emitted when user wants to focus on a different album
    album_focus_requested = pyqtSignal(str)  # album_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_type = ViewType.SIMILARITY
        self.current_album_id: Optional[str] = None
        self.current_album: Optional[Album] = None
        self.session = None  # Will be set by main app
        self.similarities: List[Tuple[Album, float, Dict[str, Any]]] = []
        
        # Debounce timer for control updates
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_refresh)
        
        self._setup_ui()
        graphics_logger.debug("Similarity bar chart view initialized")
    
    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Header with selected album info
        self.header_widget = AlbumHeaderWidget()
        layout.addWidget(self.header_widget)
        
        # ===== PRIMARY CONTROLS (always visible) =====
        primary_controls = QWidget()
        primary_layout = QHBoxLayout(primary_controls)
        primary_layout.setContentsMargins(0, 0, 0, 0)
        primary_layout.setSpacing(15)
        
        # Results limit
        primary_layout.addWidget(QLabel("Show top:"))
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(['10', '20', '50', '100'])
        self.limit_combo.setCurrentText('20')
        self.limit_combo.currentTextChanged.connect(self._schedule_refresh)
        self.limit_combo.setMinimumWidth(60)
        primary_layout.addWidget(self.limit_combo)
        
        primary_layout.addSpacing(10)
        
        # Threshold slider
        primary_layout.addWidget(QLabel("Min similarity:"))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(30)
        self.threshold_slider.setMinimumWidth(150)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        primary_layout.addWidget(self.threshold_slider)
        
        self.threshold_label = QLabel("0.30")
        self.threshold_label.setMinimumWidth(40)
        self.threshold_label.setStyleSheet("font-weight: bold;")
        primary_layout.addWidget(self.threshold_label)
        
        primary_layout.addStretch()
        
        # Back button
        self.back_button = QPushButton("← Back")
        self.back_button.setEnabled(False)
        primary_layout.addWidget(self.back_button)
        
        layout.addWidget(primary_controls)
        
        # ===== SMART MATCHING CONTROLS (highlighted) =====
        smart_group = QWidget()
        smart_group.setStyleSheet("""
            QWidget {
                background-color: rgba(70, 130, 180, 0.15);
                border: 1px solid rgba(70, 130, 180, 0.3);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        smart_layout = QHBoxLayout(smart_group)
        smart_layout.setContentsMargins(8, 6, 8, 6)
        smart_layout.setSpacing(20)
        
        smart_label = QLabel("🎯 Smart Matching:")
        smart_label.setStyleSheet("font-weight: bold; background: transparent; border: none; padding: 0;")
        smart_layout.addWidget(smart_label)
        
        # Fuzzy tag matching (prominently displayed)
        self.fuzzy_tags_cb = QCheckBox("Fuzzy tag matching")
        self.fuzzy_tags_cb.setChecked(True)
        self.fuzzy_tags_cb.setToolTip("Match related tags (e.g., 'prog rock' ~ 'progressive rock')\nBased on curated tag relationships")
        self.fuzzy_tags_cb.stateChanged.connect(self._on_fuzzy_toggle)
        self.fuzzy_tags_cb.setStyleSheet("background: transparent; border: none; font-weight: bold;")
        smart_layout.addWidget(self.fuzzy_tags_cb)
        
        # IDF weighting
        self.idf_weights_cb = QCheckBox("Prioritize rare tags")
        self.idf_weights_cb.setChecked(False)
        self.idf_weights_cb.setToolTip("Give more importance to rare/specific tags\n(e.g., 'canterbury scene' > 'rock')")
        self.idf_weights_cb.stateChanged.connect(self._on_idf_toggle)
        self.idf_weights_cb.setStyleSheet("background: transparent; border: none;")
        smart_layout.addWidget(self.idf_weights_cb)
        
        smart_layout.addStretch()
        
        # Advanced settings button (collapsible section)
        self.advanced_btn = QPushButton("⚙ Advanced Settings")
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setChecked(False)
        self.advanced_btn.clicked.connect(self._toggle_advanced)
        self.advanced_btn.setStyleSheet("background: transparent; border: none;")
        smart_layout.addWidget(self.advanced_btn)
        
        layout.addWidget(smart_group)
        
        # ===== ADVANCED SETTINGS (collapsible) =====
        self.advanced_widget = QWidget()
        self.advanced_widget.setVisible(False)  # Hidden by default
        advanced_main_layout = QVBoxLayout(self.advanced_widget)
        advanced_main_layout.setContentsMargins(0, 0, 0, 0)
        advanced_main_layout.setSpacing(8)
        
        # Component Weights section
        weights_group = QWidget()
        weights_group.setStyleSheet("""
            QWidget {
                background-color: rgba(50, 50, 50, 0.3);
                border: 1px solid rgba(100, 100, 100, 0.3);
                border-radius: 4px;
            }
        """)
        weights_main_layout = QVBoxLayout(weights_group)
        weights_main_layout.setContentsMargins(10, 8, 10, 8)
        weights_main_layout.setSpacing(6)
        
        weights_title = QLabel("Component Weights")
        weights_title.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        weights_main_layout.addWidget(weights_title)
        
        weights_layout = QHBoxLayout()
        weights_layout.setSpacing(15)
        
        # Tags weight
        tags_group = QVBoxLayout()
        tags_label = QLabel("Tags")
        tags_label.setStyleSheet("background: transparent; border: none;")
        tags_group.addWidget(tags_label)
        self.tags_slider = QSlider(Qt.Orientation.Horizontal)
        self.tags_slider.setRange(0, 100)
        self.tags_slider.setValue(70)
        self.tags_slider.setMinimumWidth(100)
        self.tags_slider.valueChanged.connect(self._on_weights_changed)
        tags_group.addWidget(self.tags_slider)
        self.tags_label = QLabel("70")
        self.tags_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tags_label.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        tags_group.addWidget(self.tags_label)
        weights_layout.addLayout(tags_group)
        
        # Vocals weight
        vocals_group = QVBoxLayout()
        vocals_label = QLabel("Vocals")
        vocals_label.setStyleSheet("background: transparent; border: none;")
        vocals_group.addWidget(vocals_label)
        self.vocals_slider = QSlider(Qt.Orientation.Horizontal)
        self.vocals_slider.setRange(0, 100)
        self.vocals_slider.setValue(0)
        self.vocals_slider.setMinimumWidth(100)
        self.vocals_slider.valueChanged.connect(self._on_weights_changed)
        vocals_group.addWidget(self.vocals_slider)
        self.vocals_label = QLabel("0")
        self.vocals_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vocals_label.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        vocals_group.addWidget(self.vocals_label)
        weights_layout.addLayout(vocals_group)
        
        # Location weight
        location_group = QVBoxLayout()
        location_label = QLabel("Location")
        location_label.setStyleSheet("background: transparent; border: none;")
        location_group.addWidget(location_label)
        self.location_slider = QSlider(Qt.Orientation.Horizontal)
        self.location_slider.setRange(0, 100)
        self.location_slider.setValue(5)
        self.location_slider.setMinimumWidth(100)
        self.location_slider.valueChanged.connect(self._on_weights_changed)
        location_group.addWidget(self.location_slider)
        self.location_label = QLabel("5")
        self.location_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.location_label.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        location_group.addWidget(self.location_label)
        weights_layout.addLayout(location_group)
        
        weights_layout.addStretch()
        
        # Weight control buttons
        self.reset_weights_btn = QPushButton("Reset")
        self.reset_weights_btn.clicked.connect(self._reset_weights)
        self.reset_weights_btn.setStyleSheet("background: transparent; border: 1px solid #666; padding: 4px 8px;")
        weights_layout.addWidget(self.reset_weights_btn)
        
        self.per_tag_btn = QPushButton("Per-tag...")
        self.per_tag_btn.clicked.connect(self._open_per_tag_dialog)
        self.per_tag_btn.setStyleSheet("background: transparent; border: 1px solid #666; padding: 4px 8px;")
        weights_layout.addWidget(self.per_tag_btn)
        
        self.reset_per_tag_btn = QPushButton("Reset Per-tag")
        self.reset_per_tag_btn.clicked.connect(self._reset_per_tag_weights)
        self.reset_per_tag_btn.setStyleSheet("background: transparent; border: 1px solid #666; padding: 4px 8px;")
        weights_layout.addWidget(self.reset_per_tag_btn)
        
        weights_main_layout.addLayout(weights_layout)
        advanced_main_layout.addWidget(weights_group)
        
        # Developer Tools section (for manual mappings)
        dev_group = QWidget()
        dev_group.setStyleSheet("""
            QWidget {
                background-color: rgba(50, 50, 50, 0.3);
                border: 1px solid rgba(100, 100, 100, 0.3);
                border-radius: 4px;
            }
        """)
        dev_layout = QVBoxLayout(dev_group)
        dev_layout.setContentsMargins(10, 8, 10, 8)
        dev_layout.setSpacing(6)
        
        dev_title = QLabel("Developer Tools (Tag Relationships)")
        dev_title.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        dev_layout.addWidget(dev_title)
        
        dev_controls = QHBoxLayout()
        dev_controls.setSpacing(8)
        
        # Manual mapping toggle
        self.manual_enable_cb = QCheckBox("Override with custom mappings")
        self.manual_enable_cb.setChecked(False)
        self.manual_enable_cb.setToolTip("Replace default relationships with custom file")
        self.manual_enable_cb.stateChanged.connect(self._on_manual_toggle)
        self.manual_enable_cb.setStyleSheet("background: transparent; border: none;")
        dev_controls.addWidget(self.manual_enable_cb)
        
        # Status indicator showing relationship count
        self.manual_status_label = QLabel("(0 relationships)")
        self.manual_status_label.setStyleSheet("background: transparent; border: none; color: #888; font-size: 10px;")
        dev_controls.addWidget(self.manual_status_label)
        
        self.manual_slider = QSlider(Qt.Orientation.Horizontal)
        self.manual_slider.setRange(0, 100)
        self.manual_slider.setValue(50)
        self.manual_slider.setMinimumWidth(100)
        self.manual_slider.setMaximumWidth(120)
        self.manual_slider.valueChanged.connect(self._on_manual_weight_changed)
        self.manual_slider.setEnabled(False)
        dev_controls.addWidget(self.manual_slider)
        
        self.manual_label = QLabel("0.50")
        self.manual_label.setMinimumWidth(35)
        self.manual_label.setStyleSheet("background: transparent; border: none;")
        dev_controls.addWidget(self.manual_label)
        
        dev_controls.addStretch()
        
        self.load_manual_btn = QPushButton("Load File...")
        self.load_manual_btn.clicked.connect(self._load_manual_file)
        self.load_manual_btn.setStyleSheet("background: transparent; border: 1px solid #666; padding: 4px 8px;")
        self.load_manual_btn.setEnabled(False)
        dev_controls.addWidget(self.load_manual_btn)
        
        self.validate_manual_btn = QPushButton("Validate")
        self.validate_manual_btn.clicked.connect(self._validate_manual_mappings)
        self.validate_manual_btn.setStyleSheet("background: transparent; border: 1px solid #666; padding: 4px 8px;")
        dev_controls.addWidget(self.validate_manual_btn)
        
        self.edit_manual_btn = QPushButton("Edit...")
        self.edit_manual_btn.clicked.connect(self._edit_manual_mappings)
        self.edit_manual_btn.setStyleSheet("background: transparent; border: 1px solid #666; padding: 4px 8px;")
        dev_controls.addWidget(self.edit_manual_btn)
        
        self.suggest_manual_btn = QPushButton("Discover...")
        self.suggest_manual_btn.clicked.connect(self._open_suggester)
        self.suggest_manual_btn.setStyleSheet("background: transparent; border: 1px solid #666; padding: 4px 8px;")
        self.suggest_manual_btn.setToolTip("Auto-discover potential relationships from database")
        dev_controls.addWidget(self.suggest_manual_btn)
        
        dev_layout.addLayout(dev_controls)
        advanced_main_layout.addWidget(dev_group)
        
        layout.addWidget(self.advanced_widget)
        
        # Results count label
        self.results_label = QLabel("Select an album to see similar albums")
        self.results_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.results_label)
        
        # Table widget for displaying results (using table instead of pure bar chart for simplicity)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Album', 'Similarity', 'Score'])
        
        # Configure table
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        
        # Configure column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 80)
        # Enable mouse tracking so hover tooltips appear reliably
        self.table.setMouseTracking(True)

        # Apply a dark tooltip style so the hover popup matches the app theme
        try:
            QToolTip.setFont(self.font())
            QToolTip.setStyleSheet("QToolTip { background-color: #222; color: #ddd; border: 1px solid #555; padding: 6px; }")
        except Exception:
            # If styling fails, continue without crashing
            pass
        
        # Connect signals
        self.table.itemDoubleClicked.connect(self._on_album_double_clicked)
        # Context menu for favorite toggling
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # Favorites manager
        self._fav_mgr = get_favorites_manager()
        self._fav_mgr.favorites_changed.connect(self._on_favorites_changed)
        
        # Create a custom hover popup (uses ToolTip window type for consistent stacking)
        self._hover_popup = QLabel("", None)
        try:
            self._hover_popup.setWindowFlags(Qt.WindowType.ToolTip)
        except Exception:
            # Fall back if WindowType.ToolTip not available
            self._hover_popup.setWindowFlags(Qt.WindowType.Window)
        self._hover_popup.setTextFormat(Qt.TextFormat.RichText)
        self._hover_popup.setWordWrap(True)
        self._hover_popup.setStyleSheet("background-color: #222; color: #ddd; border: 1px solid #555; padding: 6px;")
        self._hover_popup.setVisible(False)
        self._hover_row = None

        # Install event filter on the table viewport to show a custom popup on hover
        self.table.viewport().installEventFilter(self)

        layout.addWidget(self.table)
        
    def set_session(self, session):
        """Set the database session."""
        self.session = session
        # per-tag weights are keyed by tag id -> multiplier (float, 1.0 = default)
        self.per_tag_weights = {}
        # IDF weights for rare tag prioritization
        self.idf_weights = {}
        # Manual relationships (loaded from file) - normalized by loader to lower-case keys
        self.manual_relationships = None
        
        # Try to load default comprehensive relationships
        try:
            from albumexplore.database.tag_relationship_similarity import load_default_relationships
            self.manual_relationships = load_default_relationships()
            if self.manual_relationships:
                graphics_logger.info(f"Loaded {len(self.manual_relationships)} tag relationships")
                # Update UI status
                self._update_manual_status()
        except Exception as e:
            graphics_logger.warning(f"Could not load default relationships: {e}")
    
    def set_album(self, album_id: str):
        """Set the focus album and refresh similarity data."""
        if not self.session:
            graphics_logger.error("Session not set for similarity view")
            return
        
        self.current_album_id = album_id
        
        # Load album details
        from sqlalchemy.orm import joinedload
        self.current_album = self.session.query(Album).options(
            joinedload(Album.tags)
        ).filter(Album.id == album_id).first()
        
        if not self.current_album:
            graphics_logger.warning(f"Album {album_id} not found")
            return
        
        # Update header
        self.header_widget.set_album(self.current_album)
        
        # Refresh data
        self._schedule_refresh()
        
        graphics_logger.info(f"Similarity view focused on: {self.current_album.pa_artist_name_on_album} - {self.current_album.title}")
    
    def _schedule_refresh(self):
        """Schedule a refresh with debouncing."""
        self._update_timer.stop()
        self._update_timer.start(300)  # 300ms debounce
    
    def _on_threshold_changed(self):
        """Handle threshold slider changes."""
        threshold = self.threshold_slider.value() / 100.0
        self.threshold_label.setText(f"{threshold:.2f}")
        self._schedule_refresh()

    def _on_weights_changed(self):
        """Handle weight slider changes and schedule refresh."""
        try:
            self.tags_label.setText(str(self.tags_slider.value()))
            self.vocals_label.setText(str(self.vocals_slider.value()))
            self.location_label.setText(str(self.location_slider.value()))
        except Exception:
            graphics_logger.exception("Error updating weight labels")
        self._schedule_refresh()

    def _reset_weights(self):
        """Reset weight sliders to defaults."""
        self.tags_slider.setValue(70)
        self.vocals_slider.setValue(0)
        self.location_slider.setValue(5)
        self._on_weights_changed()

    def _reset_per_tag_weights(self):
        """Clear any per-tag overrides."""
        self.per_tag_weights = {}
        graphics_logger.info("Per-tag weights reset to defaults")
        self._schedule_refresh()


    def _on_manual_toggle(self):
        """Handle enabling/disabling manual mappings and schedule refresh."""
        try:
            enabled = self.manual_enable_cb.isChecked()
            self.manual_slider.setEnabled(enabled)
            self.load_manual_btn.setEnabled(enabled)
            
            # Update status label
            self._update_manual_status()
            
            graphics_logger.info(f"Manual mappings enabled: {enabled}")
        except Exception:
            graphics_logger.exception("Error toggling manual mappings")
        self._schedule_refresh()
    
    
    def _toggle_advanced(self):
        """Toggle visibility of advanced settings panel."""
        try:
            is_visible = self.advanced_widget.isVisible()
            self.advanced_widget.setVisible(not is_visible)
            # Update button text to show state
            if is_visible:
                self.advanced_btn.setText("Advanced Settings ▼")
            else:
                self.advanced_btn.setText("Advanced Settings ▲")
        except Exception:
            graphics_logger.exception("Error toggling advanced settings")
    
    
    def _update_manual_status(self):
        """Update the manual relationships status indicator."""
        try:
            if not hasattr(self, 'manual_status_label'):
                return
            
            # Count relationships
            count = 0
            if self.manual_relationships:
                for tag_rels in self.manual_relationships.values():
                    count += len(tag_rels)
            
            # Update label text and color
            if count > 0:
                self.manual_status_label.setText(f"({count} relationships loaded)")
                if self.manual_enable_cb.isChecked():
                    self.manual_status_label.setStyleSheet("background: transparent; border: none; color: #4CAF50; font-size: 10px; font-weight: bold;")
                else:
                    self.manual_status_label.setStyleSheet("background: transparent; border: none; color: #888; font-size: 10px;")
            else:
                self.manual_status_label.setText("(no relationships)")
                self.manual_status_label.setStyleSheet("background: transparent; border: none; color: #888; font-size: 10px;")
        except Exception:
            graphics_logger.exception("Error updating manual status")


    def _on_manual_weight_changed(self):
        try:
            val = self.manual_slider.value() / 100.0
            self.manual_label.setText(f"{val:.2f}")
        except Exception:
            graphics_logger.exception("Error updating manual weight label")
        self._schedule_refresh()


    def _load_manual_file(self):
        """Open a file dialog and load manual mapping file (CSV/JSON/YAML)."""
        try:
            fn, _ = QFileDialog.getOpenFileName(self, "Load manual mappings", ".", "All Files (*.*);;CSV Files (*.csv);;JSON Files (*.json);;YAML Files (*.yml *.yaml)")
            if not fn:
                return
            rels = manual_mod.load_relationships(fn)
            # Store loaded relationships (they are normalized to lower-case by loader)
            self.manual_relationships = rels
            self._update_manual_status()
            graphics_logger.info(f"Loaded manual mappings from {fn} (entries: {len(rels)})")
        except Exception as e:
            graphics_logger.error(f"Failed loading manual mappings: {e}", exc_info=True)
        self._schedule_refresh()


    def _validate_manual_mappings(self):
        """Validate currently loaded manual mappings against the DB tag index and show warnings."""
        if not self.session:
            QMessageBox.information(self, "Validation", "Database session not available for validation.")
            return

        # Ensure we have mappings (try default file if none loaded)
        rels = self.manual_relationships
        if rels is None:
            default_path = "data/tag_relationships.yml"
            try:
                rels = manual_mod.load_relationships(default_path)
                self.manual_relationships = rels
                graphics_logger.info(f"Loaded default manual mappings from {default_path}")
            except Exception:
                QMessageBox.information(self, "Validation", "No manual mappings loaded and default file not found.")
                return

        # Build tag index and freqs from DB
        try:
            tags = self.session.query(Tag).all()
            tag_index = {t.name.strip().lower(): t.id for t in tags if t.name}
            tag_freqs = {t.name.strip().lower(): int(t.frequency or 0) for t in tags if t.name}
        except Exception as e:
            graphics_logger.exception("Error querying tags for validation")
            QMessageBox.critical(self, "Validation Error", f"Error querying tag database: {e}")
            return

        cleaned, warnings = manual_mod.validate_relationships(rels, tag_index, tag_freqs, min_count=5)

        if not warnings:
            QMessageBox.information(self, "Validation", "Manual mappings validated successfully (no issues found).")
            return

        # Show warnings in a dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Manual mappings validation warnings")
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(warnings))
        layout.addWidget(text)
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.resize(600, 400)
        dlg.exec()

    def _open_per_tag_dialog(self):
        """Open a dialog allowing the user to adjust weights for individual tags on the current album."""
        if not self.current_album:
            graphics_logger.info("No album selected for per-tag weighting")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Per-tag weight adjustments")
        layout = QFormLayout(dialog)

        # We'll present top composite tags from the current album
        tag_spinboxes = {}
        for tag in getattr(self.current_album, 'tags', []):
            # current multiplier default 100 -> represents 1.0
            cur = int(self.per_tag_weights.get(tag.id, 1.0) * 100)
            sb = QSpinBox()
            sb.setRange(0, 300)
            sb.setValue(cur)
            sb.setSingleStep(10)
            layout.addRow(tag.name or str(tag.id), sb)
            tag_spinboxes[tag.id] = sb

        # Buttons
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save selected multipliers
            for tid, sb in tag_spinboxes.items():
                val = sb.value()
                if val == 100:
                    # default, remove override
                    self.per_tag_weights.pop(tid, None)
                else:
                    self.per_tag_weights[tid] = float(val) / 100.0
            graphics_logger.info(f"Updated per-tag weights: {len(self.per_tag_weights)} overrides")
            self._schedule_refresh()

    def _edit_manual_mappings(self):
        """Open the ManualMappingsEditor dialog to edit mapping files."""
        try:
            # Use the currently loaded path when available, otherwise default path
            start_path = None
            if getattr(self, 'manual_relationships', None) is not None:
                # No direct path stored with relationships; prefer the repo default
                start_path = os.path.join(os.getcwd(), 'data', 'tag_relationships.yml')

            dlg = ManualMappingsEditor(self, path=start_path)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                # Try to load the saved file from the editor
                if getattr(dlg, 'path', None) and os.path.exists(dlg.path):
                    try:
                        rels = manual_mod.load_relationships(dlg.path)
                        self.manual_relationships = rels
                        self._update_manual_status()
                        graphics_logger.info(f"Loaded manual mappings from editor: {dlg.path}")
                    except Exception:
                        graphics_logger.exception("Failed to load mappings after edit")
        except Exception:
            graphics_logger.exception("Error launching manual mappings editor")
        self._schedule_refresh()

    def _open_suggester(self):
        """Run suggestion helper and open the suggestion dialog for curator review."""
        if not self.session:
            QMessageBox.information(self, "Suggest relationships", "Database session not available.")
            return

        try:
            # get candidate suggestions from helper
            candidates = manual_mod.suggest_candidates_from_db(self.session, min_count=5, min_sim=0.6, max_pairs=200)
        except Exception as e:
            graphics_logger.exception("Error generating suggestions")
            QMessageBox.critical(self, "Suggest relationships", f"Error generating suggestions: {e}")
            return

        if not candidates:
            QMessageBox.information(self, "Suggestions", "No candidate relationships found.")
            return

        dlg = ManualSuggestionDialog(self, session=self.session, suggestions=candidates, mappings_path=os.path.join(os.getcwd(), 'data', 'tag_relationships.yml'))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # If the dialog saved/appended entries, reload mappings
            if getattr(dlg, 'saved_path', None):
                try:
                    rels = manual_mod.load_relationships(dlg.saved_path)
                    self.manual_relationships = rels
                    self._update_manual_status()
                    graphics_logger.info(f"Loaded manual mappings from suggester: {dlg.saved_path}")
                except Exception:
                    graphics_logger.exception("Failed to load mappings after suggestions applied")
        self._schedule_refresh()
    
    def _on_fuzzy_toggle(self):
        """Handle fuzzy tag matching toggle."""
        enabled = self.fuzzy_tags_cb.isChecked()
        graphics_logger.info(f"Fuzzy tag matching: {enabled}")
        self._schedule_refresh()
    
    def _on_idf_toggle(self):
        """Handle IDF weighting toggle."""
        enabled = self.idf_weights_cb.isChecked()
        graphics_logger.info(f"IDF tag weighting: {enabled}")
        
        # Calculate IDF weights if needed
        if enabled and not self.idf_weights and self.session:
            try:
                from albumexplore.database.tag_idf_weights import calculate_idf_weights, normalize_weights
                raw_weights = calculate_idf_weights(self.session, min_frequency=1)
                # Normalize so mean is 1.0 (neutral)
                self.idf_weights = normalize_weights(raw_weights, target_mean=1.0)
                graphics_logger.info(f"Calculated IDF weights for {len(self.idf_weights)} tags")
            except Exception as e:
                graphics_logger.error(f"Error calculating IDF weights: {e}", exc_info=True)
                self.idf_weights_cb.setChecked(False)
                QMessageBox.warning(self, "IDF Weights", f"Error calculating IDF weights: {e}")
                return
        
        self._schedule_refresh()
    
    def _perform_refresh(self):
        """Recalculate and display similarity data."""
        if not self.current_album_id or not self.session:
            return
        
        # Get parameters
        limit = int(self.limit_combo.currentText())
        threshold = self.threshold_slider.value() / 100.0
        
        graphics_logger.debug(f"Calculating similarities: limit={limit}, threshold={threshold}")
        
        # Calculate similarities
        try:
            # Build weights based on sliders. We map three UI sliders (tags, vocals, location)
            # into internal component weights while preserving the original budget for these groups.
            base_group_total = 0.40 + 0.30 + 0.05  # composite + atomic + country = 0.75
            s_tags = self.tags_slider.value()
            s_vocals = self.vocals_slider.value()
            s_location = self.location_slider.value()
            s_sum = s_tags + s_vocals + s_location

            if s_sum <= 0:
                # Use defaults
                group_tags_weight = 0.40 + 0.30
                group_vocals_weight = 0.0
                group_location_weight = 0.05
            else:
                norm_tags = s_tags / s_sum
                norm_vocals = s_vocals / s_sum
                norm_location = s_location / s_sum
                group_tags_weight = norm_tags * base_group_total
                group_vocals_weight = norm_vocals * base_group_total
                group_location_weight = norm_location * base_group_total

            # Split tags group into composite and atomic preserving original ratio (4:3)
            if (0.40 + 0.30) > 0:
                composite_fraction = 0.40 / (0.40 + 0.30)
                atomic_fraction = 0.30 / (0.40 + 0.30)
            else:
                composite_fraction = 0.5714
                atomic_fraction = 0.4286

            composite_weight = group_tags_weight * composite_fraction
            atomic_weight = group_tags_weight * atomic_fraction

            # Other base weights stay at default (genre, year)
            genre_weight = 0.15
            year_weight = 0.10

            weights = {
                'composite_tags': composite_weight,
                'atomic_tags': atomic_weight,
                'genre': genre_weight,
                'year': year_weight,
                'country': group_location_weight,
                'vocal_style': group_vocals_weight,
            }

            # Decide whether to apply manual relationships
            manual_rels = self.manual_relationships if getattr(self, 'manual_enable_cb', None) and self.manual_enable_cb.isChecked() else None
            alpha_manual = (self.manual_slider.value() / 100.0) if getattr(self, 'manual_slider', None) else 0.5
            
            # Determine if fuzzy tag matching should be used
            use_fuzzy = getattr(self, 'fuzzy_tags_cb', None) and self.fuzzy_tags_cb.isChecked()
            
            # If fuzzy matching disabled but manual relationships enabled, use manual_relationships for old system
            # If fuzzy matching enabled, relationships will be loaded automatically by similarity engine
            if use_fuzzy:
                # Fuzzy matching: load comprehensive relationships by default
                if not manual_rels:
                    manual_rels = self.manual_relationships
            
            # Combine IDF weights with per-tag weights if IDF is enabled
            combined_tag_weights = self.per_tag_weights if hasattr(self, 'per_tag_weights') else {}
            if getattr(self, 'idf_weights_cb', None) and self.idf_weights_cb.isChecked() and self.idf_weights:
                # Merge IDF weights with user weights
                from albumexplore.database.tag_idf_weights import combine_weights
                idf_alpha = 0.5  # 50/50 blend between IDF and user weights
                combined_tag_weights = combine_weights(
                    self.idf_weights,
                    self.per_tag_weights if hasattr(self, 'per_tag_weights') else {},
                    idf_alpha=idf_alpha
                )
                graphics_logger.debug(f"Using combined IDF+user weights: {len(combined_tag_weights)} tags")

            self.similarities = calculate_album_similarity_optimized(
                self.session,
                self.current_album_id,
                limit=limit,
                min_similarity=threshold,
                weights=weights,
                per_tag_weights=combined_tag_weights,
                manual_relationships=manual_rels,
                alpha_manual=alpha_manual,
                use_fuzzy_tags=use_fuzzy,
            )
            
            graphics_logger.info(f"Found {len(self.similarities)} similar albums")
            
            # Update UI
            self._render_results()
            
        except Exception as e:
            graphics_logger.error(f"Error calculating similarities: {e}", exc_info=True)
            self.results_label.setText(f"Error: {str(e)}")
    
    def _render_results(self):
        """Render the similarity results in the table."""
        self.table.setRowCount(0)
        
        if not self.similarities:
            self.results_label.setText("No similar albums found (try lowering the threshold)")
            return
        
        # Update results label
        self.results_label.setText(f"Similar Albums ({len(self.similarities)} matches)")
        
        # Populate table
        self.table.setRowCount(len(self.similarities))
        
        for row_idx, (album, score, breakdown) in enumerate(self.similarities):
            # Album name
            artist_name = album.pa_artist_name_on_album or "Unknown Artist"
            album_name = f"{artist_name} - {album.title}"
            
            # Add indicator if fuzzy matching contributed
            use_fuzzy = getattr(self, 'fuzzy_tags_cb', None) and self.fuzzy_tags_cb.isChecked()
            if use_fuzzy and breakdown.get('fuzzy_tag_score', 0) > 0:
                album_name = "🔗 " + album_name  # Link emoji indicates relationship matching
            
            album_item = QTableWidgetItem(album_name)
            album_item.setData(Qt.ItemDataRole.UserRole, album.id)
            
            # Color code by similarity
            if score > 0.8:
                color = QColor(0, 200, 0, 30)  # Green
            elif score > 0.6:
                color = QColor(255, 200, 0, 30)  # Yellow
            else:
                color = QColor(150, 150, 150, 30)  # Gray
            album_item.setBackground(color)
            
            self.table.setItem(row_idx, 0, album_item)
            
            # Similarity bar (visual representation)
            bar_item = QTableWidgetItem()
            bar_width = int(score * 100)
            bar_item.setData(Qt.ItemDataRole.DisplayRole, "█" * (bar_width // 5))  # Each █ = 5%
            bar_item.setBackground(color)
            self.table.setItem(row_idx, 1, bar_item)
            
            # Score
            score_item = QTableWidgetItem(f"{score:.3f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            score_item.setBackground(color)
            self.table.setItem(row_idx, 2, score_item)
            
            # Store breakdown in tooltip
            tooltip = self._build_tooltip(album, score, breakdown)
            album_item.setToolTip(tooltip)
            bar_item.setToolTip(tooltip)
            score_item.setToolTip(tooltip)
    
    def _build_tooltip(self, album: Album, score: float, breakdown: Dict[str, Any]) -> str:
        """Build tooltip text with similarity breakdown."""
        lines = [
            f"<b>{album.pa_artist_name_on_album} - {album.title}</b>",
            f"<b>Overall Similarity: {score:.3f}</b>",
            "",
        ]
        
        # Check if fuzzy matching is active
        use_fuzzy = getattr(self, 'fuzzy_tags_cb', None) and self.fuzzy_tags_cb.isChecked()
        
        # Shared tags with context about matching mode
        shared_count = breakdown.get('shared_tags_count', 0)
        total_count = breakdown.get('total_tags', 0)
        
        if use_fuzzy:
            fuzzy_score = breakdown.get('fuzzy_tag_score')
            if fuzzy_score is not None:
                lines.append(f"<b style='color: #4CAF50;'>🔗 Fuzzy Tag Match: {fuzzy_score:.3f}</b>")
                lines.append(f"(Using tag relationships)")
            else:
                lines.append(f"Tag Match: {shared_count} / {total_count} exact")
        else:
            lines.append(f"Tag Match: {shared_count} / {total_count} exact")
        
        shared_tag_names = breakdown.get('shared_tag_names', [])
        if shared_tag_names:
            lines.append("  • " + ", ".join(shared_tag_names[:5]))
            if len(shared_tag_names) > 5:
                lines.append(f"  ... and {len(shared_tag_names) - 5} more")
        
        lines.append("")
        
        # Component breakdown
        lines.append("<b>Score Breakdown:</b>")
        components = []
        if 'tag_score' in breakdown:
            tag_contrib = breakdown.get('tag_score', 0) * breakdown.get('tag_weight', 0.7)
            components.append(f"  Tags: {tag_contrib:.3f}")
        if 'genre_match' in breakdown:
            genre_contrib = (1.0 if breakdown['genre_match'] else 0.0) * breakdown.get('genre_weight', 0.15)
            components.append(f"  Genre: {genre_contrib:.3f}")
        if 'year_score' in breakdown:
            year_contrib = breakdown['year_score'] * breakdown.get('year_weight', 0.1)
            components.append(f"  Year: {year_contrib:.3f}")
        if 'country_match' in breakdown:
            country_contrib = (1.0 if breakdown['country_match'] else 0.0) * breakdown.get('country_weight', 0.05)
            components.append(f"  Location: {country_contrib:.3f}")
        
        if components:
            lines.extend(components)
            lines.append("")
        
        # Genre match
        if breakdown.get('genre_match'):
            lines.append(f"Genre: ✓ {album.genre}")
        else:
            lines.append(f"Genre: {album.genre or 'Unknown'}")
        
        # Year
        year_diff = breakdown.get('year_diff')
        if year_diff is not None:
            lines.append(f"Year: {album.release_year} ({year_diff} years apart)")
        else:
            lines.append(f"Year: {album.release_year or 'Unknown'}")
        
        # Country
        if breakdown.get('country_match'):
            lines.append(f"Country: ✓ {album.country}")
        elif album.country:
            lines.append(f"Country: {album.country}")
        
        # Show manual relationship impact if active
        if use_fuzzy and shared_count > 0:
            lines.append("")
            lines.append("<span style='color: #4CAF50;'>✓ Tag relationships active</span>")
        
        lines.append("")
        lines.append("<i>Double-click to explore this album</i>")
        
        return "<br>".join(lines)

    def eventFilter(self, source, event):
        """Event filter to show a custom hover popup for the similarity table."""
        try:
            if source is self.table.viewport():
                if event.type() == QEvent.Type.MouseMove:
                    # Use integer QPoint for indexAt
                    pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                    idx = self.table.indexAt(pos)
                    if idx.isValid():
                        row = idx.row()
                        if self._hover_row != row:
                            # Update popup content
                            try:
                                album_item = self.table.item(row, 0)
                                if album_item is None:
                                    self._hover_popup.setVisible(False)
                                    self._hover_row = None
                                    return super().eventFilter(source, event)

                                # Retrieve similarity data from internal list when possible
                                if 0 <= row < len(self.similarities):
                                    album, score, breakdown = self.similarities[row]
                                    content = self._build_tooltip(album, score, breakdown)
                                else:
                                    # Fallback to tooltip text on the item
                                    content = album_item.toolTip() or album_item.text()

                                self._hover_popup.setText(content)
                                self._hover_popup.adjustSize()
                                global_pos = self.table.viewport().mapToGlobal(pos)
                                # Offset so popup doesn't overlap the cursor
                                self._hover_popup.move(global_pos + QPoint(12, 18))
                                self._hover_popup.setVisible(True)
                                self._hover_row = row
                            except Exception:
                                self._hover_popup.setVisible(False)
                                self._hover_row = None
                    else:
                        # No valid index under cursor
                        self._hover_popup.setVisible(False)
                        self._hover_row = None
                elif event.type() in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress):
                    # Hide popup when leaving the viewport or clicking
                    self._hover_popup.setVisible(False)
                    self._hover_row = None
        except Exception:
            # Swallow exceptions to avoid breaking GUI event loop
            pass

        return super().eventFilter(source, event)
    
    def _on_album_double_clicked(self, item):
        """Handle double-click on album row."""
        if item.column() != 0:
            item = self.table.item(item.row(), 0)
        
        album_id = item.data(Qt.ItemDataRole.UserRole)
        if album_id:
            graphics_logger.info(f"Requesting focus on album: {album_id}")
            self.album_focus_requested.emit(album_id)

    def _show_context_menu(self, position):
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        album_item = self.table.item(row, 0)
        if not album_item:
            return

        album_id = album_item.data(Qt.ItemDataRole.UserRole)
        if not album_id:
            return

        menu = QMenu(self)
        try:
            fav_action = QAction("Toggle Favorite", self)
            fav_action.triggered.connect(lambda: self._fav_mgr.toggle(album_id))
            menu.addAction(fav_action)
        except Exception:
            pass

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _on_favorites_changed(self):
        # Update tooltips/colors to reflect favorite state
        try:
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if not item:
                    continue
                aid = item.data(Qt.ItemDataRole.UserRole)
                if self._fav_mgr.is_favorite(aid):
                    item.setText(f"★ {item.text()}")
                else:
                    # strip leading star if present
                    txt = item.text()
                    if txt.startswith('★ '):
                        item.setText(txt[2:])
        except Exception:
            graphics_logger.exception('Error updating favorites in similarity view')
    
    def clear(self):
        """Clear the view."""
        self.current_album_id = None
        self.current_album = None
        self.similarities = []
        self.table.setRowCount(0)
        self.header_widget.clear()
        self.results_label.setText("Select an album to see similar albums")
