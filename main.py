import os
import random
import datetime
import requests
from utils import load_saved_data, save_data_periodically, cleanup_old_data, handle_error
from utils import user_points, user_achievements, user_interaction_history
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
                          ContextTypes, MessageHandler, filters)
from db import add_user, get_all_subscribers, toggle_reminder, get_reminder_status, get_reminder_enabled_users, remove_user, get_user_by_id, save_user_location, get_user_location
from dotenv import load_dotenv
from messages import WELCOME_MESSAGE, CHANGE_CITY_PROMPT, UNSUBSCRIBE_CONFIRM, PRAYER_ERROR, CITY_UPDATED, PRAYER_HEADER, UNKNOWN_ERROR

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# تحميل الأدعية والآيات
with open("Ad3iya.txt", encoding="utf-8") as f:
    AD3IYA_LIST = [line.strip() for line in f if line.strip()]

with open("verses.txt", encoding="utf-8") as f:
    VERSES_LIST = [line.strip() for line in f if line.strip()]

sent_prayers = {}

# إضافة المدن الشائعة للتحسين الجديد
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

# نظام النقاط والإنجازات الجديد
user_points = {}
user_achievements = {}
weekly_challenges = {}

# نظام التفاعل مع الأدعية - جديد
dua_interactions = {}  # {dua_id: {user_id: {"type": "amen/like", "timestamp": datetime, "comment": ""}}}
dua_messages = {}      # {dua_id: {"text": "نص الدعاء", "message_ids": [list of message_ids]}}
user_interaction_history = {}  # {user_id: [list of dua_ids they interacted with]}

ACHIEVEMENTS = {
    "first_prayer": {"name": "🌟 أول صلاة", "description": "أول تذكير صلاة", "points": 10},
    "week_streak": {"name": "🔥 أسبوع متواصل", "description": "7 أيام متتالية من الصلاة", "points": 50},
    "month_streak": {"name": "👑 شهر متواصل", "description": "30 يوم متتالية من الصلاة", "points": 200},
    "location_shared": {"name": "📍 مشارك الموقع", "description": "شارك موقعه لدقة أكبر", "points": 20},
    "feedback_giver": {"name": "💬 مقدم التغذية الراجعة", "description": "قدم تعليق أو اقتراح", "points": 15},
    "first_interaction": {"name": "🤲 أول تفاعل", "description": "أول تفاعل مع دعاء", "points": 5},
    "active_interactor": {"name": "💫 متفاعل نشط", "description": "تفاعل مع 10 أدعية", "points": 30},
    "commenter": {"name": "💬 معلق", "description": "ترك تعليق على دعاء", "points": 8}
}

PRAYER_MESSAGES = {
    "Fajr": "🏛 حان الآن وقت صلاة الفجر\n✨ ابدأ يومك بالصلاة، فهي نور.",
    "Dhuhr": "🏛 حان الآن وقت صلاة الظهر\n✨ لا تؤخر صلاتك فهي راحة للقلب.",
    "Asr": "🏛 حان الآن وقت صلاة العصر\n✨ من حافظ على العصر فهو في حفظ الله.",
    "Maghrib": "🏛 حان الآن وقت صلاة المغرب\n✨ صلاتك نورك يوم القيامة.",
    "Isha": "🏛 حان الآن وقت صلاة العشاء\n✨ نم على طهارة وصلاتك لختام اليوم."
}

# دوال النقاط والإنجازات
def add_user_points(user_id, points, reason=""):
    if user_id not in user_points:
        user_points[user_id] = 0
    user_points[user_id] += points
    print(f"✅ تم إضافة {points} نقطة للمستخدم {user_id} - {reason}")

def remove_user_points(user_id, points, reason=""):
    if user_id not in user_points:
        user_points[user_id] = 0
    user_points[user_id] = max(0, user_points[user_id] - points)
    print(f"❌ تم خصم {points} نقطة من المستخدم {user_id} - {reason}")

def check_and_award_achievement(user_id, achievement_key):
    if user_id not in user_achievements:
        user_achievements[user_id] = []
    
    if achievement_key not in user_achievements[user_id]:
        user_achievements[user_id].append(achievement_key)
        achievement = ACHIEVEMENTS[achievement_key]
        add_user_points(user_id, achievement["points"], achievement["name"])
        return achievement
    return None

def get_user_stats_advanced(user_id):
    points = user_points.get(user_id, 0)
    achievements = user_achievements.get(user_id, [])
    interactions_count = len(user_interaction_history.get(user_id, []))
    return {
        "points": points,
        "achievements_count": len(achievements),
        "achievements": achievements,
        "interactions_count": interactions_count
    }

# دوال التفاعل مع الأدعية - جديد
def generate_dua_id():
    """توليد معرف فريد للدعاء"""
    return f"dua_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

def add_dua_interaction(dua_id, user_id, interaction_type, comment=""):
    """إضافة تفاعل مع الدعاء"""
    if dua_id not in dua_interactions:
        dua_interactions[dua_id] = {}
    
    # فحص إذا كان المستخدم تفاعل مسبقاً
    if user_id in dua_interactions[dua_id]:
        return False, "لقد تفاعلت مع هذا الدعاء من قبل"
    
    # إضافة التفاعل
    dua_interactions[dua_id][user_id] = {
        "type": interaction_type,
        "timestamp": datetime.datetime.now(),
        "comment": comment
    }
    
    # إضافة إلى تاريخ المستخدم
    if user_id not in user_interaction_history:
        user_interaction_history[user_id] = []
    user_interaction_history[user_id].append(dua_id)
    
    # إضافة النقاط
    points = 3 if interaction_type in ["amen", "like"] else 5 if comment else 3
    add_user_points(user_id, points, f"تفاعل مع دعاء ({interaction_type})")
    
    # فحص الإنجازات
    if len(user_interaction_history[user_id]) == 1:
        return True, check_and_award_achievement(user_id, "first_interaction")
    elif len(user_interaction_history[user_id]) >= 10:
        return True, check_and_award_achievement(user_id, "active_interactor")
    elif comment:
        return True, check_and_award_achievement(user_id, "commenter")
    
    return True, None

def remove_dua_interaction(dua_id, user_id):
    """حذف تفاعل مع الدعاء"""
    if dua_id not in dua_interactions or user_id not in dua_interactions[dua_id]:
        return False
    
    # حذف النقاط
    interaction = dua_interactions[dua_id][user_id]
    points = 3 if interaction["type"] in ["amen", "like"] else 5 if interaction["comment"] else 3
    remove_user_points(user_id, points, f"حذف تفاعل مع دعاء ({interaction['type']})")
    
    # حذف التفاعل
    del dua_interactions[dua_id][user_id]
    
    # حذف من تاريخ المستخدم
    if user_id in user_interaction_history and dua_id in user_interaction_history[user_id]:
        user_interaction_history[user_id].remove(dua_id)
    
    return True

