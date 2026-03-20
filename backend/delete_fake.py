from pymongo import MongoClient
from dotenv import load_dotenv
import os
load_dotenv()
MONGODB_URI = os.getenv('MONGODB_URI')

print("Connecting to MongoDB...")
client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=30000)
db = client['uog_navigator']

print("Deleting maraki campus locations...")
result1 = db.campus_locations.delete_many({'campus': 'maraki'})
print(f"Deleted {result1.deleted_count} from maraki")

print("Deleting fasil campus locations...")
result2 = db.campus_locations.delete_many({'campus': 'fasil'})
print(f"Deleted {result2.deleted_count} from fasil")

print("\nVerifying remaining locations...")
count = db.campus_locations.count_documents({})
print(f"Total remaining: {count}")

for loc in db.campus_locations.find():
    print(f"  - {loc.get('campus')}: {loc.get('name')}")

print("\nDone!")
