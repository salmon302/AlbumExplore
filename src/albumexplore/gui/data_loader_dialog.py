"""
Data Loader Dialog for modular data access.
"""
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QProgressBar, QTextEdit, QCheckBox, QGroupBox,
    QSplitter, QTabWidget, QWidget, QComboBox, QSpinBox, QFileDialog, QLineEdit
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont
import pandas as pd

from albumexplore.data.parsers.csv_parser import CSVParser
from albumexplore.database import session_scope
from albumexplore.scraping.metalarchives.importer import MetalArchivesImporter
from albumexplore.scraping.progarchives.transformer import transform_progarchives_data
from albumexplore.scraping.progarchives.extract_csvs import run_extraction

logger = logging.getLogger(__name__)

class WorkerSignals(QThread):
    """Common signals for data loading workers."""
    progress_updated = pyqtSignal(int, str)  # progress, status message
    log_message = pyqtSignal(str, str)  # level, message
    op_finished = pyqtSignal(bool, str) # success, message (renamed from finished to avoid conflict)
    data_loaded = pyqtSignal(object) # Optional payload

    def __init__(self):
        super().__init__()
        self.should_cancel = False

    def cancel(self):
        self.should_cancel = True

class CSVLoadWorker(WorkerSignals):
    """Background worker for loading generic CSV data."""
    
    file_processed = pyqtSignal(str, int, bool) # filename, row_count, success

    def __init__(self, csv_files: List[Path], debug_level: str = "INFO"):
        super().__init__()
        self.csv_files = csv_files
        self.debug_level = debug_level
        
    def _standardize_columns(self, df, filename):
        """Standardize column names across different CSV formats."""
        column_mapping = {
            'artist': 'Artist', 'band': 'Artist', 'band name': 'Artist', 'artist name': 'Artist',
            'album': 'Album', 'album name': 'Album', 'album title': 'Album', 'title': 'Album',
            'release date': 'Release Date', 'release_date': 'Release Date', 'date': 'Release Date', 'year': 'Release Date',
            'genre / subgenres': 'Genre / Subgenres', 'genre': 'Genre / Subgenres', 'genres': 'Genre / Subgenres',
            'country': 'Country / State'
        }
        
        df_columns = df.columns.str.lower().str.strip()
        new_columns = {}
        for i, col in enumerate(df_columns):
            if col in column_mapping:
                new_columns[df.columns[i]] = column_mapping[col]
        
        if new_columns:
            df = df.rename(columns=new_columns)
        return df

    def run(self):
        try:
            all_dfs = []
            total = len(self.csv_files)
            
            for i, csv_file in enumerate(self.csv_files):
                if self.should_cancel:
                    self.log_message.emit("INFO", "Cancelled.")
                    return
                
                self.progress_updated.emit(int((i / total) * 100), f"Processing {csv_file.name}...")
                try:
                    parser = CSVParser(csv_file)
                    df = parser.parse_single_csv(csv_file)
                    if not df.empty:
                        df = self._standardize_columns(df, csv_file.name)
                        df['_source_file'] = csv_file.name
                        all_dfs.append(df)
                        self.file_processed.emit(csv_file.name, len(df), True)
                        self.log_message.emit("INFO", f"Loaded {csv_file.name}: {len(df)} rows")
                    else:
                        self.file_processed.emit(csv_file.name, 0, False)
                        self.log_message.emit("WARNING", f"No data in {csv_file.name}")
                except Exception as e:
                    self.file_processed.emit(csv_file.name, 0, False)
                    self.log_message.emit("ERROR", f"Error loading {csv_file.name}: {e}")

            if all_dfs:
                self.progress_updated.emit(90, "Combining...")
                combined = pd.concat(all_dfs, ignore_index=True)
                if 'Artist' in combined.columns and 'Album' in combined.columns:
                    combined = combined.drop_duplicates(subset=['Artist', 'Album'], keep='first')
                
                self.progress_updated.emit(100, "Done")
                self.data_loaded.emit(combined)
                self.op_finished.emit(True, f"Loaded {len(combined)} rows.")
            else:
                self.op_finished.emit(False, "No valid data found.")
        except Exception as e:
            self.op_finished.emit(False, f"Fatal error: {e}")

