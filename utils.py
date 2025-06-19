import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# إعداد التسجيل
logger = logging.getLogger(__name__)

# المتغيرات العامة - متوافقة مع الكود الأساسي
user_points = {}
user_achievements = {}
user_interaction_history = {}
dua_interactions = {}
dua_messages = {}
weekly_challenges = {}

# ملف البيانات
DATA_FILE = "bot_data.json"

def load_saved_data():
    """تحميل البيانات المحفوظة من الملف"""
    global user_points, user_achievements, user_interaction_history
    global dua_interactions, dua_messages, weekly_challenges
    
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # تحميل البيانات الأساسية
                user_points = data.get("user_points", {})
                user_achievements = data.get("user_achievements", {})
                user_interaction_history = data.get("user_interaction_history", {})
                
                # تحميل البيانات الجديدة
                dua_interactions = data.get("dua_interactions", {})
                dua_messages = data.get("dua_messages", {})
                weekly_challenges = data.get("weekly_challenges", {})
                
                # تحويل مفاتيح المستخدمين إلى int للتوافق
                user_points = {int(k) if str(k).isdigit() else k: v for k, v in user_points.items()}
                user_achievements = {int(k) if str(k).isdigit() else k: v for k, v in user_achievements.items()}
                user_interaction_history = {int(k) if str(k).isdigit() else k: v for k, v in user_interaction_history.items()}
                
                # تحويل timestamps في dua_interactions
                for dua_id, interactions in dua_interactions.items():
                    for user_id, interaction_data in interactions.items():
                        if isinstance(interaction_data.get("timestamp"), str):
                            try:
                                interaction_data["timestamp"] = datetime.fromisoformat(interaction_data["timestamp"])
                            except:
                                interaction_data["timestamp"] = datetime.now()
                
                logger.info("✅ تم تحميل البيانات المحفوظة بنجاح")
                print("✅ تم تحميل البيانات المحفوظة بنجاح")
        else:
            logger.info("📝 لا توجد بيانات محفوظة، بدء جديد")
            print("📝 لا توجد بيانات محفوظة، بدء جديد")
            
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل البيانات: {e}")
        print(f"❌ خطأ في تحميل البيانات: {e}")
        # تهيئة البيانات الفارغة في حالة الخطأ
        user_points = {}
        user_achievements = {}
        user_interaction_history = {}
        dua_interactions = {}
        dua_messages = {}
        weekly_challenges = {}

def save_data_periodically():
    """حفظ البيانات دورياً في الملف"""
    try:
        # تحضير البيانات للحفظ
        data_to_save = {
            "user_points": {str(k): v for k, v in user_points.items()},
            "user_achievements": {str(k): v for k, v in user_achievements.items()},
            "user_interaction_history": {str(k): v for k, v in user_interaction_history.items()},
            "dua_interactions": {},
            "dua_messages": dua_messages,
            "weekly_challenges": weekly_challenges,
            "last_save": datetime.now().isoformat(),
            "version": "2.0"
        }
        
        # تحويل dua_interactions للحفظ
        for dua_id, interactions in dua_interactions.items():
            data_to_save["dua_interactions"][dua_id] = {}
            for user_id, interaction_data in interactions.items():
                interaction_copy = interaction_data.copy()
                if isinstance(interaction_copy.get("timestamp"), datetime):
                    interaction_copy["timestamp"] = interaction_copy["timestamp"].isoformat()
                data_to_save["dua_interactions"][dua_id][str(user_id)] = interaction_copy
        
        # حفظ البيانات
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
        logger.info("💾 تم حفظ البيانات بنجاح")
        print("💾 تم حفظ البيانات بنجاح")
        
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ البيانات: {e}")
        print(f"❌ خطأ في حفظ البيانات: {e}")

