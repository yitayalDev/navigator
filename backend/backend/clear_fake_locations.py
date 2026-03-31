"""
Script to remove fake campus locations from MongoDB
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import db

def clear_fake_locations():
    print("=" * 60)
    print("Removing Fake Campus Locations from MongoDB")
    print("=" * 60)
    
    # Connect to MongoDB
    print("\nConnecting to MongoDB...")
    if not db.connect():
        print("[FAILED] Could not connect to MongoDB")
        return False
    
    print("[SUCCESS] Connected to MongoDB")
    
    # Get all locations
    print("\nFetching all locations...")
    all_locations = db.get_campus_locations()
    print(f"Total locations before: {len(all_locations)}")
    
    # Show what will be deleted
    print("\nLocations to be DELETED:")
    campuses_to_delete = ['maraki', 'fasil']
    deleted_count = 0
    
    for campus in campuses_to_delete:
        locs = db.get_campus_locations(campus_id=campus)
        if locs:
            print(f"\n--- {campus.upper()} Campus ({len(locs)} locations) ---")
            for loc in locs:
                print(f"  - {loc['name']}")
                # Delete each location
                result = db._db.campus_locations.delete_many({'campus': campus})
                deleted_count += result.deleted_count
    
    # Alternative: Delete by campus filter
    for campus in campuses_to_delete:
        result = db._db.campus_locations.delete_many({'campus': campus})
        print(f"\nDeleted {result.deleted_count} locations from {campus} campus")
    
    # Verify deletion
    print("\nVerifying deletion...")
    remaining = db.get_campus_locations()
    print(f"Total locations remaining: {len(remaining)}")
    
    # Show remaining campuses
    if remaining:
        by_campus = {}
        for loc in remaining:
            campus = loc.get('campus', 'unknown')
            if campus not in by_campus:
                by_campus[campus] = []
            by_campus[campus].append(loc)
        
        print("\nRemaining campuses:")
        for campus, locs in by_campus.items():
            print(f"  - {campus}: {len(locs)} locations")
    
    print("\n" + "=" * 60)
    print("[DONE] Fake locations removed from MongoDB!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    clear_fake_locations()