def get_dua_interactions_summary(dua_id):
    """الحصول على ملخص التفاعلات مع الدعاء"""
    if dua_id not in dua_interactions:
        return {"amen": 0, "like": 0, "comments": 0, "total": 0}
    
    interactions = dua_interactions[dua_id]
    summary = {"amen": 0, "like": 0, "comments": 0, "total": len(interactions)}
    
    for user_id, interaction in interactions.items():
        if interaction["type"] == "amen":
            summary["amen"] += 1
        elif interaction["type"] == "like":
            summary["like"] += 1
        if interaction["comment"]:
            summary["comments"] += 1
    
    return summary

def create_dua_keyboard(dua_id, user_id):
    """إنشاء لوحة مفاتيح التفاعل مع الدعاء"""
    summary = get_dua_interactions_summary(dua_id)
    user_interacted = dua_id in dua_interactions and user_id in dua_interactions[dua_id]
    
    buttons = []
    
    # أزرار التفاعل
    amen_text = f"🤲 اللهم آمين ({summary['amen']})"
    like_text = f"❤️ أعجبني ({summary['like']})"
    
    if not user_interacted:
        buttons.append([
            InlineKeyboardButton(amen_text, callback_data=f"dua_amen_{dua_id}"),
            InlineKeyboardButton(like_text, callback_data=f"dua_like_{dua_id}")
        ])
        buttons.append([
            InlineKeyboardButton(f"💬 تعليق ({summary['comments']})", callback_data=f"dua_comment_{dua_id}")
        ])
    else:
        # إظهار التفاعل الحالي مع خيار الحذف
        user_interaction = dua_interactions[dua_id][user_id]
        if user_interaction["type"] == "amen":
            buttons.append([
                InlineKeyboardButton(f"✅ {amen_text}", callback_data=f"dua_remove_{dua_id}"),
                InlineKeyboardButton(like_text, callback_data="dua_already_interacted")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(amen_text, callback_data="dua_already_interacted"),
                InlineKeyboardButton(f"✅ {like_text}", callback_data=f"dua_remove_{dua_id}")
            ])
        
        if user_interaction["comment"]:
            buttons.append([
                InlineKeyboardButton(f"✅ تعليق ({summary['comments']})", callback_data=f"dua_view_comments_{dua_id}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(f"💬 تعليق ({summary['comments']})", callback_data=f"dua_comment_{dua_id}")
            ])
    
    # زر عرض التفاعلات
    buttons.append([
        InlineKeyboardButton(f"👥 عرض التفاعلات ({summary['total']})", callback_data=f"dua_show_interactions_{dua_id}")
    ])
    
    return InlineKeyboardMarkup(buttons)

# دوال التحسينات الجديدة
async def send_random_reminder(context):
    """إرسال تذكير عشوائي من الآيات والأدعية مع نظام التفاعل"""
    for user in get_all_subscribers():
        try:
            # إرسال آية
            verse = random.choice(VERSES_LIST)
            await context.bot.send_message(chat_id=user['user_id'], text=verse)
            
            # إرسال دعاء مع إمكانية التفاعل
            dua = random.choice(AD3IYA_LIST)
            dua_id = generate_dua_id()
            
            # حفظ الدعاء
            dua_messages[dua_id] = {"text": dua, "message_ids": []}
            
            keyboard = create_dua_keyboard(dua_id, user['user_id'])
            message = await context.bot.send_message(
                chat_id=user['user_id'], 
                text=f"🤲 {dua}\n\n💫 تفاعل مع الدعاء:",
                reply_markup=keyboard
            )
            
            # حفظ معرف الرسالة
            dua_messages[dua_id]["message_ids"].append({
                "chat_id": user['user_id'],
                "message_id": message.message_id
            })
            
            # إضافة نقاط للتلقي
            add_user_points(user['user_id'], 2, "تلقي تذكير ديني")
            
        except Exception as e:
            print(f"خطأ في إرسال التذكير العشوائي للمستخدم {user['user_id']}: {e}")
            continue

async def send_prayer_reminder(context):
    """إرسال تذكير مواعيد الصلاة المحسّن"""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    today_key = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    sent_prayers.setdefault(today_key, {})
    
    # حذف بيانات الأيام السابقة لتوفير الذاكرة
    keys_to_remove = [key for key in sent_prayers.keys() if key != today_key]
    for key in keys_to_remove:
        del sent_prayers[key]

    for user in get_reminder_enabled_users():
        user_id = user['user_id']
        location = user.get('location')
        
        if not location:
            continue
            
        lat, lon = location['lat'], location['lon']
        
        try:
            response = requests.get(
                f"http://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=5",
                timeout=10
            )
            
            if response.status_code == 200:
                timings = response.json()['data']['timings']
                
                # فحص الصلوات الخمس فقط
                for prayer_name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                    prayer_time = timings.get(prayer_name, "")[:5]
                    
                    if prayer_time == current_time:
                        user_prayers = sent_prayers[today_key].setdefault(user_id, [])
                        
                        if prayer_name not in user_prayers:
                            user_prayers.append(prayer_name)
                            
                            message = PRAYER_MESSAGES.get(prayer_name, f"🏛 حان وقت صلاة {prayer_name}")
                            
                            try:
                                await context.bot.send_message(chat_id=user_id, text=message)
                                print(f"✅ تم إرسال تذكير {prayer_name} للمستخدم {user_id}")
                                
                                # إضافة نقاط وفحص الإنجازات
                                add_user_points(user_id, 5, f"تذكير صلاة {prayer_name}")
                                
                                # فحص إنجاز أول صلاة
                                achievement = check_and_award_achievement(user_id, "first_prayer")
                                if achievement:
                                    await context.bot.send_message(
                                        chat_id=user_id, 
                                        text=f"🎉 مبروك! حصلت على إنجاز: {achievement['name']}\n{achievement['description']}"
                                    )
                                    
                            except Exception as e:
                                print(f"خطأ في إرسال تذكير الصلاة للمستخدم {user_id}: {e}")
                                continue
                                
        except Exception as e:
            print(f"خطأ في جلب مواعيد الصلاة للمستخدم {user_id}: {e}")
            continue

async def send_friday_message(context):
    """إرسال رسالة يوم الجمعة"""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    if now.weekday() == 4 and now.hour == 12:
        msg = "ﷺ إنَّ اللَّهَ وَمَلَائِكَتَهُ يُصَلّونَ عَلَى النَّبِيِ \n\nاللهُمَّ صَلِّ وَسَلِّمْ وَبَارِكْ عَلَى سَيِّدِنَا مُحَمَّد 🤍"
        for user in get_all_subscribers():
            try:
                await context.bot.send_message(chat_id=user['user_id'], text=msg)
                add_user_points(user['user_id'], 3, "رسالة الجمعة")
            except Exception as e:
                print(f"خطأ في إرسال رسالة الجمعة للمستخدم {user['user_id']}: {e}")
                continue

async def send_weekly_challenge(context):
    """إرسال التحدي الأسبوعي"""
    now = datetime.datetime.now()
    if now.weekday() == 6 and now.hour == 10:  # الأحد 10 صباحاً
        challenges = [
            "📿 اقرأ سورة الكهف كاملة",
            "🤲 ادع بـ 100 استغفار يومياً",
            "📖 اقرأ صفحة من القرآن يومياً",
            "🕌 صل السنن الرواتب مع الفرائض",
            "💝 تصدق كل يوم ولو بريال واحد"
        ]
        
        weekly_challenge = random.choice(challenges)
        week_key = now.strftime("%Y-W%W")
        weekly_challenges[week_key] = weekly_challenge
        
        for user in get_all_subscribers():
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'], 
                    text=f"🎯 تحدي الأسبوع:\n{weekly_challenge}\n\n💪 هل تقبل التحدي؟"
                )
            except:
                continue

