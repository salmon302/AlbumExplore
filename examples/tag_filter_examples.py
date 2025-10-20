"""
Example demonstrating the new tag filter system with AND/OR logic.

This script shows how to use the TagFilterState and TagFilterGroup
classes to create complex tag-based queries.
"""

from albumexplore.tags.filters import TagFilterState, TagFilterGroup, SavedQuery


def example_basic_and_filter():
    """Example: Albums that are both Progressive Metal AND Instrumental"""
    print("=" * 60)
    print("Example 1: Basic AND Filter")
    print("=" * 60)
    
    state = TagFilterState()
    group = state.add_group()
    group.add_tag("Progressive Metal")
    group.add_tag("Instrumental")
    
    print(f"Filter: {state.get_filter_summary()}")
    print()
    
    # Test some albums
    test_albums = [
        {"name": "Album A", "tags": {"Progressive Metal", "Instrumental", "Epic"}},
        {"name": "Album B", "tags": {"Progressive Metal", "Vocals"}},
        {"name": "Album C", "tags": {"Death Metal", "Instrumental"}},
    ]
    
    for album in test_albums:
        matches = state.matches(album["tags"])
        print(f"  {album['name']}: {album['tags']}")
        print(f"    Matches: {'✓ YES' if matches else '✗ NO'}")
    print()


def example_multiple_groups_or():
    """Example: (Progressive Metal AND Instrumental) OR (Jazz AND Fusion)"""
    print("=" * 60)
    print("Example 2: Multiple Groups with OR Logic")
    print("=" * 60)
    
    state = TagFilterState()
    
    # Group 1: Progressive Metal AND Instrumental
    group1 = state.add_group()
    group1.name = "Prog Instrumental"
    group1.add_tag("Progressive Metal")
    group1.add_tag("Instrumental")
    
    # Group 2: Jazz AND Fusion
    group2 = state.add_group()
    group2.name = "Jazz Fusion"
    group2.add_tag("Jazz")
    group2.add_tag("Fusion")
    
    print(f"Filter: {state.get_filter_summary()}")
    print()
    
    # Test some albums
    test_albums = [
        {"name": "Album A", "tags": {"Progressive Metal", "Instrumental"}},
        {"name": "Album B", "tags": {"Jazz", "Fusion", "Smooth"}},
        {"name": "Album C", "tags": {"Progressive Metal", "Jazz"}},
        {"name": "Album D", "tags": {"Rock", "Alternative"}},
    ]
    
    for album in test_albums:
        matches = state.matches(album["tags"])
        print(f"  {album['name']}: {album['tags']}")
        print(f"    Matches: {'✓ YES' if matches else '✗ NO'}")
    print()


def example_with_exclusions():
    """Example: (Metal AND Female Vocals) but exclude Live albums"""
    print("=" * 60)
    print("Example 3: Filters with Exclusions")
    print("=" * 60)
    
    state = TagFilterState()
    
    # Include: Metal AND Female Vocals
    group = state.add_group()
    group.add_tag("Metal")
    group.add_tag("Female Vocals")
    
    # Exclude: Live and Compilation
    state.add_exclusion("Live")
    state.add_exclusion("Compilation")
    
    print(f"Filter: {state.get_filter_summary()}")
    print()
    
    # Test some albums
    test_albums = [
        {"name": "Album A", "tags": {"Metal", "Female Vocals", "Symphonic"}},
        {"name": "Album B", "tags": {"Metal", "Female Vocals", "Live"}},
        {"name": "Album C", "tags": {"Metal", "Female Vocals", "Compilation"}},
        {"name": "Album D", "tags": {"Metal", "Male Vocals"}},
    ]
    
    for album in test_albums:
        matches = state.matches(album["tags"])
        print(f"  {album['name']}: {album['tags']}")
        print(f"    Matches: {'✓ YES' if matches else '✗ NO'}")
    print()


def example_complex_query():
    """Example: Complex real-world query"""
    print("=" * 60)
    print("Example 4: Complex Real-World Query")
    print("=" * 60)
    print("Find: (Death Metal AND Technical) OR (Jazz AND Experimental)")
    print("Exclude: Live albums")
    print()
    
    state = TagFilterState()
    
    # Group 1: Death Metal AND Technical
    group1 = state.add_group()
    group1.name = "Technical Death Metal"
    group1.add_tag("Death Metal")
    group1.add_tag("Technical")
    
    # Group 2: Jazz AND Experimental
    group2 = state.add_group()
    group2.name = "Experimental Jazz"
    group2.add_tag("Jazz")
    group2.add_tag("Experimental")
    
    # Exclude live albums
    state.add_exclusion("Live")
    
    print(f"Filter: {state.get_filter_summary()}")
    print()
    
    # Test some albums
    test_albums = [
        {"name": "Obscura - Omnivium", "tags": {"Death Metal", "Technical", "Progressive"}},
        {"name": "Tigran Hamasyan - Mockroot", "tags": {"Jazz", "Experimental", "Fusion"}},
        {"name": "Death - Live in LA", "tags": {"Death Metal", "Technical", "Live"}},
        {"name": "Miles Davis - Kind of Blue", "tags": {"Jazz", "Modal"}},
        {"name": "Animals as Leaders", "tags": {"Progressive Metal", "Technical", "Instrumental"}},
    ]
    
    for album in test_albums:
        matches = state.matches(album["tags"])
        print(f"  {album['name']}:")
        print(f"    Tags: {album['tags']}")
        print(f"    Matches: {'✓ YES' if matches else '✗ NO'}")
    print()


