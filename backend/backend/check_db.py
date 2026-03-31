"""
Script to check what's stored in MongoDB
Run with: python check_db.py
"""
import sys
sys.path.insert(0, '.')

from database import db

# Connect to database
print("Connecting to MongoDB...")
if db.connect():
    print("OK - Connected successfully!")
else:
    print("ERROR - Failed to connect!")
    sys.exit(1)

# Get all locations
locations = db.get_campus_locations()
print(f"\nTotal locations in database: {len(locations)}")

# Show each location
print("\nAll locations:")
print("-" * 60)
for i, loc in enumerate(locations, 1):
    name = loc.get('name', 'N/A')
    category = loc.get('category', 'N/A')
    campus = loc.get('campus', 'N/A')
    coords = loc.get('coords', 'N/A')
    print(f"{i}. {name}")
    print(f"   Category: {category} | Campus: {campus}")
    print(f"   Coordinates: {coords}")
    print()

# Show count by category
print("-" * 60)
print("\nCount by Category:")
category_counts = db.get_building_count_by_category()
for cat in category_counts:
    print(f"  {cat['_id']}: {cat['count']}")

# Show count by campus
print("\nCount by Campus:")
campus_counts = db.get_building_count_by_campus()
for camp in campus_counts:
    print(f"  {camp['_id']}: {camp['count']}")
