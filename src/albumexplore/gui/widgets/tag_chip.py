# src/albumexplore/gui/widgets/tag_chip.py
"""Framework-agnostic TagChip widget stub.

Component contract:
- TagChip props: { tagName: string, count?: number, operator?: 'AND'|'NOT', removable?: boolean }
- Events: chipToggled(tagName, newOperator), chipRemoved(tagName), chipDragStart(tagName)
- TagChipBar props: { chips: TagChipData[], onChange: (chips)=>void }
- TagChipData: { id: string, name: string, operator: 'AND'|'NOT', count: number }

This file implements a minimal, testable, non-GUI TagChip class that can be
used by Python GUI frameworks or tests to simulate behavior.

Notes on compatibility:
- The TypeScript/TSX TagChip exposes an "operator" ('AND'|'NOT') and visual
  state where "NOT" is conceptually selected/excluded. To be convenient for
  Python views/tests we expose both operator and a boolean "selected" property
  (selected == operator == "NOT"). toggle_selected()/set_selected() are
  provided as aliases to toggle_operator()/set operator accordingly.
- We keep the constructor and callback names used by existing tests:
  tagName, count, operator, removable, on_toggled, on_removed, on_drag_start.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any

@dataclass
class TagChipData:
    """Lightweight DTO representing chip data.

    Kept as a simple dataclass so other components (e.g. TagChipBar) can
    construct and copy instances as needed. Validation ensures sensible
    defaults.
    """
    id: str
    name: str
    operator: str = "AND"
    count: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("TagChipData.id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("TagChipData.name must be a non-empty string")
        if self.operator not in ("AND", "NOT"):
            self.operator = "AND"
        if not isinstance(self.count, int) or self.count < 0:
            raise ValueError("TagChipData.count must be an int >= 0")

class TagChip:
    """TagChip model/controller for tests and light-weight Python views.

    Public API (kept compatible with tests and the TSX component):
      - Constructor: TagChip(tagName: str, count: int = 0, operator: str = "AND",
                             removable: bool = True, on_toggled=None, on_removed=None, on_drag_start=None)
      - Properties: label (alias for tagName), count, operator, selected (bool)
      - Methods: toggle_operator(), set_selected(bool), toggle_selected(),
                 remove(), drag_start(), key_press(key), aria_attrs(), to_dict()
      - Callback registration: supply callbacks via constructor or set attributes:
        on_toggled, on_removed, on_drag_start, on_click

    Minimal validation is applied to inputs (non-empty tagName, non-negative count).
    """
    def __init__(
        self,
        tagName: str,
        count: int = 0,
        operator: str = "AND",
        removable: bool = True,
        on_toggled: Optional[Callable[[str, str], None]] = None,
        on_removed: Optional[Callable[[str], None]] = None,
        on_drag_start: Optional[Callable[[str], None]] = None,
        on_click: Optional[Callable[[str], None]] = None,
    ) -> None:
        # Input validation
        if not isinstance(tagName, str) or not tagName:
            raise ValueError("tagName must be a non-empty string")
        if not isinstance(count, int) or count < 0:
            raise ValueError("count must be an int >= 0")
        if operator not in ("AND", "NOT"):
            operator = "AND"

        self.tagName: str = tagName
        self._count: int = count
        self.operator: str = operator
        self.removable: bool = removable

        # Event callbacks (may be set/overridden after construction)
        self.on_toggled: Optional[Callable[[str, str], None]] = on_toggled
        self.on_removed: Optional[Callable[[str], None]] = on_removed
        self.on_drag_start: Optional[Callable[[str], None]] = on_drag_start
        self.on_click: Optional[Callable[[str], None]] = on_click

        # Transient UI state for tests
        self.focused: bool = False

    # Properties
    @property
    def label(self) -> str:
        """Alias for the tag name (keeps parity with other widget APIs)."""
        return self.tagName

    @label.setter
    def label(self, value: str) -> None:
        if not isinstance(value, str) or not value:
            raise ValueError("label must be a non-empty string")
        self.tagName = value

    @property
    def count(self) -> int:
        return self._count

    @count.setter
    def count(self, value: int) -> None:
        if not isinstance(value, int) or value < 0:
            raise ValueError("count must be an int >= 0")
        self._count = value

    @property
    def selected(self) -> bool:
        """Boolean view over the operator: selected == operator == 'NOT'."""
        return self.operator == "NOT"

    @selected.setter
    def selected(self, value: bool) -> None:
        self.set_selected(bool(value))

    # Core behavior
    def toggle_operator(self) -> None:
        """Toggle operator between 'AND' and 'NOT' and emit on_toggled."""
        self.operator = "NOT" if self.operator == "AND" else "AND"
        if self.on_toggled:
            # match TSX signature: onToggled(tagName, newOperator)
            self.on_toggled(self.tagName, self.operator)

    # convenience aliases to match a boolean-centric API
    def toggle_selected(self) -> None:
        """Alias to toggle operator using boolean semantics."""
        self.toggle_operator()

    def set_selected(self, value: bool) -> None:
        """Set selected boolean which maps to operator value."""
        desired_op = "NOT" if value else "AND"
        if self.operator != desired_op:
            self.operator = desired_op
            if self.on_toggled:
                self.on_toggled(self.tagName, self.operator)

    def remove(self) -> None:
        """Request removal; respects the removable flag and emits on_removed."""
        if not self.removable:
            return
        if self.on_removed:
            self.on_removed(self.tagName)

    def drag_start(self) -> None:
        """Simulate drag start event for tests."""
        if self.on_drag_start:
            self.on_drag_start(self.tagName)

    def click(self) -> None:
        """Simulate click event; primarily for view tests that attach on_click."""
        if self.on_click:
            self.on_click(self.tagName)

    def key_press(self, key: str) -> None:
        """Handle keyboard actions used by tests.

        Keys:
          - Enter / Space -> toggle operator
          - Delete / Backspace -> remove
        """
        if key in ("Enter", " "):
            self.toggle_operator()
        elif key in ("Delete", "Backspace"):
            self.remove()

    def focus(self) -> None:
        self.focused = True

    def blur(self) -> None:
        self.focused = False

    # Helpers
    def aria_attrs(self) -> Dict[str, Any]:
        """Return minimal accessibility attributes similar to TSX output.

        Note: returns Python primitives to be serializable in tests.
        """
        return {
            "role": "button",
            "aria-pressed": self.operator == "NOT",
            "tabindex": 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return a small serializable representation for tests/views.

        Uses 'label' and 'count' keys to be framework-agnostic.
        """
        return {"label": self.label, "count": self.count, "selected": self.selected}