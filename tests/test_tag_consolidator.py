import pytest
import pandas as pd
from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer
from albumexplore.tags.analysis.tag_consolidator import (
	TagConsolidator, ConflictType, MergeConflict, MergePreview
)

@pytest.fixture
def test_data():
	return pd.DataFrame({
		'tags': [
			['metal', 'heavy-metal', 'heavy metal'],
			['black-metal', 'blackmetal', 'atmospheric'],
			['death-metal', 'deathmetal', 'technical'],
			['prog', 'progressive', 'prog-metal']
		]
	})

@pytest.fixture
def analyzer(test_data):
	return TagAnalyzer(test_data)

@pytest.fixture
def consolidator(analyzer):
	return TagConsolidator(analyzer)

def test_identify_merge_candidates(consolidator):
	candidates = consolidator.identify_merge_candidates(similarity_threshold=0.3)
	assert isinstance(candidates, dict)
	assert len(candidates) > 0
	
	# Check if similar tags are identified
	for tag, similar in candidates.items():
		assert isinstance(similar, list)
		if similar:
			assert isinstance(similar[0], tuple)
			assert similar[0][1] >= 0.3

def test_consolidation_rules(consolidator):
	# Add consolidation rules
	consolidator.add_consolidation_rule(pattern="heavy-metal", replacement="metal", min_similarity=0.8)
	consolidator.add_consolidation_rule(pattern="prog", replacement="progressive", min_similarity=0.7)
	
	# Identify candidates with rules
	candidates = consolidator.identify_merge_candidates(similarity_threshold=0.7)
	
	# Check if rules were applied
	assert "metal" in candidates
	metal_candidates = [tag for tag, _ in candidates["metal"]]
	assert "heavy-metal" in metal_candidates
	
	assert "progressive" in candidates
	prog_candidates = [tag for tag, _ in candidates["progressive"]]
	assert "prog" in prog_candidates


def test_conflict_detection(consolidator):
	# Test frequency mismatch conflict
	consolidator.add_consolidation_rule(pattern="prog", replacement="progressive", min_similarity=0.7)
	conflicts = consolidator.detect_conflicts(primary_tag="prog", tags_to_merge={"progressive"})
	freq_conflicts = [c for c in conflicts if c.type == ConflictType.FREQUENCY_MISMATCH]
	assert len(freq_conflicts) > 0
	
	# Test relationship conflict
	consolidator.add_consolidation_rule(pattern="black-metal", replacement="metal", min_similarity=0.8)
	conflicts = consolidator.detect_conflicts(primary_tag="metal", tags_to_merge={"black-metal"})
	rel_conflicts = [c for c in conflicts if c.type == ConflictType.RELATIONSHIP_CONFLICT]
	assert len(rel_conflicts) > 0


def test_merge_preview(consolidator):
	preview = consolidator.preview_merge("metal", {"heavy-metal", "heavy metal"})
	assert isinstance(preview, MergePreview)
	assert preview.primary_tag == "metal"
	assert preview.tags_to_merge == {"heavy-metal", "heavy metal"}
	assert preview.affected_albums > 0
	assert preview.frequency_change > 0

def test_forced_merge(consolidator):
	# Try merge that would normally conflict
	success = consolidator.queue_merge(primary_tag="prog", tags_to_merge={"progressive"}, force=False)
	assert not success  # Should fail due to conflicts
	
	# Force the merge
	success = consolidator.queue_merge(primary_tag="prog", tags_to_merge={"progressive"}, force=True)
	assert success  # Should succeed with force=True
	
	# Apply the forced merge
	applied = consolidator.apply_pending_merges()
	assert len(applied) == 1
	assert applied[0]["primary_tag"] == "prog"

def test_suggest_merges(consolidator):
	consolidator.identify_merge_candidates(similarity_threshold=0.5)
	suggestions = consolidator.suggest_merges(min_frequency=1)
	
	assert isinstance(suggestions, list)
	if suggestions:
		suggestion = suggestions[0]
		assert 'primary_tag' in suggestion
		assert 'candidate_tag' in suggestion
		assert 'similarity' in suggestion
		assert 'primary_freq' in suggestion
		assert 'candidate_freq' in suggestion

def test_queue_and_apply_merges(consolidator, analyzer):
	# Queue some merges
	success = consolidator.queue_merge(primary_tag='metal', tags_to_merge={'heavy-metal', 'heavy metal'})
	assert success
	
	# Apply the merges
	applied = consolidator.apply_pending_merges()
	assert isinstance(applied, list)
	assert len(applied) == 1
	
	# Verify the merge was applied
	merged_tags = set()
	for tags in analyzer.df['tags']:
		merged_tags.update(tags)
	
	assert 'metal' in merged_tags
	assert 'heavy-metal' not in merged_tags
	assert 'heavy metal' not in merged_tags

def test_merge_history(consolidator):
	consolidator.queue_merge('metal', {'heavy-metal', 'heavy metal'})
	consolidator.apply_pending_merges()
	
	history = consolidator.get_merge_history()
	assert isinstance(history, list)
	if history:
		entry = history[0]
		assert 'primary_tag' in entry
		assert 'merged_tags' in entry
		assert 'timestamp' in entry