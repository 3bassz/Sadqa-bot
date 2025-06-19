import os
import random
import datetime
import requests
import json
import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
                          ContextTypes, MessageHandler, filters)
from db import (add_user, get_all_subscribers, toggle_reminder, get_reminder_status, 
                get_reminder_enabled_users, remove_user, get_user_by_id, 
                save_user_location, get_user_location,
                save_user_points, get_user_points, save_user_achievement, get_user_achievements,
                save_dua_reaction, get_dua_reactions, cleanup_old_data, init_database,
                save_user_interaction, get_user_interactions, get_total_users_count,
                get_active_users_count, get_top_users_by_points)
from dotenv import load_dotenv
from messages import (WELCOME_MESSAGE, CHANGE_CITY_PROMPT, UNSUBSCRIBE_CONFIRM, PRAYER_ERROR, 
                     CITY_UPDATED, PRAYER_HEADER, UNKNOWN_ERROR, LOCATION_UPDATED,
                     REMINDER_ENABLED, REMINDER_DISABLED, POINTS_HEADER, POINTS_DISPLAY,
                     DUA_INTERACTION_AMEN, DUA_INTERACTION_LIKE, DUA_COMMENT_PROMPT,
                     FEEDBACK_PROMPT, FEEDBACK_THANKS, ADMIN_WELCOME, STATS_HEADER,
                     FRIDAY_MESSAGE, WEEKLY_CHALLENGES, ACHIEVEMENT_EARNED)

# إعداد نظام التسجيل المحسّن
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# تحميل البيانات مع معالجة أخطاء محسّنة
def load_text_data(filename: str) -> list:
    """تحميل البيانات النصية مع معالجة الأخطاء"""
    try:
        with open(filename, encoding="utf-8") as f:
            data = [line.strip() for line in f if line.strip()]
            logger.info(f"تم تحميل {len(data)} عنصر من {filename}")
            return data
    except FileNotFoundError:
        logger.error(f"ملف {filename} غير موجود")
        return []
    except Exception as e:
        logger.error(f"خطأ في تحميل {filename}: {e}")
        return []

AD3IYA_LIST = load_text_data("Ad3iya.txt")
VERSES_LIST = load_text_data("verses.txt")

# إزالة المتغيرات العامة المشكلة واستبدالها بحلول آمنة
sent_prayers = {}  # فقط للتتبع المؤقت لليوم الحالي

# إعدادات منظمة في فئة
class BotConfig:
    POPULAR_CITIES = {
        "القاهرة": {"lat": 30.0444, "lon": 31.2357, "timezone": 2},
        "الرياض": {"lat": 24.7136, "lon": 46.6753, "timezone": 3},
        "دبي": {"lat": 25.2048, "lon": 55.2708, "timezone": 4},
        "الكويت": {"lat": 29.3759, "lon": 47.9774, "timezone": 3},
        "الدوحة": {"lat": 25.2854, "lon": 51.5310, "timezone": 3},
        "بغداد": {"lat": 33.3152, "lon": 44.3661, "timezone": 3},
        "عمان": {"lat": 31.9454, "lon": 35.9284, "timezone": 2},
        "بيروت": {"lat": 33.8938, "lon": 35.5018, "timezone": 2},
        "دمشق": {"lat": 33.5138, "lon": 36.2765, "timezone": 2},
        "الدار البيضاء": {"lat": 33.5731, "lon": -7.5898, "timezone": 1}
    }
    
    ACHIEVEMENTS = {
        "first_prayer": {"name": "🌟 أول صلاة", "description": "أول تذكير صلاة", "points": 10},
        "week_streak": {"name": "🔥 أسبوع متواصل", "description": "7 أيام متتالية من الصلاة", "points": 50},
        "month_streak": {"name": "👑 شهر متواصل", "description": "30 يوم متتالية من الصلاة", "points": 200},
        "location_shared": {"name": "📍 مشارك الموقع", "description": "شارك موقعه لدقة أكبر", "points": 20},
        "feedback_giver": {"name": "💬 مقدم التغذية الراجعة", "description": "قدم تعليق أو اقتراح", "points": 15},
        "amen_lover": {"name": "🤲 محب الأدعية", "description": "تفاعل مع 10 أدعية", "points": 25},
        "commenter": {"name": "💬 معلق نشط", "description": "كتب 5 تعليقات على الأدعية", "points": 30}
    }
    
    PRAYER_MESSAGES = {
        "Fajr": "🏛 حان الآن وقت صلاة الفجر\n✨ ابدأ يومك بالصلاة، فهي نور.",
        "Dhuhr": "🏛 حان الآن وقت صلاة الظهر\n✨ لا تؤخر صلاتك فهي راحة للقلب.",
        "Asr": "🏛 حان الآن وقت صلاة العصر\n✨ من حافظ على العصر فهو في حفظ الله.",
        "Maghrib": "🏛 حان الآن وقت صلاة المغرب\n✨ صلاتك نورك يوم القيامة.",
        "Isha": "🏛 حان الآن وقت صلاة العشاء\n✨ نم على طهارة وصلاتك لختام اليوم."
    }

