# University of Gondar Knowledge Base
# This file contains all campus information for the AI chatbot

UNIVERSITY_INFO = {
    "name": "University of Gondar",
    "location": "Gondar, Ethiopia",
    "established": "1953",
    "campuses": [
        {
            "id": "main",
            "name": "Main Campus (Central)",
            "description": "The central hub of the university with administrative buildings and main facilities",
            "buildings": [
                {
                    "name": "Administration Building",
                    "description": "Houses the Dean's office, Registrar, and administrative departments",
                    "floors": 4,
                    "features": ["Dean's Office", "Registrar", "Finance Department", "Human Resources"]
                },
                {
                    "name": "Main Library",
                    "description": "Central library with study areas and computer stations",
                    "floors": 3,
                    "features": ["Study Rooms", "Computer Lab", "Digital Archives", "Research Section"]
                },
                {
                    "name": "Central Auditorium",
                    "description": "Main event hall for ceremonies and large gatherings",
                    "capacity": 500,
                    "features": ["Stage", "Sound System", "Projector", "Air Conditioning"]
                },
                {
                    "name": "Student Union Building",
                    "description": "Hub for student activities and organizations",
                    "features": ["Meeting Rooms", "Student Council Office", "Event Space"]
                },
                {
                    "name": "Main Cafeteria",
                    "description": "Primary dining facility for students and staff",
                    "hours": "7:00 AM - 8:00 PM",
                    "features": ["Indoor Seating", "Outdoor Seating", "Coffee Shop"]
                }
            ]
        },
        {
            "id": "science",
            "name": "Science Campus",
            "description": "Dedicated to natural sciences and research",
            "buildings": [
                {
                    "name": "Chemistry Building",
                    "description": "Chemistry department with laboratories",
                    "floors": 3,
                    "features": ["Organic Chemistry Lab", "Analytical Lab", "Research Labs"]
                },
                {
                    "name": "Physics Building",
                    "description": "Physics department and research facilities",
                    "floors": 3,
                    "features": ["Physics Lab", "Observatory", "Lecture Halls"]
                },
                {
                    "name": "Biology Building",
                    "description": "Biology and life sciences department",
                    "floors": 3,
                    "features": ["Biology Lab", "Botany Lab", "Zoology Lab", "Greenhouse"]
                },
                {
                    "name": "Computer Science Building",
                    "description": "Computing and IT facilities",
                    "floors": 4,
                    "features": ["Computer Labs", "Server Room", "Lecture Halls", "Research Labs"]
                }
            ]
        },
        {
            "id": "technology",
            "name": "Technology Campus",
            "description": "Engineering and technology programs",
            "buildings": [
                {
                    "name": "Engineering Building",
                    "description": "Main engineering facility",
                    "floors": 5,
                    "features": ["Civil Engineering Lab", "Structural Lab", "Drawing Hall"]
                },
                {
                    "name": "Mechanical Workshop",
                    "description": "Hands-on mechanical engineering training",
                    "features": ["Workshop Equipment", "3D Printers", "Manufacturing Tools"]
                },
                {
                    "name": "Electrical Engineering Building",
                    "description": "Electrical and electronics engineering",
                    "floors": 4,
                    "features": ["Circuit Labs", "Power Systems Lab", "Electronics Lab"]
                }
            ]
        },
        {
            "id": "medical",
            "name": "Medical Campus",
            "description": "Health sciences and teaching hospital",
            "buildings": [
                {
                    "name": "Teaching Hospital",
                    "description": "University-affiliated hospital for training",
                    "beds": 500,
                    "features": ["Emergency Room", "Surgery", "Outpatient Clinics", "Pharmacy"]
                },
                {
                    "name": "Medical School Building",
                    "description": "Medical education facilities",
                    "floors": 4,
                    "features": ["Lecture Halls", "Anatomy Lab", "Simulation Center"]
                },
                {
                    "name": "Pharmacy Building",
                    "description": "Pharmacy education and research",
                    "floors": 3,
                    "features": ["Pharmaceutical Lab", "Dispensing Practice Lab"]
                }
            ]
        }
    ],
    "facilities": {
        "wifi_locations": [
            "Main Library",
            "Main Cafeteria",
            "Computer Science Building",
            "Administration Building",
            "Student Union Building"
        ],
        "restrooms": "Available in all buildings, clearly marked",
        "parking": "Main parking area near Technology Campus entrance",
        "emergency_exits": "Clearly marked in all buildings",
        "atms": ["Near Administration Building", "Near Main Cafeteria"],
        "health_center": "Located between Main Campus and Medical Campus"
    },
    "services": {
        "registration": "Beginning of each semester at Administration Building",
        "library_hours": "7:00 AM - 10:00 PM (Weekdays), 8:00 AM - 6:00 PM (Weekends)",
        "cafeteria_hours": "7:00 AM - 8:00 PM",
        "wifi_access": "Student ID required, available in all main buildings"
    }
}