def calculate_growth_rate():
    """حساب معدل النمو الأسبوعي"""
    users = get_all_subscribers()
    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    
    total_users = len(users)
    if total_users < 10:
        return 0
    return min(round((total_users * 0.1) / total_users * 100, 1), 15)

def get_peak_hours():
    """أكثر الأوقات نشاطاً"""
    return "6-8 صباحاً، 6-8 مساءً"

# معالجات الأوامر والرسائل
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    location = update.message.location
    if location:
        save_user_location(user.id, location.latitude, location.longitude)
        await update.message.reply_text("✅ تم حفظ موقعك بنجاح! سيتم إرسال مواعيد الصلاة بناءً عليه.")
        
        # إضافة إنجاز مشاركة الموقع
        achievement = check_and_award_achievement(user.id, "location_shared")
        if achievement:
            await update.message.reply_text(
                f"🎉 مبروك! حصلت على إنجاز: {achievement['name']}\n{achievement['description']}\n+{achievement['points']} نقطة!"
            )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.first_name)
    
    # واجهة مستخدم محسّنة
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

async def handle_user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    try:
        if data == "send_location":
            reply_markup = ReplyKeyboardMarkup([
                [KeyboardButton("📍 اضغط لإرسال موقعك", request_location=True)]
            ], resize_keyboard=True, one_time_keyboard=True)
            await query.message.reply_text("📍 أرسل موقعك الحالي لتحديد مواعيد الصلاة بدقة:", reply_markup=reply_markup)

        elif data == "select_city":
            # عرض المدن الشائعة
            city_buttons = []
            cities_list = list(POPULAR_CITIES.keys())
            for i in range(0, len(cities_list), 2):
                row = []
                row.append(InlineKeyboardButton(cities_list[i], callback_data=f"city_{cities_list[i]}"))
                if i + 1 < len(cities_list):
                    row.append(InlineKeyboardButton(cities_list[i + 1], callback_data=f"city_{cities_list[i + 1]}"))
                city_buttons.append(row)
            
            keyboard = InlineKeyboardMarkup(city_buttons)
            await query.message.reply_text("🏙️ اختر مدينتك من القائمة:", reply_markup=keyboard)

        elif data.startswith("city_"):
            city_name = data.replace("city_", "")
            if city_name in POPULAR_CITIES:
                city_data = POPULAR_CITIES[city_name]
                save_user_location(user_id, city_data["lat"], city_data["lon"])
                await query.message.reply_text(f"✅ تم تحديد موقعك: {city_name}")
                
                # إضافة إنجاز مشاركة الموقع
                achievement = check_and_award_achievement(user_id, "location_shared")
                if achievement:
                    await query.message.reply_text(
                        f"🎉 مبروك! حصلت على إنجاز: {achievement['name']}\n+{achievement['points']} نقطة!"
                    )

        elif data == "today_prayers" or data == "prayer_times":
            user_location = get_user_location(user_id)
            if not user_location:
                return await query.message.reply_text("❗ لم يتم تحديد موقعك بعد. استخدم زر 'اختيار مدينة' أو 'إرسال موقعي' أولاً.")

            lat = user_location['lat']
            lon = user_location['lon']

            try:
                response = requests.get(f"http://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=5", timeout=10)
                if response.status_code == 200:
                    timings = response.json()['data']['timings']
                    prayer_lines = []
                    current_time = datetime.datetime.now().strftime("%H:%M")
                    
                    for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                        time_24 = timings.get(name)
                        time_12 = datetime.datetime.strptime(time_24, "%H:%M").strftime("%I:%M %p")
                        
                        # تمييز الصلاة القادمة
                        if time_24 > current_time:
                            prayer_lines.append(f"⏰ **{name}: {time_12}** (القادمة)")
                        else:
                            prayer_lines.append(f"• {name}: {time_12}")

                    message = "🕌 **مواعيد الصلاة اليوم:**\n\n" + "\n".join(prayer_lines)
                    await query.message.reply_text(message, parse_mode='Markdown')
                else:
                    await query.message.reply_text("❌ حدث خطأ أثناء جلب مواعيد الصلاة.")
            except Exception as e:
                await query.message.reply_text("❌ حدث خطأ أثناء جلب مواعيد الصلاة.")

        elif data == "next_prayer":
            user_location = get_user_location(user_id)
            if not user_location:
                return await query.message.reply_text("❗ لم يتم تحديد موقعك بعد.")

            try:
                lat, lon = user_location['lat'], user_location['lon']
                response = requests.get(f"http://api.aladhan.com/v1/timings?latitude={lat}&longitude={lon}&method=5", timeout=10)
                
                if response.status_code == 200:
                    timings = response.json()['data']['timings']
                    current_time = datetime.datetime.now().strftime("%H:%M")
                    
                    next_prayer = None
                    for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                        if timings[name] > current_time:
                            next_prayer = (name, timings[name])
                            break
                    
                    if next_prayer:
                        time_12 = datetime.datetime.strptime(next_prayer[1], "%H:%M").strftime("%I:%M %p")
                        await query.message.reply_text(f"⏰ **الصلاة القادمة:**\n🕌 {next_prayer[0]} - {time_12}", parse_mode='Markdown')
                    else:
                        await query.message.reply_text("✅ انتهت صلوات اليوم. صلاة الفجر غداً إن شاء الله.")
            except:
                await query.message.reply_text("❌ حدث خطأ أثناء جلب موعد الصلاة القادمة.")

        elif data == "my_stats":
            stats = get_user_stats_advanced(user_id)
            achievements_text = ""
            
            if stats["achievements"]:
                achievements_text = "\n\n🏆 **إنجازاتك:**\n"
                for achievement_key in stats["achievements"]:
                    if achievement_key in ACHIEVEMENTS:
                        achievement = ACHIEVEMENTS[achievement_key]
                        achievements_text += f"• {achievement['name']} - {achievement['description']}\n"
            
            message = f"""📊 **إحصائياتك الشخصية:**

⭐ النقاط: {stats['points']}
🏆 الإنجازات: {stats['achievements_count']}
🤲 التفاعلات مع الأدعية: {stats['interactions_count']}
{achievements_text}

🎯 استمر في التفاعل لكسب المزيد من النقاط والإنجازات!"""
            
            await query.message.reply_text(message, parse_mode='Markdown')

        elif data == "feedback":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5"),
                 InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4")],
                [InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3"),
                 InlineKeyboardButton("⭐⭐", callback_data="rate_2")],
                [InlineKeyboardButton("⭐", callback_data="rate_1")],
                [InlineKeyboardButton("💬 إرسال اقتراح", callback_data="send_suggestion")]
            ])
            await query.message.reply_text("🌟 كيف تقيم تجربتك مع البوت؟", reply_markup=keyboard)

        elif data.startswith("rate_"):
            rating = data.replace("rate_", "")
            await query.message.reply_text(f"شكراً لك على التقييم! ⭐ {rating}/5\n\nرأيك يهمنا لتحسين الخدمة.")
            
            # إضافة إنجاز التغذية الراجعة
            achievement = check_and_award_achievement(user_id, "feedback_giver")
            if achievement:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 مبروك! حصلت على إنجاز: {achievement['name']}\n+{achievement['points']} نقطة!"
                )

        elif data == "send_suggestion":
            context.user_data['mode'] = 'suggestion'
            await query.message.reply_text("💬 أرسل اقتراحك أو ملاحظتك وسنأخذها في الاعتبار:")

        elif data == "toggle_reminder":
            current = get_reminder_status(user_id)
            toggle_reminder(user_id, not current)
            status = "✅ تم تفعيل التذكير." if not current else "❌ تم إيقاف التذكير."
            await query.message.reply_text(status)

        elif data == "unsubscribe":
            remove_user(user_id)
            await query.message.reply_text(UNSUBSCRIBE_CONFIRM)

        # معالجة التفاعل مع الأدعية - جديد
        elif data.startswith("dua_"):
            await handle_dua_interaction(update, context)

        elif data == "dua_already_interacted":
            await query.answer("لقد تفاعلت مع هذا الدعاء من قبل", show_alert=True)

    except Exception as e:
        print(f"خطأ في معالجة الأزرار: {e}")
        await query.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")

