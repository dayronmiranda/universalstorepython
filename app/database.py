"""MongoDB database connection using Motor (async driver)"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings


class Database:
    """Database connection manager"""
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


database = Database()


async def connect_to_mongo():
    """Connect to MongoDB on application startup"""
    database.client = AsyncIOMotorClient(settings.mongodb_url)
    database.db = database.client[settings.mongodb_db_name]
    print(f"Connected to MongoDB: {settings.mongodb_db_name}")


async def close_mongo_connection():
    """Close MongoDB connection on application shutdown"""
    if database.client:
        database.client.close()
        print("Closed MongoDB connection")


def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance"""
    return database.db
