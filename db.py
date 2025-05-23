import pymongo
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client["sadqa_bot"]
subscribers = db["subscribers"]

def add_user(user_id, name):
    if not subscribers.find_one({"user_id": user_id}):
        subscribers.insert_one({"user_id": user_id, "name": name, "reminder": False})

def get_all_subscribers():
    return list(subscribers.find({}, {"_id": 0}))

def toggle_reminder(user_id, enable):
    subscribers.update_one({"user_id": user_id}, {"$set": {"reminder": enable}})

def get_reminder_status(user_id):
    user = subscribers.find_one({"user_id": user_id}, {"_id": 0})
    return user.get("reminder", False) if user else False

def get_reminder_enabled_users():
    return list(subscribers.find({"reminder": True}, {"_id": 0}))

def remove_user(user_id):
    subscribers.delete_one({"user_id": user_id})

def get_user_by_id(user_id):
    return subscribers.find_one({"user_id": user_id}, {"_id": 0})