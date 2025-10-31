"""Dialog to present suggested tag relationship candidates and allow curator to accept them.

The dialog accepts a list of suggestion tuples (source, target, sim, direct_count)
and allows the user to pick relation type and weight for each. Accepted suggestions
are appended to the specified mappings file (default: data/tag_relationships.yml).
"""
from __future__ import annotations

import os
import logging
import json
from typing import List, Tuple, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from albumexplore.similarity import manual as manual_mod

logger = logging.getLogger(__name__)


DEFAULT_PATH = os.path.join(os.getcwd(), "data", "tag_relationships.yml")


class ManualSuggestionDialog(QDialog):
    def __init__(self, parent=None, session=None, suggestions: Optional[List[Tuple[str, str, float, int]]] = None, mappings_path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Suggested Tag Relationships")
        self.resize(800, 500)
        self.session = session
        self.suggestions = suggestions or []
        self.mappings_path = mappings_path or DEFAULT_PATH
        self.saved_path: Optional[str] = None

        self.layout = QVBoxLayout(self)

        self.layout.addWidget(QLabel(f"Found {len(self.suggestions)} candidate pairs"))

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Select", "Source", "Target", "Sim", "Cooccur", "Type / Weight"])
        self.table.setRowCount(len(self.suggestions))

        for r, (a, b, sim, direct) in enumerate(self.suggestions):
            # Select checkbox
            sel = QTableWidgetItem()
            sel.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            sel.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(r, 0, sel)

            self.table.setItem(r, 1, QTableWidgetItem(a))
            self.table.setItem(r, 2, QTableWidgetItem(b))
            self.table.setItem(r, 3, QTableWidgetItem(f"{sim:.3f}"))
            self.table.setItem(r, 4, QTableWidgetItem(str(direct)))

            # Type combobox and weight spinner combined into a small widget replacement
            type_cb = QComboBox()
            type_cb.addItems(["related", "close_related", "synonym", "historic", "parent_child", "influence"]) 
            weight_sb = QDoubleSpinBox()
            weight_sb.setRange(0.0, 1.0)
            weight_sb.setSingleStep(0.05)
            # Default weight based on sim
            weight_sb.setValue(min(0.95, max(0.2, sim)))

            # Put both widgets side-by-side in a small layout container
            from PyQt6.QtWidgets import QWidget, QHBoxLayout

            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(type_cb)
            hl.addWidget(weight_sb)
            self.table.setCellWidget(r, 5, w)

        self.layout.addWidget(self.table)

        btns = QHBoxLayout()
        self.apply_btn = QPushButton("Append selected to mappings")
        self.apply_btn.clicked.connect(self._apply_selected)
        btns.addWidget(self.apply_btn)

        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.clicked.connect(self._save_as)
        btns.addWidget(self.save_as_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        btns.addWidget(self.close_btn)

        self.layout.addLayout(btns)

    def _gather_selected(self):
        out = []
        for r in range(self.table.rowCount()):
            sel = self.table.item(r, 0)
            if sel is None or sel.checkState() != Qt.CheckState.Checked:
                continue
            src = self.table.item(r, 1).text().strip().lower()
            tgt = self.table.item(r, 2).text().strip().lower()
            # get widgets
            cell_w = self.table.cellWidget(r, 5)
            if cell_w is None:
                rtype = "related"
                weight = 0.75
            else:
                cb = cell_w.findChild(QComboBox)
                sb = cell_w.findChild(QDoubleSpinBox)
                rtype = cb.currentText() if cb else "related"
                weight = float(sb.value()) if sb else 0.75
            out.append((src, tgt, rtype, weight))
        return out

    def _apply_selected(self):
        sel = self._gather_selected()
        if not sel:
            QMessageBox.information(self, "No selection", "No candidates selected to append.")
            return

        # Load existing mappings if present
        existing = {}
        if os.path.exists(self.mappings_path):
            try:
                existing = manual_mod.load_relationships(self.mappings_path)
            except Exception:
                logger.exception("Failed to load existing mappings; will start fresh")

        # Merge
        for src, tgt, rtype, weight in sel:
            entry = {"tag": tgt, "type": rtype, "weight": float(weight)}
            existing.setdefault(src, []).append(entry)

        # Write back using yaml if available, otherwise JSON
        yaml = None
        try:
            import yaml as _yaml  # type: ignore
            yaml = _yaml
        except Exception:
            yaml = None

        try:
            if yaml is not None and self.mappings_path.lower().endswith(('.yml', '.yaml')):
                with open(self.mappings_path, 'w', encoding='utf-8') as fh:
                    yaml.safe_dump(existing, fh, sort_keys=True, allow_unicode=True)
            else:
                # fallback to json
                with open(self.mappings_path, 'w', encoding='utf-8') as fh:
                    json.dump(existing, fh, indent=2, ensure_ascii=False)
            self.saved_path = self.mappings_path
            QMessageBox.information(self, "Saved", f"Appended {len(sel)} entries to {self.mappings_path}")
            self.accept()
        except Exception as e:
            logger.exception("Failed to save mappings")
            QMessageBox.critical(self, "Save Error", f"Failed to save mappings: {e}")

    def _save_as(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Save mappings as", self.mappings_path, "YAML Files (*.yml *.yaml);;JSON Files (*.json)")
        if not fn:
            return
        self.mappings_path = fn
        QMessageBox.information(self, "Path updated", f"Will save to: {self.mappings_path}")
