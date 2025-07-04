# استخدم import من هذا الملف في main.py

# جميع الرسائل النصية المستخدمة في البوت

WELCOME_MESSAGE = (
    "🌿 أهلاً بك في بوت صدقه | Sadqa الإسلامي.\n"
    " البوت صدقه جارية على روح صديقنا (يوسف أحمد إبراهيم) ادعو له بالرحمه والمغفره 🤍 \n\n"
    "🤲 مميزات البوت:\n"
    "• تذكير بأوقات الصلاة حسب موقعك\n"
    "• آيات قرآنية وأدعية يومية\n"
    "• نظام نقاط وإنجازات تفاعلي\n"
    "• تفاعل مع الأدعية والآيات\n"
    "• تحديات أسبوعية دينية\n\n"
    "اختر ما يناسبك 👇"
)

# رسائل الإعدادات والتنقل
CHANGE_CITY_PROMPT = "✏️ من فضلك أرسل اسم مدينتك الآن:"
SELECT_CITY_MESSAGE = "📍 اختر مدينتك من القائمة أو أرسل موقعك:"
LOCATION_REQUEST = "📍 أرسل موقعك الحالي للحصول على أوقات صلاة دقيقة"

# رسائل الحالة والأخطاء
PRAYER_ERROR = "⚠️ لم نتمكن من جلب المواقيت حاليًا. تأكد من موقعك وحاول مرة أخرى."
CITY_UPDATED = "✅ تم تحديث مدينتك إلى: {city}"
LOCATION_UPDATED = "✅ تم تحديث موقعك بنجاح"
PRAYER_HEADER = "🕌 مواعيد الصلاة في {city}:\n\n"
UNKNOWN_ERROR = "⚠️ حدث خطأ غير متوقع. حاول مرة أخرى."

# رسائل الاشتراك والإلغاء
UNSUBSCRIBE_CONFIRM = "🛑 تم إلغاء اشتراكك. نراك لاحقًا بإذن الله.\n💔 ستفقد جميع نقاطك وإنجازاتك"
UNSUBSCRIBE_WARNING = "⚠️ هل أنت متأكد من إلغاء الاشتراك؟\nستفقد:\n• جميع نقاطك ({points} نقطة)\n• إنجازاتك ({achievements} إنجاز)\n• تذكيرات الصلاة"
REMINDER_ENABLED = "🔔 تم تفعيل تذكير الصلاة"
REMINDER_DISABLED = "🔕 تم إيقاف تذكير الصلاة"

# رسائل النقاط والإنجازات
POINTS_HEADER = "🏆 إحصائياتك الشخصية:\n\n"
POINTS_DISPLAY = "💎 نقاطك: {points} نقطة\n🏅 إنجازاتك: {achievements} إنجاز"
NO_ACHIEVEMENTS = "لم تحصل على أي إنجازات بعد"
ACHIEVEMENT_EARNED = "🎉 مبروك! حصلت على إنجاز جديد:\n{name}\n{description}\n+{points} نقطة!"
LEADERBOARD_HEADER = "🏆 لوحة المتصدرين:\n\n"

# رسائل التفاعل مع الأدعية
DUA_INTERACTION_AMEN = "🤲 اللهم آمين يارب العالمين\n+3 نقاط"
DUA_INTERACTION_LIKE = "❤️ شكراً لإعجابك!\n+2 نقطة"
DUA_COMMENT_PROMPT = "💬 اكتب تعليقك على الدعاء:"
DUA_COMMENT_SAVED = "✅ تم حفظ تعليقك\n+5 نقاط"
DUA_COMMENT_ERROR = "❌ حدث خطأ في حفظ التعليق"

# رسائل التحديات والمسابقات
WEEKLY_CHALLENGE_HEADER = "🎯 تحدي الأسبوع:\n"
FRIDAY_MESSAGE = "ﷺ إنَّ اللَّهَ وَمَلَائِكَتَهُ يُصَلّونَ عَلَى النَّبِيِ\n\nاللهُمَّ صَلِّ وَسَلِّمْ وَبَارِكْ عَلَى سَيِّدِنَا مُحَمَّد 🤍\n\n+3 نقاط لتلقي رسالة الجمعة"

# رسائل التغذية الراجعة
FEEDBACK_PROMPT = "💬 شاركنا رأيك أو اقتراحك لتحسين البوت:"
FEEDBACK_THANKS = "🙏 شكراً لك! تم إرسال رأيك للمطور\n+15 نقطة لمشاركة التغذية الراجعة"
SUGGESTION_PROMPT = "💡 شاركنا اقتراحك لتطوير البوت:"
SUGGESTION_THANKS = "💡 شكراً لاقتراحك القيم!\n+10 نقاط"

# رسائل المطور (لوحة التحكم)
ADMIN_WELCOME = "🎛 مرحباً بك في لوحة تحكم المطور"
BROADCAST_PROMPT = "📢 اكتب الرسالة التي تريد إرسالها لجميع المستخدمين:"
BROADCAST_SUCCESS = "✅ تم إرسال الرسالة لـ {count} مستخدم"
BROADCAST_FAILED = "❌ فشل إرسال الرسالة لـ {count} مستخدم"
ANNOUNCE_PROMPT = "📣 اكتب الإعلان:"
USER_SEARCH_PROMPT = "🔍 أدخل ID المستخدم أو جزء من اسمه:"
USER_NOT_FOUND = "❌ لم يتم العثور على المستخدم"
USER_DELETED = "✅ تم حذف المستخدم"

