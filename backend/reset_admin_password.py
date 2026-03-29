"""
Directly reset admin password - No phone verification needed
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

# New password - CHANGE THIS to your desired password
new_password = 'admin123'  # You can change this

# Hash the password
hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

# Update admin user
admin_username = 'admin123'
result = db.admin_users.update_one(
    {'username': admin_username},
    {'$set': {'password': hashed.decode('utf-8')}}
)

if result.modified_count > 0:
    print(f"✅ SUCCESS: Password reset for '{admin_username}'")
    print(f"New password: {new_password}")
else:
    # Try to insert if user doesn't exist
    admin_user = {
        'username': admin_username,
        'password': hashed.decode('utf-8'),
        'phone_number': '+251979791838',
        'is_active': True
    }
    db.admin_users.insert_one(admin_user)
    print(f"✅ Created new admin user: {admin_username}")
    print(f"Password: {new_password}")

print("\n=== All Admin Users ===")
users = db.admin_users.find({})
for user in users:
    print(f"Username: {user.get('username')}")
    print(f"Phone: {user.get('phone_number', 'NOT SET')}")
    print("---")
