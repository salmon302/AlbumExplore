// src/albumexplore/gui/views/TagExplorer.tsx
// React TagChipBar / TagExplorer demo and container.
//
// Contract (copy into implemented files):
// - TagChipBar props: { chips: TagChipData[], onChange: (chips)=>void }
// - TagChipData: { id: string, name: string, operator: 'AND'|'NOT', count: number }
//
// Minimal, accessible TagChipBar with keyboard support and drag/drop reordering.
// Keep CSS minimal and inline for the demo.

import React, { useCallback, useEffect, useRef, useState } from 'react';
import TagChip from '../widgets/TagChip';

export type Operator = 'AND' | 'NOT';

export interface TagChipData {
    id: string;
    name: string;
    operator: Operator;
    count: number;
}

export interface TagChipBarProps {
    chips: TagChipData[];
    onChange?: (chips: TagChipData[]) => void;
}

/**
 * TagChipBar
 * - renders chips using TagChip
 * - supports keyboard navigation (Left/Right), Delete/Backspace to remove,
 *   Enter/Space to toggle operator
 * - supports drag-and-drop reordering and dropping to the Exclude zone
 */
export function TagChipBar({ chips: initialChips, onChange }: TagChipBarProps) {
    const [chips, setChips] = useState<TagChipData[]>(initialChips || []);
    const [focusedIndex, setFocusedIndex] = useState<number | null>(chips.length ? 0 : null);
    const dragIndexRef = useRef<number | null>(null);
    const chipRefs = useRef<Array<HTMLDivElement | null>>([]);

    useEffect(() => {
        setChips(initialChips || []);
    }, [initialChips]);

    useEffect(() => {
        if (onChange) onChange(chips.slice());
    }, [chips, onChange]);

    // Helpers
    const updateChips = useCallback((next: TagChipData[]) => {
        setChips(next.slice());
    }, []);

    const handleToggled = useCallback((tagName: string, newOperator: Operator) => {
        updateChips(chips.map(c => (c.name === tagName ? { ...c, operator: newOperator } : c)));
    }, [chips, updateChips]);

    const handleRemoved = useCallback((tagName: string) => {
        const filtered = chips.filter(c => c.name !== tagName);
        updateChips(filtered);
        setFocusedIndex(prev => {
            if (filtered.length === 0) return null;
            if (prev === null) return 0;
            return Math.min(prev, filtered.length - 1);
        });
    }, [chips, updateChips]);

    const handleDragStart = useCallback((tagName: string) => {
        const idx = chips.findIndex(c => c.name === tagName);
        dragIndexRef.current = idx >= 0 ? idx : null;
    }, [chips]);

    const onDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    const onDropOnBar = (e: React.DragEvent, toIndex: number | null = null) => {
        e.preventDefault();
        const from = dragIndexRef.current;
        if (from === null || from < 0) return;
        const to = toIndex === null ? chips.length - 1 : toIndex;
        if (from === to) return;
        const next = chips.slice();
        const [moved] = next.splice(from, 1);
        // If dropped at end (toIndex null), append
        const insertAt = toIndex === null ? next.length : to;
        next.splice(insertAt, 0, moved);
        dragIndexRef.current = null;
        setChips(next);
    };

    const onDropOnExclude = (e: React.DragEvent) => {
        e.preventDefault();
        const from = dragIndexRef.current;
        if (from === null || from < 0) return;
        const next = chips.slice();
        next[from] = { ...next[from], operator: 'NOT' };
        dragIndexRef.current = null;
        setChips(next);
    };

    // Keyboard handling at the bar level for Left/Right focus movement
    const handleContainerKeyDown = (e: React.KeyboardEvent) => {
        if (chips.length === 0) return;
        if (focusedIndex === null) {
            setFocusedIndex(0);
            return;
        }
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            setFocusedIndex(Math.max(0, focusedIndex - 1));
            chipRefs.current[Math.max(0, focusedIndex - 1)]?.focus();
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            setFocusedIndex(Math.min(chips.length - 1, focusedIndex + 1));
            chipRefs.current[Math.min(chips.length - 1, focusedIndex + 1)]?.focus();
        } else if (e.key === 'Delete' || e.key === 'Backspace') {
            e.preventDefault();
            const target = chips[focusedIndex];
            handleRemoved(target.name);
            // focus will be adjusted by handleRemoved
            setTimeout(() => {
                if (focusedIndex !== null && chipRefs.current[focusedIndex]) {
                    chipRefs.current[focusedIndex]?.focus();
                } else if (chipRefs.current[0]) {
                    chipRefs.current[0].focus();
                }
            }, 0);
        } else if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            const target = chips[focusedIndex];
            handleToggled(target.name, target.operator === 'AND' ? 'NOT' : 'AND');
        }
    };

    // Refs assignment helper
    const setChipRef = (el: HTMLDivElement | null, idx: number) => {
        chipRefs.current[idx] = el;
    };

    // Render
    return (
        <div>
            <div
                role="list"
                aria-label="Active tag filters"
                tabIndex={0}
                onKeyDown={handleContainerKeyDown}
                style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', minHeight: 40 }}
                onDragOver={onDragOver}
                onDrop={(e) => onDropOnBar(e, null)}
            >
                {chips.map((c, idx) => (
                    <div
                        key={c.id}
                        ref={el => setChipRef(el, idx)}
                        style={{ outline: focusedIndex === idx ? '2px solid #4c9aff' : 'none', borderRadius: 4 }}
                    >
                        <TagChip
                            tagName={c.name}
                            count={c.count}
                            operator={c.operator}
                            removable={true}
                            onToggled={(name, nextOp) => handleToggled(name, nextOp as Operator)}
                            onRemoved={() => handleRemoved(c.name)}
                            onDragStart={() => handleDragStart(c.name)}
                        />
                    </div>
                ))}
            </div>

            {/* Exclude drop zone */}
            <div
                onDragOver={(e) => { e.preventDefault(); }}
                onDrop={onDropOnExclude}
                role="region"
                aria-label="Exclude drop zone"
                style={{
                    marginTop: 12,
                    padding: 8,
                    border: '1px dashed #ccc',
                    borderRadius: 6,
                    color: '#555',
                }}
            >
                Drop here to exclude (NOT)
            </div>
        </div>
    );
}

/**
 * Small demo component that manages an in-memory filter model and renders the bar.
 * This can act as a small runnable example/story.
 */
export function TagExplorerDemo() {
    const sample: TagChipData[] = [
        { id: '1', name: 'rock', operator: 'AND', count: 123 },
        { id: '2', name: 'psychedelic', operator: 'AND', count: 45 },
        { id: '3', name: 'experimental', operator: 'NOT', count: 8 },
    ];

    const [filters, setFilters] = useState<TagChipData[]>(sample);

    return (
        <div>
            <h4>Tag Explorer (demo)</h4>
            <TagChipBar
                chips={filters}
                onChange={(next) => {
                    setFilters(next);
                    // In a real app, you would sync this to your client-side filter model
                    // or emit an event to the rest of the app.
                }}
            />
            <pre style={{ marginTop: 12 }}>{JSON.stringify(filters, null, 2)}</pre>
        </div>
    );
}

export default TagChipBar;