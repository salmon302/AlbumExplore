"""
Scraper Control Dialog for ProgArchives Data Pipeline.
"""
import logging
import sys
import os
from pathlib import Path
from typing import Optional

# Ensure we can import from src if running as script
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir / 'src') not in sys.path:
    sys.path.insert(0, str(root_dir / 'src'))

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QProgressBar, QTextEdit, QComboBox, QDoubleSpinBox, 
    QLineEdit, QGroupBox, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QObject

from albumexplore.scraping.progarchives.pipeline import run_collection
from albumexplore.scraping.hybrid_pipeline import run_hybrid_collection

logger = logging.getLogger(__name__)

class ScraperWorker(QThread):
    """Background worker for the scraping pipeline."""
    
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(bool) # success
    log_message = pyqtSignal(str, str) # level, message

    def __init__(self, output_dir: str, letters: Optional[str], delay: float, mode: str, force_reindex: bool,
                 use_browser: bool, browser_headful: bool):
        super().__init__()
        self.output_dir = output_dir
        self.letters = letters
        self.delay = delay
        self.mode = mode
        self.force_reindex = force_reindex
        self.use_browser = use_browser
        self.browser_headful = browser_headful
        self._is_stopped = False
        self._is_paused = False
        
    def run(self):
        # Setup logging redirection
        self._setup_logging()
        
        try:
            if self.mode == "hybrid":
                run_hybrid_collection(
                    output_dir=self.output_dir,
                    letters=self.letters,
                    delay=self.delay,
                    use_browser=self.use_browser,
                    browser_headful=self.browser_headful,
                    progress_callback=self._on_progress,
                    stop_check=self._check_stop
                )
            else:
                run_collection(
                    output_dir=self.output_dir,
                    letters=self.letters,
                    delay=self.delay,
                    mode=self.mode,
                    force_reindex=self.force_reindex,
                    use_browser=self.use_browser,
                    browser_headful=self.browser_headful,
                    progress_callback=self._on_progress,
                    stop_check=self._check_stop
                )
            self.finished.emit(True)
        except Exception as e:
            self.log_message.emit("ERROR", f"Pipeline failed: {e}")
            self.finished.emit(False)
            
    def stop(self):
        self._is_stopped = True
        
    def _check_stop(self) -> bool:
        # Simple pause implementation: strict blocking sleep
        while self._is_paused and not self._is_stopped:
            self.msleep(100)
        return self._is_stopped

    def pause(self):
        self._is_paused = True
    
    def resume(self):
        self._is_paused = False

    def _on_progress(self, current, total, message):
        self.progress_updated.emit(current, total, message)
        
    def _setup_logging(self):
        # Add a handler to redirect pipeline logs to the GUI
        class SignalHandler(logging.Handler):
            def __init__(self, emitter):
                super().__init__()
                self.emitter = emitter
            def emit(self, record):
                self.emitter.emit(record.levelname, self.format(record))
                
        pipeline_logger = logging.getLogger("albumexplore.scraping.progarchives.pipeline")
        collector_logger = logging.getLogger("albumexplore.scraping.progarchives.collectors")
        hybrid_logger = logging.getLogger("albumexplore.scraping.hybrid_pipeline")
        
        handler = SignalHandler(self.log_message)
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        pipeline_logger.addHandler(handler)
        pipeline_logger.setLevel(logging.INFO)
        collector_logger.addHandler(handler)
        collector_logger.setLevel(logging.INFO)
        hybrid_logger.addHandler(handler)
        hybrid_logger.setLevel(logging.INFO)


class ScraperDialog(QDialog):
    """GUI Control for the ProgArchives Scraper."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProgArchives Scraper")
        self.setMinimumSize(600, 500)
        self.worker = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Config Section ---
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["full", "download", "index", "hybrid"])
        self.mode_combo.setToolTip("hybrid: Use PA for Artist Index, Last.fm for Data")
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        config_layout.addLayout(mode_layout)
        
        # Letters
        letters_layout = QHBoxLayout()
        letters_layout.addWidget(QLabel("Artist Letters (e.g. 'abc'):"))
        self.letters_input = QLineEdit()
        self.letters_input.setPlaceholderText("Leave empty for all")
        letters_layout.addWidget(self.letters_input)
        config_layout.addLayout(letters_layout)
        
        # Delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Request Delay (sec):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.1, 10.0)
        self.delay_spin.setValue(1.0)
        self.delay_spin.setSingleStep(0.1)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        config_layout.addLayout(delay_layout)
        
        # Options
        self.reindex_check = QCheckBox("Force Re-Index")
        config_layout.addWidget(self.reindex_check)
        
        # Browser Options
        self.browser_check = QCheckBox("Use Browser Fallback (Selenium)")
        self.browser_check.setToolTip("Use a real browser if headers/cloudscraper fail (bypasses 403s)")
        config_layout.addWidget(self.browser_check)
        
        self.headful_check = QCheckBox("Show Browser (Headful)")
        self.headful_check.setToolTip("Show the browser window (useful for solving Captchas manually)")
        config_layout.addWidget(self.headful_check)
        
        layout.addWidget(config_group)
        
        # --- Progress Section ---
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_group)
        
        # --- Log Section ---
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: Consolas; font-size: 10px;")
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start/Resume")
        self.start_btn.clicked.connect(self.toggle_start)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_scraping)
        self.stop_btn.setEnabled(False)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)

    def toggle_start(self):
        if self.worker is None:
            # Start new
            self.start_scraping()
        else:
            # Already running? Button text should handle this logic, but if we are paused, this acts as resume
            if self.worker._is_paused:
                self.worker.resume()
                self.status_label.setText("Resumed...")
                self.pause_btn.setText("Pause")
                self.start_btn.setEnabled(False) # Disable start while running
    
    def start_scraping(self):
        output_dir = "raw_data/progarchives" # Default for GUI
        letters = self.letters_input.text().strip() or None
        delay = self.delay_spin.value()
        mode = self.mode_combo.currentText()
        force_reindex = self.reindex_check.isChecked()
        use_browser = self.browser_check.isChecked()
        browser_headful = self.headful_check.isChecked()
        
        self.worker = ScraperWorker(output_dir, letters, delay, mode, force_reindex, use_browser, browser_headful)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(self.scraping_finished)
        
        self.worker.start()
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Starting...")
        
    def toggle_pause(self):
        if self.worker and not self.worker._is_paused:
            self.worker.pause()
            self.status_label.setText("Paused")
            self.pause_btn.setText("Resume")
        elif self.worker and self.worker._is_paused:
            self.worker.resume()
            self.status_label.setText("Resumed")
            self.pause_btn.setText("Pause")
            
    def stop_scraping(self):
        if self.worker:
            self.status_label.setText("Stopping...")
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.start_btn.setText("Start")
        self.status_label.setText("Stopped")

    def scraping_finished(self, success):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.start_btn.setText("Start")
        
        if success:
            self.status_label.setText("Finished successfully.")
        else:
            self.status_label.setText("Finished with errors or stopped.")
        
        self.worker = None

    def update_progress(self, current, total, message):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
        
    def append_log(self, level, message):
        color = "black"
        if level == "ERROR": color = "red"
        elif level == "WARNING": color = "orange"
        
        self.log_text.append(f'<span style="color:{color}">[{level}] {message}</span>')

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = ScraperDialog()
    window.show()
    sys.exit(app.exec())