# فئة إدارة النقاط والإنجازات المحسّنة
class PointsManager:
    @staticmethod
    def add_user_points(user_id: int, points: int, reason: str = "") -> bool:
        """إضافة نقاط للمستخدم مع حفظ آمن في قاعدة البيانات"""
        try:
            current_points = get_user_points(user_id)
            new_total = current_points + points
            success = save_user_points(user_id, new_total)
            if success:
                logger.info(f"تم إضافة {points} نقطة للمستخدم {user_id} - {reason}")
            return success
        except Exception as e:
            logger.error(f"خطأ في إضافة النقاط للمستخدم {user_id}: {e}")
            return False

    @staticmethod
    def check_and_award_achievement(user_id: int, achievement_key: str) -> Optional[Dict[str, Any]]:
        """فحص ومنح الإنجازات مع حفظ آمن في قاعدة البيانات"""
        try:
            user_achievements = get_user_achievements(user_id)
            
            if achievement_key not in user_achievements:
                achievement = BotConfig.ACHIEVEMENTS.get(achievement_key)
                if achievement:
                    success = save_user_achievement(user_id, achievement_key)
                    if success:
                        PointsManager.add_user_points(user_id, achievement["points"], achievement["name"])
                        return achievement
            return None
        except Exception as e:
            logger.error(f"خطأ في فحص الإنجازات للمستخدم {user_id}: {e}")
            return None

    @staticmethod
    def get_user_stats_advanced(user_id: int) -> Dict[str, Any]:
        """الحصول على إحصائيات المستخدم المتقدمة مع معالجة الأخطاء"""
        try:
            points = get_user_points(user_id)
            achievements = get_user_achievements(user_id)
            return {
                "points": points,
                "achievements_count": len(achievements),
                "achievements": achievements
            }
        except Exception as e:
            logger.error(f"خطأ في جلب إحصائيات المستخدم {user_id}: {e}")
            return {"points": 0, "achievements_count": 0, "achievements": []}

# فئة إدارة التفاعلات المحسّنة (مُصححة)
class InteractionManager:
    @staticmethod
    def track_user_interaction(user_id: int, interaction_type: str) -> Optional[Dict[str, Any]]:
        """تتبع تفاعلات المستخدم مع حفظ آمن في قاعدة البيانات"""
        try:
            # حفظ التفاعل في قاعدة البيانات (مُصحح)
            success = save_user_interaction(user_id, interaction_type, 1)
            if not success:
                return None
            
            # فحص الإنجازات بناءً على عدد التفاعلات
            interactions = get_user_interactions(user_id)
            
            if interaction_type == "amen" and interactions.get("amen", 0) >= 10:
                return PointsManager.check_and_award_achievement(user_id, "amen_lover")
            
            if interaction_type == "comments" and interactions.get("comments", 0) >= 5:
                return PointsManager.check_and_award_achievement(user_id, "commenter")
            
            return None
        except Exception as e:
            logger.error(f"خطأ في تتبع التفاعل للمستخدم {user_id}: {e}")
            return None