# رسائل الإحصائيات
STATS_HEADER = "📊 إحصائيات البوت:\n\n"
STATS_USERS = "👥 إجمالي المستخدمين: {total}\n🔔 المستخدمين النشطين: {active}"
STATS_POINTS = "💎 إجمالي النقاط الموزعة: {total_points}\n🏆 أعلى نقاط: {highest_points}"
STATS_REACTIONS = "🤲 إجمالي الآمين: {amen}\n❤️ إجمالي الإعجابات: {likes}\n💬 إجمالي التعليقات: {comments}"

# رسائل الأوقات والصلوات
NEXT_PRAYER_FORMAT = "⏰ الصلاة القادمة: {prayer}\n🕐 الوقت: {time}\n⏳ متبقي: {remaining}"
TODAY_PRAYERS_HEADER = "🕌 صلوات اليوم:\n\n"
PRAYER_TIME_FORMAT = "{prayer}: {time}"
PRAYER_REMINDER_FORMAT = "🏛 حان الآن وقت صلاة {prayer}\n✨ {message}"

# رسائل الصلوات المخصصة
PRAYER_MESSAGES = {
    "Fajr": "ابدأ يومك بالصلاة، فهي نور",
    "Dhuhr": "لا تؤخر صلاتك فهي راحة للقلب", 
    "Asr": "من حافظ على العصر فهو في حفظ الله",
    "Maghrib": "صلاتك نورك يوم القيامة",
    "Isha": "نم على طهارة وصلاتك لختام اليوم"
}

# رسائل التقييم
RATING_PROMPT = "⭐ كيف تقيم البوت من 1 إلى 5؟"
RATING_THANKS = "🙏 شكراً لتقييمك! ({rating}/5)\n+10 نقاط"
RATING_FEEDBACK_PROMPT = "💬 أخبرنا عن تجربتك (اختياري):"

# رسائل المدن الشائعة
POPULAR_CITIES_HEADER = "🌍 المدن الشائعة:"
CITY_SELECTED = "✅ تم اختيار {city}"
CUSTOM_CITY_PROMPT = "✏️ اكتب اسم مدينتك:"

# رسائل الأخطاء المتقدمة
API_ERROR = "⚠️ خطأ في الاتصال بالخدمة، حاول لاحقاً"
DATABASE_ERROR = "⚠️ خطأ في قاعدة البيانات، حاول مرة أخرى"
PERMISSION_DENIED = "❌ ليس لديك صلاحية لهذا الأمر"
FEATURE_UNAVAILABLE = "⚠️ هذه الميزة غير متاحة حالياً"

# رسائل التحفيز والتشجيع
DAILY_MOTIVATION = [
    "🌟 كل يوم جديد هو فرصة للتقرب من الله",
    "🤲 الدعاء مخ العبادة، فأكثر منه",
    "📿 الذكر طمأنينة القلوب",
    "🕌 الصلاة عماد الدين فحافظ عليها",
    "💝 الصدقة تطفئ غضب الرب"
]

# رسائل الإنجازات المفصلة
ACHIEVEMENT_DESCRIPTIONS = {
    "first_prayer": "🌟 أول صلاة - أول تذكير صلاة تتلقاه",
    "week_streak": "🔥 أسبوع متواصل - 7 أيام متتالية من الصلاة", 
    "month_streak": "👑 شهر متواصل - 30 يوم متتالية من الصلاة",
    "location_shared": "📍 مشارك الموقع - شارك موقعه لدقة أكبر",
    "feedback_giver": "💬 مقدم التغذية الراجعة - قدم تعليق أو اقتراح",
    "amen_lover": "🤲 محب الأدعية - تفاعل مع 10 أدعية",
    "commenter": "💬 معلق نشط - كتب 5 تعليقات على الأدعية"
}

# رسائل التحديات الأسبوعية
WEEKLY_CHALLENGES = [
    "📿 اقرأ سورة الكهف كاملة",
    "🤲 ادع بـ 100 استغفار يومياً", 
    "📖 اقرأ صفحة من القرآن يومياً",
    "🕌 صل السنن الرواتب مع الفرائض",
    "💝 تصدق كل يوم ولو بريال واحد",
    "🌙 قم الليل ولو ركعتين",
    "📚 احفظ آية جديدة كل يوم"
]

# رسائل الحالة والصحة
BOT_STATUS_HEALTHY = "✅ البوت يعمل بشكل طبيعي"
BOT_STATUS_WARNING = "⚠️ البوت يواجه بعض المشاكل"
BOT_STATUS_ERROR = "❌ البوت يواجه مشاكل خطيرة"

# رسائل المساعدة
HELP_MESSAGE = """
🆘 مساعدة البوت:

🔹 الأوامر الأساسية:
/start - بدء استخدام البوت
/dash - لوحة تحكم المطور (للمطور فقط)

🔹 الميزات:
• تذكير أوقات الصلاة
• آيات وأدعية يومية  
• نظام نقاط وإنجازات
• تفاعل مع المحتوى الديني

🔹 للمساعدة أو الاقتراحات:
استخدم زر "💬 تقييم البوت" من القائمة الرئيسية
"""

# رسائل الصيانة
MAINTENANCE_MESSAGE = "🔧 البوت تحت الصيانة حالياً، سيعود قريباً بإذن الله"
UPDATE_MESSAGE = "🆕 تم تحديث البوت! تحقق من الميزات الجديدة"
