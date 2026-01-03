"""Main GUI application module."""
import sys
import logging
from pathlib import Path # Added Path
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QApplication, QStackedWidget
from PyQt6.QtGui import QAction, QColor, QPalette # Added QAction, QColor, QPalette
from PyQt6.QtCore import Qt, QTimer
from .views.table_view import TableView
from .views.similarity_bar_view import SimilarityBarChartView
from albumexplore.visualization.views.tag_explorer_view import TagExplorerView # Corrected import
from .widgets.loading_widget import LoadingWidget
try:
    from .views.world_map_view import WorldMapView
    MAP_VIEW_AVAILABLE = True
except ImportError as e:
    graphics_logger = logging.getLogger('albumexplore.graphics')
    graphics_logger.warning(f"Map view not available: {e}. Install 'folium' and 'PyQt6-WebEngine' to enable.")
    MAP_VIEW_AVAILABLE = False
    WorldMapView = None
from albumexplore.visualization.view_manager import ViewManager
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import graphics_logger # Changed from gui_logger to graphics_logger
from albumexplore.database import init_db, get_session # Added imports
from albumexplore.database.csv_loader import load_dataframe_data # Added import
# Removed auto-loading import: from albumexplore.database.csv_loader import load_csv_data
from albumexplore.visualization.data_interface import DataInterface # Added import

