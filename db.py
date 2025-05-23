from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["my_bot_db"]
subscribers = db["subscribers"]

def get_all_subscribers():
    return list(subscribers.find({}, {"_id": 0}))
