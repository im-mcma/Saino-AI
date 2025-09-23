# -*- coding: utf-8 -*-
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings, logger
import backoff

class DatabaseManager:
    """
    Manages the connection to the MongoDB database.
    Handles connection, disconnection, and provides access to the database object.
    """
    _client: AsyncIOMotorClient | None = None
    _db = None

    @backoff.on_exception(backoff.expo, Exception, max_tries=5)
    async def connect_to_database(self):
        if self._client and self._db:
            logger.info("Database connection already established.")
            return
        
        logger.info("Connecting to MongoDB...")
        self._client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        try:
            await self._client.admin.command('ping')
            self._db = self._client[settings.DB_NAME]
            logger.info("✅ Successfully connected to MongoDB.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    async def close_database_connection(self):
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")

    @property
    def db(self):
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect_to_database first.")
        return self._db

# Create a single instance to be used across the application
db_manager = DatabaseManager()