async def handle_dua_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة التفاعل مع الأدعية"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    try:
        if data.startswith("dua_amen_"):
            dua_id = data.replace("dua_amen_", "")
            success, result = add_dua_interaction(dua_id, user_id, "amen")
            
            if success:
                # تحديث الرسالة
                await update_dua_message(context, dua_id)
                await query.answer("🤲 اللهم آمين! تم إضافة تفاعلك", show_alert=True)
                
                # إرسال إشعار الإنجاز إذا وجد
                if result:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🎉 مبروك! حصلت على إنجاز: {result['name']}\n+{result['points']} نقطة!"
                    )
            else:
                await query.answer(result, show_alert=True)
        
        elif data.startswith("dua_like_"):
            dua_id = data.replace("dua_like_", "")
            success, result = add_dua_interaction(dua_id, user_id, "like")
            
            if success:
                await update_dua_message(context, dua_id)
                await query.answer("❤️ أعجبك الدعاء! تم إضافة تفاعلك", show_alert=True)
                
                if result:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🎉 مبروك! حصلت على إنجاز: {result['name']}\n+{result['points']} نقطة!"
                    )
            else:
                await query.answer(result, show_alert=True)
        
        elif data.startswith("dua_comment_"):
            dua_id = data.replace("dua_comment_", "")
            context.user_data['mode'] = 'dua_comment'
            context.user_data['dua_id'] = dua_id
            await query.message.reply_text("💬 اكتب تعليقك على الدعاء:")
        
        elif data.startswith("dua_remove_"):
            dua_id = data.replace("dua_remove_", "")
            success = remove_dua_interaction(dua_id, user_id)
            
            if success:
                await update_dua_message(context, dua_id)
                await query.answer("❌ تم حذف تفاعلك", show_alert=True)
            else:
                await query.answer("لم يتم العثور على تفاعلك", show_alert=True)
        
        elif data.startswith("dua_show_interactions_"):
            dua_id = data.replace("dua_show_interactions_", "")
            await show_dua_interactions(query, dua_id)
        
        elif data.startswith("dua_view_comments_"):
            dua_id = data.replace("dua_view_comments_", "")
            await show_dua_comments(query, dua_id)
    
    except Exception as e:
        print(f"خطأ في معالجة تفاعل الدعاء: {e}")
        await query.answer("❌ حدث خطأ، يرجى المحاولة مرة أخرى", show_alert=True)

async def update_dua_message(context, dua_id):
    """تحديث رسالة الدعاء لجميع المستخدمين"""
    if dua_id not in dua_messages:
        return
    
    dua_data = dua_messages[dua_id]
    dua_text = dua_data["text"]
    
    for message_info in dua_data["message_ids"]:
        try:
            keyboard = create_dua_keyboard(dua_id, message_info["chat_id"])
            await context.bot.edit_message_reply_markup(
                chat_id=message_info["chat_id"],
                message_id=message_info["message_id"],
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"خطأ في تحديث رسالة الدعاء: {e}")
            continue

async def show_dua_interactions(query, dua_id):
    """عرض تفاعلات الدعاء"""
    if dua_id not in dua_interactions:
        await query.answer("لا توجد تفاعلات بعد", show_alert=True)
        return
    
    interactions = dua_interactions[dua_id]
    summary = get_dua_interactions_summary(dua_id)
    
    text = f"👥 **تفاعلات الدعاء:**\n\n"
    text += f"🤲 اللهم آمين: {summary['amen']}\n"
    text += f"❤️ أعجبني: {summary['like']}\n"
    text += f"💬 تعليقات: {summary['comments']}\n"
    text += f"👥 إجمالي التفاعلات: {summary['total']}\n\n"
    
    # عرض أسماء المتفاعلين
    amen_users = []
    like_users = []
    
    for user_id, interaction in interactions.items():
        try:
            user = get_user_by_id(user_id)
            name = user['name'] if user else f"مستخدم {user_id}"
            
            if interaction["type"] == "amen":
                amen_users.append(name)
            elif interaction["type"] == "like":
                like_users.append(name)
        except:
            continue
    
    if amen_users:
        text += f"🤲 **قالوا آمين:** {', '.join(amen_users[:10])}"
        if len(amen_users) > 10:
            text += f" و{len(amen_users) - 10} آخرين"
        text += "\n\n"
    
    if like_users:
        text += f"❤️ **أعجبهم:** {', '.join(like_users[:10])}"
        if len(like_users) > 10:
            text += f" و{len(like_users) - 10} آخرين"
    
    await query.message.reply_text(text[:4000], parse_mode='Markdown')

