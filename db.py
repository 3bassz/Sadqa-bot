import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client["sadqa_bot"]
subscribers = db["subscribers"]

# إضافة مستخدم جديد
def add_user(user_id, name):
    if not subscribers.find_one({"user_id": user_id}):
        subscribers.insert_one({
            "user_id": user_id,
            "name": name,
            "reminder": False,
            "location": None
        })

# جلب كل المشتركين
def get_all_subscribers():
    return list(subscribers.find({}, {"_id": 0}))

# تفعيل/إلغاء تذكير الصلاة
def toggle_reminder(user_id, enable):
    subscribers.update_one({"user_id": user_id}, {"$set": {"reminder": enable}})

# حالة التذكير للمستخدم
def get_reminder_status(user_id):
    user = subscribers.find_one({"user_id": user_id}, {"_id": 0, "reminder": 1})
    return user.get("reminder", False) if user else False

# جلب المشتركين المفعّل لديهم التذكير
def get_reminder_enabled_users():
    return list(subscribers.find({"reminder": True}, {"_id": 0}))

# حذف مستخدم
def remove_user(user_id):
    subscribers.delete_one({"user_id": user_id})

# جلب بيانات مستخدم معين
def get_user_by_id(user_id):
    return subscribers.find_one({"user_id": user_id}, {"_id": 0})

# حفظ موقع المستخدم
def save_user_location(user_id, lat, lon):
    subscribers.update_one(
        {"user_id": user_id},
        {"$set": {"location": {"lat": lat, "lon": lon}}}
    )

# جلب موقع المستخدم
def get_user_location(user_id):
    user = subscribers.find_one({"user_id": user_id}, {"_id": 0, "location": 1})
    return user.get("location") if user else None
