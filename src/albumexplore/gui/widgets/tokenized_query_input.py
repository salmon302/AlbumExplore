from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QMessageBox, QCompleter
from PyQt6.QtCore import pyqtSignal, QStringListModel, Qt


class TokenizedQueryInput(QWidget):
    """A compact tokenized query input with operator buttons.

    Emits `applyQuery(str)` when the user applies the query.
    """
    applyQuery = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_completer()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText('Advanced query (e.g. TagA AND (TagB OR "Tag C"))')
        self.query_input.setToolTip(
            'Enter boolean queries using:\n'
            '• AND - all tags must match\n'
            '• OR - any tag can match\n'
            '• NOT - exclude tags\n'
            '• ( ) - group operations\n'
            '• "Tag Name" - tags with spaces need quotes'
        )
        layout.addWidget(self.query_input)

        for op in ["AND", "OR", "NOT", "(", ")"]:
            btn = QPushButton(op)
            btn.setFixedWidth(40 if len(op) <= 3 else 50)
            btn.setToolTip(f"Insert {op} operator")
            btn.clicked.connect(lambda checked, o=op: self._insert_token(o))
            layout.addWidget(btn)

        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setToolTip("Check if query syntax is valid (Ctrl+Shift+V)")
        self.validate_btn.setShortcut("Ctrl+Shift+V")
        self.validate_btn.clicked.connect(self._validate)
        layout.addWidget(self.validate_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setToolTip("Apply this query to filter results (Ctrl+Return)")
        self.apply_btn.clicked.connect(self._apply)
        layout.addWidget(self.apply_btn)
        
        # Connect Return key to apply
        self.query_input.returnPressed.connect(self._apply)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear)
        layout.addWidget(self.clear_btn)

    def _insert_token(self, token: str):
        cur = self.query_input.cursorPosition()
        text = self.query_input.text()
        ins = f" {token} " if token.isalpha() else token
        new = text[:cur] + ins + text[cur:]
        self.query_input.setText(new)
        self.query_input.setFocus()
        self.query_input.setCursorPosition(cur + len(ins))

    def _validate(self):
        q = self.query_input.text().strip()
        if not q:
            QMessageBox.information(self, "Validate", "Query is empty")
            return
        try:
            # Defer heavy evaluation to caller; just try parsing here
            from ...search.query import parse_query, explain_query
            node = parse_query(q)
        except Exception as e:
            QMessageBox.critical(self, "Parse Error", f"Error parsing query:\n\n{e}\n\nTip: Use quotes for tags with spaces")
            return

        # Try to produce a brief explain using parent view's index if possible
        tag_index = {}
        all_ids = set()
        pv = getattr(self.parent(), 'parent', None)
        # parent of this widget should be TagFilterPanel; that panel's parent() is the TagExplorerView
        try:
            view = self.parent().parent()
            if view and hasattr(view, 'tag_to_album_nodes'):
                for tag, nodes in view.tag_to_album_nodes.items():
                    ids = {n.get('id') for n in nodes if n.get('id') is not None}
                    tag_index[tag] = ids
                    all_ids.update(ids)
        except Exception:
            pass

        try:
            explain = explain_query(q, tag_index, all_ids)
            # Show only top-level count in a message
            cnt = explain.get('count') if isinstance(explain, dict) else None
            if cnt is not None:
                QMessageBox.information(self, "Valid Query", 
                    f"✓ Query parsed successfully\n\n"
                    f"Would match: {cnt} albums")
            else:
                QMessageBox.information(self, "Valid Query", "✓ Query parsed successfully")
        except Exception as e:
            QMessageBox.information(self, "Parsed", 
                f"Query syntax is valid, but evaluation encountered an issue:\n\n{e}")


    def _apply(self):
        q = self.query_input.text().strip()
        if not q:
            QMessageBox.information(self, "Apply", "Query is empty")
            return
        self.applyQuery.emit(q)

    def _clear(self):
        self.query_input.clear()

    def _setup_completer(self):
        """Setup QCompleter for tag suggestions."""
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.model = QStringListModel()
        self.completer.setModel(self.model)
        self.query_input.setCompleter(self.completer)
        self.completer.activated.connect(self._on_completion_selected)

    def update_available_tags(self, tags: list):
        """Update the completer's tag list.

        This should be called by the parent panel when tag availability changes.
        """
        try:
            unique = sorted(set(tags))
            self.model.setStringList(unique)
        except Exception:
            pass

    def _on_completion_selected(self, text: str):
        """Insert the completed tag at the current cursor position."""
        cur = self.query_input.cursorPosition()
        txt = self.query_input.text()
        ins = text
        # If previous char isn't whitespace, add a space before
        if cur > 0 and not txt[cur-1].isspace():
            ins = ' ' + ins
        new = txt[:cur] + ins + txt[cur:]
        self.query_input.setText(new)
        self.query_input.setFocus()
        self.query_input.setCursorPosition(cur + len(ins))