# فئة إدارة مواعيد الصلاة المحسّنة
class PrayerManager:
    @staticmethod
    async def get_prayer_times(lat: float, lon: float) -> Optional[Dict[str, str]]:
        """جلب مواعيد الصلاة مع معالجة أخطاء شاملة ومهلة زمنية"""
        try:
            response = requests.get(
                f"http://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=5",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'timings' in data['data']:
                    return data['data']['timings']
                else:
                    logger.error("استجابة API غير صحيحة - بيانات مفقودة")
                    return None
            else:
                logger.error(f"خطأ في API مواعيد الصلاة: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            logger.error("انتهت مهلة الاتصال بـ API مواعيد الصلاة")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"خطأ في الاتصال بـ API مواعيد الصلاة: {e}")
            return None
        except Exception as e:
            logger.error(f"خطأ غير متوقع في جلب مواعيد الصلاة: {e}")
            return None

    @staticmethod
    def cleanup_sent_prayers():
        """تنظيف بيانات الصلوات المرسلة للأيام السابقة"""
        try:
            today_key = datetime.datetime.now().strftime("%Y-%m-%d")
            keys_to_remove = [key for key in sent_prayers.keys() if key != today_key]
            for key in keys_to_remove:
                del sent_prayers[key]
            if keys_to_remove:
                logger.info(f"تم تنظيف {len(keys_to_remove)} يوم من بيانات الصلوات")
        except Exception as e:
            logger.error(f"خطأ في تنظيف بيانات الصلوات: {e}")

# الدوال المفقودة المُضافة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دالة البداية المحسّنة"""
    try:
        user = update.effective_user
        if not user:
            return
            
        add_user(user.id, user.first_name or "مستخدم")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🕌 صلاتي اليوم", callback_data="today_prayers")],
            [InlineKeyboardButton("⏰ الصلاة القادمة", callback_data="next_prayer")],
            [InlineKeyboardButton("📍 اختيار مدينة", callback_data="select_city"),
             InlineKeyboardButton("📍 إرسال موقعي", callback_data="send_location")],
            [InlineKeyboardButton("🏆 نقاطي وإنجازاتي", callback_data="my_stats")],
            [InlineKeyboardButton("🔔 إعدادات التذكير", callback_data="toggle_reminder")],
            [InlineKeyboardButton("💬 تقييم البوت", callback_data="feedback")],
            [InlineKeyboardButton("🚫 إلغاء الاشتراك", callback_data="unsubscribe")]
        ])

        await update.message.reply_text(WELCOME_MESSAGE, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"خطأ في دالة start: {e}")
        try:
            await update.message.reply_text("❌ حدث خطأ، حاول مرة أخرى")
        except:
            pass

