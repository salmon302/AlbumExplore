import random
from typing import List, Tuple, Dict
from albumexplore.visualization.models import VisualNode, VisualEdge

class TestDataGenerator:
    """Utility class for generating test data with realistic characteristics."""
    
    def __init__(self):
        self.genres = ["metal", "rock", "jazz", "classical", "electronic", "folk"]
        self.subgenres = {
            "metal": ["black", "death", "doom", "thrash", "progressive"],
            "rock": ["hard", "progressive", "psychedelic", "indie", "alternative"],
            "jazz": ["fusion", "bebop", "free", "modal", "contemporary"],
            "classical": ["baroque", "romantic", "modern", "minimalist", "orchestral"],
            "electronic": ["ambient", "techno", "house", "experimental", "idm"],
            "folk": ["traditional", "contemporary", "celtic", "americana", "world"]
        }
    
    def generate_nodes(self, count: int) -> List[VisualNode]:
        """Generate a specified number of nodes with realistic properties."""
        nodes = []
        for i in range(count):
            genre = random.choice(self.genres)
            subgenres = random.sample(self.subgenres[genre], k=random.randint(1, 3))
            tags = [genre] + subgenres
            
            nodes.append(VisualNode(
                id=f"album_{i}",
                label=f"Artist {i} - Album {i}",
                size=len(tags),
                color=self._get_genre_color(genre),
                shape="circle" if random.random() > 0.2 else "square",
                data={
                    "type": "album",
                    "artist": f"Artist {i}",
                    "title": f"Album {i}",
                    "year": random.randint(1970, 2023),
                    "tags": tags,
                    "x": random.uniform(0, 1000),
                    "y": random.uniform(0, 1000)
                }
            ))
        return nodes
    
    def generate_edges(self, nodes: List[VisualNode], density: float = 0.1) -> List[VisualEdge]:
        """Generate edges between nodes based on tag similarity."""
        edges = []
        node_count = len(nodes)
        expected_edges = int(node_count * node_count * density)
        
        # Create edges based on tag similarity
        edge_count = 0
        for i in range(node_count):
            for j in range(i + 1, node_count):
                if edge_count >= expected_edges:
                    break
                
                tags1 = set(nodes[i].data["tags"])
                tags2 = set(nodes[j].data["tags"])
                shared_tags = tags1 & tags2
                
                if shared_tags:
                    edges.append(VisualEdge(
                        source=nodes[i].id,
                        target=nodes[j].id,
                        weight=len(shared_tags),
                        thickness=len(shared_tags) * 0.5,
                        color="#666666",
                        data={"shared_tags": list(shared_tags)}
                    ))
                    edge_count += 1
        
        return edges
    
    def _get_genre_color(self, genre: str) -> str:
        """Return a consistent color for each genre."""
        colors = {
            "metal": "#c41e3a",    # Red
            "rock": "#4169e1",     # Blue
            "jazz": "#32cd32",     # Green
            "classical": "#ffd700", # Gold
            "electronic": "#9370db",# Purple
            "folk": "#ff8c00"      # Orange
        }
        return colors.get(genre, "#808080")

def create_test_dataset(node_count: int, edge_density: float = 0.1) -> Tuple[List[VisualNode], List[VisualEdge]]:
    """Convenience function to create a complete test dataset."""
    generator = TestDataGenerator()
    nodes = generator.generate_nodes(node_count)
    edges = generator.generate_edges(nodes, edge_density)
    return nodes, edges