# Sample directions between locations
DIRECTIONS = {
    "main_to_science": {
        "start": "Main Campus",
        "end": "Science Campus",
        "duration": "5 minutes walking",
        "instructions": "Exit Main Campus through the south gate, walk straight on the main road, Science Campus is on your left"
    },
    "main_to_technology": {
        "start": "Main Campus",
        "end": "Technology Campus",
        "duration": "10 minutes walking",
        "instructions": "Head east from Main Campus main gate, continue on University Avenue, Technology Campus is on the right"
    },
    "main_to_medical": {
        "start": "Main Campus",
        "end": "Medical Campus",
        "duration": "15 minutes walking",
        "instructions": "Take the main road east from Main Campus, turn right at the hospital sign, Medical Campus is ahead"
    },
    "science_to_technology": {
        "start": "Science Campus",
        "end": "Technology Campus",
        "duration": "7 minutes walking",
        "instructions": "Exit Science Campus through the east gate, walk through the garden path, Technology Campus entrance is ahead"
    },
    "library_to_cafeteria": {
        "start": "Main Library",
        "end": "Main Cafeteria",
        "duration": "2 minutes walking",
        "instructions": "Exit Library heading south, Cafeteria is directly across the central courtyard"
    },
    "admin_to_auditorium": {
        "start": "Administration Building",
        "end": "Central Auditorium",
        "duration": "3 minutes walking",
        "instructions": "From Administration Building, walk west across the main plaza, Auditorium is the large building ahead"
    }
}

# Quick answers for common questions
QUICK_ANSWERS = {
    "wifi_password": "WiFi: UoG_Student, Password: Your student ID number",
    "library hours": "Library Hours: Monday-Friday 7AM-10PM, Weekends 8AM-6PM",
    "cafeteria hours": "Cafeteria: 7:00 AM - 8:00 PM daily",
    "emergency": "Emergency: Call 911 or visit Health Center between Main and Medical Campus",
    "admin contact": "Administration: +251-58-114-1234, Email: info@uog.edu.et"
}

def get_knowledge_context():
    """Generate a comprehensive context string for the AI"""
    context = f"""
You are an AI assistant for the {UNIVERSITY_INFO['name']} in {UNIVERSITY_INFO['location']}.

UNIVERSITY OVERVIEW:
- Established: {UNIVERSITY_INFO['established']}
- Located in: {UNIVERSITY_INFO['location']}

CAMPUSES AND BUILDINGS:
"""
    
    for campus in UNIVERSITY_INFO['campuses']:
        context += f"\n{campus['name']}: {campus['description']}\n"
        for building in campus['buildings']:
            context += f"  - {building['name']}: {building['description']}\n"
    
    context += """
FACILITIES:
- WiFi available at: """ + ", ".join(UNIVERSITY_INFO['facilities']['wifi_locations']) + """
- Restrooms: Available in all buildings
- Health Center: Between Main and Medical Campus

IMPORTANT RULES:
1. If asked about directions, provide walking directions with estimated time
2. If asked about facilities, mention availability and hours
3. If you don't know a specific detail, suggest contacting Administration
4. Keep responses concise but helpful
5. Be friendly and supportive to students
6. Use text labels like [LIBRARY] [CAFETERIA] instead of emojis

When giving directions, mention landmarks and estimated walking time.
"""
    return context
