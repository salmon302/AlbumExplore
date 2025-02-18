import unittest
import pandas as pd
from albumexplore.tags.management.quality_metrics import QualityMetrics, TagQualityScore
from albumexplore.tags.management.review_queue import ReviewQueue, ReviewStatus, ChangeType
from albumexplore.tags.analysis.tag_analyzer import TagAnalyzer

class TestQualityMetrics(unittest.TestCase):
    def setUp(self):
        self.test_data = pd.DataFrame({
            'tags': [
                ['metal', 'heavy-metal', 'heavy metal'],
                ['black-metal', 'blackmetal', 'atmospheric'],
                ['death-metal', 'deathmetal', 'technical'],
                ['prog', 'progressive', 'prog-metal']
            ]
        })
        
        self.analyzer = TagAnalyzer(self.test_data)
        # Ensure relationships are calculated
        self.analyzer.calculate_relationships()
        # Build graph connections
        for tags in self.test_data['tags']:
            for i, tag1 in enumerate(tags):
                for tag2 in tags[i+1:]:
                    if not self.analyzer.graph.has_edge(tag1, tag2):
                        self.analyzer.graph.add_edge(tag1, tag2, weight=1.0)
        
        self.review_queue = ReviewQueue()
        self.metrics = QualityMetrics(self.analyzer, self.review_queue)

    def test_consistency_score(self):
        score = self.metrics.calculate_consistency_score('heavy-metal')
        self.assertGreaterEqual(score, 0.5)
        
        score = self.metrics.calculate_consistency_score('HeavY MetaL')
        self.assertLess(score, 0.5)

    def test_ambiguity_index(self):
        # Debug: Print tag frequencies and relationships
        print("\nTag Frequencies:", self.analyzer.tag_frequencies)
        print("\nGraph Edges:")
        for edge in self.analyzer.graph.edges(data=True):
            print(f"{edge[0]} -- {edge[1]} (weight: {edge[2]['weight']})")
        
        score = self.metrics.calculate_ambiguity_index('progressive')
        print("\nAmbiguity Score for 'progressive':", score)
        
        # Debug: Print similar tags
        similar_tags = self.analyzer.find_similar_tags('progressive', threshold=0.3)
        print("\nSimilar tags:", similar_tags)
        
        self.assertGreaterEqual(score, 0.4)
        
        score = self.metrics.calculate_ambiguity_index('prog')
        self.assertLessEqual(score, 0.6)

    def test_relationship_strength(self):
        score = self.metrics.calculate_relationship_strength('metal')
        self.assertGreaterEqual(score, 0.5)
        
        score = self.metrics.calculate_relationship_strength('unknown-tag')
        self.assertEqual(score, 0.0)

    def test_feedback_score(self):
        change_id = self.review_queue.add_change(
            change_type=ChangeType.RENAME,
            old_value='prog',
            new_value='progressive',
            notes='Using full term'
        )
        self.review_queue.approve_change(change_id, 'test_user')
        
        score = self.metrics.calculate_feedback_score('prog')
        self.assertNotEqual(score, 0.5)

    def test_overall_score(self):
        quality_score = self.metrics.calculate_overall_score('heavy-metal')
        
        self.assertIsInstance(quality_score, TagQualityScore)
        self.assertGreaterEqual(quality_score.overall_score, 0.0)
        self.assertLessEqual(quality_score.overall_score, 1.0)
        self.assertEqual(quality_score.tag, 'heavy-metal')

    def test_get_low_quality_tags(self):
        for tags in self.test_data['tags']:
            for tag in tags:
                self.metrics.calculate_overall_score(tag)
        
        low_quality = self.metrics.get_low_quality_tags(threshold=0.7)
        self.assertIsInstance(low_quality, list)
        
        if low_quality:
            self.assertLess(low_quality[0].overall_score, 0.7)
            self.assertTrue(all(t.overall_score < 0.7 for t in low_quality))

if __name__ == '__main__':
    unittest.main()
