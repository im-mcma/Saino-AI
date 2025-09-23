# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from cryptography.fernet import Fernet
import os

# Generate a key with: Fernet.generate_key().decode()
# Store this securely, NOT in the code. Read from environment.
ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY", "your-32-byte-fernet-key-for-db-encryption")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

class EnvManager:
    """Manages dynamic, user-specific, and system-wide API keys stored securely in the database."""
    
    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id
        self.keys_collection = self.db["api_keys"]

    def _encrypt(self, value: str) -> str:
        return cipher_suite.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        return cipher_suite.decrypt(value.encode()).decode()

    async def set_key(self, service: str, value: str, is_system_key: bool = False):
        """Sets or updates an API key for a service."""
        owner_id = "system" if is_system_key else self.user_id
        encrypted_value = self._encrypt(value)
        await self.keys_collection.update_one(
            {"owner_id": owner_id, "service": service},
            {"$set": {"value": encrypted_value}},
            upsert=True
        )

    async def get_key(self, service: str) -> Optional[str]:
        """Gets a user's key, falling back to the system key if not found."""
        # Try user-specific key first
        user_key = await self.keys_collection.find_one({"owner_id": self.user_id, "service": service})
        if user_key:
            return self._decrypt(user_key["value"])
        
        # Fallback to system key
        system_key = await self.keys_collection.find_one({"owner_id": "system", "service": service})
        if system_key:
            return self._decrypt(system_key["value"])
            
        return None

    async def get_all_user_keys(self) -> List[Dict]:
        """Lists all services for which the user has set a key."""
        keys_cursor = self.keys_collection.find({"owner_id": self.user_id})
        user_keys = []
        async for key_doc in keys_cursor:
            user_keys.append({
                "service": key_doc["service"],
                "is_set": True
            })
        return user_keys
