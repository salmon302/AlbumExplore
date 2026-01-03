"""Loading indicator widget for view transitions."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie


class LoadingWidget(QWidget):
    """Widget to display loading state during view transitions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the loading UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Loading label
        self.label = QLabel("Loading view...")
        self.label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #64b5f6;
            padding: 10px;
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Progress bar (indeterminate)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(300)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #2c323a;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #64b5f6;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 11px;
            color: #9aa0a6;
            padding-top: 10px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
    def set_message(self, message: str):
        """Set the loading message."""
        self.label.setText(message)
        
    def set_status(self, status: str):
        """Set the status message."""
        self.status_label.setText(status)
