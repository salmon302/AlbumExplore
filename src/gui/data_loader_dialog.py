"""
Data Loader Dialog for selective CSV file processing.
"""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QProgressBar, QTextEdit, QCheckBox, QGroupBox,
    QSplitter, QTabWidget, QWidget, QComboBox, QSpinBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont
import pandas as pd

from albumexplore.data.parsers.csv_parser import CSVParser
from albumexplore.data.validators.data_validator import DataValidator

logger = logging.getLogger(__name__)


class DataLoadWorker(QThread):
    """Background worker for loading CSV data."""
    
    progress_updated = pyqtSignal(int, str)  # progress, status message
    file_processed = pyqtSignal(str, int, bool)  # filename, row_count, success
    loading_complete = pyqtSignal(object)  # DataFrame
    error_occurred = pyqtSignal(str)  # error message
    log_message = pyqtSignal(str, str)  # level, message
    
    def __init__(self, csv_files: List[Path], debug_level: str = "INFO"):
        super().__init__()
        self.csv_files = csv_files
        self.debug_level = debug_level
        self.should_cancel = False
        
    def run(self):
        """Process selected CSV files."""
        try:
            # Set up logging for this worker
            self._setup_worker_logging()
            
            all_dfs = []
            total_files = len(self.csv_files)
            
            for i, csv_file in enumerate(self.csv_files):
                if self.should_cancel:
                    self.log_message.emit("INFO", "Processing cancelled by user")
                    return
                    
                self.progress_updated.emit(
                    int((i / total_files) * 100), 
                    f"Processing {csv_file.name}..."
                )
                
                try:
                    # Process single file
                    parser = CSVParser(csv_file)
                    df = parser.parse_single_csv(csv_file)
                    
                    if not df.empty:
                        df['_source_file'] = csv_file.name
                        all_dfs.append(df)
                        self.file_processed.emit(csv_file.name, len(df), True)
                        self.log_message.emit("INFO", f"Successfully processed {csv_file.name}: {len(df)} rows")
                    else:
                        self.file_processed.emit(csv_file.name, 0, False)
                        self.log_message.emit("WARNING", f"No data found in {csv_file.name}")
                        
                except Exception as e:
                    self.file_processed.emit(csv_file.name, 0, False)
                    self.log_message.emit("ERROR", f"Error processing {csv_file.name}: {str(e)}")
                    
            # Combine all dataframes
            if all_dfs:
                self.progress_updated.emit(90, "Combining data...")
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                self.progress_updated.emit(95, "Removing duplicates...")
                combined_df = combined_df.drop_duplicates(subset=['Artist', 'Album'], keep='first')
                
                self.progress_updated.emit(100, "Complete!")
                self.loading_complete.emit(combined_df)
                self.log_message.emit("INFO", f"Data loading complete: {len(combined_df)} total rows from {len(all_dfs)} files")
            else:
                self.error_occurred.emit("No valid data found in any selected files")
                
        except Exception as e:
            self.error_occurred.emit(f"Fatal error during data loading: {str(e)}")
            
    def cancel(self):
        """Cancel the loading process."""
        self.should_cancel = True
        
    def _setup_worker_logging(self):
        """Set up logging for the worker thread."""
        # Configure logging level based on user selection
        level = getattr(logging, self.debug_level.upper(), logging.INFO)
        
        # Create a custom handler that emits signals
        class SignalHandler(logging.Handler):
            def __init__(self, signal_emitter):
                super().__init__()
                self.signal_emitter = signal_emitter
                
            def emit(self, record):
                self.signal_emitter.emit(record.levelname, self.format(record))
        
        # Set up the logger
        worker_logger = logging.getLogger('albumexplore.data.parsers')
        worker_logger.setLevel(level)
        
        # Remove existing handlers to avoid duplication
        for handler in worker_logger.handlers[:]:
            worker_logger.removeHandler(handler)
            
        # Add our signal handler
        signal_handler = SignalHandler(self.log_message)
        signal_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        worker_logger.addHandler(signal_handler)


