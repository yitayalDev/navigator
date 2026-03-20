"""
Secure Configuration Module for UOG Student Navigation Bot
Handles environment variables and sensitive configuration securely.
"""
import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


class Config:
    """Configuration class for the bot."""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Security
    ADMIN_USER_IDS: str = os.getenv('ADMIN_USER_IDS', '')
    ADMIN_IDS_LIST: List[int] = [
        int(uid.strip()) for uid in ADMIN_USER_IDS.split(',') if uid.strip()
    ] if ADMIN_USER_IDS else []
    
    # API Keys (for future use)
    MAPS_API_KEY: Optional[str] = os.getenv('MAPS_API_KEY')
    
    # SDMR Server for shortest path routing
    # Default: OSRM public server
    # Can be set to a custom SDMR server URL
    SDMR_SERVER: Optional[str] = os.getenv('SDMR_SERVER', 'http://router.project-osrm.org')
    
    # Flask Server URL (for webhook mode)
    FLASK_SERVER_URL: Optional[str] = os.getenv('FLASK_SERVER_URL')
    
    # MongoDB Configuration
    MONGODB_URI: Optional[str] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/uog_navigator')
    MONGODB_DB_NAME: Optional[str] = os.getenv('MONGODB_DB_NAME', 'uog_navigator')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.TELEGRAM_BOT_TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN not found in environment variables!")
            print("Please set it in the .env file or as an environment variable.")
            return False
        return True
    
    @classmethod
    def get_bot_token(cls) -> str:
        """Get bot token with validation."""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured!")
        return cls.TELEGRAM_BOT_TOKEN