async def dash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المطور"""
    try:
        if update.effective_user.id != OWNER_ID:
            return
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 إحصائيات متقدمة", callback_data="advanced_stats")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="user_management")],
            [InlineKeyboardButton("📈 إحصائيات النقاط", callback_data="points_stats")],
            [InlineKeyboardButton("🔧 حالة النظام", callback_data="system_status")]
        ])
        
        await update.message.reply_text(ADMIN_WELCOME, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"خطأ في لوحة التحكم: {e}")

async def handle_user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار المستخدمين"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        if data == "today_prayers":
            location = get_user_location(user_id)
            if not location:
                await query.answer("📍 يرجى تحديد موقعك أولاً", show_alert=True)
                return
                
            timings = await PrayerManager.get_prayer_times(location['lat'], location['lon'])
            if timings:
                prayers_text = PRAYER_HEADER.format(city="موقعك") + "\n\n"
                for prayer in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                    prayers_text += f"{prayer}: {timings.get(prayer, 'غير متاح')}\n"
                await query.edit_message_text(prayers_text)
            else:
                await query.answer(PRAYER_ERROR, show_alert=True)
                
        elif data == "my_stats":
            stats = PointsManager.get_user_stats_advanced(user_id)
            stats_text = POINTS_HEADER + POINTS_DISPLAY.format(
                points=stats['points'],
                achievements=stats['achievements_count']
            )
            await query.edit_message_text(stats_text)
            
        elif data == "toggle_reminder":
            current_status = get_reminder_status(user_id)
            new_status = not current_status
            toggle_reminder(user_id, new_status)
            
            message = REMINDER_ENABLED if new_status else REMINDER_DISABLED
            await query.answer(message, show_alert=True)
            
        elif data == "feedback":
            context.user_data['mode'] = 'feedback'
            await query.edit_message_text(FEEDBACK_PROMPT)
            
        elif data == "unsubscribe":
            stats = PointsManager.get_user_stats_advanced(user_id)
            warning_text = UNSUBSCRIBE_CONFIRM.format(
                points=stats['points'],
                achievements=stats['achievements_count']
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ نعم، إلغاء الاشتراك", callback_data="confirm_unsubscribe")],
                [InlineKeyboardButton("❌ لا، العودة للقائمة", callback_data="back_to_menu")]
            ])
            
            await query.edit_message_text(warning_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"خطأ في معالجة أزرار المستخدمين: {e}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الموقع"""
    try:
        user_id = update.effective_user.id
        location = update.message.location
        
        success = save_user_location(user_id, location.latitude, location.longitude)
        if success:
            # منح إنجاز مشاركة الموقع
            achievement = PointsManager.check_and_award_achievement(user_id, "location_shared")
            
            message = LOCATION_UPDATED
            if achievement:
                message += f"\n\n{ACHIEVEMENT_EARNED.format(**achievement)}"
                
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ حدث خطأ في حفظ الموقع")
            
    except Exception as e:
        logger.error(f"خطأ في معالجة الموقع: {e}")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل"""
    try:
        user_id = update.effective_user.id
        text = update.message.text
        mode = context.user_data.get('mode')
        
        if mode == 'feedback':
            # حفظ التغذية الراجعة
            context.user_data.pop('mode', None)
            
            # إرسال للمطور
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"💬 تغذية راجعة من {update.effective_user.first_name} ({user_id}):\n\n{text}"
            )
            
            # منح نقاط وإنجاز
            PointsManager.add_user_points(user_id, 15, "تقديم تغذية راجعة")
            achievement = PointsManager.check_and_award_achievement(user_id, "feedback_giver")
            
            message = FEEDBACK_THANKS
            if achievement:
                message += f"\n\n{ACHIEVEMENT_EARNED.format(**achievement)}"
                
            await update.message.reply_text(message)
            
        elif mode == 'dua_comment':
            dua_id = context.user_data.get('dua_id')
            context.user_data.pop('mode', None)
            context.user_data.pop('dua_id', None)
            
            # حفظ التعليق
            save_dua_reaction(dua_id, "comments", 1, "dua")
            save_user_interaction(user_id, "comments", 1)
            
            # منح نقاط
            PointsManager.add_user_points(user_id, 5, "تعليق على دعاء")
            achievement = InteractionManager.track_user_interaction(user_id, "comments")
            
            message = "✅ تم حفظ تعليقك\n+5 نقاط"
            if achievement:
                message += f"\n\n{ACHIEVEMENT_EARNED.format(**achievement)}"
                
            await update.message.reply_text(message)
            
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسائل: {e}")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج callbacks المطور"""
    try:
        query = update.callback_query
        data = query.data
        
        if query.from_user.id != OWNER_ID:
            await query.answer("❌ ليس لديك صلاحية", show_alert=True)
            return
            
        if data == "advanced_stats":
            total_users = get_total_users_count()
            active_users = get_active_users_count()
            
            stats_text = STATS_HEADER + f"👥 إجمالي المستخدمين: {total_users}\n🔔 المستخدمين النشطين: {active_users}"
            await query.edit_message_text(stats_text)
            
    except Exception as e:
        logger.error(f"خطأ في معالجة callbacks المطور: {e}")

# باقي الدوال كما هي...
async def send_random_reminder(context: ContextTypes.DEFAULT_TYPE):
    """إرسال تذكير عشوائي محسّن مع معالجة أخطاء شاملة"""
    if not AD3IYA_LIST or not VERSES_LIST:
        logger.error("قوائم الآيات أو الأدعية فارغة")
        return
    
    success_count = 0
    failed_count = 0
    
    try:
        users = get_all_subscribers()
        if not users:
            logger.warning("لا يوجد مشتركين لإرسال التذكير")
            return
            
        for user in users:
            try:
                user_id = user.get('user_id')
                if not user_id:
                    continue
                    
                verse = random.choice(VERSES_LIST)
                dua = random.choice(AD3IYA_LIST)
                
                # إرسال الآية
                await context.bot.send_message(chat_id=user_id, text=verse)
                
                # إنشاء معرف فريد للدعاء
                dua_id = abs(hash(dua)) % 10000
                
                # الحصول على عدد التفاعلات من قاعدة البيانات
                reactions = get_dua_reactions(str(dua_id), "dua")
                amen_count = reactions.get("amen", 0)
                like_count = reactions.get("likes", 0)
                comment_count = reactions.get("comments", 0)
                
                # إنشاء أزرار التفاعل
                interaction_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🤲 اللهم آمين ({amen_count})", callback_data=f"amen_{dua_id}"),
                     InlineKeyboardButton(f"❤️ أعجبني ({like_count})", callback_data=f"like_{dua_id}")],
                    [InlineKeyboardButton(f"💬 أضف تعليق ({comment_count})", callback_data=f"comment_{dua_id}")]
                ])
                
                # إرسال الدعاء مع أزرار التفاعل
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=dua, 
                    reply_markup=interaction_keyboard
                )
                
                # إضافة نقاط للتفاعل
                PointsManager.add_user_points(user_id, 2, "تلقي تذكير ديني")
                success_count += 1
                
            except Exception as e:
                logger.error(f"خطأ في إرسال التذكير للمستخدم {user.get('user_id', 'unknown')}: {e}")
                failed_count += 1
                continue
        
        logger.info(f"تم إرسال التذكير العشوائي لـ {success_count} مستخدم، فشل مع {failed_count}")
        
    except Exception as e:
        logger.error(f"خطأ عام في إرسال التذكير العشوائي: {e}")

