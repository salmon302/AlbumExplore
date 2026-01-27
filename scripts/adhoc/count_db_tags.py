from albumexplore.database import session_scope, models
from sqlalchemy import func

def count_tags():
    with session_scope() as session:
        total_tags = session.query(models.Tag).count()
        canonical_tags = session.query(models.Tag).filter(models.Tag.is_canonical == 1).count()
        non_canonical_tags = session.query(models.Tag).filter(models.Tag.is_canonical == 0).count()
        
        # Count unique normalized names
        unique_normalized = session.query(func.count(func.distinct(models.Tag.normalized_name))).scalar()
        
        print(f"Total Tags: {total_tags}")
        print(f"Canonical Tags (Normalized Targets): {canonical_tags}")
        print(f"Non-Canonical Tags (Mapped Variants): {non_canonical_tags}")
        print(f"Unique Normalized Names: {unique_normalized}")

if __name__ == "__main__":
    count_tags()
