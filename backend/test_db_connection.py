"""
MongoDB Connection Test Script
Run this script to verify the connection between the app and MongoDB.

Usage:
    python test_db_connection.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Get MongoDB URI from config
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/uog_navigator')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'uog_navigator')


def test_mongodb_connection():
    """Test MongoDB connection and display results."""
    print("=" * 60)
    print("MongoDB Connection Test")
    print("=" * 60)
    
    print("\nMongoDB URI: {}".format(MONGODB_URI))
    print("Database Name: {}".format(MONGODB_DB_NAME))
    
    # Mask password in URI for display
    display_uri = MONGODB_URI
    if '@' in display_uri:
        # Mask the password part
        parts = display_uri.split('@')
        user_pass = parts[0].split('//')[1] if '//' in parts[0] else parts[0]
        if ':' in user_pass:
            user = user_pass.split(':')[0]
            display_uri = "{}//{}:****@{}".format(parts[0].split('//')[0], user, parts[1])
    print("   (Masked URI: {})".format(display_uri))
    
    print("\nTesting connection...")
    
    try:
        # Attempt connection with timeout
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000
        )
        
        # Test connection
        server_info = client.server_info()
        
        print("\n[SUCCESS] CONNECTION ESTABLISHED!")
        print("-" * 40)
        print("MongoDB Version: {}".format(server_info.get('version', 'unknown')))
        print("Connected Database: {}".format(MONGODB_DB_NAME))
        
        # Get database
        db = client[MONGODB_DB_NAME]
        
        # List collections
        collections = db.list_collection_names()
        print("\nCollections in database:")
        if collections:
            for coll in collections:
                count = db[coll].count_documents({})
                print("   - {}: {} document(s)".format(coll, count))
        else:
            print("   (No collections found - empty database)")
        
        # Test database operations
        print("\nTesting database operations...")
        
        # Test 1: Insert and retrieve a test document
        test_result = db.connection_test.insert_one({
            'test': 'connection_test',
            'timestamp': __import__('datetime').datetime.utcnow()
        })
        print("   Insert test: document ID {}".format(test_result.inserted_id))
        
        # Clean up test document
        db.connection_test.delete_one({'_id': test_result.inserted_id})
        print("   Delete test: test document cleaned up")
        
        print("\n" + "=" * 60)
        print("[PASSED] All tests passed - MongoDB is working!")
        print("=" * 60)
        
        client.close()
        return True
        
    except ServerSelectionTimeoutError as e:
        print("\n[FAILED] CONNECTION TIMEOUT")
        print("   Error: {}".format(e))
        print("\nPossible causes:")
        print("   - MongoDB server is not running")
        print("   - Network/firewall blocking connection")
        print("   - Incorrect MongoDB URI")
        return False
        
    except ConnectionFailure as e:
        print("\n[FAILED] CONNECTION FAILED")
        print("   Error: {}".format(e))
        print("\nPossible causes:")
        print("   - Wrong username or password")
        print("   - IP not whitelisted (MongoDB Atlas)")
        print("   - Network issues")
        return False
        
    except Exception as e:
        print("\n[ERROR]")
        print("   Error: {}".format(e))
        return False


def test_with_database_module():
    """Test using the database module."""
    print("\n" + "=" * 60)
    print("Testing with Database Module")
    print("=" * 60)
    
    try:
        from database import db
        
        print("\nConnecting to MongoDB...")
        connected = db.connect()
        
        if connected:
            print("[SUCCESS] Database connected!")
            
            # Check if connected
            if db.is_connected():
                print("[SUCCESS] Database connection verified")
                
                # Try getting users
                users = db.get_all_users()
                print("   Users in database: {}".format(len(users)))
                
                # Try getting locations
                locations = db.get_campus_locations()
                print("   Campus locations: {}".format(len(locations)))
                
                print("\n[PASSED] Database module is working!")
                return True
            else:
                print("[FAILED] Database connection lost")
                return False
        else:
            print("[FAILED] Failed to connect to database")
            return False
            
    except Exception as e:
        print("[ERROR] Error testing database module: {}".format(e))
        return False


if __name__ == "__main__":
    print("\n" + "# " * 15)
    print("UOG Navigator - MongoDB Connection Test")
    print("# " * 15)
    
    # Run direct MongoDB test
    result1 = test_mongodb_connection()
    
    # Run database module test
    result2 = test_with_database_module()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("   Direct MongoDB Test: {}".format('PASSED' if result1 else 'FAILED'))
    print("   Database Module Test:  {}".format('PASSED' if result2 else 'FAILED'))
    print("=" * 60)
    
    if result1 and result2:
        print("\nAll connection tests passed!")
        print("The app is properly connected to MongoDB.")
    else:
        print("\nSome tests failed. Please check the errors above.")