async def cleanup_old_data():
    """تنظيف البيانات القديمة"""
    try:
        current_time = datetime.now()
        cutoff_date = current_time - timedelta(days=30)
        
        # تنظيف التفاعلات القديمة مع الأدعية
        cleaned_interactions = 0
        for dua_id in list(dua_interactions.keys()):
            interactions = dua_interactions[dua_id]
            for user_id in list(interactions.keys()):
                interaction_data = interactions[user_id]
                timestamp = interaction_data.get("timestamp")
                
                if isinstance(timestamp, datetime) and timestamp < cutoff_date:
                    del interactions[user_id]
                    cleaned_interactions += 1
            
            # حذف الدعاء إذا لم تعد هناك تفاعلات
            if not interactions:
                del dua_interactions[dua_id]
                if dua_id in dua_messages:
                    del dua_messages[dua_id]
        
        # تنظيف التحديات الأسبوعية القديمة
        cleaned_challenges = 0
        for week_key in list(weekly_challenges.keys()):
            try:
                # استخراج السنة والأسبوع من المفتاح
                if week_key.startswith("20"):  # تنسيق السنة
                    year_week = week_key.split("-W")
                    if len(year_week) == 2:
                        year = int(year_week[0])
                        week = int(year_week[1])
                        
                        # حساب تاريخ بداية الأسبوع
                        week_start = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
                        
                        if week_start < cutoff_date:
                            del weekly_challenges[week_key]
                            cleaned_challenges += 1
            except:
                continue
        
        # تنظيف رسائل الأدعية اليتيمة (بدون تفاعلات)
        cleaned_messages = 0
        for dua_id in list(dua_messages.keys()):
            if dua_id not in dua_interactions:
                del dua_messages[dua_id]
                cleaned_messages += 1
        
        # حفظ البيانات بعد التنظيف
        if cleaned_interactions > 0 or cleaned_challenges > 0 or cleaned_messages > 0:
            save_data_periodically()
        
        logger.info(f"🧹 تم تنظيف البيانات: {cleaned_interactions} تفاعل، {cleaned_challenges} تحدي، {cleaned_messages} رسالة")
        print(f"🧹 تم تنظيف البيانات: {cleaned_interactions} تفاعل، {cleaned_challenges} تحدي، {cleaned_messages} رسالة")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تنظيف البيانات: {e}")
        print(f"❌ خطأ في تنظيف البيانات: {e}")

async def handle_error(update, context):
    """معالج الأخطاء المحسن"""
    try:
        error_message = str(context.error)
        logger.error(f"❌ خطأ غير متوقع: {error_message}")
        print(f"❌ خطأ غير متوقع: {error_message}")
        
        # محاولة إرسال رسالة للمستخدم
        if update and update.effective_user:
            try:
                chat_id = update.effective_chat.id if update.effective_chat else update.effective_user.id
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❗ حدث خطأ مؤقت. يرجى المحاولة مرة أخرى."
                )
            except Exception as send_error:
                logger.error(f"فشل في إرسال رسالة الخطأ: {send_error}")
                
        # حفظ البيانات في حالة الخطأ الحرج
        if "critical" in error_message.lower() or "database" in error_message.lower():
            save_data_periodically()
            
    except Exception as e:
        logger.error(f"خطأ في معالج الأخطاء نفسه: {e}")
        print(f"خطأ في معالج الأخطاء نفسه: {e}")

# دوال مساعدة إضافية للتوافق مع الكود الأساسي

def get_user_stats(user_id: int) -> Dict[str, Any]:
    """الحصول على إحصائيات المستخدم"""
    try:
        points = user_points.get(user_id, 0)
        achievements = user_achievements.get(user_id, [])
        interactions = user_interaction_history.get(user_id, [])
        
        return {
            "points": points,
            "achievements_count": len(achievements),
            "achievements": achievements,
            "interactions_count": len(interactions)
        }
    except Exception as e:
        logger.error(f"خطأ في جلب إحصائيات المستخدم {user_id}: {e}")
        return {"points": 0, "achievements_count": 0, "achievements": [], "interactions_count": 0}

