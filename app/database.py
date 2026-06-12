from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.config import settings
from app.security import hash_password
from app.schemas import GeolocationResponse, UserCreate

try:
    from bson import ObjectId
    from pymongo import ASCENDING, DESCENDING
    from pymongo.errors import DuplicateKeyError
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    ObjectId = None
    ASCENDING = 1
    DESCENDING = -1
    DuplicateKeyError = Exception
    AsyncIOMotorClient = None


class MongoDatabase:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db = None
        self.ready = False
        self.error: str | None = None

    async def connect(self) -> None:
        if AsyncIOMotorClient is None:
            self.error = "Драйвер MongoDB не встановлено. Виконайте: pip install -r requirements.txt"
            return

        try:
            self.client = AsyncIOMotorClient(settings.mongo_url, serverSelectionTimeoutMS=3000)
            await self.client.admin.command("ping")
            self.db = self.client[settings.mongo_db]
            await self._create_indexes()
            self.ready = True
            self.error = None
        except Exception:
            self.ready = False
            self.error = "MongoDB недоступна. Перевірте, що сервер бази даних запущено на MONGO_URL."

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()

    def ensure_ready(self) -> None:
        if not self.ready or self.db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=self.error or "MongoDB тимчасово недоступна.",
            )

    async def _create_indexes(self) -> None:
        await self.db.users.create_index([("email", ASCENDING)], unique=True)
        await self.db.users.create_index([("username_key", ASCENDING)], unique=True)
        await self.db.lookups.create_index([("user_id", ASCENDING), ("requested_at", DESCENDING)])
        await self.db.lookups.create_index([("ip_address", ASCENDING)])

    async def create_user(self, user: UserCreate) -> dict[str, Any]:
        self.ensure_ready()
        document = {
            "username": user.username,
            "username_key": user.username.lower(),
            "email": user.email,
            "password_hash": hash_password(user.password),
            "created_at": datetime.now(timezone.utc),
        }

        try:
            result = await self.db.users.insert_one(document)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Користувач із таким email або іменем вже існує.",
            ) from exc

        document["_id"] = result.inserted_id
        return document

    async def get_user_by_login(self, login: str) -> dict[str, Any] | None:
        self.ensure_ready()
        normalized_login = login.strip().lower()
        return await self.db.users.find_one(
            {"$or": [{"email": normalized_login}, {"username_key": normalized_login}]}
        )

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        self.ensure_ready()
        if ObjectId is None:
            return None

        try:
            object_id = ObjectId(user_id)
        except Exception:
            return None

        return await self.db.users.find_one({"_id": object_id})

    async def save_lookup(
        self,
        user: dict[str, Any],
        ip_address: str,
        geolocation: GeolocationResponse,
    ) -> str:
        self.ensure_ready()
        document = {
            "user_id": str(user["_id"]),
            "user_username": user["username"],
            "ip_address": ip_address,
            "requested_at": geolocation.requested_at,
            "geolocation": geolocation.model_dump(mode="json"),
        }
        result = await self.db.lookups.insert_one(document)
        return str(result.inserted_id)

    async def get_history(self, user: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
        self.ensure_ready()
        cursor = (
            self.db.lookups.find({"user_id": str(user["_id"])})
            .sort("requested_at", DESCENDING)
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        return [serialize_lookup(document) for document in documents]


def serialize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "created_at": user["created_at"],
    }


def serialize_lookup(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "ip_address": document["ip_address"],
        "requested_at": document["requested_at"],
        "geolocation": document["geolocation"],
    }


database = MongoDatabase()
