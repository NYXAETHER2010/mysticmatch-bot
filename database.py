# Database operations
from pymongo import MongoClient
import config

# Connect to MongoDB
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]

# Collections
users = db[config.USERS_COLLECTION]
matches = db[config.MATCHES_COLLECTION]
likes = db[config.LIKES_COLLECTION]
chats = db[config.CHATS_COLLECTION]

# User functions
def create_user(user_id, username, name, age, gender, city, bio, photo):
    """Create new user profile"""
    user = {
        "user_id": user_id,
        "username": username,
        "name": name,
        "age": age,
        "gender": gender,
        "interested_in": None,
        "city": city,
        "bio": bio,
        "photo": photo,
        "active": True
    }
    users.insert_one(user)
    return user

def get_user(user_id):
    """Get user by ID"""
    return users.find_one({"user_id": user_id})

def update_user(user_id, updates):
    """Update user data"""
    users.update_one({"user_id": user_id}, {"$set": updates})

def get_potential_matches(user_id):
    """Get users to show for swiping"""
    current_user = get_user(user_id)
    if not current_user:
        return []
    
    already_seen = set()
    for like in likes.find({"user_id": user_id}):
        already_seen.add(like["target_id"])
    
    query = {
        "user_id": {"$ne": user_id},
        "user_id": {"$nin": list(already_seen)},
        "gender": current_user.get("interested_in", "all"),
        "active": True
    }
    
    if current_user.get("interested_in") == "all":
        del query["gender"]
    
    return list(users.find(query).limit(50))

def add_like(user_id, target_id, liked):
    """Record a like or pass"""
    like = {
        "user_id": user_id,
        "target_id": target_id,
        "liked": liked
    }
    likes.insert_one(like)
    
    if liked:
        mutual = likes.find_one({
            "user_id": target_id,
            "target_id": user_id,
            "liked": True
        })
        if mutual:
            create_match(user_id, target_id)
            return True
    return False

def create_match(user1_id, user2_id):
    """Create a match between two users"""
    match = {
        "user1_id": user1_id,
        "user2_id": user2_id,
        "active": True
    }
    matches.insert_one(match)

def get_matches(user_id):
    """Get all matches for a user"""
    user_matches = []
    
    for match in matches.find({"user1_id": user_id, "active": True}):
        other_user = get_user(match["user2_id"])
        if other_user:
            user_matches.append(other_user)
    
    for match in matches.find({"user2_id": user_id, "active": True}):
        other_user = get_user(match["user1_id"])
        if other_user:
            user_matches.append(other_user)
    
    return user_matches

def is_matched(user1_id, user2_id):
    """Check if two users are matched"""
    return matches.find_one({
        "$or": [
            {"user1_id": user1_id, "user2_id": user2_id},
            {"user1_id": user2_id, "user2_id": user1_id}
        ],
        "active": True
    }) is not None

def save_message(from_user_id, to_user_id, message):
    """Save a chat message"""
    msg = {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "message": message
    }
    chats.insert_one(msg)

def get_chat_history(user1_id, user2_id, limit=50):
    """Get chat history between two users"""
    messages = chats.find({
        "$or": [
            {"from_user_id": user1_id, "to_user_id": user2_id},
            {"from_user_id": user2_id, "to_user_id": user1_id}
        ]
    }).sort("_id", -1).limit(limit)
    
    return list(reversed(list(messages)))
