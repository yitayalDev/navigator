"""Check admin user raw data from MongoDB"""
import sys
sys.path.insert(0, '.')

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
client = MongoClient(mongo_uri)
db = client['uog_navigator']

# Get raw admin user document
print("=== Raw MongoDB Document for admin123 ===")
user = db.admin_users.find_one({'username': 'admin123'})

if user:
    # Print all fields
    for key, value in user.items():
        print(f"{key}: {value}")
else:
    print("User 'admin123' not found!")

print("\n=== Checking for 'phone_number' field ===")
print(f"phone_number exists: {'phone_number' in user if user else 'N/A'}")
print(f"phone exists: {'phone' in user if user else 'N/A'}")