import pymongo
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

# إعداد التسجيل
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client["sadqa_bot"]

# المجموعات المحسّنة
subscribers = db["subscribers"]
user_points = db["user_points"]
user_achievements = db["user_achievements"]
dua_reactions = db["dua_reactions"]
user_interactions = db["user_interactions"]
# إضافة مجموعات جديدة للتوافق مع الكود الأساسي
dua_interactions = db["dua_interactions"]
dua_messages = db["dua_messages"]
weekly_challenges = db["weekly_challenges"]

def init_database():
    """تهيئة قاعدة البيانات مع الفهارس المطلوبة"""
    try:
        # إنشاء فهارس للأداء الأمثل
        subscribers.create_index("user_id", unique=True)
        user_points.create_index("user_id", unique=True)
        user_achievements.create_index([("user_id", 1), ("achievement_key", 1)], unique=True)
        dua_reactions.create_index([("item_id", 1), ("reaction_type", 1), ("item_type", 1)], unique=True)
        user_interactions.create_index([("user_id", 1), ("interaction_type", 1)], unique=True)
        # فهارس جديدة
        dua_interactions.create_index([("dua_id", 1), ("user_id", 1)], unique=True)
        dua_messages.create_index("dua_id", unique=True)
        weekly_challenges.create_index("week_key", unique=True)
        
        logger.info("تم تهيئة قاعدة البيانات MongoDB بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")

# الدوال الأساسية المحسّنة
def add_user(user_id: int, name: str):
    """إضافة مستخدم جديد مع تهيئة النقاط"""
    try:
        if not subscribers.find_one({"user_id": user_id}):
            # إضافة المستخدم
            subscribers.insert_one({
                "user_id": user_id,
                "name": name,
                "reminder": True,  # تفعيل التذكير افتراضياً
                "location": None,
                "created_at": datetime.now()
            })
            
            # تهيئة النقاط
            user_points.insert_one({
                "user_id": user_id,
                "points": 0,
                "last_updated": datetime.now()
            })
            
            logger.info(f"تم إضافة مستخدم جديد: {user_id}")
    except Exception as e:
        logger.error(f"خطأ في إضافة المستخدم {user_id}: {e}")

def get_all_subscribers():
    """جلب كل المشتركين مع معالجة الأخطاء"""
    try:
        return list(subscribers.find({}, {"_id": 0}))
    except Exception as e:
        logger.error(f"خطأ في جلب المشتركين: {e}")
        return []