# University of Gondar Campus Locations Data
class CampusData:
    """Static data for University of Gondar campuses."""
    
    CAMPUSES = {
        'maraki': {
            'name': 'Maraki Campus',
            'description': 'Main campus of University of Gondar',
            'center': '12.5980,37.3900',
            'buildings': []
        },
        'tewodros': {
            'name': 'Tewodros Campus',
            'description': 'Tewodros campus - Located near the city center',
            'center': '12.5950,37.3850',
            'buildings': []
        },
        'fasil': {
            'name': 'Fasil Campus',
            'description': 'Fasil campus - Historical area',
            'center': '12.5850,37.3800',
            'buildings': []
        }
    }
    
    # All locations with coordinates - Only Tewodros Campus (Real Data)
    # 6 Categories: building, administration, library, lab, cafe, dorm
    # Maraki and Fasil campuses are empty (no locations)
    LOCATIONS = [
        # Administration (category: administration)
        {"name": "President Office 1", "category": "administration", "campus": "tewodros", "coords": "12.59078,37.44360", "description": "President Office building"},
        {"name": "President Office 2", "category": "administration", "campus": "tewodros", "coords": "12.58905,37.44273", "description": "President Office building 2"},
        {"name": "Registrar ICT", "category": "administration", "campus": "tewodros", "coords": "12.58903,37.44238", "description": "Registrar ICT office"},
        {"name": "Main Registrar", "category": "administration", "campus": "tewodros", "coords": "12.58765,37.43945", "description": "Main Registrar building"},
        {"name": "Student Association", "category": "administration", "campus": "tewodros", "coords": "12.58536,37.44007", "description": "Student Association office"},
        {"name": "Veterinary Registration", "category": "administration", "campus": "tewodros", "coords": "12.58486,37.43905", "description": "Veterinary Registration"},
        
        # Buildings
        {"name": "Sador Building", "category": "building", "campus": "tewodros", "coords": "12.58999,37.44300", "description": "Sador Building"},
        {"name": "Main Store", "category": "building", "campus": "tewodros", "coords": "12.58966,37.44264", "description": "Main Store"},
        {"name": "Informatics", "category": "building", "campus": "tewodros", "coords": "12.58883,37.44188", "description": "Informatics building"},
        {"name": "New Building", "category": "building", "campus": "tewodros", "coords": "12.58783,37.44015", "description": "New Building"},
        {"name": "Lecture Houses", "category": "building", "campus": "tewodros", "coords": "12.58579,37.43788", "description": "Lecture Houses"},
        {"name": "Maraki Main Gate", "category": "building", "campus": "tewodros", "coords": "12.590668,37.44411", "description": "Main entrance to Maraki campus"},
        {"name": "Post Office", "category": "building", "campus": "tewodros", "coords": "12.58889,37.44122", "description": "Post Office"},
        {"name": "T11 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58802,37.44220", "description": "T11 Lecture Hall"},
        {"name": "T12 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58779,37.44219", "description": "T12 Lecture Hall"},
        {"name": "T13 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58753,37.44222", "description": "T13 Lecture Hall"},
        {"name": "T14 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58734,37.44191", "description": "T14 Lecture Hall"},
        {"name": "T148 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58719,37.44226", "description": "T148 Lecture Hall"},
        {"name": "T23 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58572,37.44199", "description": "T23 Lecture Hall"},
        {"name": "T24 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58574,37.44164", "description": "T24 Lecture Hall"},
        {"name": "T25 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58540,37.44155", "description": "T25 Lecture Hall"},
        {"name": "T26 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58489,37.44151", "description": "T26 Lecture Hall"},
        {"name": "T27 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58442,37.44163", "description": "T27 Lecture Hall"},
        {"name": "T28 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58575,37.44125", "description": "T28 Lecture Hall"},
        {"name": "T29 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58535,37.44124", "description": "T29 Lecture Hall"},
        {"name": "T30 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58226,37.44103", "description": "T30 Lecture Hall"},
        {"name": "T31 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58217,37.44035", "description": "T31 Lecture Hall"},
        {"name": "T32 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58178,37.44035", "description": "T32 Lecture Hall"},
        {"name": "T33 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58177,37.44134", "description": "T33 Lecture Hall"},
        {"name": "T34 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58222,37.44138", "description": "T34 Lecture Hall"},
        {"name": "T35 Lecture Hall", "category": "building", "campus": "tewodros", "coords": "12.58263,37.44139", "description": "T35 Lecture Hall"},
        {"name": "Veterinary Class", "category": "building", "campus": "tewodros", "coords": "12.58401,37.44033", "description": "Veterinary Class"},
        {"name": "University Clinic", "category": "building", "campus": "tewodros", "coords": "12.58549,37.44038", "description": "University Clinic"},
        {"name": "Stadium", "category": "building", "campus": "tewodros", "coords": "12.58636,37.44012", "description": "Stadium"},
        {"name": "Animal House", "category": "building", "campus": "tewodros", "coords": "12.58355,37.43773", "description": "Animal House"},
        {"name": "Veterinary Hospital", "category": "building", "campus": "tewodros", "coords": "12.58507,37.43650", "description": "Veterinary Hospital"},
        
        # Libraries
        {"name": "Post Library", "category": "library", "campus": "tewodros", "coords": "12.58910,37.44125", "description": "Post Library"},
        {"name": "T15 Library", "category": "library", "campus": "tewodros", "coords": "12.58775,37.44134", "description": "T15 Library"},
        {"name": "Veterinary Library", "category": "library", "campus": "tewodros", "coords": "12.58349,37.44003", "description": "Veterinary Library"},
        
        # Labs
        {"name": "T9 Computer Lab", "category": "lab", "campus": "tewodros", "coords": "12.58826,37.44157", "description": "T9 Computer Lab"},
        {"name": "T10 Lab", "category": "lab", "campus": "tewodros", "coords": "12.58827,37.44192", "description": "T10 Lab"},
        {"name": "Biology Lab", "category": "lab", "campus": "tewodros", "coords": "12.58727,37.44123", "description": "Biology Lab"},
        {"name": "Chemistry Lab", "category": "lab", "campus": "tewodros", "coords": "12.58721,37.44160", "description": "Chemistry Lab"},
        {"name": "Physics Lab", "category": "lab", "campus": "tewodros", "coords": "12.58671,37.44160", "description": "Physics Lab"},
        {"name": "Info Science Lab", "category": "lab", "campus": "tewodros", "coords": "12.58667,37.44200", "description": "Info Science Lab"},
        {"name": "Info System Lab", "category": "lab", "campus": "tewodros", "coords": "12.58671,37.44197", "description": "Info System Lab"},
        {"name": "Veterinary Lab", "category": "lab", "campus": "tewodros", "coords": "12.58402,37.44003", "description": "Veterinary Lab"},
        
        # Cafes
        {"name": "Main Cafeteria", "category": "cafe", "campus": "tewodros", "coords": "12.58382,37.44225", "description": "Main campus cafeteria"},
        {"name": "Cafe Store", "category": "cafe", "campus": "tewodros", "coords": "12.58320,37.44225", "description": "Cafe Store"},
        {"name": "Addis Hiywot", "category": "cafe", "campus": "tewodros", "coords": "12.58405,37.44092", "description": "Addis Hiywot cafe"},
        {"name": "T-Lounge", "category": "cafe", "campus": "tewodros", "coords": "12.58466,37.44087", "description": "T-Lounge"},
        {"name": "Aman Lounge", "category": "cafe", "campus": "tewodros", "coords": "12.58544,37.43976", "description": "Aman Lounge"},
        
        # Dormitories
        {"name": "Federal Dormitory", "category": "dorm", "campus": "tewodros", "coords": "12.58278,37.44037", "description": "Federal Dormitory"},
        {"name": "Prep Dormitory", "category": "dorm", "campus": "tewodros", "coords": "12.58201,37.44033", "description": "Prep Dormitory"},
    ]
    
    @classmethod
    def get_locations_by_category(cls, category: str) -> list:
        """Get all locations of a specific category."""
        return [loc for loc in cls.LOCATIONS if loc['category'] == category]
    
    @classmethod
    def get_locations_by_campus(cls, campus: str) -> list:
        """Get all locations in a specific campus."""
        return [loc for loc in cls.LOCATIONS if loc['campus'] == campus]
    
    @classmethod
    def get_all_categories(cls) -> list:
        """Get all unique categories."""
        return list(set(loc['category'] for loc in cls.LOCATIONS))
    
    @classmethod
    def find_nearest_location(cls, coords: str, category: str = None) -> dict:
        """Find nearest location to given coordinates."""
        # Simple implementation - can be enhanced with actual distance calculation
        locations = cls.LOCATIONS
        if category:
            locations = cls.get_locations_by_category(category)
        return locations[0] if locations else None


# Export config instance
config = Config()
