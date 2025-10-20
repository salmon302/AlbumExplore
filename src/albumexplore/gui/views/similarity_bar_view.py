"""Similarity bar chart visualization view."""
from typing import Dict, Any, List, Tuple, Optional
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                               QSlider, QPushButton, QWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from .base_view import BaseView
from .album_header_widget import AlbumHeaderWidget
from albumexplore.visualization.state import ViewType
from albumexplore.database.models import Album
from albumexplore.database.similarity import calculate_album_similarity_optimized
from albumexplore.gui.gui_logging import graphics_logger


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
        layout.setSpacing(10)
        
        # Header with selected album info
        self.header_widget = AlbumHeaderWidget()
        layout.addWidget(self.header_widget)
        
        # Controls panel
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Limit selector
        controls_layout.addWidget(QLabel("Show top:"))
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(['10', '20', '50', '100'])
        self.limit_combo.setCurrentText('20')
        self.limit_combo.currentTextChanged.connect(self._schedule_refresh)
        controls_layout.addWidget(self.limit_combo)
        
        controls_layout.addSpacing(20)
        
        # Threshold slider
        controls_layout.addWidget(QLabel("Min similarity:"))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(30)
        self.threshold_slider.setMinimumWidth(150)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        controls_layout.addWidget(self.threshold_slider)
        
        self.threshold_label = QLabel("0.30")
        self.threshold_label.setMinimumWidth(40)
        controls_layout.addWidget(self.threshold_label)
        
        controls_layout.addStretch()
        
        # Back button
        self.back_button = QPushButton("← Back")
        self.back_button.setEnabled(False)
        controls_layout.addWidget(self.back_button)
        
        layout.addWidget(controls_widget)
        
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
        
        # Connect signals
        self.table.itemDoubleClicked.connect(self._on_album_double_clicked)
        
        layout.addWidget(self.table)
        
    def set_session(self, session):
        """Set the database session."""
        self.session = session
    
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
            self.similarities = calculate_album_similarity_optimized(
                self.session,
                self.current_album_id,
                limit=limit,
                min_similarity=threshold
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
        
        # Shared tags
        shared_count = breakdown.get('shared_tags_count', 0)
        total_count = breakdown.get('total_tags', 0)
        lines.append(f"Shared Tags: {shared_count} / {total_count}")
        
        shared_tag_names = breakdown.get('shared_tag_names', [])
        if shared_tag_names:
            lines.append("  • " + ", ".join(shared_tag_names[:5]))
            if len(shared_tag_names) > 5:
                lines.append(f"  ... and {len(shared_tag_names) - 5} more")
        
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
        
        lines.append("")
        lines.append("<i>Double-click to explore this album</i>")
        
        return "<br>".join(lines)
    
    def _on_album_double_clicked(self, item):
        """Handle double-click on album row."""
        if item.column() != 0:
            item = self.table.item(item.row(), 0)
        
        album_id = item.data(Qt.ItemDataRole.UserRole)
        if album_id:
            graphics_logger.info(f"Requesting focus on album: {album_id}")
            self.album_focus_requested.emit(album_id)
    
    def clear(self):
        """Clear the view."""
        self.current_album_id = None
        self.current_album = None
        self.similarities = []
        self.table.setRowCount(0)
        self.header_widget.clear()
        self.results_label.setText("Select an album to see similar albums")