class DataLoaderDialog(QDialog):
    """Dialog for selecting and loading CSV files."""
    
    data_loaded = pyqtSignal(object)  # Emits the loaded DataFrame
    
    def __init__(self, parent=None, csv_directory: Optional[Path] = None):
        super().__init__(parent)
        self.setWindowTitle("Load Album Data")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        self.csv_directory = csv_directory or Path("csv")
        self.worker = None
        self.loaded_data = None
        
        self._setup_ui()
        self._discover_csv_files()
        
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel: File selection
        left_panel = self._create_file_selection_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Progress and logs
        right_panel = self._create_progress_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 400])
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Load Selected Files")
        self.load_button.clicked.connect(self._start_loading)
        self.load_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancel Loading")
        self.cancel_button.clicked.connect(self._cancel_loading)
        self.cancel_button.setEnabled(False)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        
        self.use_data_button = QPushButton("Use Loaded Data")
        self.use_data_button.clicked.connect(self._use_loaded_data)
        self.use_data_button.setEnabled(False)
        
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.use_data_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def _create_file_selection_panel(self):
        """Create the file selection panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Select CSV Files to Load")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # File list with checkboxes
        self.file_list = QListWidget()
        self.file_list.itemChanged.connect(self._update_load_button_state)
        layout.addWidget(self.file_list)
        
        # Selection controls
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_files)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_no_files)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._discover_csv_files)
        
        selection_layout.addWidget(select_all_btn)
        selection_layout.addWidget(select_none_btn)
        selection_layout.addWidget(refresh_btn)
        
        layout.addLayout(selection_layout)
        
        # Debug level selection
        debug_group = QGroupBox("Debug Level")
        debug_layout = QVBoxLayout(debug_group)
        
        self.debug_combo = QComboBox()
        self.debug_combo.addItems(["ERROR", "WARNING", "INFO", "DEBUG"])
        self.debug_combo.setCurrentText("INFO")
        debug_layout.addWidget(self.debug_combo)
        
        layout.addWidget(debug_group)
        
        return panel
        
    def _create_progress_panel(self):
        """Create the progress and logging panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Progress section
        progress_group = QGroupBox("Loading Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to load data")
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_group)
        
        # File status section
        status_group = QGroupBox("File Processing Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_list = QListWidget()
        status_layout.addWidget(self.status_list)
        
        layout.addWidget(status_group)
        
        # Log viewer
        log_group = QGroupBox("Processing Logs")
        log_layout = QVBoxLayout(log_group)
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(200)
        self.log_viewer.setFont(QFont("Consolas", 9))
        
        log_layout.addWidget(self.log_viewer)
        
        # Log controls
        log_controls = QHBoxLayout()
        
        clear_logs_btn = QPushButton("Clear Logs")
        clear_logs_btn.clicked.connect(self.log_viewer.clear)
        
        export_logs_btn = QPushButton("Export Logs")
        export_logs_btn.clicked.connect(self._export_logs)
        
        log_controls.addWidget(clear_logs_btn)
        log_controls.addWidget(export_logs_btn)
        log_controls.addStretch()
        
        log_layout.addLayout(log_controls)
        layout.addWidget(log_group)
        
        return panel
        
    def _discover_csv_files(self):
        """Discover CSV files in the specified directory."""
        self.file_list.clear()
        
        if not self.csv_directory.exists():
            self.file_list.addItem(f"Directory not found: {self.csv_directory}")
            return
            
        csv_files = list(self.csv_directory.glob("*.csv")) + list(self.csv_directory.glob("*.tsv"))
        
        if not csv_files:
            self.file_list.addItem("No CSV/TSV files found in directory")
            return
            
        for csv_file in sorted(csv_files):
            item = QListWidgetItem(f"{csv_file.name} ({csv_file.stat().st_size // 1024} KB)")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, csv_file)
            self.file_list.addItem(item)
            
    def _select_all_files(self):
        """Select all CSV files."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole):  # Only if it has file data
                item.setCheckState(Qt.CheckState.Checked)
                
    def _select_no_files(self):
        """Deselect all CSV files."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
            
    def _update_load_button_state(self):
        """Update the load button state based on file selection."""
        selected_count = sum(1 for i in range(self.file_list.count()) 
                           if self.file_list.item(i).checkState() == Qt.CheckState.Checked)
        self.load_button.setEnabled(selected_count > 0)
        
    def _start_loading(self):
        """Start loading the selected CSV files."""
        selected_files = []
        
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                file_path = item.data(Qt.ItemDataRole.UserRole)
                if file_path:
                    selected_files.append(file_path)
                    
        if not selected_files:
            return
            
        # Set up UI for loading
        self.load_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.close_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_list.clear()
        
        # Create and start worker
        debug_level = self.debug_combo.currentText()
        self.worker = DataLoadWorker(selected_files, debug_level)
        
        # Connect signals
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.file_processed.connect(self._update_file_status)
        self.worker.loading_complete.connect(self._loading_complete)
        self.worker.error_occurred.connect(self._loading_error)
        self.worker.log_message.connect(self._add_log_message)
        
        self.worker.start()
        
    def _cancel_loading(self):
        """Cancel the loading process."""
        if self.worker:
            self.worker.cancel()
            self.worker.wait()  # Wait for thread to finish
            
        self._reset_ui_after_loading()
        
    def _update_progress(self, value: int, message: str):
        """Update the progress bar and message."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
    def _update_file_status(self, filename: str, row_count: int, success: bool):
        """Update the file processing status."""
        status_icon = "✓" if success else "✗"
        status_text = f"{status_icon} {filename}: {row_count} rows" if success else f"{status_icon} {filename}: Failed"
        self.status_list.addItem(status_text)
        
    def _loading_complete(self, dataframe):
        """Handle successful data loading."""
        self.loaded_data = dataframe
        self._reset_ui_after_loading()
        self.use_data_button.setEnabled(True)
        self.progress_label.setText(f"Loading complete! {len(dataframe)} total rows loaded.")
        
    def _loading_error(self, error_message: str):
        """Handle loading errors."""
        self._reset_ui_after_loading()
        self.progress_label.setText(f"Error: {error_message}")
        self._add_log_message("ERROR", error_message)
        
    def _add_log_message(self, level: str, message: str):
        """Add a message to the log viewer."""
        # Color code by level
        color_map = {
            "DEBUG": "#888888",
            "INFO": "#000000", 
            "WARNING": "#FF8C00",
            "ERROR": "#FF0000"
        }
        
        color = color_map.get(level, "#000000")
        formatted_message = f'<span style="color: {color};">[{level}] {message}</span>'
        
        self.log_viewer.append(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _reset_ui_after_loading(self):
        """Reset UI state after loading completes or is cancelled."""
        self.load_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        self._update_load_button_state()  # Re-check file selection
        
    def _use_loaded_data(self):
        """Emit the loaded data and close the dialog."""
        if self.loaded_data is not None:
            self.data_loaded.emit(self.loaded_data)
            self.accept()
            
    def _export_logs(self):
        """Export the current logs to a file."""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Logs", 
            f"albumexplore_logs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_viewer.toPlainText())
                self._add_log_message("INFO", f"Logs exported to {filename}")
            except Exception as e:
                self._add_log_message("ERROR", f"Failed to export logs: {str(e)}")