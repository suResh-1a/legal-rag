import os
from database.manager import DatabaseManager
from dotenv import load_dotenv, find_dotenv

env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path, override=True)

db = DatabaseManager()
db.reset_database()
print("Successfully wiped Mongo and Remote Qdrant databases for a fresh Universal Pipeline ingestion.")
