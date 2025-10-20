# TagChip component README

Short description:
A small, reusable TagChip + TagChipBar UI pattern for interactive tag filters.
Provided as framework-agnostic Python stubs and a React TSX example/demo.

Props (contract)
- TagChip props: { tagName: string, count?: number, operator?: 'AND'|'NOT', removable?: boolean }
- TagChipBar props: { chips: TagChipData[], onChange?: (chips)=>void }
- TagChipData: { id: string, name: string, operator: 'AND'|'NOT', count: number }

Events
- chipToggled(tagName, newOperator)
- chipRemoved(tagName)
- chipDragStart(tagName)

Keyboard shortcuts / interactions
- Left / Right arrow: move focus between chips (handled by TagChipBar container)
- Enter / Space: toggle chip operator between AND (include) and NOT (exclude)
- Delete / Backspace: remove the focused chip

Accessibility notes
- Each chip exposes role="button" and aria-pressed to surface operator state (NOT => pressed)
- Chips are keyboard-focusable (tabindex=0) and show visible focus outlines
- Exclude drop-zone uses role="region" and aria-label for screen-reader discovery

Files (examples)
- Python widget stub: src/albumexplore/gui/widgets/tag_chip.py
- Python container: src/albumexplore/gui/views/tag_explorer.py
- React component (example): src/albumexplore/gui/widgets/TagChip.tsx
- React demo/story: src/albumexplore/gui/views/TagExplorer.tsx
- Unit tests (python): tests/gui/test_tag_chip.py

Runnable demo / story
- TagExplorerDemo is exported from src/albumexplore/gui/views/TagExplorer.tsx and provides a minimal runnable example showing chips being added/removed/toggled and a drop zone to mark chips as NOT.
