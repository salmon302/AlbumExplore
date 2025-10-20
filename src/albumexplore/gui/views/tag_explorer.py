# src/albumexplore/gui/views/tag_explorer.py
\"\"\"TagChipBar container and example in-memory filter model.

Component contract:
- TagChip props: { tagName: string, count?: number, operator?: 'AND'|'NOT', removable?: boolean }
- Events: chipToggled(tagName, newOperator), chipRemoved(tagName), chipDragStart(tagName)
- TagChipBar props: { chips: TagChipData[], onChange: (chips)=>void }
- TagChipData: { id: string, name: string, operator: 'AND'|'NOT', count: number }

This file implements a minimal TagChipBar that manages TagChipData entries,
handles keyboard navigation and reordering, and emits on_change when the
chips collection mutates. It is framework-agnostic and suitable for unit tests.
\"\"\"

from typing import Callable, List, Optional
from dataclasses import dataclass
from src.albumexplore.gui.widgets.tag_chip import TagChipData

class TagChipBar:
    \"\"\"Container for TagChipData items.

    Props:
      chips: List[TagChipData]
      on_change: Optional[Callable[[List[TagChipData]], None]]

    Keyboard:
      Left/Right move focus between chips.
      Delete/Backspace removes focused chip.
      Enter/Space toggles operator on focused chip.
    \"\"\"
    def __init__(self, chips: Optional[List[TagChipData]] = None,
                 on_change: Optional[Callable[[List[TagChipData]], None]] = None):
        self.chips: List[TagChipData] = chips[:] if chips else []
        self.on_change = on_change
        self.focus_index: Optional[int] = 0 if self.chips else None

    def emit_change(self):
        if self.on_change:
            # pass a shallow copy to avoid external mutation
            self.on_change([TagChipData(c.id, c.name, c.operator, c.count) for c in self.chips])

    def add_chip(self, chip: TagChipData):
        self.chips.append(chip)
        if self.focus_index is None:
            self.focus_index = 0
        self.emit_change()

    def remove_chip_by_id(self, chip_id: str):
        idx = next((i for i,c in enumerate(self.chips) if c.id == chip_id), None)
        if idx is None:
            return
        del self.chips[idx]
        # adjust focus
        if not self.chips:
            self.focus_index = None
        else:
            self.focus_index = min(idx, len(self.chips)-1)
        self.emit_change()

    def toggle_operator_by_id(self, chip_id: str):
        for c in self.chips:
            if c.id == chip_id:
                c.operator = \"NOT\" if c.operator == \"AND\" else \"AND\"
                self.emit_change()
                return

    def move_chip(self, from_index: int, to_index: int):
        if from_index < 0 or from_index >= len(self.chips):
            return
        to_index = max(0, min(to_index, len(self.chips)-1))
        chip = self.chips.pop(from_index)
        self.chips.insert(to_index, chip)
        # update focus if needed
        if self.focus_index == from_index:
            self.focus_index = to_index
        elif self.focus_index is not None:
            # shift focus index to account for the moved element
            if from_index < self.focus_index <= to_index:
                self.focus_index -= 1
            elif to_index <= self.focus_index < from_index:
                self.focus_index += 1
        self.emit_change()

    def drop_to_exclude(self, chip_id: str):
        for c in self.chips:
            if c.id == chip_id:
                c.operator = \"NOT\"
                self.emit_change()
                return

    # Keyboard helpers
    def focus_left(self):
        if self.focus_index is None or not self.chips:
            return
        self.focus_index = max(0, self.focus_index - 1)

    def focus_right(self):
        if self.focus_index is None or not self.chips:
            return
        self.focus_index = min(len(self.chips)-1, self.focus_index + 1)

    def key_press_on_focused(self, key: str):
        \"\"\"Simulate keyboard action for the focused chip.
        Keys: 'Left','Right','Enter',' ','Delete','Backspace'
        \"\"\"
        if self.focus_index is None:
            return
        if key == \"Left\":
            self.focus_left()
        elif key == \"Right\":
            self.focus_right()
        elif key in (\"Enter\",\" \"):
            chip = self.chips[self.focus_index]
            self.toggle_operator_by_id(chip.id)
        elif key in (\"Delete\",\"Backspace\"):
            chip = self.chips[self.focus_index]
            self.remove_chip_by_id(chip.id)

    def to_dict(self):
        return [ {\"id\": c.id, \"name\": c.name, \"operator\": c.operator, \"count\": c.count} for c in self.chips ]

# Example in-memory filter model used by the demo
class InMemoryFilterModel:
    \"\"\"Simple client-side filter state to be used in demos/tests.\"\"\"
    def __init__(self):
        self.filters: List[TagChipData] = []

    def set_filters(self, chips: List[TagChipData]):
        self.filters = chips[:]  # copy

    def apply_change(self, chips: List[TagChipData]):
        # For demo, replace filters wholesale
        self.set_filters(chips)

    def to_dict(self):
        return [ {\"id\": c.id, \"name\": c.name, \"operator\": c.operator, \"count\": c.count} for c in self.filters ]