class ProgArchivesWorker(WorkerSignals):
    """Worker for ProgArchives Transformation Pipeline."""
    def __init__(self, raw_data_dir: str):
        super().__init__()
        self.raw_data_dir = raw_data_dir
        
    def run(self):
        self.progress_updated.emit(0, "Starting transformation...")
        self.log_message.emit("INFO", f"Transforming data from {self.raw_data_dir}")
        try:
            # Check inputs
            path = Path(self.raw_data_dir)
            if not path.exists():
                self.op_finished.emit(False, f"Directory not found: {self.raw_data_dir}")
                return

            # Automatic Parsing Step
            csv_path = path / "pa_raw_albums.csv"
            has_csv = csv_path.exists()
            # Simple validity check: Is it larger than just a header? (e.g. > 100 bytes)
            is_valid_csv = has_csv and csv_path.stat().st_size > 100

            if not has_csv or not is_valid_csv:
                msg = "No CSVs found." if not has_csv else "CSV file seems empty or invalid."
                self.log_message.emit("INFO", f"{msg} Attempting to parse local HTML files...")
                try:
                    # Provide a generic feedback loop logic?
                    self.log_message.emit("INFO", "Running extractor...")
                    run_extraction(str(path), str(path))
                    self.log_message.emit("INFO", "Parsing complete. CSVs generated.")
                except Exception as e:
                    import traceback
                    logger.error(traceback.format_exc())
                    self.log_message.emit("ERROR", f"Parsing failed: {e}")
                    self.op_finished.emit(False, f"Parsing failed: {e}")
                    return

            self.log_message.emit("INFO", "Running ETL pipeline... check console for details if needed.")
            
            result = transform_progarchives_data(
                raw_data_dir=self.raw_data_dir,
                db_uri="sqlite:///albumexplore.db",
                dry_run=False,
                force=True # Force for manual trigger
            )

            # transformer may return either a boolean or (bool, list_of_ids)
            success = False
            processed_ids = None
            if isinstance(result, tuple):
                success, processed_ids = result
            else:
                success = bool(result)

            if success:
                self.progress_updated.emit(100, "Complete")
                # If we have processed ids, emit them so the main UI can focus
                if processed_ids:
                    self.data_loaded.emit({'album_ids': processed_ids})
                self.op_finished.emit(True, "ProgArchives data imported successfully.")
            else:
                self.op_finished.emit(False, "Transformation failed. Check logs.")
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            self.log_message.emit("ERROR", str(e))
            self.op_finished.emit(False, f"Error: {e}")

class MetalArchivesWorker(WorkerSignals):
    """Worker for MetalArchives Import."""
    def __init__(self, data_dir: str):
        super().__init__()
        self.data_dir = data_dir
        
    def run(self):
        self.progress_updated.emit(0, "Initializing importer...")
        self.log_message.emit("INFO", f"Importing MetalArchives from {self.data_dir}")
        
        try:
             # Check inputs
            path = Path(self.data_dir)
            if not path.exists():
                self.op_finished.emit(False, f"Directory not found: {self.data_dir}")
                return

            with session_scope() as session:
                importer = MetalArchivesImporter(session, data_dir=self.data_dir)
                
                self.log_message.emit("INFO", "Starting batch import... This may take a while.")
                
                importer.import_batch(limit=None, dry_run=False)
                
                stats = importer.stats
                msg = f"Imported: {stats['albums_created']} albums, {stats['artists_created']} artists."
                self.log_message.emit("INFO", msg)
                self.op_finished.emit(True, msg)
                
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            self.log_message.emit("ERROR", str(e))
            self.op_finished.emit(False, f"Error: {e}")

