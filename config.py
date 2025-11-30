# Configuration loader
import secrets

# Load bot token
BOT_TOKEN = secrets.TELEGRAM_BOT_TOKEN

# Load database URI
MONGO_URI = secrets.MONGODB_URI

# Database name
DB_NAME = "mysticmatch"

# Collections
USERS_COLLECTION = "users"
MATCHES_COLLECTION = "matches"
LIKES_COLLECTION = "likes"
CHATS_COLLECTION = "chats"
