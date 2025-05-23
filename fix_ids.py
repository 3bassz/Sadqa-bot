from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["sadqa"]
subscribers = db["subscribers"]

fixed_count = 0

for doc in subscribers.find():
    uid = doc.get("user_id")
    if isinstance(uid, str):
        try:
            new_uid = int(uid)
            subscribers.update_one(
                {"_id": doc["_id"]},
                {"$set": {"user_id": new_uid}}
            )
            fixed_count += 1
        except ValueError:
            print(f"❌ غير قابل للتحويل: {uid}")

print(f"✅ تم تصحيح {fixed_count} من المعرفات.")
