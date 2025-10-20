// src/albumexplore/gui/widgets/TagChip.tsx
// React/TSX TagChip component implemented to mirror the Python TagChip model
// (src/albumexplore/gui/widgets/tag_chip.py). Small, dependency-free component.

import React, { MouseEvent } from 'react';

export interface TagChipProps {
    label: string;
    count?: number;
    selected?: boolean;
    // Called when the chip area is clicked. Receives the original mouse event so
    // parent can inspect modifier keys (Ctrl/Shift/Meta) for multi-select behavior.
    onClick?: (e?: MouseEvent<HTMLDivElement>) => void;
    onToggle?: (selected: boolean) => void;
    onRemove?: () => void;
    // Optional preview callbacks for hover-based previews
    onPreview?: () => void;
    onPreviewEnd?: () => void;
    // Optional generic select callback that receives modifier key state.
    onSelect?: (modifiers: { ctrlKey: boolean; shiftKey: boolean; metaKey: boolean; altKey: boolean; }) => void;
}

// Exported helper to provide a serializable representation similar to Python's to_dict()
export function toDict(props: TagChipProps) {
    const label = props.label && props.label.length > 0 ? props.label : '<empty>';
    const rawCount = typeof props.count === 'number' ? props.count : 0;
    const count = rawCount < 0 ? 0 : rawCount;
    const selected = !!props.selected;
    return { label, count, selected };
}

// Functional component
export const TagChip: React.FC<TagChipProps> = ({
    label,
    count = 0,
    selected = false,
    onClick,
    onToggle,
    onRemove,
    onPreview,
    onPreviewEnd,
    onSelect,
}) => {
    // Input coercion to mirror Python validation: placeholder for empty label, clamp negative counts
    const displayLabel = label && label.length > 0 ? label : '<empty>';
    const displayCount = count < 0 ? 0 : count;

    // Toggle selection and call onToggle with new boolean (mirrors toggle_operator -> operator mapping)
    function handleToggle(e?: React.MouseEvent<HTMLElement> | React.KeyboardEvent<HTMLElement>) {
        if (e && 'stopPropagation' in e) {
            (e as React.MouseEvent<HTMLElement>).stopPropagation();
        }
        const next = !selected;
        onToggle && onToggle(next);
    }

    function handleRemove(e?: React.MouseEvent<HTMLElement> | React.KeyboardEvent<HTMLElement>) {
        if (e && 'stopPropagation' in e) {
            (e as React.MouseEvent<HTMLElement>).stopPropagation();
        }
        onRemove && onRemove();
    }

    function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
        // Support Enter/Space to toggle selection. If a modifier is held, forward
        // the modifier info to the optional onSelect callback.
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            if (onSelect) {
                onSelect({ ctrlKey: e.ctrlKey, shiftKey: e.shiftKey, metaKey: e.metaKey, altKey: e.altKey });
            } else {
                handleToggle(e);
            }
        } else if (e.key === 'Delete' || e.key === 'Backspace') {
            e.preventDefault();
            handleRemove(e);
        }
    }

    return (
        <div
            role="button"
            aria-pressed={selected}
            tabIndex={0}
            onClick={(e: React.MouseEvent<HTMLDivElement>) => {
                e.stopPropagation();
                // Inform parent of the raw click (so it can inspect modifier keys)
                onClick && onClick(e);
                // Also forward a simplified modifiers object for convenience
                onSelect && onSelect({ ctrlKey: e.ctrlKey, shiftKey: e.shiftKey, metaKey: e.metaKey, altKey: e.altKey });
            }}
            onMouseEnter={() => {
                onPreview && onPreview();
            }}
            onMouseLeave={() => {
                onPreviewEnd && onPreviewEnd();
            }}
            onKeyDown={handleKeyDown}
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 8px',
                borderRadius: 16,
                border: '1px solid #ccc',
                background: selected ? '#ffecec' : '#f2f4f7',
                cursor: 'pointer',
                outline: 'none',
                userSelect: 'none',
            }}
        >
            <span style={{ fontSize: 13 }}>{displayLabel}</span>

            <span
                aria-hidden
                style={{
                    minWidth: 20,
                    height: 18,
                    lineHeight: '18px',
                    textAlign: 'center',
                    borderRadius: 9,
                    background: '#ddd',
                    fontSize: 12,
                }}
            >
                {displayCount}
            </span>

            <button
                type="button"
                aria-label={selected ? 'Operator: NOT (toggle)' : 'Operator: AND (toggle)'}
                onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                    e.stopPropagation();
                    handleToggle(e as unknown as React.MouseEvent<HTMLElement>);
                }}
                style={{
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    padding: 4,
                    fontSize: 12,
                }}
            >
                {selected ? 'NOT' : 'AND'}
            </button>

            <button
                type="button"
                aria-label={`Remove ${displayLabel}`}
                onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                    e.stopPropagation();
                    handleRemove(e as unknown as React.MouseEvent<HTMLElement>);
                }}
                style={{
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    padding: 4,
                    fontSize: 12,
                }}
            >
                ✕
            </button>
        </div>
    );
};

export default TagChip;