# باقي الدوال...
async def send_prayer_reminder(context: ContextTypes.DEFAULT_TYPE):
    """إرسال تذكير مواعيد الصلاة المحسّن مع معالجة أخطاء شاملة"""
    try:
        # تنظيف البيانات القديمة أولاً
        PrayerManager.cleanup_sent_prayers()
        
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        today_key = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        
        sent_prayers.setdefault(today_key, {})
        
        success_count = 0
        failed_count = 0
        
        users = get_reminder_enabled_users()
        if not users:
            return
            
        for user in users:
            try:
                user_id = user.get('user_id')
                location = user.get('location')
                
                if not user_id or not location:
                    continue
                    
                lat, lon = location.get('lat'), location.get('lon')
                if lat is None or lon is None:
                    continue
                    
                timings = await PrayerManager.get_prayer_times(lat, lon)
                
                if not timings:
                    failed_count += 1
                    continue
                
                # فحص الصلوات الخمس فقط
                for prayer_name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                    prayer_time = timings.get(prayer_name, "")[:5]
                    
                    if prayer_time == current_time:
                        user_prayers = sent_prayers[today_key].setdefault(user_id, [])
                        
                        if prayer_name not in user_prayers:
                            user_prayers.append(prayer_name)
                            
                            message = BotConfig.PRAYER_MESSAGES.get(
                                prayer_name, 
                                f"🏛 حان وقت صلاة {prayer_name}"
                            )
                            
                            await context.bot.send_message(chat_id=user_id, text=message)
                            logger.info(f"تم إرسال تذكير {prayer_name} للمستخدم {user_id}")
                            
                            # إضافة نقاط وفحص الإنجازات
                            PointsManager.add_user_points(user_id, 5, f"تذكير صلاة {prayer_name}")
                            
                            # فحص إنجاز أول صلاة
                            achievement = PointsManager.check_and_award_achievement(user_id, "first_prayer")
                            if achievement:
                                await context.bot.send_message(
                                    chat_id=user_id, 
                                    text=ACHIEVEMENT_EARNED.format(**achievement)
                                )
                            
                            success_count += 1
                            
            except Exception as e:
                logger.error(f"خطأ في إرسال تذكير الصلاة للمستخدم {user.get('user_id', 'unknown')}: {e}")
                failed_count += 1
                continue
        
        if success_count > 0 or failed_count > 0:
            logger.info(f"تذكير الصلاة: نجح {success_count}، فشل {failed_count}")
            
    except Exception as e:
        logger.error(f"خطأ عام في إرسال تذكير الصلاة: {e}")

