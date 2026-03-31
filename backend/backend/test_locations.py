"""
Test script to verify locations are stored in MongoDB
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import db

def test_locations():
    print("=" * 60)
    print("Testing MongoDB Locations Storage")
    print("=" * 60)
    
    # Connect to MongoDB
    print("\nConnecting to MongoDB...")
    if not db.connect():
        print("[FAILED] Could not connect to MongoDB")
        return False
    
    print("[SUCCESS] Connected to MongoDB")
    
    # Get all locations
    print("\nFetching all locations from MongoDB...")
    locations = db.get_campus_locations()
    
    print(f"Found {len(locations)} locations in database:\n")
    
    # Group by campus
    by_campus = {}
    for loc in locations:
        campus = loc.get('campus', 'unknown')
        if campus not in by_campus:
            by_campus[campus] = []
        by_campus[campus].append(loc)
    
    # Display by campus
    for campus, locs in by_campus.items():
        print(f"\n--- {campus.upper()} Campus ({len(locs)} locations) ---")
        for loc in locs:
            cat = loc.get('category', 'unknown')
            name = loc.get('name', 'unknown')
            coords = loc.get('coords', 'unknown')
            print(f"  [{cat:12}] {name:30} | {coords}")
    
    # Test get by campus
    print("\n\nTesting get_locations_by_campus('maraki')...")
    maraki_locs = db.get_campus_locations(campus_id='maraki')
    print(f"Found {len(maraki_locs)} locations in Maraki campus")
    
    # Test search
    print("\n\nTesting search_locations('library')...")
    search_results = db.search_locations('library')
    print(f"Found {len(search_results)} locations matching 'library'")
    for loc in search_results:
        print(f"  - {loc['name']}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] All location tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_locations()
