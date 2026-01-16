"""
Dialog for fetching and loading Last.fm data.
"""
import logging
import traceback
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QProgressBar, QTextEdit, QCheckBox, QGroupBox, QSpinBox, 
    QComboBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

from albumexplore.database import get_session
from albumexplore.database.models import Album
from albumexplore.scraping.lastfm.fetcher import LastFmFetcher
from albumexplore.scraping.lastfm.transform_lastfm_data import LastFmTransformer

logger = logging.getLogger(__name__)

class LastFmWorker(QThread):
    """Background worker for fetching Last.fm data."""
    
    progress_updated = pyqtSignal(int, str)  # progress (0-100), message
    log_message = pyqtSignal(str, str)       # level, message
    finished_success = pyqtSignal(bool)      # success status

    def __init__(self, limit: int = 0, force: bool = False, transform: bool = True):
        super().__init__()
        self.limit = limit
        self.force = force
        self.transform = transform
        self.should_cancel = False

    def run(self):
        session = None
        try:
            self.log_message.emit("INFO", "Starting Last.fm data fetch...")
            
            # 1. Get albums from database
            session = get_session()
            query = session.query(Album).filter(
                Album.pa_artist_name_on_album != None,
                Album.title != None
            )
            
            # Simple heuristic: prioritize those without lastfm data if not forcing
            if not self.force:
                query = query.filter(Album.lastfm_playcount == None)
                
            albums = query.all()
            
            if self.limit > 0:
                albums = albums[:self.limit]
                
            total_albums = len(albums)
            self.log_message.emit("INFO", f"Found {total_albums} albums to process.")
            
            if total_albums == 0:
                self.log_message.emit("WARNING", "No albums found needing updates.")
                self.finished_success.emit(True)
                return

            # 2. Fetch Data
            fetcher = LastFmFetcher() # Uses default raw_data_dir
            
            album_list = [
                (album.pa_artist_name_on_album, album.title)
                for album in albums
            ]
            
            processed_count = 0
            success_count = 0
            
            # Define progress callback for fetcher
            def fetch_progress(current, total, result):
                nonlocal processed_count, success_count
                if self.should_cancel:
                    return
                
                processed_count = current
                if result.success:
                    success_count += 1
                    status_icon = "✓"
                else:
                    status_icon = "✗"
                    
                msg = f"[{current}/{total}] {status_icon} {result.artist} - {result.album}"
                if not result.success and result.error:
                    msg += f" ({result.error})"
                
                level = "INFO" if result.success else "WARNING"
                self.log_message.emit(level, msg)
                
                percent = int((current / total) * 100) if total > 0 else 0
                # Scale progress to 0-80% for fetch, 80-100% for transform
                scaled_percent = int(percent * 0.8) if self.transform else percent
                self.progress_updated.emit(scaled_percent, f"Fetching: {msg}")

            # Run batch fetch
            # We iterate manually to handle cancellation easily if needed, 
            # though fetcher has a generator.
            results_iter = fetcher.fetch_albums_batch(
                album_list,
                skip_if_exists=not self.force,
                progress_callback=fetch_progress
            )
            
            # Consume the generator
            for result in results_iter:
                if self.should_cancel:
                    self.log_message.emit("WARNING", "Operation cancelled by user.")
                    break

            if self.should_cancel:
                self.finished_success.emit(False)
                return

            self.log_message.emit("INFO", f"Fetch complete. {success_count}/{total_albums} successful.")

            # 3. Transform Data
            if self.transform:
                self.log_message.emit("INFO", "Starting data transformation...")
                self.progress_updated.emit(80, "Transforming data...")
                
                # Run transformer
                # Note: transformer might take a while, but it's typically faster than network IO.
                # We initialize with default URI
                transformer = LastFmTransformer(db_uri=str(session.get_bind().url))
                
                # Capture logs via logging handler wrapper?
                # For now, just run it. The transformer logs to standard python logging,
                # which isn't captured here unless we add a handler. 
                # Let's trust it works and report final stats.
                
                stats = transformer.transform_all()
                
                self.log_message.emit("INFO", f"Transformation stats: {stats}")
                self.progress_updated.emit(100, "Processing Complete")
                
            self.finished_success.emit(True)

        except Exception as e:
            err_msg = f"Error in Last.fm worker: {str(e)}\n{traceback.format_exc()}"
            self.log_message.emit("ERROR", err_msg)
            self.finished_success.emit(False)
        finally:
            if session:
                session.close()

    def cancel(self):
        self.should_cancel = True


class LastFmLoaderDialog(QDialog):
    """Dialog for fetching Last.fm metadata."""
    
    data_changed = pyqtSignal() # Emit when something might have changed in DB

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Last.fm Data")
        self.resize(600, 500)
        self.worker = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Options Group
        options_group = QGroupBox("Fetch Options")
        options_layout = QVBoxLayout(options_group)
        
        # Limit
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Limit albums:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 100000)
        self.limit_spin.setValue(50)
        self.limit_spin.setSpecialValueText("No Limit")
        limit_layout.addWidget(self.limit_spin)
        limit_layout.addStretch()
        options_layout.addLayout(limit_layout)
        
        # Checkboxes
        self.force_check = QCheckBox("Force re-fetch (ignore existing cache)")
        self.transform_check = QCheckBox("Apply updates to database immediately")
        self.transform_check.setChecked(True)
        
        options_layout.addWidget(self.force_check)
        options_layout.addWidget(self.transform_check)
        layout.addWidget(options_group)
        
        # Progress
        self.progress_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        # Log Output
        log_group = QGroupBox("Log Output")
        log_layout = QVBoxLayout(log_group)
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_viewer)
        layout.addWidget(log_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.clicked.connect(self._start_processing)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel_processing)
        self.cancel_btn.setEnabled(False)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def _start_processing(self):
        limit = self.limit_spin.value()
        force = self.force_check.isChecked()
        transform = self.transform_check.isChecked()
        
        self.log_viewer.clear()
        self.log_viewer.append("Initializing worker...")
        
        self.worker = LastFmWorker(limit=limit, force=force, transform=transform)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.log_message.connect(self._on_log)
        self.worker.finished_success.connect(self._on_finished)
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.close_btn.setEnabled(False)
        self.limit_spin.setEnabled(False)
        self.force_check.setEnabled(False)
        
        self.worker.start()

    def _cancel_processing(self):
        if self.worker and self.worker.isRunning():
            self.log_viewer.append("Cancelling...")
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def _on_log(self, level, message):
        color = "#000000"
        if level == "WARNING": color = "#FF8C00"
        if level == "ERROR": color = "#FF0000"
        
        current_time = self._get_timestamp()
        self.log_viewer.append(f'<span style="color:{color}">[{current_time}] {message}</span>')
        # Scroll to bottom
        sb = self.log_viewer.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_finished(self, success):
        self.progress_bar.setValue(100)
        
        if success:
            self.progress_label.setText("Processing finished successfully.")
            if self.transform_check.isChecked():
                self.data_changed.emit()
        else:
            self.progress_label.setText("Processing stopped or failed.")
            
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        self.limit_spin.setEnabled(True)
        self.force_check.setEnabled(True)

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