class AlbumExplorer(QMainWindow):
    """Main application window."""
    
    def __init__(self, parent=None):
        """Initialize the application window."""
        super().__init__(parent)
        self.setWindowTitle("Album Explorer - Ready for Data Loading") # Updated title
        self.setMinimumSize(1200, 800)
        
        try:
            init_db()
            # Initialize database session and data interface without loading CSV data
            graphics_logger.info("Initializing database session...")
            self.session = get_session() 
            self.data_interface = DataInterface(self.session) 
            self.view_manager = ViewManager(self.data_interface, parent=self) 
            
            # Initialize views dictionary for lazy loading
            self._views = {}  # Will be populated on-demand
            self._view_initialized = {
                ViewType.TABLE: False,
                ViewType.TAG_EXPLORER: False,
                ViewType.SIMILARITY: False,
                ViewType.MAP: False
            }

            # Setup Menu Bar for view switching and data loading
            self._setup_menu_bar()

            # Connect view_manager signals
            self.view_manager.view_changed.connect(self._update_active_view) 

            # Create a stacked widget to hold different views
            self.stacked_widget = QStackedWidget()
            
            # Create and add loading widget
            self.loading_widget = LoadingWidget()
            self.stacked_widget.addWidget(self.loading_widget)

            # Set the central widget
            self.setCentralWidget(self.stacked_widget)

            # Show a welcome message instead of loading data
            self._show_welcome_view()

            graphics_logger.info("Album Explorer initialized - ready for data loading")
            
        except Exception as e:
            graphics_logger.error(f"Failed to initialize Album Explorer: {e}", exc_info=True) 
            raise
    
    def _get_or_create_view(self, view_type: ViewType):
        """Get or create a view lazily on first access."""
        if view_type in self._views:
            graphics_logger.debug(f"Reusing cached view for {view_type.value}")
            return self._views[view_type]
        
        graphics_logger.info(f"Creating view for {view_type.value}...")
        
        if view_type == ViewType.TABLE:
            view = TableView()
            view.show_similar_requested.connect(self._show_similar_albums)
            self._views[ViewType.TABLE] = view
        elif view_type == ViewType.TAG_EXPLORER:
            view = TagExplorerView()
            self._views[ViewType.TAG_EXPLORER] = view
        elif view_type == ViewType.SIMILARITY:
            view = SimilarityBarChartView()
            view.set_session(self.session)
            view.album_focus_requested.connect(self._show_similar_albums)
            self._views[ViewType.SIMILARITY] = view
        elif view_type == ViewType.MAP and MAP_VIEW_AVAILABLE:
            view = WorldMapView()
            self._views[ViewType.MAP] = view
        else:
            graphics_logger.warning(f"Unknown or unavailable view type: {view_type.value}")
            return None
        
        # Add to stacked widget
        self.stacked_widget.addWidget(view)
        self._view_initialized[view_type] = True
        
        graphics_logger.info(f"View {view_type.value} created and added to stack")
        return view
    
    def _show_welcome_view(self):
        """Show a welcome message until data is loaded."""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        
        welcome_label = QLabel("Welcome to Album Explorer")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        instruction_label = QLabel("Use File > Load Data to select CSV files to process")
        instruction_label.setStyleSheet("font-size: 14px; margin: 10px;")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(welcome_label)
        layout.addWidget(instruction_label)
        
        # Add the welcome widget to the stacked widget
        self.stacked_widget.addWidget(welcome_widget)
        self.stacked_widget.setCurrentWidget(welcome_widget)
        self.welcome_widget = welcome_widget
    
    def _show_data_loader(self):
        """Show the data loader dialog."""
        from .data_loader_dialog import DataLoaderDialog
        
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        csv_directory = project_root / "csv"
        
        dialog = DataLoaderDialog(self, csv_directory)
        dialog.data_loaded.connect(self._on_data_loaded)
        dialog.exec()
    
    def _on_data_loaded(self, dataframe):
        """Handle data loaded from the dialog."""
        graphics_logger.info(f"Data loaded: {len(dataframe)} rows. Saving to database with optimized processing...")
        
        # Debug: Check what columns are in the DataFrame
        graphics_logger.info(f"DataFrame columns: {list(dataframe.columns)}")
        
        # Debug: Check first few rows for genre/tag data
        if len(dataframe) > 0:
            for i in range(min(3, len(dataframe))):
                row = dataframe.iloc[i]
                graphics_logger.info(f"Row {i}: Artist='{row.get('Artist', 'N/A')}', Album='{row.get('Album', 'N/A')}'")
                graphics_logger.info(f"Row {i}: Genre='{row.get('Genre / Subgenres', 'N/A')}', Country='{row.get('Country / State', 'N/A')}'")
        
        # Load the dataframe into the database using optimized method
        try:
            session = get_session()
            
            # Use optimized loader for better performance
            from albumexplore.database.optimized_csv_loader import load_dataframe_data_optimized
            load_dataframe_data_optimized(dataframe, session)
            graphics_logger.info("Successfully saved data to database using optimized processing.")
            
            # Debug: Check what was actually saved to the database
            from albumexplore.database.csv_loader import debug_database_tags
            debug_database_tags()
            
        except Exception as e:
            graphics_logger.error(f"Failed to save data to database: {e}", exc_info=True)
            # Fall back to original method if optimized fails
            graphics_logger.info("Falling back to original data loading method...")
            try:
                from albumexplore.database.csv_loader import load_dataframe_data
                load_dataframe_data(dataframe, session)
                graphics_logger.info("Successfully saved data using fallback method.")
            except Exception as fallback_error:
                graphics_logger.error(f"Fallback method also failed: {fallback_error}", exc_info=True)
                return
        
        # Enable view menu actions
        self.table_action.setEnabled(True)
        self.tag_explorer_action.setEnabled(True)
        self.similarity_action.setEnabled(True)
        if MAP_VIEW_AVAILABLE and hasattr(self, 'map_action'):
            self.map_action.setEnabled(True)
        
        # Update the window title
        self.setWindowTitle(f"Album Explorer - {len(dataframe)} albums loaded")
        
        # Switch to table view to show the data
        self.view_manager.switch_view(ViewType.TABLE)
        
        # Remove welcome widget if it exists (guard against deleted C/C++ object)
        if hasattr(self, 'welcome_widget'):
            try:
                # indexOf will return -1 if the widget isn't in the stack; it may
                # raise RuntimeError if the underlying C++ object was already deleted.
                if self.stacked_widget.indexOf(self.welcome_widget) != -1:
                    self.stacked_widget.removeWidget(self.welcome_widget)
            except RuntimeError:
                graphics_logger.warning("welcome_widget already deleted when attempting to remove it from stacked_widget")
            finally:
                try:
                    # Safe to call deleteLater(); if the object is already deleted
                    # this may raise, so guard it.
                    self.welcome_widget.deleteLater()
                except Exception:
                    pass
            # Remove attribute reference so future calls won't attempt removal again
            try:
                delattr(self, 'welcome_widget')
            except Exception:
                # fallback to deleting attribute directly if delattr fails
                if hasattr(self, 'welcome_widget'):
                    del self.welcome_widget

    def _setup_menu_bar(self):
        """Sets up the main menu bar with data loading and view switching actions."""
        menu_bar = self.menuBar()
        
        # File menu for data loading
        file_menu = menu_bar.addMenu("&File")
        
        load_data_action = QAction("&Load Data...", self)
        load_data_action.setShortcut("Ctrl+O")
        load_data_action.triggered.connect(self._show_data_loader)
        file_menu.addAction(load_data_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu for switching views
        view_menu = menu_bar.addMenu("&View")

        table_action = QAction("&Table View", self)
        table_action.triggered.connect(lambda: self._handle_view_switch(ViewType.TABLE))
        table_action.setEnabled(False)  # Disabled until data is loaded
        view_menu.addAction(table_action)
        self.table_action = table_action

        tag_explorer_action = QAction("&Tag Explorer View", self)
        tag_explorer_action.triggered.connect(lambda: self._handle_view_switch(ViewType.TAG_EXPLORER))
        tag_explorer_action.setEnabled(False)  # Disabled until data is loaded
        view_menu.addAction(tag_explorer_action)
        self.tag_explorer_action = tag_explorer_action

        similarity_action = QAction("&Similarity View", self)
        similarity_action.triggered.connect(lambda: self._handle_view_switch(ViewType.SIMILARITY))
        similarity_action.setEnabled(False)  # Disabled until data is loaded
        view_menu.addAction(similarity_action)
        self.similarity_action = similarity_action

        if MAP_VIEW_AVAILABLE:
            map_action = QAction("&Map View", self)
            map_action.triggered.connect(lambda: self._handle_view_switch(ViewType.MAP))
            map_action.setEnabled(False)  # Disabled until data is loaded
            view_menu.addAction(map_action)
            self.map_action = map_action

    def _handle_view_switch(self, view_type: ViewType):
        """Switches the current view in the ViewManager."""
        graphics_logger.info(f"[AlbumExplorer._handle_view_switch] Switching to {view_type.value}")
        
        # Debug: Check database when switching to tag explorer
        if view_type == ViewType.TAG_EXPLORER:
            from albumexplore.database.csv_loader import debug_database_tags
            debug_database_tags()
            
        self.view_manager.switch_view(view_type)
        # _update_active_view will be called via the view_changed signal from ViewManager

    def _update_active_view(self):
        """Updates the currently displayed view based on ViewManager's state."""
        graphics_logger.info("AlbumExplorer: Updating active view")
        current_view_type = self.view_manager.current_view_type
        
        # Show loading widget
        self.loading_widget.set_message(f"Loading {current_view_type.value} view...")
        self.loading_widget.set_status("Preparing data...")
        self.stacked_widget.setCurrentWidget(self.loading_widget)
        QApplication.processEvents()  # Force UI update
        
        render_data = self.view_manager.get_render_data() # Get current render data

        if not render_data:
            graphics_logger.warning("AlbumExplorer: No render data available from get_render_data(). Attempting to force render.")
            self.loading_widget.set_status("Rendering view data...")
            QApplication.processEvents()
            # Attempt to render if data is missing, might be initial call
            render_data = self.view_manager._render_view() # Call internal method as a fallback
            if not render_data:
                graphics_logger.error("AlbumExplorer: Still no render data after explicit _render_view call.")
                return
            else:
                graphics_logger.info("AlbumExplorer: Successfully fetched render_data via _render_view fallback.")

        # Lazy load the view if not already created
        self.loading_widget.set_status("Initializing view components...")
        QApplication.processEvents()
        view = self._get_or_create_view(current_view_type)
        if not view:
            graphics_logger.error(f"Failed to create or get view for {current_view_type.value}")
            return

        self.loading_widget.set_status("Populating view data...")
        QApplication.processEvents()
        
        if current_view_type == ViewType.TABLE:
            graphics_logger.info(f"AlbumExplorer: Setting TableView. Data type: {render_data.get('type')}")
            view.update_data(render_data)
            self.stacked_widget.setCurrentWidget(view)
        elif current_view_type == ViewType.TAG_EXPLORER: # Added condition for TagExplorerView
            graphics_logger.info(f"AlbumExplorer: Setting TagExplorerView. Data type: {render_data.get('type')}")
            nodes = render_data.get('nodes', [])
            edges = render_data.get('edges', []) # edges might not be directly used by TagExplorerView but good to pass if available
            view.update_data(nodes, edges)
            self.stacked_widget.setCurrentWidget(view)
        elif current_view_type == ViewType.SIMILARITY:
            graphics_logger.info(f"AlbumExplorer: Setting SimilarityView. Data type: {render_data.get('type')}")
            # For similarity view, we need to set an album first
            # Check if there's a selected album
            selected_ids = render_data.get('selected_ids', set())
            if selected_ids:
                album_id = list(selected_ids)[0]
                view.set_album(album_id)
            self.stacked_widget.setCurrentWidget(view)
        elif current_view_type == ViewType.MAP and MAP_VIEW_AVAILABLE:
            graphics_logger.info(f"AlbumExplorer: Setting MapView. Data type: {render_data.get('type')}")
            view.update_data(render_data)
            self.stacked_widget.setCurrentWidget(view)
        else:
            graphics_logger.warning(f"AlbumExplorer: Unknown view type {current_view_type}")
        
        # Ensure the window is shown and brought to front - REMOVED, handled by main()

    def _show_similar_albums(self, album_id: str):
        """Switch to similarity view and focus on the given album."""
        graphics_logger.info(f"Switching to similarity view for album: {album_id}")
        
        # Set the album in the similarity view
        self.similarity_view.set_album(album_id)
        
        # Switch to similarity view
        self.view_manager.switch_view(ViewType.SIMILARITY)
    
    def init_data_and_views(self): # This method seems to be called from main after window.show()
        """Load initial data and trigger the first view update."""
        graphics_logger.info("[AlbumExplorer.init_data_and_views] Called.")
        # Ensure data is loaded by ViewManager if it wasn't already by switch_view
        # The _update_active_view method will fetch the latest render data.
        # self.view_manager.update_data() # This might be redundant if switch_view already prepared data
        self._update_active_view() # This will set the correct widget and update its data
        
        graphics_logger.info("[AlbumExplorer.init_data_and_views] Initial view update triggered.")

def main():
    """Run the GUI application."""
    try:
        graphics_logger.info("[main] Creating QApplication...") # Changed to graphics_logger
        app = QApplication(sys.argv)
        # Apply global dark theme so all views inherit the TagExplorer styling
        try:
            background_hex = "#121212"
            surface_hex = "#181818"
            raised_hex = "#202124"
            border_hex = "#2a2d32"
            hover_hex = "#2c3239"
            text_primary_hex = "#f1f3f4"
            text_muted_hex = "#9aa0a6"
            accent_hex = "#64b5f6"
            accent_hover_hex = "#81c9ff"
            accent_pressed_hex = "#4aa4e3"
            success_hex = "#7bd88f"
            danger_hex = "#f77676"
            control_base_hex = "#2c323a"
            control_hover_hex = "#37414b"
            control_pressed_hex = "#425163"

            palette = app.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor(background_hex))
            palette.setColor(QPalette.ColorRole.Base, QColor(surface_hex))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(raised_hex))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(text_primary_hex))
            palette.setColor(QPalette.ColorRole.Text, QColor(text_primary_hex))
            palette.setColor(QPalette.ColorRole.Button, QColor(control_base_hex))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(text_primary_hex))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(accent_hex))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(background_hex))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(raised_hex))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(text_primary_hex))

            stylesheet = f"""
            QWidget {{
                background-color: {background_hex};
                color: {text_primary_hex};
                font-size: 10pt;
            }}
            QWidget#filterHeader {{
                background-color: {surface_hex};
                border-bottom: 1px solid {border_hex};
                padding: 6px 10px;
            }}
            QWidget#tagPanel, QWidget#albumPanel {{
                background-color: {surface_hex};
            }}
            QLabel#statusBarLabel {{
                background-color: {raised_hex};
                color: {text_primary_hex};
                padding: 6px 12px;
                border-top: 1px solid {border_hex};
                font-size: 10pt;
                font-weight: 500;
            }}
            QLabel {{ color: {text_primary_hex}; }}
            QLabel#tagCountLabel {{ color: {accent_hex}; font-weight: 600; }}
            QLineEdit {{
                background-color: {control_base_hex};
                border: 1px solid {border_hex};
                border-radius: 4px;
                padding: 4px 8px;
                color: {text_primary_hex};
            }}
            QLineEdit:focus {{ border-color: {accent_hex}; background-color: {raised_hex}; }}
            QPushButton {{
                background-color: {control_base_hex};
                border: 1px solid {border_hex};
                border-radius: 4px;
                padding: 4px 10px;
                color: {text_primary_hex};
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {control_hover_hex}; border-color: {accent_hex}; }}
            QPushButton:pressed {{ background-color: {control_pressed_hex}; border-color: {accent_pressed_hex}; }}
            QPushButton:disabled {{ color: {text_muted_hex}; border-color: {border_hex}; }}
            QComboBox {{ background-color: {control_base_hex}; border: 1px solid {border_hex}; border-radius: 4px; padding: 4px 24px 4px 8px; color: {text_primary_hex}; }}
            QComboBox QAbstractItemView {{ background-color: {raised_hex}; selection-background-color: {accent_hex}; selection-color: {background_hex}; }}
            QCheckBox {{ spacing: 6px; color: {text_primary_hex}; }}
            QTableWidget {{ gridline-color: {border_hex}; background-color: {surface_hex}; alternate-background-color: {raised_hex}; selection-background-color: {accent_hex}; selection-color: {background_hex}; }}
            QHeaderView::section {{ background-color: {raised_hex}; color: {text_primary_hex}; border: none; border-right: 1px solid {border_hex}; padding: 6px 8px; }}
            QHeaderView::section:selected {{ background-color: {accent_hex}; color: {background_hex}; }}
            QScrollBar:vertical {{ background: {surface_hex}; width: 14px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: {raised_hex}; border-radius: 6px; min-height: 24px; }}
            QScrollBar::handle:vertical:hover {{ background: {accent_hex}; }}
            QSplitter::handle {{ background-color: {raised_hex}; width: 5px; }}
            QSplitter::handle:hover {{ background-color: {accent_hex}; }}
            QProgressBar {{ background-color: {surface_hex}; border: 1px solid {border_hex}; border-radius: 4px; text-align: center; color: {text_primary_hex}; }}
            QProgressBar::chunk {{ background-color: {accent_hex}; }}
            QToolTip {{
                background-color: {raised_hex};
                color: {text_primary_hex};
                border: 1px solid {border_hex};
                padding: 4px;
                border-radius: 4px;
            }}
            """

            app.setPalette(palette)
            app.setStyleSheet(stylesheet)
        except Exception as e:
            graphics_logger.debug(f"Failed to apply global dark theme: {e}")
        app.setQuitOnLastWindowClosed(False)
        graphics_logger.info("[main] QApplication created.") # Changed to graphics_logger

        graphics_logger.info("[main] Creating AlbumExplorer window...") # Changed to graphics_logger
        window = AlbumExplorer()
        graphics_logger.info("[main] AlbumExplorer window created.") # Changed to graphics_logger

        # Call init_data_and_views after the window is created but before it's shown,
        # or rely on __init__ to set up the initial view.
        # For now, __init__ calls switch_view which triggers _update_active_view.
        # If init_data_and_views is meant to be the primary data loading point,
        # then the call in __init__ might need adjustment.
        # window.init_data_and_views() # Let's see if __init__ handles it first.

        graphics_logger.info("[main] Calling window.show()...") # Changed to graphics_logger
        window.show() # This should now show the view set by _update_active_view
        graphics_logger.info("[main] window.show() called.") # Changed to graphics_logger
        
        # If init_data_and_views is essential for a post-show update or delayed load:
        # window.init_data_and_views() 

        graphics_logger.info("[main] Calling app.exec()...") # Changed to graphics_logger
        exit_code = app.exec()
        graphics_logger.info(f"[main] app.exec() returned with exit code: {exit_code}") # Changed to graphics_logger
        return exit_code

    except Exception as e:
        graphics_logger.error(f"[main] Error starting GUI: {str(e)}", exc_info=True) # Changed to graphics_logger
        return 1

if __name__ == "__main__":
    effective_exit_code = main()
    
    # Using print for this final message as logging might be shut down
    # or if the issue is with logging itself.
    print(f"[app.py __main__] Script completing. main() returned: {effective_exit_code}. Exiting with sys.exit({effective_exit_code}).", flush=True)
    sys.exit(effective_exit_code)