def backup_user_data(user_id: int) -> Dict[str, Any]:
    """إنشاء نسخة احتياطية لبيانات مستخدم معين"""
    try:
        backup_data = {
            "user_id": user_id,
            "points": user_points.get(user_id, 0),
            "achievements": user_achievements.get(user_id, []),
            "interaction_history": user_interaction_history.get(user_id, []),
            "backup_timestamp": datetime.now().isoformat()
        }
        
        # إضافة تفاعلات الأدعية للمستخدم
        user_dua_interactions = {}
        for dua_id, interactions in dua_interactions.items():
            if str(user_id) in interactions or user_id in interactions:
                user_interaction = interactions.get(str(user_id)) or interactions.get(user_id)
                if user_interaction:
                    interaction_copy = user_interaction.copy()
                    if isinstance(interaction_copy.get("timestamp"), datetime):
                        interaction_copy["timestamp"] = interaction_copy["timestamp"].isoformat()
                    user_dua_interactions[dua_id] = interaction_copy
        
        backup_data["dua_interactions"] = user_dua_interactions
        
        return backup_data
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية للمستخدم {user_id}: {e}")
        return {}

def restore_user_data(backup_data: Dict[str, Any]) -> bool:
    """استعادة بيانات مستخدم من النسخة الاحتياطية"""
    try:
        user_id = backup_data.get("user_id")
        if not user_id:
            return False
        
        # استعادة البيانات الأساسية
        user_points[user_id] = backup_data.get("points", 0)
        user_achievements[user_id] = backup_data.get("achievements", [])
        user_interaction_history[user_id] = backup_data.get("interaction_history", [])
        
        # استعادة تفاعلات الأدعية
        user_dua_interactions = backup_data.get("dua_interactions", {})
        for dua_id, interaction_data in user_dua_interactions.items():
            if dua_id not in dua_interactions:
                dua_interactions[dua_id] = {}
            
            interaction_copy = interaction_data.copy()
            if isinstance(interaction_copy.get("timestamp"), str):
                try:
                    interaction_copy["timestamp"] = datetime.fromisoformat(interaction_copy["timestamp"])
                except:
                    interaction_copy["timestamp"] = datetime.now()
            
            dua_interactions[dua_id][user_id] = interaction_copy
        
        # حفظ البيانات المستعادة
        save_data_periodically()
        
        logger.info(f"تم استعادة بيانات المستخدم {user_id} بنجاح")
        return True
        
    except Exception as e:
        logger.error(f"خطأ في استعادة بيانات المستخدم: {e}")
        return False

def get_system_stats() -> Dict[str, Any]:
    """الحصول على إحصائيات النظام العامة"""
    try:
        total_users = len(user_points)
        total_achievements = sum(len(achievements) for achievements in user_achievements.values())
        total_interactions = sum(len(history) for history in user_interaction_history.values())
        total_dua_interactions = sum(len(interactions) for interactions in dua_interactions.values())
        total_duas = len(dua_messages)
        total_challenges = len(weekly_challenges)
        
        # حساب إجمالي النقاط
        total_points = sum(user_points.values())
        
        # حساب متوسط النقاط
        avg_points = total_points / total_users if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "total_points": total_points,
            "avg_points": round(avg_points, 2),
            "total_achievements": total_achievements,
            "total_interactions": total_interactions,
            "total_dua_interactions": total_dua_interactions,
            "total_duas": total_duas,
            "total_challenges": total_challenges,
            "data_file_size": os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0,
            "last_update": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"خطأ في جلب إحصائيات النظام: {e}")
        return {}

# دالة تهيئة البيانات عند بدء التشغيل
def initialize_data():
    """تهيئة البيانات عند بدء التشغيل"""
    try:
        load_saved_data()
        logger.info("✅ تم تهيئة نظام البيانات بنجاح")
        print("✅ تم تهيئة نظام البيانات بنجاح")
    except Exception as e:
        logger.error(f"❌ فشل في تهيئة نظام البيانات: {e}")
        print(f"❌ فشل في تهيئة نظام البيانات: {e}")

# تشغيل التهيئة عند استيراد الملف
if __name__ != "__main__":
    initialize_data()
