from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt

from ...search import query as query_mod
from ...search import api as search_api


class QueryEditorDialog(QDialog):
    """Simple Query Editor dialog for advanced boolean queries.

    Uses parent view's in-memory tag->album index when available for validation
    and explain previews.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Tag Query")
        self.setMinimumSize(650, 400)
        self.parent_view = parent
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e8e8e8;
                font-size: 11px;
            }
            QLineEdit, QTextEdit {
                background-color: #2d2d30;
                color: #e8e8e8;
                border: 1px solid #3f3f46;
                border-radius: 3px;
                padding: 6px;
                font-size: 11px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4a7ba7;
            }
            QPushButton {
                background-color: #2d2d30;
                color: #e8e8e8;
                border: 1px solid #3f3f46;
                border-radius: 3px;
                padding: 6px 16px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d3d40;
                border-color: #4a7ba7;
            }
            QPushButton:pressed {
                background-color: #4a7ba7;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title and instructions
        title = QLabel("Advanced Tag Query")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e8e8e8; margin-bottom: 8px;")
        layout.addWidget(title)
        
        label = QLabel("Enter boolean query using AND, OR, NOT operators with parentheses.\nExample: progressive AND (symphonic OR \"neo-prog\")")
        label.setStyleSheet("color: #b0b0b0; font-size: 10px; margin-bottom: 4px;")
        label.setWordWrap(True)
        layout.addWidget(label)

        # Query input with label
        input_label = QLabel("Query:")
        input_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(input_label)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Enter your boolean query here...")
        layout.addWidget(self.query_input)

        # Explain output with label
        explain_label = QLabel("Query Explanation:")
        explain_label.setStyleSheet("font-weight: bold; margin-top: 12px;")
        layout.addWidget(explain_label)
        
        self.explain_out = QTextEdit()
        self.explain_out.setReadOnly(True)
        self.explain_out.setMinimumHeight(150)
        self.explain_out.setPlaceholderText("Click 'Validate' to see query explanation and match counts...")
        layout.addWidget(self.explain_out)

        btn_layout = QHBoxLayout()
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self.on_validate)
        btn_layout.addWidget(self.validate_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.on_apply)
        btn_layout.addWidget(self.apply_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def set_query(self, q: str):
        self.query_input.setText(q)

    def on_validate(self):
        q = self.query_input.text().strip()
        if not q:
            QMessageBox.warning(self, "Empty Query", "Please enter a query to validate.")
            return

        # Try parse
        try:
            node = query_mod.parse_query(q)
        except Exception as e:
            self.explain_out.setPlainText(f"Parse error: {e}")
            return

        # Build local tag_index from parent view if available, else empty
        tag_index = {}
        all_ids = set()
        pv = getattr(self, 'parent_view', None)
        if pv is not None and hasattr(pv, 'tag_to_album_nodes'):
            for tag, nodes in pv.tag_to_album_nodes.items():
                ids = {n.get('id') for n in nodes if n.get('id') is not None}
                tag_index[tag] = ids
                all_ids.update(ids)

        try:
            explain = query_mod.explain_query(q, tag_index, all_ids)
            # pretty print explain
            import json

            self.explain_out.setPlainText(json.dumps(explain, indent=2))
        except Exception as e:
            self.explain_out.setPlainText(f"Evaluation error: {e}")

    def on_apply(self):
        q = self.query_input.text().strip()
        if not q:
            QMessageBox.warning(self, "Empty Query", "Please enter a query to apply.")
            return

        try:
            state = search_api.query_to_filter_state(q)
        except Exception as e:
            QMessageBox.warning(self, "Cannot convert query",
                                f"Query cannot be converted into filter groups: {e}\nYou can still keep this as an advanced-only query.")
            return

        # First try to use filter_panel attribute set directly on the dialog
        if hasattr(self, 'filter_panel') and self.filter_panel is not None:
            self.filter_panel.set_filter_state(state)
            QMessageBox.information(self, "Applied", "Advanced query converted and applied to filters.")
            self.accept()
            return

        # Fallback: Apply to parent view's filter panel if available
        pv = getattr(self, 'parent_view', None)
        if pv is not None and hasattr(pv, 'filter_panel') and pv.filter_panel is not None:
            pv.filter_panel.set_filter_state(state)
            QMessageBox.information(self, "Applied", "Advanced query converted and applied to filters.")
            self.accept()
            return

        # Fallback: store in dialog and close
        QMessageBox.information(self, "Converted", "Query converted but no filter panel found to apply to.")
        self.accept()
