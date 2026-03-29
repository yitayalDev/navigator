"""
Add phone number to admin user - Run this to enable password reset
"""
import os
import sys
sys.path.insert(0, '.')

from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()
mongo_uri = os.getenv('MONGODB_URI')

if not mongo_uri:
    print("ERROR: MONGODB_URI not found!")
    sys.exit(1)

client = MongoClient(mongo_uri)
db = client['uog_navigator']

# Admin username to update
admin_username = 'admin123'
new_phone = '+251979791838'  # Your actual phone number

# Update the admin user with phone number
result = db.admin_users.update_one(
    {'username': admin_username},
    {'$set': {'phone_number': new_phone}}
)

if result.modified_count > 0:
    print(f"✅ SUCCESS: Added phone number {new_phone} to admin user '{admin_username}'")
    print("You can now use the 'Forgot Password' feature!")
else:
    print("⚠️ No changes made - user may not exist or phone already set")

# Display current admin users
print("\n=== Current Admin Users ===")
users = db.admin_users.find({})
for user in users:
    print(f"Username: {user.get('username')}")
    print(f"Phone: {user.get('phone_number', 'NOT SET')}")
    print("---")