# معالج التفاعلات المحسّن مع معالجة أخطاء شاملة
async def handle_dua_interactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تفاعلات الأدعية مع معالجة أخطاء شاملة"""
    try:
        query = update.callback_query
        if not query:
            return
            
        user_id = query.from_user.id
        data = query.data
        
        if data.startswith("amen_"):
            dua_id = data.replace("amen_", "")
            
            # تسجيل التفاعل في قاعدة البيانات
            success = save_dua_reaction(dua_id, "amen", 1, "dua")
            if not success:
                await query.answer("❌ حدث خطأ، حاول مرة أخرى", show_alert=True)
                return
            
            # إضافة نقاط للمستخدم
            PointsManager.add_user_points(user_id, 3, "تفاعل آمين مع دعاء")
            save_user_interaction(user_id, "amen", 1)
            achievement = InteractionManager.track_user_interaction(user_id, "amen")
            
            # الحصول على العدد المحدث
            reactions = get_dua_reactions(dua_id, "dua")
            amen_count = reactions.get("amen", 0)
            
            await query.answer(
                text=f"{DUA_INTERACTION_AMEN}\nإجمالي الآمين: {amen_count}", 
                show_alert=True
            )
            
            # تحديث الأزرار
            like_count = reactions.get("likes", 0)
            comment_count = reactions.get("comments", 0)
            
            updated_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🤲 اللهم آمين ({amen_count})", callback_data=f"amen_{dua_id}"),
                 InlineKeyboardButton(f"❤️ أعجبني ({like_count})", callback_data=f"like_{dua_id}")],
                [InlineKeyboardButton(f"💬 أضف تعليق ({comment_count})", callback_data=f"comment_{dua_id}")]
            ])
            
            try:
                await query.edit_message_reply_markup(reply_markup=updated_keyboard)
            except Exception as e:
                logger.warning(f"لا يمكن تحديث أزرار الرسالة: {e}")
            
            # إرسال رسالة إنجاز إذا حقق المستخدم إنجاز محب الأدعية
            if achievement:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=ACHIEVEMENT_EARNED.format(**achievement)
                )
        
        elif data.startswith("like_"):
            dua_id = data.replace("like_", "")
            
            # تسجيل الإعجاب
            success = save_dua_reaction(dua_id, "likes", 1, "dua")
            if not success:
                await query.answer("❌ حدث خطأ، حاول مرة أخرى", show_alert=True)
                return
            
            # إضافة نقاط للمستخدم
            PointsManager.add_user_points(user_id, 2, "إعجاب بدعاء")
            save_user_interaction(user_id, "likes", 1)
            
            # الحصول على العدد المحدث
            reactions = get_dua_reactions(dua_id, "dua")
            like_count = reactions.get("likes", 0)
            
            await query.answer(
                text=f"{DUA_INTERACTION_LIKE}\nإجمالي الإعجابات: {like_count}", 
                show_alert=True
            )
            
            # تحديث الأزرار
            amen_count = reactions.get("amen", 0)
            comment_count = reactions.get("comments", 0)
            
            updated_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🤲 اللهم آمين ({amen_count})", callback_data=f"amen_{dua_id}"),
                 InlineKeyboardButton(f"❤️ أعجبني ({like_count})", callback_data=f"like_{dua_id}")],
                [InlineKeyboardButton(f"💬 أضف تعليق ({comment_count})", callback_data=f"comment_{dua_id}")]
            ])
            
            try:
                await query.edit_message_reply_markup(reply_markup=updated_keyboard)
            except Exception as e:
                logger.warning(f"لا يمكن تحديث أزرار الرسالة: {e}")
        
        elif data.startswith("comment_"):
            dua_id = data.replace("comment_", "")
            
            # تفعيل وضع التعليق
            context.user_data['mode'] = 'dua_comment'
            context.user_data['dua_id'] = dua_id
            
            await query.answer("💬 اكتب تعليقك الآن", show_alert=True)
            await context.bot.send_message(
                chat_id=user_id,
                text=DUA_COMMENT_PROMPT
            )
            
    except Exception as e:
        logger.error(f"خطأ في معالجة تفاعل الدعاء: {e}")
        try:
            await query.answer("❌ حدث خطأ، حاول مرة أخرى", show_alert=True)
        except:
            pass

# باقي الدوال كما هي...
async def send_friday_message(context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة يوم الجمعة مع معالجة أخطاء"""
    try:
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        if now.weekday() == 4 and now.hour == 12:
            success_count = 0
            failed_count = 0
            
            for user in get_all_subscribers():
                try:
                    user_id = user.get('user_id')
                    if user_id:
                        await context.bot.send_message(chat_id=user_id, text=FRIDAY_MESSAGE)
                        PointsManager.add_user_points(user_id, 3, "رسالة الجمعة")
                        success_count += 1
                except Exception as e:
                    logger.error(f"خطأ في إرسال رسالة الجمعة للمستخدم {user.get('user_id', 'unknown')}: {e}")
                    failed_count += 1
                    continue
            
            logger.info(f"رسالة الجمعة: نجح {success_count}، فشل {failed_count}")
    except Exception as e:
        logger.error(f"خطأ عام في إرسال رسالة الجمعة: {e}")