def toggle_reminder(user_id: int, enable: bool):
    """تفعيل/إلغاء تذكير الصلاة"""
    try:
        result = subscribers.update_one(
            {"user_id": user_id}, 
            {"$set": {"reminder": enable, "updated_at": datetime.now()}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"خطأ في تحديث التذكير للمستخدم {user_id}: {e}")
        return False

def get_reminder_status(user_id: int) -> bool:
    """حالة التذكير للمستخدم"""
    try:
        user = subscribers.find_one({"user_id": user_id}, {"_id": 0, "reminder": 1})
        return user.get("reminder", False) if user else False
    except Exception as e:
        logger.error(f"خطأ في جلب حالة التذكير للمستخدم {user_id}: {e}")
        return False

def get_reminder_enabled_users():
    """جلب المشتركين المفعّل لديهم التذكير"""
    try:
        return list(subscribers.find(
            {"reminder": True}, 
            {"_id": 0, "user_id": 1, "location": 1, "name": 1}
        ))
    except Exception as e:
        logger.error(f"خطأ في جلب المستخدمين المفعّل لديهم التذكير: {e}")
        return []

def remove_user(user_id: int):
    """حذف مستخدم وجميع بياناته"""
    try:
        # حذف من جميع المجموعات
        subscribers.delete_one({"user_id": user_id})
        user_points.delete_one({"user_id": user_id})
        user_achievements.delete_many({"user_id": user_id})
        user_interactions.delete_many({"user_id": user_id})
        # حذف تفاعلات الأدعية
        dua_interactions.delete_many({"user_id": user_id})
        
        logger.info(f"تم حذف المستخدم {user_id} وجميع بياناته")
    except Exception as e:
        logger.error(f"خطأ في حذف المستخدم {user_id}: {e}")

def get_user_by_id(user_id: int):
    """جلب بيانات مستخدم معين"""
    try:
        return subscribers.find_one({"user_id": user_id}, {"_id": 0})
    except Exception as e:
        logger.error(f"خطأ في جلب بيانات المستخدم {user_id}: {e}")
        return None

def save_user_location(user_id: int, lat: float, lon: float):
    """حفظ موقع المستخدم"""
    try:
        result = subscribers.update_one(
            {"user_id": user_id},
            {"$set": {
                "location": {"lat": lat, "lon": lon},
                "location_updated_at": datetime.now()
            }}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"خطأ في حفظ موقع المستخدم {user_id}: {e}")
        return False

def get_user_location(user_id: int):
    """جلب موقع المستخدم"""
    try:
        user = subscribers.find_one({"user_id": user_id}, {"_id": 0, "location": 1})
        return user.get("location") if user else None
    except Exception as e:
        logger.error(f"خطأ في جلب موقع المستخدم {user_id}: {e}")
        return None

# دوال النقاط الجديدة - محدثة للتوافق مع الكود الأساسي
def save_user_points(user_id: int, points: int) -> bool:
    """حفظ نقاط المستخدم"""
    try:
        result = user_points.update_one(
            {"user_id": user_id},
            {"$set": {
                "points": points,
                "last_updated": datetime.now()
            }},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"خطأ في حفظ النقاط للمستخدم {user_id}: {e}")
        return False

def get_user_points(user_id: int) -> int:
    """جلب نقاط المستخدم"""
    try:
        user = user_points.find_one({"user_id": user_id}, {"_id": 0, "points": 1})
        return user.get("points", 0) if user else 0
    except Exception as e:
        logger.error(f"خطأ في جلب النقاط للمستخدم {user_id}: {e}")
        return 0

def add_user_points(user_id: int, points: int, reason: str = ""):
    """إضافة نقاط للمستخدم"""
    try:
        current_points = get_user_points(user_id)
        new_points = current_points + points
        save_user_points(user_id, new_points)
        logger.info(f"تم إضافة {points} نقطة للمستخدم {user_id} - {reason}")
    except Exception as e:
        logger.error(f"خطأ في إضافة النقاط للمستخدم {user_id}: {e}")

def remove_user_points(user_id: int, points: int, reason: str = ""):
    """خصم نقاط من المستخدم"""
    try:
        current_points = get_user_points(user_id)
        new_points = max(0, current_points - points)
        save_user_points(user_id, new_points)
        logger.info(f"تم خصم {points} نقطة من المستخدم {user_id} - {reason}")
    except Exception as e:
        logger.error(f"خطأ في خصم النقاط للمستخدم {user_id}: {e}")

# دوال الإنجازات الجديدة - محدثة
def save_user_achievement(user_id: int, achievement_key: str) -> bool:
    """حفظ إنجاز المستخدم"""
    try:
        result = user_achievements.update_one(
            {"user_id": user_id, "achievement_key": achievement_key},
            {"$set": {
                "user_id": user_id,
                "achievement_key": achievement_key,
                "earned_at": datetime.now()
            }},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"خطأ في حفظ الإنجاز للمستخدم {user_id}: {e}")
        return False

def get_user_achievements(user_id: int) -> List[str]:
    """جلب إنجازات المستخدم"""
    try:
        achievements = user_achievements.find(
            {"user_id": user_id}, 
            {"_id": 0, "achievement_key": 1}
        )
        return [achievement["achievement_key"] for achievement in achievements]
    except Exception as e:
        logger.error(f"خطأ في جلب الإنجازات للمستخدم {user_id}: {e}")
        return []

def check_and_award_achievement(user_id: int, achievement_key: str):
    """فحص وإعطاء الإنجاز للمستخدم"""
    try:
        existing_achievements = get_user_achievements(user_id)
        if achievement_key not in existing_achievements:
            save_user_achievement(user_id, achievement_key)
            return True
        return False
    except Exception as e:
        logger.error(f"خطأ في فحص الإنجاز للمستخدم {user_id}: {e}")
        return False

# دوال تفاعلات الأدعية الجديدة - محدثة للتوافق مع الكود الأساسي
def save_dua_interaction(dua_id: str, user_id: int, interaction_type: str) -> bool:
    """حفظ تفاعل مع دعاء"""
    try:
        result = dua_interactions.update_one(
            {"dua_id": dua_id, "user_id": user_id},
            {"$set": {
                "dua_id": dua_id,
                "user_id": user_id,
                "interaction_type": interaction_type,
                "timestamp": datetime.now()
            }},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"خطأ في حفظ تفاعل الدعاء: {e}")
        return False

def remove_dua_interaction(dua_id: str, user_id: int) -> bool:
    """حذف تفاعل مع دعاء"""
    try:
        result = dua_interactions.delete_one({"dua_id": dua_id, "user_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"خطأ في حذف تفاعل الدعاء: {e}")
        return False

def get_dua_interactions_summary(dua_id: str) -> Dict[str, int]:
    """جلب ملخص تفاعلات دعاء"""
    try:
        pipeline = [
            {"$match": {"dua_id": dua_id}},
            {"$group": {
                "_id": "$interaction_type",
                "count": {"$sum": 1}
            }}
        ]
        
        results = list(dua_interactions.aggregate(pipeline))
        summary = {"amen": 0, "like": 0, "total": 0}
        
        for result in results:
            if result["_id"] in ["amen", "like"]:
                summary[result["_id"]] = result["count"]
                summary["total"] += result["count"]
                
        return summary
    except Exception as e:
        logger.error(f"خطأ في جلب ملخص التفاعلات: {e}")
        return {"amen": 0, "like": 0, "total": 0}

def check_user_dua_interaction(dua_id: str, user_id: int) -> Optional[str]:
    """فحص إذا كان المستخدم تفاعل مع الدعاء"""
    try:
        interaction = dua_interactions.find_one(
            {"dua_id": dua_id, "user_id": user_id},
            {"_id": 0, "interaction_type": 1}
        )
        return interaction.get("interaction_type") if interaction else None
    except Exception as e:
        logger.error(f"خطأ في فحص تفاعل المستخدم: {e}")
        return None

def get_user_interaction_history(user_id: int) -> List[str]:
    """جلب تاريخ تفاعلات المستخدم مع الأدعية"""
    try:
        interactions = dua_interactions.find(
            {"user_id": user_id},
            {"_id": 0, "dua_id": 1}
        )
        return [interaction["dua_id"] for interaction in interactions]
    except Exception as e:
        logger.error(f"خطأ في جلب تاريخ التفاعلات للمستخدم {user_id}: {e}")
        return []

# دوال رسائل الأدعية
def save_dua_message(dua_id: str, text: str, message_ids: List[Dict]) -> bool:
    """حفظ رسالة دعاء"""
    try:
        result = dua_messages.update_one(
            {"dua_id": dua_id},
            {"$set": {
                "dua_id": dua_id,
                "text": text,
                "message_ids": message_ids,
                "created_at": datetime.now()
            }},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"خطأ في حفظ رسالة الدعاء: {e}")
        return False

def get_dua_message(dua_id: str) -> Optional[Dict]:
    """جلب رسالة دعاء"""
    try:
        return dua_messages.find_one({"dua_id": dua_id}, {"_id": 0})
    except Exception as e:
        logger.error(f"خطأ في جلب رسالة الدعاء: {e}")
        return None

# دوال التحديات الأسبوعية
def save_weekly_challenge(week_key: str, challenge_text: str) -> bool:
    """حفظ التحدي الأسبوعي"""
    try:
        result = weekly_challenges.update_one(
            {"week_key": week_key},
            {"$set": {
                "week_key": week_key,
                "challenge_text": challenge_text,
                "created_at": datetime.now()
            }},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"خطأ في حفظ التحدي الأسبوعي: {e}")
        return False

def get_weekly_challenge(week_key: str) -> Optional[str]:
    """جلب التحدي الأسبوعي"""
    try:
        challenge = weekly_challenges.find_one(
            {"week_key": week_key},
            {"_id": 0, "challenge_text": 1}
        )
        return challenge.get("challenge_text") if challenge else None
    except Exception as e:
        logger.error(f"خطأ في جلب التحدي الأسبوعي: {e}")
        return None

# دوال تفاعلات الأدعية القديمة - للتوافق مع الكود الموجود
def save_dua_reaction(item_id: str, reaction_type: str, count: int, item_type: str = "dua") -> bool:
    """حفظ تفاعل مع دعاء"""
    try:
        result = dua_reactions.update_one(
            {"item_id": item_id, "reaction_type": reaction_type, "item_type": item_type},
            {"$inc": {"count": count}, "$set": {"last_updated": datetime.now()}},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"خطأ في حفظ التفاعل: {e}")
        return False

def get_dua_reactions(item_id: str, item_type: str = "dua") -> Dict[str, int]:
    """جلب تفاعلات دعاء"""
    try:
        reactions_data = dua_reactions.find(
            {"item_id": item_id, "item_type": item_type},
            {"_id": 0, "reaction_type": 1, "count": 1}
        )
        
        reactions = {"amen": 0, "likes": 0, "comments": 0}
        for reaction in reactions_data:
            reactions[reaction["reaction_type"]] = reaction["count"]
            
        return reactions
    except Exception as e:
        logger.error(f"خطأ في جلب التفاعلات: {e}")
        return {"amen": 0, "likes": 0, "comments": 0}

# دوال تتبع تفاعلات المستخدمين
def save_user_interaction(user_id: int, interaction_type: str, count: int = 1) -> bool:
    """حفظ تفاعل المستخدم"""
    try:
        result = user_interactions.update_one(
            {"user_id": user_id, "interaction_type": interaction_type},
            {"$inc": {"count": count}, "$set": {"last_updated": datetime.now()}},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"خطأ في حفظ تفاعل المستخدم {user_id}: {e}")
        return False

def get_user_interactions(user_id: int) -> Dict[str, int]:
    """جلب تفاعلات المستخدم"""
    try:
        interactions_data = user_interactions.find(
            {"user_id": user_id},
            {"_id": 0, "interaction_type": 1, "count": 1}
        )
        
        interactions = {}
        for interaction in interactions_data:
            interactions[interaction["interaction_type"]] = interaction["count"]
            
        return interactions
    except Exception as e:
        logger.error(f"خطأ في جلب تفاعلات المستخدم {user_id}: {e}")
        return {}

# دوال الإحصائيات المتقدمة
def get_total_users_count() -> int:
    """جلب إجمالي عدد المستخدمين"""
    try:
        return subscribers.count_documents({})
    except Exception as e:
        logger.error(f"خطأ في جلب عدد المستخدمين: {e}")
        return 0

def get_active_users_count() -> int:
    """جلب عدد المستخدمين النشطين (الذين فعلوا التذكير)"""
    try:
        return subscribers.count_documents({"reminder": True})
    except Exception as e:
        logger.error(f"خطأ في جلب عدد المستخدمين النشطين: {e}")
        return 0

def get_top_users_by_points(limit: int = 10) -> List[Dict]:
    """جلب أفضل المستخدمين بالنقاط"""
    try:
        pipeline = [
            {"$lookup": {
                "from": "subscribers",
                "localField": "user_id",
                "foreignField": "user_id",
                "as": "user_info"
            }},
            {"$unwind": "$user_info"},
            {"$sort": {"points": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "user_id": 1,
                "points": 1,
                "name": "$user_info.name"
            }}
        ]
        
        return list(user_points.aggregate(pipeline))
    except Exception as e:
        logger.error(f"خطأ في جلب أفضل المستخدمين: {e}")
        return []

def get_total_reactions_count() -> Dict[str, int]:
    """جلب إجمالي عدد التفاعلات"""
    try:
        pipeline = [
            {"$group": {
                "_id": "$interaction_type",
                "total": {"$sum": 1}
            }}
        ]
        
        results = list(dua_interactions.aggregate(pipeline))
        reactions = {"amen": 0, "like": 0, "total": 0}
        
        for result in results:
            if result["_id"] in ["amen", "like"]:
                reactions[result["_id"]] = result["total"]
                reactions["total"] += result["total"]
                
        return reactions
    except Exception as e:
        logger.error(f"خطأ في جلب إجمالي التفاعلات: {e}")
        return {"amen": 0, "like": 0, "total": 0}

# تنظيف البيانات القديمة
def cleanup_old_data():
    """تنظيف البيانات القديمة"""
    try:
        # حذف التفاعلات الأقدم من 30 يوم
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        result = dua_reactions.delete_many({
            "last_updated": {"$lt": thirty_days_ago}
        })
        
        logger.info(f"تم حذف {result.deleted_count} تفاعل قديم")
        
        # تنظيف التفاعلات الصفرية
        zero_reactions = dua_reactions.delete_many({"count": {"$lte": 0}})
        logger.info(f"تم حذف {zero_reactions.deleted_count} تفاعل صفري")
        
        # تنظيف رسائل الأدعية القديمة
        old_messages = dua_messages.delete_many({
            "created_at": {"$lt": thirty_days_ago}
        })
        logger.info(f"تم حذف {old_messages.deleted_count} رسالة دعاء قديمة")
        
    except Exception as e:
        logger.error(f"خطأ في تنظيف البيانات القديمة: {e}")

# دوال البحث والتصفية
def search_users_by_name(name: str, limit: int = 10) -> List[Dict]:
    """البحث عن المستخدمين بالاسم"""
    try:
        return list(subscribers.find(
            {"name": {"$regex": name, "$options": "i"}},
            {"_id": 0}
        ).limit(limit))
    except Exception as e:
        logger.error(f"خطأ في البحث عن المستخدمين: {e}")
        return []

def get_users_by_location_exists() -> List[Dict]:
    """جلب المستخدمين الذين لديهم موقع محفوظ"""
    try:
        return list(subscribers.find(
            {"location": {"$ne": None}},
            {"_id": 0, "user_id": 1, "name": 1, "location": 1}
        ))
    except Exception as e:
        logger.error(f"خطأ في جلب المستخدمين بالموقع: {e}")
        return []

# دوال النسخ الاحتياطي والاستعادة
def backup_user_data(user_id: int) -> Dict[str, Any]:
    """إنشاء نسخة احتياطية لبيانات المستخدم"""
    try:
        user_data = get_user_by_id(user_id)
        points = get_user_points(user_id)
        achievements = get_user_achievements(user_id)
        interactions = get_user_interactions(user_id)
        interaction_history = get_user_interaction_history(user_id)
        
        return {
            "user_data": user_data,
            "points": points,
            "achievements": achievements,
            "interactions": interactions,
            "interaction_history": interaction_history,
            "backup_date": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية للمستخدم {user_id}: {e}")
        return {}

# تهيئة قاعدة البيانات عند الاستيراد
try:
    init_database()
except Exception as e:
    logger.error(f"فشل في تهيئة قاعدة البيانات: {e}")