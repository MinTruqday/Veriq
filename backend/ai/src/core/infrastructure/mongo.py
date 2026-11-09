from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database


class MongoClient:
    def __init__(self):
        self.db_name = settings.AI_DB_NAME

    def get_db(self):
        if not database.mongodb:
            raise RuntimeError("MongoDB is not initialized")
        return database.mongodb[self.db_name]

    async def find_one(self, collection: str, query: dict, projection: dict = None, **kwargs):
        return await self.get_db()[collection].find_one(query, projection, **kwargs)

    def find(
        self,
        collection: str,
        query: dict,
        projection: dict = None,
        sort=None,
        skip: int = 0,
        limit: int = 0,
    ):
        cursor = self.get_db()[collection].find(query, projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return cursor

    def aggregate(self, collection: str, pipeline: list):
        cursor = self.get_db()[collection].aggregate(pipeline)
        return cursor

    async def insert_one(self, collection: str, document: dict, **kwargs):
        return await self.get_db()[collection].insert_one(document, **kwargs)

    async def insert_many(self, collection: str, documents: list):
        return await self.get_db()[collection].insert_many(documents)

    async def update_one(self, collection: str, filter: dict, update: dict, upsert: bool = False):
        return await self.get_db()[collection].update_one(filter, update, upsert=upsert)

    async def update_many(self, collection: str, filter: dict, update: dict, upsert: bool = False):
        return await self.get_db()[collection].update_many(filter, update, upsert=upsert)

    async def delete_one(self, collection: str, filter: dict):
        return await self.get_db()[collection].delete_one(filter)

    async def delete_many(self, collection: str, filter: dict):
        return await self.get_db()[collection].delete_many(filter)

    async def count_documents(self, collection: str, filter: dict | None = None):
        return await self.get_db()[collection].count_documents(filter or {})

mongo = MongoClient()
