from pymongo import MongoClient
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class Database:
    client: MongoClient = None
    db = None

    def connect(self):
        try:
            self.client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
            self.db = self.client[settings.DATABASE_NAME]
            logger.info(f"Connected to MongoDB at {settings.MONGODB_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}. Server will start but DB features are unavailable.")
            self.db = None

    def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_collection(self, name: str):
        if self.db is None:
            raise RuntimeError("Database is not connected")
        return self.db[name]

    def get_db(self):
        return self.db

db = Database()
db.connect()