class DataLoaderDialog(QDialog):
    """Unified Dialog for loading/importing data."""
    
    data_loaded = pyqtSignal(object)  # Emits data if loading CSVs directly to view
    
    def __init__(self, parent=None, csv_directory: Optional[Path] = None):
        super().__init__(parent)
        self.setWindowTitle("Data Manager")
        self.resize(800, 600)
        self.worker = None
        self.loaded_data = None
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #C2C7CB; }
            QTabBar::tab { background: #E0E0E0; border: 1px solid #C4C4C3; padding: 5px; min-width: 100px; color: black; }
            QTabBar::tab:selected { background: #FFFFFF; border-bottom-color: #FFFFFF; }
        """)

        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Tab 1: CSV Loader
        self.csv_tab = QWidget()
        self.setup_csv_tab(self.csv_tab)
        self.tabs.addTab(self.csv_tab, "Load CSVs")
        
        # Tab 2: ProgArchives
        self.pa_tab = QWidget()
        self.setup_pa_tab(self.pa_tab)
        self.tabs.addTab(self.pa_tab, "ProgArchives")
        
        # Tab 3: MetalArchives
        self.ma_tab = QWidget()
        self.setup_ma_tab(self.ma_tab)
        self.tabs.addTab(self.ma_tab, "MetalArchives")
        
        layout.addWidget(self.tabs)
        
        # Shared Log Viewer
        log_group = QGroupBox("Logs & Progress")
        log_layout = QVBoxLayout(log_group)
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready")
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(150)
        
        log_layout.addWidget(self.status_label)
        log_layout.addWidget(self.progress_bar)
        log_layout.addWidget(self.log_viewer)
        layout.addWidget(log_group)
        
        # Log Controls
        log_controls = QHBoxLayout()
        export_btn = QPushButton("Export Logs")
        export_btn.clicked.connect(self.export_logs)
        log_controls.addWidget(export_btn)
        log_controls.addStretch()
        log_layout.addLayout(log_controls)

        # Shared Bottom Buttons
        btn_layout = QHBoxLayout()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_worker)
        self.cancel_btn.setEnabled(False)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def setup_csv_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # File list
        self.file_list = QListWidget()
        self.refresh_csv_list()
        layout.addWidget(QLabel("Select files to load into current view:"))
        layout.addWidget(self.file_list)
        
        btns = QHBoxLayout()
        refresh = QPushButton("Refresh List")
        refresh.clicked.connect(self.refresh_csv_list)
        # Select All / Unselect All button next to Load Selected
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.toggle_select_all)

        load = QPushButton("Load Selected")
        load.clicked.connect(self.start_csv_load)
        
        btns.addWidget(refresh)
        btns.addStretch()
        btns.addWidget(self.select_all_btn)
        btns.addWidget(load)
        layout.addLayout(btns)

    def toggle_select_all(self):
        """Toggle selection state for all items in the file list.

        If any item is unchecked, select all. Otherwise unselect all.
        """
        count = self.file_list.count()
        if count == 0:
            return

        # If any item is not checked, we will check them all; otherwise uncheck all.
        any_unchecked = any(self.file_list.item(i).checkState() != Qt.CheckState.Checked for i in range(count))
        new_state = Qt.CheckState.Checked if any_unchecked else Qt.CheckState.Unchecked
        for i in range(count):
            item = self.file_list.item(i)
            item.setCheckState(new_state)

        # Update the button label to reflect next action
        self.select_all_btn.setText("Unselect All" if new_state == Qt.CheckState.Checked else "Select All")
        
    def refresh_csv_list(self):
        self.file_list.clear()
        csv_dir = Path("data/csv")
        if csv_dir.exists():
            for f in csv_dir.glob("*.csv"):
                item = QListWidgetItem(f.name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, f)
                self.file_list.addItem(item)
                
    def setup_pa_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Import ProgArchives data from scraped raw files."))
        
        form = QHBoxLayout()
        form.addWidget(QLabel("Raw Data Dir:"))
        # Point to the root raw_data/progarchives where new scraper outputs
        self.pa_dir_input = QLineEdit("raw_data/progarchives") 
        form.addWidget(self.pa_dir_input)
        layout.addLayout(form)
        
        run_btn = QPushButton("Run Import Pipeline")
        run_btn.clicked.connect(self.start_pa_import)
        layout.addWidget(run_btn)
        layout.addStretch()
        
    def setup_ma_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Import MetalArchives data from CSV dump."))
        
        form = QHBoxLayout()
        form.addWidget(QLabel("Data Directory:"))
        self.ma_dir_input = QLineEdit("data/MetalArchives")
        form.addWidget(self.ma_dir_input)
        layout.addLayout(form)
        
        run_btn = QPushButton("Run Import")
        run_btn.clicked.connect(self.start_ma_import)
        layout.addWidget(run_btn)
        layout.addStretch()

    # --- Worker Management ---
    def start_worker(self, worker):
        if self.worker is not None:
            return
            
        self.worker = worker
        # Keep a reference to the concrete worker type for post-run actions
        self._current_worker = worker
        self.worker.progress_updated.connect(lambda p, m: (self.progress_bar.setValue(p), self.status_label.setText(m)))
        self.worker.log_message.connect(self.append_log)
        self.worker.op_finished.connect(self.worker_finished) # Use op_finished
        # Connect worker data_loaded to appropriate handler so the dialog
        # forwards payloads to the main window. CSVLoadWorker provides a
        # DataFrame and has a specialized handler; other workers emit
        # payloads (e.g. {'album_ids': [...]}) and should be forwarded.
        if isinstance(worker, CSVLoadWorker):
            self.worker.data_loaded.connect(self.on_csv_data_loaded)
        else:
            self.worker.data_loaded.connect(self.on_worker_data_loaded)
            
        self.cancel_btn.setEnabled(True)
        self.close_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.worker.start()
        
    def worker_finished(self, success, msg):
        self.append_log("INFO" if success else "ERROR", msg)
        self.status_label.setText("Finished")
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        # For CSVLoadWorker, the worker emits `data_loaded` with DataFrame.
        # For ETL/import workers (ProgArchives/MetalArchives) they emit an explicit
        # `data_loaded` payload when there's something to preview. Avoid emitting
        # a generic None here which would force a full DB refresh.
        self.worker = None
        self._current_worker = None
        
    def cancel_worker(self):
        if self.worker:
            self.worker.cancel()
            self.status_label.setText("Cancelling...")

    def append_log(self, level, msg):
        color = "black"
        if level == "ERROR": color = "red"
        elif level == "WARNING": color = "orange"
        self.log_viewer.append(f'<span style="color:{color}">[{level}] {msg}</span>')

    def export_logs(self):
        """Export the current logs to a file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Logs", 
            f"data_manager_logs.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_viewer.toPlainText())
                self.append_log("INFO", f"Logs exported to {filename}")
            except Exception as e:
                self.append_log("ERROR", f"Failed to export logs: {str(e)}")

    # --- Actions ---
    def start_csv_load(self):
        files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                files.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not files:
            self.append_log("WARNING", "No files selected.")
            return
            
        self.start_worker(CSVLoadWorker(files))
        
    def on_csv_data_loaded(self, df):
        self.loaded_data = df
        self.data_loaded.emit(df) # Notify main window
        self.append_log("INFO", "Data emitted to view.")

    def on_worker_data_loaded(self, payload):
        """Generic handler for non-CSV workers that emit payloads to preview.

        This forwards the worker payload via the dialog's `data_loaded` signal
        so the main window can act on it (e.g. preview album IDs).
        """
        try:
            self.loaded_data = payload
            self.data_loaded.emit(payload)
            self.append_log("INFO", "Data emitted to view from worker.")
        except Exception as e:
            self.append_log("ERROR", f"Failed to forward worker payload: {e}")

    def start_pa_import(self):
        d = self.pa_dir_input.text()
        self.start_worker(ProgArchivesWorker(d))

    def start_ma_import(self):
        d = self.ma_dir_input.text()
        self.start_worker(MetalArchivesWorker(d))

    def reject(self):
        """Override close via Cancel/Close to ensure background workers are stopped."""
        if self.worker is not None:
            self.append_log("WARNING", "Worker running — cancelling and waiting to finish before close.")
            try:
                self.worker.cancel()
            except Exception:
                pass
            try:
                # Ask the thread to quit if it has an event loop
                self.worker.quit()
            except Exception:
                pass
            # Wait briefly for thread to finish; do not block indefinitely
            try:
                self.worker.wait(5000)
            except Exception:
                pass
        super().reject()

    def closeEvent(self, event):
        """Handle window close (e.g. app exit) to avoid destroying active QThreads."""
        if self.worker is not None:
            self.append_log("WARNING", "Worker running — cancelling and waiting to finish before close.")
            try:
                self.worker.cancel()
            except Exception:
                pass
            try:
                self.worker.quit()
            except Exception:
                pass
            try:
                self.worker.wait(5000)
            except Exception:
                pass
        super().closeEvent(event)
