# Sadqa Bot Final - main.py (نسخة كاملة بالكود النهائي مع أمر /dash)

import os
import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
                          ContextTypes, MessageHandler, filters)
from db import (
    add_user,
    get_all_subscribers,
    toggle_reminder,
    get_reminder_status,
    get_reminder_enabled_users,
    remove_user,
    get_user_by_id
)

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

with open("Ad3iya.txt", encoding="utf-8") as f:
    AD3IYA_LIST = [line.strip() for line in f if line.strip()]

with open("verses.txt", encoding="utf-8") as f:
    VERSES_LIST = [line.strip() for line in f if line.strip()]

# --- مهام مجدولة ---
async def send_random_reminder(context):
    for user in get_all_subscribers():
        try:
            verse = random.choice(VERSES_LIST)
            dua = random.choice(AD3IYA_LIST)
            await context.bot.send_message(chat_id=user['user_id'], text=f"{verse}\n\n{dua}")
        except: continue

PRAYER_TIMES = {"Fajr": 5, "Dhuhr": 12, "Asr": 15, "Maghrib": 18, "Isha": 20}
PRAYER_MESSAGES = {
    "Fajr": "🕌 حان الآن وقت صلاة الفجر\n✨ ابدأ يومك بالصلاة، فهي نور.",
    "Dhuhr": "🕌 حان الآن وقت صلاة الظهر\n✨ لا تؤخر صلاتك فهي راحة للقلب.",
    "Asr": "🕌 حان الآن وقت صلاة العصر\n✨ من حافظ على العصر فهو في حفظ الله.",
    "Maghrib": "🕌 حان الآن وقت صلاة المغرب\n✨ صلاتك نورك يوم القيامة.",
    "Isha": "🕌 حان الآن وقت صلاة العشاء\n✨ نم على طهارة وصلاتك لختام اليوم."
}

async def send_prayer_reminder(context):
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    hour = now.hour
    for prayer, time_hour in PRAYER_TIMES.items():
        if hour == time_hour:
            for user in get_reminder_enabled_users():
                try:
                    await context.bot.send_message(chat_id=user['user_id'], text=PRAYER_MESSAGES[prayer])
                except: continue

async def send_friday_message(context):
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    if now.weekday() == 4 and now.hour == 12:
        msg = "﴿ إِنَّ اللَّهَ وَمَلَائِكَتَهُ يُصَلُّونَ عَلَى النَّبِيِّ ﴾\n\nاللهم صل وسلم وبارك على سيدنا محمد 🤍"
        for user in get_all_subscribers():
            try:
                await context.bot.send_message(chat_id=user['user_id'], text=msg)
            except: continue

# --- الأوامر ---
async def start(update: Update, context):
    user = update.effective_user
    add_user(user.id, user.first_name)
    await update.message.reply_text("مرحبًا بك في بوت صدقة، اكتب /dash إن كنت مالك البوت للدخول إلى لوحة التحكم.")

async def dash(update: Update, context):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى لوحة التحكم.")

    keyboard = [
        [InlineKeyboardButton("📢 رسالة جماعية", callback_data="broadcast"),
         InlineKeyboardButton("📣 إعلان", callback_data="announce")],
        [InlineKeyboardButton("📋 المشتركين", callback_data="list_users"),
         InlineKeyboardButton("🔎 بحث بالـ ID", callback_data="search_user")],
        [InlineKeyboardButton("❌ حذف عضو", callback_data="delete_user"),
         InlineKeyboardButton("🔢 عدد المشتركين", callback_data="count")],
        [InlineKeyboardButton("📊 حالة البوت", callback_data="status"),
         InlineKeyboardButton("✅ اختبار رسالة", callback_data="test_broadcast")]
    ]

    await update.message.reply_text("مرحبًا بك في لوحة تحكم بوت صدقة 🎛️\nاختر من الأزرار التالية 👇",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callbacks(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id != OWNER_ID:
        return await query.edit_message_text("❌ غير مصرح.")

    data = query.data
    if data == "count":
        count = len(get_all_subscribers())
        await query.edit_message_text(f"🔢 عدد المشتركين: {count}")

    elif data == "list_users":
        users = get_all_subscribers()
        text = "📋 المشتركين:\n" + "\n".join(f"{u['name']} - {u['user_id']}" for u in users)
        await query.edit_message_text(text[:4000])

    elif data == "test_broadcast":
        for user in get_all_subscribers():
            try:
                await context.bot.send_message(chat_id=user['user_id'], text="📢 هذه رسالة اختبارية من مالك البوت.")
            except: continue
        await query.edit_message_text("✅ تم إرسال الرسالة الاختبارية.")

    elif data == "broadcast":
        context.user_data['mode'] = 'broadcast'
        await query.edit_message_text("📝 أرسل الرسالة التي تريد إرسالها لجميع المشتركين.")

    elif data == "announce":
        context.user_data['mode'] = 'announce'
        await query.edit_message_text("📝 أرسل الإعلان الآن.")

    elif data == "search_user":
        context.user_data['mode'] = 'search_user'
        await query.edit_message_text("🔎 أرسل ID المستخدم.")

    elif data == "delete_user":
        context.user_data['mode'] = 'delete_user'
        await query.edit_message_text("❌ أرسل ID المستخدم لحذفه.")

    elif data == "status":
        await query.edit_message_text("📊 البوت يعمل بشكل جيد ✅")

async def handle_messages(update: Update, context):
    mode = context.user_data.get('mode')
    text = update.message.text.strip()

    if mode == 'broadcast':
        for user in get_all_subscribers():
            try:
                await context.bot.send_message(chat_id=user['user_id'], text=text)
            except: continue
        await update.message.reply_text("✅ تم إرسال الرسالة بنجاح.")

    elif mode == 'announce':
        for user in get_all_subscribers():
            try:
                await context.bot.send_message(chat_id=user['user_id'], text=f"📣 إعلان:\n{text}")
            except: continue
        await update.message.reply_text("✅ تم إرسال الإعلان.")

    elif mode == 'search_user':
        user = get_user_by_id(int(text))
        if user:
            await update.message.reply_text(f"👤 {user['name']} - {user['user_id']}")
        else:
            await update.message.reply_text("❌ المستخدم غير موجود.")

    elif mode == 'delete_user':
        remove_user(int(text))
        await update.message.reply_text("🗑️ تم حذف المستخدم.")

    context.user_data['mode'] = None

# --- تشغيل البوت ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dash", dash))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_messages))

    app.job_queue.run_repeating(send_random_reminder, interval=10800, first=10)
    app.job_queue.run_repeating(send_prayer_reminder, interval=3600, first=30)
    app.job_queue.run_repeating(send_friday_message, interval=3600, first=60)

    print("✅ Sadqa Bot is running...")
    app.run_polling()