def example_saved_query():
    """Example: Saving and loading a query"""
    print("=" * 60)
    print("Example 5: Saved Queries")
    print("=" * 60)
    
    # Create a filter
    state = TagFilterState()
    group = state.add_group()
    group.add_tag("Progressive Metal")
    group.add_tag("Instrumental")
    state.add_exclusion("Live")
    
    # Save it
    saved = SavedQuery(
        name="Prog Instrumentals",
        filter_state=state,
        description="Progressive metal instrumental albums, excluding live recordings"
    )
    
    print("Created saved query:")
    print(f"  Name: {saved.name}")
    print(f"  Description: {saved.description}")
    print(f"  Filter: {saved.filter_state.get_filter_summary()}")
    print()
    
    # Serialize to JSON
    json_data = saved.filter_state.to_json()
    print("Serialized to JSON:")
    print(json_data)
    print()
    
    # Restore from JSON
    restored_state = TagFilterState.from_json(json_data)
    print("Restored from JSON:")
    print(f"  Filter: {restored_state.get_filter_summary()}")
    print()


def example_legacy_migration():
    """Example: Migrating from legacy include/exclude system"""
    print("=" * 60)
    print("Example 6: Legacy Filter Migration")
    print("=" * 60)
    
    # Old system: simple include/exclude sets
    old_include = {"Metal", "Jazz", "Progressive"}
    old_exclude = {"Live", "Compilation"}
    
    print("Old system (implicit OR):")
    print(f"  Include: {old_include}")
    print(f"  Exclude: {old_exclude}")
    print()
    
    # Migrate with OR behavior (default - each tag in its own group)
    state_or = TagFilterState.from_legacy_filters(old_include, old_exclude)
    print("Migrated with OR behavior (default):")
    print(f"  {state_or.get_filter_summary()}")
    print(f"  Groups created: {len(state_or.groups)}")
    print()
    
    # Migrate with AND behavior (all tags in one group)
    state_and = TagFilterState.from_legacy_filters_as_and(old_include, old_exclude)
    print("Migrated with AND behavior (alternative):")
    print(f"  {state_and.get_filter_summary()}")
    print(f"  Groups created: {len(state_and.groups)}")
    print()
    
    # Test behavior difference
    test_album = {"Metal", "Epic"}
    print(f"Test album tags: {test_album}")
    print(f"  OR behavior matches: {'✓ YES' if state_or.matches(test_album) else '✗ NO'}")
    print(f"  AND behavior matches: {'✓ YES' if state_and.matches(test_album) else '✗ NO'}")
    print()


def example_tag_management():
    """Example: Managing tags across groups"""
    print("=" * 60)
    print("Example 7: Tag Management Operations")
    print("=" * 60)
    
    state = TagFilterState()
    
    # Create groups
    group1 = state.add_group()
    group1.name = "Heavy Metal"
    group1.add_tag("Metal")
    group1.add_tag("Heavy")
    
    group2 = state.add_group()
    group2.name = "Progressive"
    group2.add_tag("Progressive")
    
    print("Initial state:")
    print(f"  {state.get_filter_summary()}")
    print()
    
    # Find where a tag is used
    locations = state.get_tag_locations("Metal")
    print(f"Tag 'Metal' is used in:")
    print(f"  Groups: {locations['groups']}")
    print(f"  Excluded: {locations['excluded']}")
    print()
    
    # Move a tag between groups
    state.move_tag("Metal", group1.group_id, group2.group_id)
    print("After moving 'Metal' from Group 1 to Group 2:")
    print(f"  {state.get_filter_summary()}")
    print()
    
    # Check if group is empty
    print(f"Group 1 empty: {group1.is_empty()}")
    print(f"Group 2 empty: {group2.is_empty()}")
    print()


def main():
    """Run all examples"""
    examples = [
        example_basic_and_filter,
        example_multiple_groups_or,
        example_with_exclusions,
        example_complex_query,
        example_saved_query,
        example_legacy_migration,
        example_tag_management,
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"Error in {example_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
        print()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
