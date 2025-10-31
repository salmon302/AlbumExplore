"""Simple YAML editor dialog for manual tag mappings.

This dialog provides a lightweight text-based editor for the manual mapping
YAML file. It intentionally avoids building a full table editor to keep the
implementation small and robust. Users can load/save the file and press
Validate to run the same validation used by the app.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox

from albumexplore.similarity import manual as manual_mod

logger = logging.getLogger(__name__)


DEFAULT_PATH = os.path.join(os.getcwd(), "data", "tag_relationships.yml")


class ManualMappingsEditor(QDialog):
    """A minimal text-editor dialog for manual mapping files (YAML/JSON/CSV).

    The editor allows loading a file into an editable text area and saving it
    back. The Validate button parses the current text via the loader to ensure
    the content is syntactically and semantically valid (normalized to mapping).
    """

    def __init__(self, parent=None, path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Manual Tag Mappings Editor")
        self.resize(800, 600)
        self.path = path or DEFAULT_PATH

        self.layout = QVBoxLayout(self)

        self.info_label = QLabel(f"Editing: {self.path}")
        self.layout.addWidget(self.info_label)

        self.text = QTextEdit()
        self.layout.addWidget(self.text)

        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("Load file")
        self.load_btn.clicked.connect(self.load_file_dialog)
        btn_row.addWidget(self.load_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_file)
        btn_row.addWidget(self.save_btn)

        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self.validate_current)
        btn_row.addWidget(self.validate_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)

        self.layout.addLayout(btn_row)

        # Try to load default file content if exists
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self.text.setPlainText(fh.read())
            except Exception:
                logger.exception("Failed to read default mappings file")

    def load_file_dialog(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open mappings file", os.getcwd(), "All Files (*.*);;YAML Files (*.yml *.yaml);;JSON Files (*.json);;CSV Files (*.csv)")
        if not fn:
            return
        try:
            with open(fn, "r", encoding="utf-8") as fh:
                self.text.setPlainText(fh.read())
            self.path = fn
            self.info_label.setText(f"Editing: {self.path}")
        except Exception as e:
            logger.exception("Failed to load mappings file")
            QMessageBox.critical(self, "Load Error", f"Failed to load file: {e}")

    def save_file(self):
        # Save current text to self.path (confirm overwrite if exists and not default)
        if not self.path:
            fn, _ = QFileDialog.getSaveFileName(self, "Save mappings file", DEFAULT_PATH, "YAML Files (*.yml *.yaml);;JSON Files (*.json);;CSV Files (*.csv)")
            if not fn:
                return
            self.path = fn

        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(self.text.toPlainText())
            QMessageBox.information(self, "Saved", f"Saved mappings to {self.path}")
        except Exception as e:
            logger.exception("Failed to save mappings file")
            QMessageBox.critical(self, "Save Error", f"Failed to save file: {e}")

    def validate_current(self):
        """Validate the YAML/JSON/CSV content currently in the editor using the loader."""
        tmp = self.text.toPlainText()
        # Try to write to a temp file and use loader to parse (loader expects a path)
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8") as fh:
                fh.write(tmp)
                tmpfn = fh.name
            # Attempt to load via loader which normalizes structure
            rels = manual_mod.load_relationships(tmpfn)
            # If load succeeded, show a success dialog with counts
            total_src = len(rels)
            total_rels = sum(len(v) for v in rels.values())
            QMessageBox.information(self, "Valid", f"Parsed relationships successfully. Sources: {total_src}, relations: {total_rels}")
        except Exception as e:
            logger.exception("Validation failed")
            QMessageBox.critical(self, "Validation Error", f"Validation failed: {e}")
        finally:
            try:
                os.unlink(tmpfn)
            except Exception:
                pass