async def send_weekly_challenge(context: ContextTypes.DEFAULT_TYPE):
    """إرسال التحدي الأسبوعي مع معالجة أخطاء"""
    try:
        now = datetime.datetime.now()
        if now.weekday() == 6 and now.hour == 10:  # الأحد 10 صباحاً
            weekly_challenge = random.choice(WEEKLY_CHALLENGES)
            
            success_count = 0
            failed_count = 0
            
            for user in get_all_subscribers():
                try:
                    user_id = user.get('user_id')
                    if user_id:
                        await context.bot.send_message(
                            chat_id=user_id, 
                            text=f"🎯 تحدي الأسبوع:\n{weekly_challenge}\n\n💪 هل تقبل التحدي؟"
                        )
                        success_count += 1
                except Exception as e:
                    logger.error(f"خطأ في إرسال التحدي الأسبوعي للمستخدم {user.get('user_id', 'unknown')}: {e}")
                    failed_count += 1
                    continue
            
            logger.info(f"التحدي الأسبوعي: نجح {success_count}، فشل {failed_count}")
    except Exception as e:
        logger.error(f"خطأ عام في إرسال التحدي الأسبوعي: {e}")

# تنظيف البيانات التلقائي
async def cleanup_old_data_job(context: ContextTypes.DEFAULT_TYPE):
    """تنظيف البيانات القديمة دورياً"""
    try:
        cleanup_old_data()  # دالة من قاعدة البيانات
        PrayerManager.cleanup_sent_prayers()
        logger.info("تم تنظيف البيانات القديمة بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تنظيف البيانات القديمة: {e}")

# معالج الأخطاء العام
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء العام للبوت"""[7][9]
    logger.error(f"Exception while handling an update: {context.error}")
    
    # إرسال تقرير خطأ للمطور
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"🚨 خطأ في البوت:\n{str(context.error)[:1000]}"
        )
    except Exception as e:
        logger.error(f"فشل في إرسال تقرير الخطأ: {e}")

if __name__ == '__main__':
    logger.info("🤖 بدء تشغيل بوت تليجرام المحسّن...")
    
    try:
        # تهيئة قاعدة البيانات
        init_database()
        
        # إنشاء التطبيق
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        # إضافة معالج الأخطاء العام
        app.add_error_handler(error_handler)

        # إضافة المعالجات المحسّنة
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("dash", dash))
        
        # معالجات الأزرار المنظمة
        app.add_handler(CallbackQueryHandler(handle_user_buttons, pattern="^(prayer_times|today_prayers|next_prayer|change_city|toggle_reminder|unsubscribe|send_location|select_city|my_stats|feedback|send_suggestion|city_|rate_|confirm_unsubscribe|back_to_menu)"))
        app.add_handler(CallbackQueryHandler(handle_callbacks, pattern="^(broadcast|announce|list_users|search_user|delete_user|count|status|test_broadcast|advanced_stats|growth_analytics|user_management|points_stats|system_status|manage_challenges|view_feedback|dua_stats)"))
        app.add_handler(CallbackQueryHandler(handle_dua_interactions, pattern="^(amen_|like_|comment_)"))

        # معالجات الرسائل
        app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_messages))
        app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.VIDEO_NOTE | filters.Sticker.ALL, handle_messages))

        # المهام المجدولة المحسّنة
        if app.job_queue:
            app.job_queue.run_repeating(send_random_reminder, interval=18000, first=10)
            app.job_queue.run_repeating(send_prayer_reminder, interval=300, first=30)
            app.job_queue.run_repeating(send_friday_message, interval=3600, first=60)
            app.job_queue.run_repeating(send_weekly_challenge, interval=3600, first=120)
            app.job_queue.run_repeating(cleanup_old_data_job, interval=86400, first=3600)  # تنظيف يومي
            logger.info("✅ تم تهيئة JobQueue بنجاح")
        else:
            logger.warning("❌ JobQueue غير متاح")

        # تشغيل البوت
        logger.info("✅ بوت صدقة المحسّن يعمل الآن...")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        raise
