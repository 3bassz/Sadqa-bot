import json

# المتغيرات يجب تعريفها global لكي تكون متاحة من الملف الرئيسي
user_points = {}
user_achievements = {}
user_interaction_history = {}

def load_saved_data():
    global user_points, user_achievements, user_interaction_history
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            user_points = data.get("user_points", {})
            user_achievements = data.get("user_achievements", {})
            user_interaction_history = data.get("user_interaction_history", {})
    except FileNotFoundError:
        pass

def save_data_periodically():
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({
            "user_points": user_points,
            "user_achievements": user_achievements,
            "user_interaction_history": user_interaction_history
        }, f, ensure_ascii=False, indent=2)

def cleanup_old_data():
    # يمكنك لاحقًا تنظيف التفاعلات القديمة أو غير المستخدمة هنا
    pass

async def handle_error(update, context):
    print(f"❌ خطأ غير متوقع: {context.error}")
    if update and update.effective_user:
        try:
            await context.bot.send_message(chat_id=update.effective_user.id, text="❗ حدث خطأ غير متوقع. الرجاء المحاولة لاحقاً.")
        except:
            pass
