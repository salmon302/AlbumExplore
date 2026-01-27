import json
from pathlib import Path

def merge_suggestions():
    base_dir = Path('data/exports')
    file1 = base_dir / 'singleton_suggestions.json'
    file2 = base_dir / 'cooccurrence_suggestions.json'
    output_file = base_dir / 'merged_suggestions.json'
    
    suggestions = {}
    stats = {'total_singletons': 0, 'suggested': 0}
    
    # Load File 1 (Auto Singleton Mapper)
    if file1.exists():
        with open(file1, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
            # Use update to merge dictionaries
            suggestions.update(data1.get('suggestions', {}))
            stats['total_singletons'] = data1.get('stats', {}).get('total_singletons', 0)

    # Load File 2 (Co-occurrence)
    if file2.exists():
        with open(file2, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
            # For conflicts, co-occurrence might be "better" if it has reason text specifically about co-occurrence
            # But let's just update for now. 
            # Ideally we'd compare scores, but auto_singleton doesn't have scores yet (they are added by scorer).
            new_suggestions = data2.get('suggestions', {})
            for tag, info in new_suggestions.items():
                if tag in suggestions:
                    # Conflict!
                    # If co-occurrence found something with high confidence, maybe keep it?
                    # Let's append the reason
                    suggestions[tag]['reason'] += f"; ALSO co-occurrence: {info['suggestion']}"
                else:
                    suggestions[tag] = info

    stats['suggested'] = len(suggestions)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'stats': stats, 'suggestions': suggestions}, f, indent=2, ensure_ascii=False)
        
    print(f"Merged suggestions into {output_file}. Total: {len(suggestions)}")

if __name__ == "__main__":
    merge_suggestions()
