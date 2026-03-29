"""Update admin user with phone number in MongoDB Atlas"""
import sys
sys.path.insert(0, '.')

from pymongo import MongoClient

# Use the cloud MongoDB Atlas connection
mongo_uri = "mongodb+srv://paypal831363_db_user:uRPdFYdubkXo4cNv@cluster0.upsy9z8.mongodb.net/uog_navigator?retryWrites=true&w=majority"
client = MongoClient(mongo_uri)
db = client['uog_navigator']

phone = '+251979791838'

# Update ALL admin users with this username
result = db.admin_users.update_many(
    {'username': 'admin123'},
    {'$set': {'phone_number': phone}}
)

print(f"[OK] Updated {result.modified_count} admin user(s) with phone number: {phone}")

# List all admin users
print("\n=== All admin users in MongoDB Atlas ===")
users = db.admin_users.find({})
for user in users:
    print(f"ID: {user['_id']}")
    print(f"Username: {user['username']}")
    print(f"Phone: {user.get('phone_number', 'NOT SET')}")
    print("---")