from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from app.core.config import settings

mongo_client = MongoClient(settings.MONGO_URI)
memory_saver = MongoDBSaver(mongo_client, db_name=settings.DATABASE_NAME)