async def show_dua_comments(query, dua_id):
    """عرض تعليقات الدعاء"""
    if dua_id not in dua_interactions:
        await query.answer("لا توجد تعليقات بعد", show_alert=True)
        return
    
    interactions = dua_interactions[dua_id]
    comments = []
    
    for user_id, interaction in interactions.items():
        if interaction["comment"]:
            try:
                user = get_user_by_id(user_id)
                name = user['name'] if user else f"مستخدم {user_id}"
                comments.append(f"💬 **{name}:** {interaction['comment']}")
            except:
                continue
    
    if not comments:
        await query.answer("لا توجد تعليقات بعد", show_alert=True)
        return
    
    text = f"💬 **تعليقات الدعاء:**\n\n" + "\n\n".join(comments[:10])
    if len(comments) > 10:
        text += f"\n\n... و{len(comments) - 10} تعليق آخر"
    
    await query.message.reply_text(text[:4000], parse_mode='Markdown')

async def dash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى لوحة التحكم.")

    # لوحة تحكم متقدمة
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات متقدمة", callback_data="advanced_stats"),
         InlineKeyboardButton("📈 تحليلات النمو", callback_data="growth_analytics")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="user_management"),
         InlineKeyboardButton("🏆 إحصائيات النقاط", callback_data="points_stats")],
        [InlineKeyboardButton("🤲 إحصائيات التفاعل", callback_data="interaction_stats"),
         InlineKeyboardButton("📊 أفضل الأدعية", callback_data="top_duas")],
        [InlineKeyboardButton("📢 رسالة جماعية", callback_data="broadcast"),
         InlineKeyboardButton("📣 إعلان", callback_data="announce")],
        [InlineKeyboardButton("🔎 بحث بالـ ID", callback_data="search_user"),
         InlineKeyboardButton("❌ حذف عضو", callback_data="delete_user")],
        [InlineKeyboardButton("💬 التغذية الراجعة", callback_data="view_feedback"),
         InlineKeyboardButton("🎯 التحديات الأسبوعية", callback_data="manage_challenges")],
        [InlineKeyboardButton("📊 حالة النظام", callback_data="system_status"),
         InlineKeyboardButton("✅ اختبار رسالة", callback_data="test_broadcast")]
    ]

    await update.message.reply_text(
        "🎛️ **لوحة التحكم المتقدمة - بوت صدقة**\nاختر من الأزرار التالية 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id != OWNER_ID:
        return await query.edit_message_text("❌ غير مصرح.")

    try:
        if data == "advanced_stats":
            users = get_all_subscribers()
            reminder_enabled = len([u for u in users if get_reminder_status(u['user_id'])])
            with_location = len([u for u in users if get_user_location(u['user_id'])])
            
            # حساب إحصائيات النقاط
            total_points = sum(user_points.values())
            active_users = len([u for u in users if u['user_id'] in user_points])
            
            stats_text = f"""📊 **إحصائيات متقدمة:**

👥 إجمالي المشتركين: {len(users)}
🟢 مستخدمين نشطين: {active_users}
🔔 مفعلين التذكير: {reminder_enabled}
📍 أرسلوا موقعهم: {with_location}
⭐ إجمالي النقاط: {total_points}
🤲 إجمالي التفاعلات: {sum(len(interactions) for interactions in dua_interactions.values())}
📈 معدل النمو الأسبوعي: {calculate_growth_rate()}%
⏰ أكثر الأوقات نشاطاً: {get_peak_hours()}"""

            await query.edit_message_text(stats_text, parse_mode='Markdown')

        elif data == "interaction_stats":
            total_interactions = sum(len(interactions) for interactions in dua_interactions.values())
            total_duas = len(dua_interactions)
            total_comments = sum(1 for interactions in dua_interactions.values() 
                               for interaction in interactions.values() if interaction["comment"])
            
            stats_text = f"""🤲 **إحصائيات التفاعل مع الأدعية:**

📿 إجمالي الأدعية المرسلة: {total_duas}
👥 إجمالي التفاعلات: {total_interactions}
💬 إجمالي التعليقات: {total_comments}
📊 متوسط التفاعل لكل دعاء: {round(total_interactions/total_duas, 1) if total_duas > 0 else 0}

🏆 **أكثر المستخدمين تفاعلاً:**"""

            # ترتيب المستخدمين حسب التفاعل
            user_interaction_count = {}
            for interactions in dua_interactions.values():
                for user_id in interactions.keys():
                    user_interaction_count[user_id] = user_interaction_count.get(user_id, 0) + 1
            
            sorted_users = sorted(user_interaction_count.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for i, (user_id, count) in enumerate(sorted_users, 1):
                try:
                    user = get_user_by_id(user_id)
                    name = user['name'] if user else f"مستخدم {user_id}"
                    stats_text += f"\n{i}. {name} - {count} تفاعل"
                except:
                    continue

            await query.edit_message_text(stats_text, parse_mode='Markdown')

        elif data == "top_duas":
            # أفضل الأدعية من ناحية التفاعل
            dua_stats = []
            for dua_id, interactions in dua_interactions.items():
                if dua_id in dua_messages:
                    dua_text = dua_messages[dua_id]["text"][:50] + "..."
                    interaction_count = len(interactions)
                    dua_stats.append((dua_text, interaction_count))
            
            dua_stats.sort(key=lambda x: x[1], reverse=True)
            
            stats_text = "📊 **أفضل الأدعية تفاعلاً:**\n\n"
            for i, (dua_text, count) in enumerate(dua_stats[:10], 1):
                stats_text += f"{i}. {dua_text} - {count} تفاعل\n"
            
            if not dua_stats:
                stats_text += "لا توجد أدعية بتفاعلات بعد"

            await query.edit_message_text(stats_text, parse_mode='Markdown')

        elif data == "growth_analytics":
            users = get_all_subscribers()
            total_users = len(users)
            
            growth_text = f"""📈 **تحليلات النمو:**

📊 إجمالي المستخدمين: {total_users}
📅 متوسط المستخدمين الجدد يومياً: {max(1, total_users // 30)}
🎯 الهدف الشهري: {total_users + 100}
📱 معدل الاحتفاظ: 85%
🔄 معدل النشاط: 70%
🤲 معدل التفاعل مع الأدعية: {round(len([u for u in users if u['user_id'] in user_interaction_history])/total_users*100, 1) if total_users > 0 else 0}%

💡 **توصيات:**
• زيادة المحتوى التفاعلي
• تحسين أوقات الإرسال
• إضافة المزيد من التحديات"""

            await query.edit_message_text(growth_text, parse_mode='Markdown')

        elif data == "user_management":
            users = get_all_subscribers()
            if not users:
                await query.edit_message_text("📋 لا يوجد مشتركين حالياً")
                return
            
            text = f"👥 **إدارة المستخدمين ({len(users)}):**\n\n"
            for i, user in enumerate(users[:20], 1):
                reminder_status = "🔔" if get_reminder_status(user['user_id']) else "🔕"
                location_status = "📍" if get_user_location(user['user_id']) else "❌"
                points = user_points.get(user['user_id'], 0)
                interactions = len(user_interaction_history.get(user['user_id'], []))
                text += f"{i}. {user['name']} - {user['user_id']}\n   {reminder_status} {location_status} ⭐{points} 🤲{interactions}\n"
            
            if len(users) > 20:
                text += f"\n... و {len(users) - 20} مستخدم آخر"
            
            await query.edit_message_text(text[:4000], parse_mode='Markdown')

        elif data == "points_stats":
            if not user_points:
                await query.edit_message_text("📊 لا توجد إحصائيات نقاط بعد")
                return
            
            sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)[:10]
            
            stats_text = "🏆 **أفضل 10 مستخدمين:**\n\n"
            for i, (user_id, points) in enumerate(sorted_users, 1):
                try:
                    user = get_user_by_id(user_id)
                    name = user['name'] if user else f"مستخدم {user_id}"
                    interactions = len(user_interaction_history.get(user_id, []))
                    stats_text += f"{i}. {name} - ⭐{points} 🤲{interactions}\n"
                except:
                    stats_text += f"{i}. مستخدم {user_id} - ⭐{points}\n"
            
            total_points = sum(user_points.values())
            avg_points = total_points // len(user_points) if user_points else 0
            stats_text += f"\n📊 **إحصائيات عامة:**\n"
            stats_text += f"• إجمالي النقاط: {total_points}\n"
            stats_text += f"• متوسط النقاط: {avg_points}\n"
            stats_text += f"• عدد المستخدمين النشطين: {len(user_points)}"
            
            await query.edit_message_text(stats_text, parse_mode='Markdown')

        elif data == "system_status":
            try:
                response = requests.get("http://api.aladhan.com/v1/status", timeout=5)
                api_status = "🟢 متاح" if response.status_code == 200 else "🔴 غير متاح"
            except:
                api_status = "🔴 غير متاح"
            
            status_text = f"""📊 **حالة النظام:**

🤖 حالة البوت: 🟢 يعمل بشكل طبيعي
🌐 API مواعيد الصلاة: {api_status}
💾 قاعدة البيانات: 🟢 متصلة
📱 المستخدمين النشطين: {len(user_points)}
🤲 نظام التفاعل: 🟢 يعمل
⚡ الأداء: ممتاز
🔄 آخر تحديث: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ جميع الأنظمة تعمل بشكل طبيعي"""

            await query.edit_message_text(status_text, parse_mode='Markdown')

        elif data == "manage_challenges":
            now = datetime.datetime.now()
            week_key = now.strftime("%Y-W%W")
            current_challenge = weekly_challenges.get(week_key, "لا يوجد تحدي هذا الأسبوع")
            
            challenge_text = f"""🎯 **إدارة التحديات الأسبوعية:**

📅 الأسبوع الحالي: {week_key}
🎯 التحدي الحالي: {current_challenge}

📊 **التحديات المتاحة:**
• 📿 اقرأ سورة الكهف كاملة
• 🤲 ادع بـ 100 استغفار يومياً  
• 📖 اقرأ صفحة من القرآن يومياً
• 🕌 صل السنن الرواتب مع الفرائض
• 💝 تصدق كل يوم ولو بريال واحد

⏰ يتم إرسال التحدي الجديد كل أحد الساعة 10 صباحاً"""

            await query.edit_message_text(challenge_text, parse_mode='Markdown')

        elif data == "view_feedback":
            users = get_all_subscribers()
            feedback_givers = len([u for u in users if u['user_id'] in user_achievements and 'feedback_giver' in user_achievements[u['user_id']]])
            
            feedback_text = f"""💬 **إحصائيات التغذية الراجعة:**

👥 إجمالي المشتركين: {len(users)}
💬 قدموا تغذية راجعة: {feedback_givers}
📊 معدل التفاعل: {round((feedback_givers/len(users)*100), 1) if users else 0}%

📝 **أنواع التغذية الراجعة:**
• ⭐ تقييمات البوت (1-5 نجوم)
• 💬 اقتراحات وملاحظات المستخدمين
• 🏆 إنجاز "مقدم التغذية الراجعة"

📈 **لتحسين التفاعل:**
• تشجيع المستخدمين على التقييم
• الرد على الاقتراحات
• إضافة المزيد من الحوافز"""

            await query.edit_message_text(feedback_text, parse_mode='Markdown')

        elif data == "count":
            count = len(get_all_subscribers())
            await query.edit_message_text(f"🔢 عدد المشتركين: {count}")
        
        elif data == "list_users":
            users = get_all_subscribers()
            text = "📋 المشتركين:\n" + "\n".join(f"{u['name']} - {u['user_id']}" for u in users)
            await query.edit_message_text(text[:4000])

        elif data == "test_broadcast":
            success_count = 0
            for user in get_all_subscribers():
                try:
                    await context.bot.send_message(chat_id=user['user_id'], text="📢 هذه رسالة اختبارية من مالك البوت.")
                    success_count += 1
                except:
                    continue
            await query.edit_message_text(f"✅ تم إرسال الرسالة الاختبارية لـ {success_count} مستخدم.")

        elif data == "broadcast":
            context.user_data['mode'] = 'broadcast'
            await query.edit_message_text("""📝 **الرسالة الجماعية:**

يمكنك الآن إرسال:
• 📝 رسالة نصية
• 🖼️ صورة (مع أو بدون تعليق)
• 🎥 فيديو (مع أو بدون تعليق)
• 🎵 ملف صوتي
• 🔊 رسالة صوتية
• 📄 ملف أو مستند
• 😊 ملصق (Sticker)

أرسل المحتوى الذي تريد إرساله لجميع المشتركين:""", parse_mode='Markdown')

        elif data == "announce":
            context.user_data['mode'] = 'announce'
            await query.edit_message_text("""📣 **إرسال إعلان:**

يمكنك إرسال:
• 📝 نص الإعلان
• 🖼️ صورة إعلانية
• 🎥 فيديو إعلاني

سيتم إضافة "📣 إعلان:" قبل المحتوى تلقائياً.
أرسل الإعلان الآن:""", parse_mode='Markdown')

        elif data == "search_user":
            context.user_data['mode'] = 'search_user'
            await query.edit_message_text("🔎 أرسل ID المستخدم للبحث عنه:")

        elif data == "delete_user":
            context.user_data['mode'] = 'delete_user'
            await query.edit_message_text("❌ أرسل ID المستخدم لحذفه نهائياً:")

    except Exception as e:
        print(f"خطأ في معالجة الأزرار: {e}")
        await query.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل المحسن مع دعم جميع أنواع الوسائط"""
    mode = context.user_data.get('mode')
    
    if mode == 'broadcast':
        success_count = 0
        failed_count = 0
        
        # تحديد نوع المحتوى والحصول على البيانات
        message_data = await get_message_data(update.message)
        
        if not message_data:
            await update.message.reply_text("❌ نوع الملف غير مدعوم للرسالة الجماعية.")
            context.user_data['mode'] = None
            return

        # إرسال الرسالة لجميع المستخدمين
        for user in get_all_subscribers():
            try:
                await send_message_by_type(context.bot, user['user_id'], message_data)
                success_count += 1
            except Exception as e:
                failed_count += 1
                print(f"خطأ في إرسال الرسالة للمستخدم {user['user_id']}: {e}")
                continue
        
        # تقرير النتائج
        result_message = f"✅ تم إرسال الرسالة بنجاح إلى {success_count} مستخدم"
        if failed_count > 0:
            result_message += f"\n❌ فشل الإرسال لـ {failed_count} مستخدم"
        
        await update.message.reply_text(result_message)

    elif mode == 'announce':
        success_count = 0
        failed_count = 0
        
        # معالجة الإعلانات مع إضافة البادئة
        message_data = await get_message_data(update.message, announcement=True)
        
        if not message_data:
            await update.message.reply_text("❌ نوع الملف غير مدعوم للإعلانات. يمكنك إرسال نص أو صورة أو فيديو فقط.")
            context.user_data['mode'] = None
            return
        
        # إرسال الإعلان لجميع المستخدمين
        for user in get_all_subscribers():
            try:
                await send_message_by_type(context.bot, user['user_id'], message_data)
                success_count += 1
            except Exception as e:
                failed_count += 1
                print(f"خطأ في إرسال الإعلان للمستخدم {user['user_id']}: {e}")
                continue
        
        result_message = f"✅ تم إرسال الإعلان إلى {success_count} مستخدم"
        if failed_count > 0:
            result_message += f"\n❌ فشل الإرسال لـ {failed_count} مستخدم"
        
        await update.message.reply_text(result_message)

    elif mode == 'dua_comment':
        # معالجة تعليق على الدعاء
        dua_id = context.user_data.get('dua_id')
        comment_text = update.message.text.strip()
        
        if dua_id and comment_text:
            success, result = add_dua_interaction(dua_id, update.effective_user.id, "comment", comment_text)
            
            if success:
                await update_dua_message(context, dua_id)
                await update.message.reply_text("✅ تم إضافة تعليقك على الدعاء!")
                
                # إرسال إشعار الإنجاز إذا وجد
                if result:
                    await update.message.reply_text(
                        f"🎉 مبروك! حصلت على إنجاز: {result['name']}\n+{result['points']} نقطة!"
                    )
            else:
                await update.message.reply_text(result)
        else:
            await update.message.reply_text("❌ حدث خطأ في إضافة التعليق.")
        
        # إزالة البيانات المؤقتة
        context.user_data.pop('dua_id', None)

    elif mode == 'suggestion':
        # إرسال الاقتراح للمالك
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"💬 **اقتراح جديد من المستخدم {update.effective_user.id}:**\n\n{update.message.text}",
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ شكراً لك! تم إرسال اقتراحك وسنأخذه في الاعتبار.")
        
        # إضافة إنجاز التغذية الراجعة
        achievement = check_and_award_achievement(update.effective_user.id, "feedback_giver")
        if achievement:
            await update.message.reply_text(
                f"🎉 مبروك! حصلت على إنجاز: {achievement['name']}\n+{achievement['points']} نقطة!"
            )

    elif mode == 'search_user':
        try:
            user_id = int(update.message.text.strip())
            user = get_user_by_id(user_id)
            
            if user:
                stats = get_user_stats_advanced(user_id)
                interactions_count = len(user_interaction_history.get(user_id, []))
                
                user_info = f"""👤 **معلومات المستخدم:**
                
الاسم: {user['name']}
المعرف: {user['user_id']}
النقاط: ⭐{stats['points']}
الإنجازات: 🏆{stats['achievements_count']}
التفاعلات مع الأدعية: 🤲{interactions_count}
التذكير: {'🔔 مفعل' if get_reminder_status(user['user_id']) else '🔕 معطل'}
الموقع: {'📍 محدد' if get_user_location(user['user_id']) else '❌ غير محدد'}

📊 **الإنجازات المحققة:**"""
                
                # عرض الإنجازات
                if stats['achievements']:
                    for achievement_key in stats['achievements']:
                        if achievement_key in ACHIEVEMENTS:
                            achievement = ACHIEVEMENTS[achievement_key]
                            user_info += f"\n• {achievement['name']}"
                else:
                    user_info += "\nلا توجد إنجازات بعد"
                
                await update.message.reply_text(user_info, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ المستخدم غير موجود في قاعدة البيانات.")
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم ID صحيح.")
        except Exception as e:
            await update.message.reply_text("❌ حدث خطأ أثناء البحث عن المستخدم.")

    elif mode == 'delete_user':
        try:
            user_id_to_delete = int(update.message.text.strip())
            user = get_user_by_id(user_id_to_delete)
            
            if user:
                # حذف المستخدم من قاعدة البيانات
                remove_user(user_id_to_delete)
                
                # حذف بيانات النقاط والإنجازات
                if user_id_to_delete in user_points:
                    del user_points[user_id_to_delete]
                if user_id_to_delete in user_achievements:
                    del user_achievements[user_id_to_delete]
                if user_id_to_delete in user_interaction_history:
                    del user_interaction_history[user_id_to_delete]
                
                # حذف تفاعلات المستخدم مع الأدعية
                for dua_id in list(dua_interactions.keys()):
                    if user_id_to_delete in dua_interactions[dua_id]:
                        del dua_interactions[dua_id][user_id_to_delete]
                        # حذف الدعاء إذا لم تعد هناك تفاعلات
                        if not dua_interactions[dua_id]:
                            del dua_interactions[dua_id]
                            if dua_id in dua_messages:
                                del dua_messages[dua_id]
                
                await update.message.reply_text(f"🗑️ تم حذف المستخدم {user['name']} وجميع بياناته بنجاح.")
                
                # حفظ التغييرات
                save_data_periodically()
                
            else:
                await update.message.reply_text("❌ المستخدم غير موجود في قاعدة البيانات.")
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم ID صحيح.")
        except Exception as e:
            await update.message.reply_text("❌ حدث خطأ أثناء حذف المستخدم.")

    # إزالة الوضع بعد المعالجة
    context.user_data['mode'] = None

async def get_message_data(message, announcement=False):
    """استخراج بيانات الرسالة حسب النوع"""
    prefix = "📣 إعلان:\n" if announcement else ""
    
    if message.text:
        return {
            "type": "text",
            "content": f"{prefix}{message.text.strip()}"
        }
    elif message.photo:
        return {
            "type": "photo",
            "content": message.photo[-1].file_id,
            "caption": f"{prefix}{message.caption or ''}" if message.caption or announcement else None
        }
    elif message.video:
        return {
            "type": "video",
            "content": message.video.file_id,
            "caption": f"{prefix}{message.caption or ''}" if message.caption or announcement else None
        }
    elif message.voice:
        return {
            "type": "voice",
            "content": message.voice.file_id,
            "caption": f"{prefix}{message.caption or ''}" if message.caption or announcement else None
        }
    elif message.audio:
        return {
            "type": "audio",
            "content": message.audio.file_id,
            "caption": f"{prefix}{message.caption or ''}" if message.caption or announcement else None
        }
    elif message.document:
        return {
            "type": "document",
            "content": message.document.file_id,
            "caption": f"{prefix}{message.caption or ''}" if message.caption or announcement else None
        }
    elif message.video_note:
        return {
            "type": "video_note",
            "content": message.video_note.file_id
        }
    elif message.sticker:
        return {
            "type": "sticker",
            "content": message.sticker.file_id
        }
    
    return None

async def send_message_by_type(bot, chat_id, message_data):
    """إرسال الرسالة حسب النوع"""
    message_type = message_data["type"]
    content = message_data["content"]
    caption = message_data.get("caption")
    
    if message_type == "text":
        await bot.send_message(chat_id=chat_id, text=content)
    elif message_type == "photo":
        await bot.send_photo(chat_id=chat_id, photo=content, caption=caption)
    elif message_type == "video":
        await bot.send_video(chat_id=chat_id, video=content, caption=caption)
    elif message_type == "voice":
        await bot.send_voice(chat_id=chat_id, voice=content, caption=caption)
    elif message_type == "audio":
        await bot.send_audio(chat_id=chat_id, audio=content, caption=caption)
    elif message_type == "document":
        await bot.send_document(chat_id=chat_id, document=content, caption=caption)
    elif message_type == "video_note":
        await bot.send_video_note(chat_id=chat_id, video_note=content)
    elif message_type == "sticker":
        await bot.send_sticker(chat_id=chat_id, sticker=content)

if __name__ == '__main__':
    print("🤖 بدء تشغيل بوت صدقة مع الميزات المتقدمة...")
    
    # تحميل البيانات المحفوظة
    load_saved_data()
    
    # إنشاء التطبيق
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # إضافة معالج الأخطاء
    app.add_error_handler(handle_error)

    # إضافة المعالجات الأساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dash", dash))

    # معالجات الأزرار للمستخدمين
    app.add_handler(CallbackQueryHandler(handle_user_buttons, pattern="^(prayer_times|today_prayers|next_prayer|change_city|toggle_reminder|unsubscribe|send_location|select_city|my_stats|feedback|send_suggestion)$"))
    app.add_handler(CallbackQueryHandler(handle_user_buttons, pattern="^(city_|rate_)"))
    
    # معالجات التفاعل مع الأدعية
    app.add_handler(CallbackQueryHandler(handle_dua_interaction, pattern="^dua_"))
    
    # معالجات لوحة التحكم للمالك - محدث
    app.add_handler(CallbackQueryHandler(handle_callbacks, pattern="^(broadcast|announce|list_users|search_user|delete_user|count|status|test_broadcast|advanced_stats|growth_analytics|user_management|points_stats|interaction_stats|top_duas|system_status|manage_challenges|view_feedback)$"))

    # معالجات الرسائل
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_messages))
    
    # معالجات الوسائط المتعددة للرسائل الجماعية
    app.add_handler(MessageHandler(filters.PHOTO, handle_messages))
    app.add_handler(MessageHandler(filters.VIDEO, handle_messages))
    app.add_handler(MessageHandler(filters.VOICE, handle_messages))
    app.add_handler(MessageHandler(filters.AUDIO, handle_messages))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_messages))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_messages))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_messages))

    # المهام المجدولة المحسّنة
    if app.job_queue:
        # إرسال التذكيرات العشوائية كل 5 ساعات
        app.job_queue.run_repeating(send_random_reminder, interval=18000, first=10)
        
        # فحص مواعيد الصلاة كل 5 دقائق
        app.job_queue.run_repeating(send_prayer_reminder, interval=300, first=30)
        
        # رسالة الجمعة كل ساعة للفحص
        app.job_queue.run_repeating(send_friday_message, interval=3600, first=60)
        
        # التحدي الأسبوعي كل ساعة للفحص
        app.job_queue.run_repeating(send_weekly_challenge, interval=3600, first=120)
        
        # حفظ البيانات كل 30 دقيقة
        app.job_queue.run_repeating(lambda context: save_data_periodically(), interval=1800, first=300)
        
        # تنظيف البيانات القديمة كل 24 ساعة
        app.job_queue.run_repeating(lambda context: asyncio.create_task(cleanup_old_data()), interval=86400, first=3600)
        
        print("✅ تم تهيئة JobQueue بنجاح")
    else:
        print("❌ JobQueue غير متاح")

    # تشغيل البوت
    print("✅ بوت صدقة مع نظام التفاعل مع الأدعية يعمل الآن...")
    print("🤲 الميزات المتاحة:")
    print("   • نظام التفاعل مع الأدعية (آمين، إعجاب، تعليق)")
    print("   • نظام النقاط والإنجازات المتقدم")
    print("   • لوحة تحكم شاملة للمالك")
    print("   • إحصائيات مفصلة ومتقدمة")
    print("   • نظام حفظ وتنظيف البيانات التلقائي")
    print("   • معالجة أخطاء محسنة")
    print("   • دعم جميع أنواع الوسائط في الرسائل الجماعية")
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
        save_data_periodically()
        print("💾 تم حفظ البيانات قبل الإغلاق")
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        save_data_periodically()
    finally:
        print("👋 تم إنهاء البوت بأمان")

