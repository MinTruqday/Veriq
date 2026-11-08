from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.core.infrastructure.mongo import mongo


class AgentRepository:
    @staticmethod
    def _get_db():
        db_name = settings.AI_DB_NAME
        return database.mongodb.get_database(db_name)

    @classmethod
    async def insert_trace(cls, *args, **kwargs):
        return await mongo.insert_one("agent_traces", *args, **kwargs)

    @classmethod
    async def insert_one(cls, *args, **kwargs):
        return await mongo.insert_one("agent_traces", *args, **kwargs)

    @classmethod
    async def insert_many(cls, *args, **kwargs):
        return await mongo.insert_many("agent_traces", *args, **kwargs)

    @classmethod
    async def find_one(cls, *args, **kwargs):
        return await mongo.find_one("agent_traces", *args, **kwargs)

    @classmethod
    async def update_one(cls, *args, **kwargs):
        return await mongo.update_one("agent_traces", *args, **kwargs)

    @classmethod
    async def update_many(cls, *args, **kwargs):
        return await mongo.update_many("agent_traces", *args, **kwargs)

    @classmethod
    async def delete_one(cls, *args, **kwargs):
        return await mongo.delete_one("agent_traces", *args, **kwargs)

    @classmethod
    async def delete_many(cls, *args, **kwargs):
        return await mongo.delete_many("agent_traces", *args, **kwargs)

    @classmethod
    async def count_documents(cls, *args, **kwargs):
        return await mongo.count_documents("agent_traces", *args, **kwargs)

    @classmethod
    def find(cls, *args, **kwargs):
        return mongo.find("agent_traces", *args, **kwargs)

    @classmethod
    def aggregate(cls, *args, **kwargs):
        return mongo.aggregate("agent_traces", *args, **kwargs)

    @classmethod
    def query(cls, *args, **kwargs):
        return mongo.query("agent_traces", *args, **kwargs)
