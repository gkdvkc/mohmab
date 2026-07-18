import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    Message, CallbackQuery, ChatMemberUpdated,
    InputMediaPhoto, InputFile
)
import time
import random
import re
import json
import os
import string
import hashlib
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

# ========== تنظیمات ==========
BOT_TOKEN = "8793482183:AAEGUa7ZEURP26N34DzKvrudnndC3q7apBk"
ADMIN_IDS = [8680457924]  # ادمین‌های اصلی
bot = telebot.TeleBot(BOT_TOKEN)

# ========== دیتابیس فوق‌پیشرفته ==========
class UltraDatabase:
    def __init__(self):
        # تنظیمات گروه‌ها
        self.groups = {}
        # اطلاعات کاربران
        self.users = defaultdict(lambda: {
            "warnings": {},
            "muted_until": 0,
            "banned_until": 0,
            "messages": deque(maxlen=50),
            "captcha_attempts": 0,
            "level": 0,
            "xp": 0,
            "last_activity": 0,
            "join_date": 0,
            "reports": [],
            "verified": False,
            "referred_by": None,
            "referral_count": 0,
            "achievements": [],
            "is_admin": False,
            "notes": "",
            "warn_count": 0,
            "strike_count": 0,
        })
        # داده‌های کپچا
        self.captcha = {}
        # زمان ورود برای ضد رید
        self.join_times = defaultdict(list)
        # تیکت‌ها
        self.tickets = defaultdict(list)
        # آمار
        self.stats = defaultdict(int)
        # تنظیمات پیش‌فرض
        self.default_settings = {
            # تنظیمات پایه
            "welcome": "👋 به گروه خوش آمدید {user_name}! لطفاً قوانین را رعایت کنید.\n📌 /قوانین برای مشاهده قوانین",
            "welcome_enabled": True,
            "welcome_photo": None,
            "captcha": True,
            "captcha_timeout": 60,
            "captcha_max_attempts": 3,
            "auto_delete": True,
            "auto_delete_seconds": 3600,  # 60 دقیقه
            
            # ضد اسپم
            "anti_spam": True,
            "spam_threshold": 5,
            "spam_action": "mute",
            "spam_duration": 300,
            "anti_raid": True,
            "raid_threshold": 5,
            "raid_action": "kick",
            
            # محدودیت‌ها
            "anti_mentions": True,
            "mention_limit": 3,
            "anti_caps": True,
            "caps_limit": 70,
            "anti_emoji": True,
            "emoji_limit": 5,
            "anti_newlines": True,
            "newline_limit": 5,
            "anti_reply_spam": True,
            "reply_spam_threshold": 3,
            "anti_forward": True,
            "forward_limit": 3,
            
            # امنیت
            "anti_link": True,
            "anti_link_action": "warn",
            "anti_link_whitelist": ["youtube.com", "youtu.be", "instagram.com", "telegram.me"],
            "anti_bad_words": True,
            "anti_bad_words_action": "mute",
            "anti_bad_words_duration": 600,
            "anti_advertising": True,
            "anti_advertising_action": "kick",
            "anti_bot": True,
            "anti_bot_action": "ban",
            "anti_commands": True,
            "anti_commands_list": ["/ban", "/kick", "/mute", "/warn", "/add", "/delete", "/بن", "/اخراج", "/میوت"],
            
            # قفل گروه
            "group_lock": False,
            "group_lock_mode": "admin_only",
            
            # سیستم سطح
            "leveling": True,
            "level_multiplier": 1.0,
            "level_message": "🎉 {user_name} به سطح {level} رسید!",
            
            # قوانین
            "rules": "📋 قوانین گروه:\n1. احترام به یکدیگر\n2. بدون اسپم و تبلیغات\n3. رعایت ادب و اخلاق\n4. بدون ارسال محتوای نامناسب\n5. همراهی با مدیریت",
            
            # سیستم اخطار
            "warn_limit": 3,
            "warn_action": "mute",
            "warn_duration": 3600,
            "max_warn_reset": 86400,
            
            # لاگ
            "log_channel": None,
            "auto_report": True,
            "auto_report_channel": None,
            
            # تنظیمات پیشرفته
            "anti_voice_spam": True,
            "voice_spam_threshold": 3,
            "anti_media_spam": True,
            "media_spam_threshold": 5,
            "min_account_age": 0,
            "two_factor_auth": False,
            "verified_only": False,
        }
    
    def get_group(self, group_id):
        if group_id not in self.groups:
            self.groups[group_id] = self.default_settings.copy()
        return self.groups[group_id]
    
    def get_user(self, user_id):
        return self.users[user_id]
    
    def add_warning(self, group_id, user_id, reason):
        user = self.get_user(user_id)
        if group_id not in user["warnings"]:
            user["warnings"][group_id] = []
        user["warnings"][group_id].append({
            "time": time.time(),
            "reason": reason
        })
        user["warn_count"] += 1
        self.stats["total_warns"] += 1
        # حذف اخطارهای قدیمی
        settings = self.get_group(group_id)
        now = time.time()
        user["warnings"][group_id] = [
            w for w in user["warnings"][group_id]
            if now - w["time"] < settings.get("max_warn_reset", 86400)
        ]
        return len(user["warnings"][group_id])
    
    def clear_warnings(self, group_id, user_id):
        user = self.get_user(user_id)
        if group_id in user["warnings"]:
            user["warnings"][group_id] = []
            user["warn_count"] = 0
            return True
        return False
    
    def get_warnings(self, group_id, user_id):
        user = self.get_user(user_id)
        return user["warnings"].get(group_id, [])
    
    def set_mute(self, user_id, duration):
        self.users[user_id]["muted_until"] = int(time.time()) + duration
    
    def remove_mute(self, user_id):
        self.users[user_id]["muted_until"] = 0
    
    def is_muted(self, user_id):
        return self.users[user_id]["muted_until"] > int(time.time())
    
    def get_mute_remaining(self, user_id):
        return max(0, self.users[user_id]["muted_until"] - int(time.time()))
    
    def set_temp_ban(self, user_id, duration):
        self.users[user_id]["banned_until"] = int(time.time()) + duration
    
    def is_temp_banned(self, user_id):
        return self.users[user_id]["banned_until"] > int(time.time())
    
    def add_message(self, user_id):
        self.users[user_id]["messages"].append(time.time())
        if len(self.users[user_id]["messages"]) % 10 == 0:
            self.add_xp(user_id, 2)
    
    def get_message_count(self, user_id, seconds):
        now = time.time()
        msgs = self.users[user_id]["messages"]
        return sum(1 for t in msgs if now - t <= seconds)
    
    def add_join(self, group_id):
        now = time.time()
        self.join_times[group_id].append(now)
        if len(self.join_times[group_id]) > 30:
            self.join_times[group_id] = self.join_times[group_id][-30:]
    
    def get_join_count(self, group_id, seconds):
        now = time.time()
        return sum(1 for t in self.join_times[group_id] if now - t <= seconds)
    
    def save_captcha(self, user_id, group_id, answer):
        self.captcha[user_id] = {
            "answer": answer,
            "time": time.time(),
            "group": group_id,
            "attempts": 0
        }
    
    def get_captcha(self, user_id):
        return self.captcha.get(user_id)
    
    def delete_captcha(self, user_id):
        if user_id in self.captcha:
            del self.captcha[user_id]
    
    def increment_captcha_attempts(self, user_id):
        if user_id in self.captcha:
            self.captcha[user_id]["attempts"] += 1
            return self.captcha[user_id]["attempts"]
        return 0
    
    def add_xp(self, user_id, amount):
        user = self.get_user(user_id)
        user["xp"] += amount
        user["last_activity"] = time.time()
        new_level = int(user["xp"] ** 0.4)
        if new_level > user["level"]:
            user["level"] = new_level
            return True
        return False
    
    def get_level(self, user_id):
        return self.users[user_id]["level"]
    
    def get_xp(self, user_id):
        return self.users[user_id]["xp"]
    
    def verify_user(self, user_id):
        self.users[user_id]["verified"] = True
    
    def is_verified(self, user_id):
        return self.users[user_id]["verified"]
    
    def add_ticket(self, group_id, user_id, subject):
        ticket_id = len(self.tickets[group_id]) + 1
        self.tickets[group_id].append({
            "id": ticket_id,
            "user": user_id,
            "subject": subject,
            "time": time.time(),
            "status": "open",
            "messages": []
        })
        return ticket_id
    
    def close_ticket(self, group_id, ticket_id):
        for t in self.tickets[group_id]:
            if t["id"] == ticket_id:
                t["status"] = "closed"
                return True
        return False
    
    def add_ticket_message(self, group_id, ticket_id, user_id, message):
        for t in self.tickets[group_id]:
            if t["id"] == ticket_id:
                t["messages"].append({
                    "user": user_id,
                    "message": message,
                    "time": time.time()
                })
                return True
        return False

db = UltraDatabase()

# ========== ابزارهای کمکی ==========
def is_admin(user_id, chat_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

def is_bot_admin(user_id):
    return user_id in ADMIN_IDS

def get_user_mention(user):
    name = user.first_name
    if user.username:
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{name}</a>"

def format_duration(seconds):
    if seconds < 60:
        return f"{seconds} ثانیه"
    elif seconds < 3600:
        return f"{seconds // 60} دقیقه"
    elif seconds < 86400:
        return f"{seconds // 3600} ساعت"
    else:
        return f"{seconds // 86400} روز"

def contains_bad_words(text):
    bad_words = ["فحش", "کیر", "کون", "کس", "گه", "گوه", "حرام", "لعنت", "جاکش", "جنده", "فاحشه", "خایه", "مادرجنده"]
    text = text.lower()
    for word in bad_words:
        if word in text:
            return True
    return False

def contains_ad_keywords(text):
    ad_words = ["خرید", "فروش", "قیمت", "تخفیف", "فروشگاه", "سفارش", "تبلیغات", "تبلیغ", "اسپانسر", "حامی", "کسب درآمد", "ارز دیجیتال", "بیت‌کوین", "فارکس"]
    text = text.lower()
    for word in ad_words:
        if word in text:
            return True
    return False

def contains_link(text):
    url_pattern = r'(https?://[^\s]+)|(www\.[^\s]+)|(t\.me/[^\s]+)|(telegram\.me/[^\s]+)'
    return re.search(url_pattern, text) is not None

def extract_links(text):
    url_pattern = r'(https?://[^\s]+)|(www\.[^\s]+)|(t\.me/[^\s]+)|(telegram\.me/[^\s]+)'
    return re.findall(url_pattern, text)

def is_forwarded(message):
    return message.forward_from is not None or message.forward_from_chat is not None

# ========== کیبوردهای پیشرفته ==========
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
        InlineKeyboardButton("📊 آمار", callback_data="stats"),
        InlineKeyboardButton("📋 قوانین", callback_data="rules"),
        InlineKeyboardButton("🏆 رنکینگ", callback_data="ranking"),
        InlineKeyboardButton("🎫 تیکت", callback_data="tickets"),
        InlineKeyboardButton("👤 پروفایل", callback_data="profile"),
        InlineKeyboardButton("🆘 راهنما", callback_data="help"),
        InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh")
    )
    return keyboard

def settings_menu(group_id):
    settings = db.get_group(group_id)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔰 تنظیمات پایه", callback_data=f"basic_{group_id}"),
        InlineKeyboardButton("🛡️ ضد اسپم", callback_data=f"spam_{group_id}"),
        InlineKeyboardButton("🚫 محدودیت‌ها", callback_data=f"restrict_{group_id}"),
        InlineKeyboardButton("🔐 امنیت", callback_data=f"security_{group_id}"),
        InlineKeyboardButton("🎯 پیشرفته", callback_data=f"advanced_{group_id}"),
        InlineKeyboardButton("📝 قوانین", callback_data=f"rules_edit_{group_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
    )
    return keyboard

def basic_settings(group_id):
    settings = db.get_group(group_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"{'✅' if settings['welcome_enabled'] else '❌'} پیام خوش‌آمدگویی", callback_data=f"toggle_welcome_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['captcha'] else '❌'} کپچا", callback_data=f"toggle_captcha_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['auto_delete'] else '❌'} حذف خودکار (۶۰ دقیقه)", callback_data=f"toggle_autodelete_{group_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_settings_{group_id}")
    )
    return keyboard

def spam_settings(group_id):
    settings = db.get_group(group_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"{'✅' if settings['anti_spam'] else '❌'} ضد اسپم", callback_data=f"toggle_antispam_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_raid'] else '❌'} ضد رید", callback_data=f"toggle_antiraid_{group_id}"),
        InlineKeyboardButton(f"📊 آستانه اسپم: {settings['spam_threshold']}", callback_data=f"set_spam_{group_id}"),
        InlineKeyboardButton(f"⏱️ مدت میوت: {settings['spam_duration']}s", callback_data=f"set_mutedur_{group_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_settings_{group_id}")
    )
    return keyboard

def restrict_settings(group_id):
    settings = db.get_group(group_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"{'✅' if settings['anti_mentions'] else '❌'} ضد منشن", callback_data=f"toggle_mentions_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_caps'] else '❌'} ضد کپس", callback_data=f"toggle_caps_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_emoji'] else '❌'} ضد ایموجی", callback_data=f"toggle_emoji_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_newlines'] else '❌'} ضد خط جدید", callback_data=f"toggle_newlines_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_forward'] else '❌'} ضد فوروارد", callback_data=f"toggle_forward_{group_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_settings_{group_id}")
    )
    return keyboard

def security_settings(group_id):
    settings = db.get_group(group_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"{'✅' if settings['anti_bot'] else '❌'} ضد ربات", callback_data=f"toggle_bot_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_link'] else '❌'} ضد لینک", callback_data=f"toggle_link_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_bad_words'] else '❌'} ضد فحش", callback_data=f"toggle_badwords_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['anti_advertising'] else '❌'} ضد تبلیغات", callback_data=f"toggle_advert_{group_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_settings_{group_id}")
    )
    return keyboard

def advanced_settings(group_id):
    settings = db.get_group(group_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"{'🔒' if settings['group_lock'] else '🔓'} قفل گروه", callback_data=f"toggle_lock_{group_id}"),
        InlineKeyboardButton(f"{'✅' if settings['leveling'] else '❌'} سیستم سطح", callback_data=f"toggle_level_{group_id}"),
        InlineKeyboardButton(f"⚠️ اخطار تا جریمه: {settings['warn_limit']}", callback_data=f"set_warn_{group_id}"),
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_settings_{group_id}")
    )
    return keyboard

def back_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    return keyboard

# ========== دستورات فارسی ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user = message.from_user
    text = f"""
✨ **ربات محافظ فوق‌پیشرفته Luffy Ultra** ✨
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {user.first_name}
🆔 **آیدی:** `{user.id}`
👑 **نقش:** {'👑 ادمین اصلی' if is_bot_admin(user.id) else '👤 کاربر'}
━━━━━━━━━━━━━━━━━━━━━━

🛡️ **قابلیت‌های فوق‌پیشرفته:**
• ضد اسپم، رید، منشن، کپس، ایموجی، خط جدید
• ضد لینک، فحش، تبلیغات، ربات، فوروارد
• کپچا هوشمند با تایید دو مرحله‌ای
• سیستم سطح‌بندی و امتیازدهی
• قفل گروه و محدودیت‌های پیشرفته
• سیستم تیکت پشتیبانی
• گزارش‌گیری خودکار
• و ده‌ها قابلیت دیگر!

📌 برای مدیریت گروه، بات را به گروه اضافه و ادمین کنید.
"""
    bot.reply_to(message, text, reply_markup=main_menu(), parse_mode='HTML')

@bot.message_handler(commands=['راهنما', 'help'])
def help_command(message):
    text = """
📋 **راهنمای کامل ربات**
━━━━━━━━━━━━━━━━━━━━━━
**دستورات عمومی:**
/start - منوی اصلی
/راهنما - این راهنما
/قوانین - نمایش قوانین
/رتبه - نمایش رتبه شما
/رنکینگ - رنکینگ گروه
/پروفایل - پروفایل شما
/تیکت [موضوع] - تیکت جدید

**دستورات مدیریت (فقط ادمین‌ها):**
/تنظیمات - تنظیمات پیشرفته
/آمار - آمار گروه
/بن [کاربر] - بن کاربر
/آنبن [کاربر] - آن‌بن
/اخراج [کاربر] - اخراج
/میوت [کاربر] [مدت] - میوت
/آنمیوت [کاربر] - رفع میوت
/اخطار [کاربر] [دلیل] - اخطار
/اخطارها [کاربر] - نمایش اخطارها
/پاکسازی اخطارها [کاربر] - بازنشانی اخطارها
/پاکسازی (ریپلای) - پاک‌سازی پیام‌ها
/سنجاق (ریپلای) - پین
/برداشتن سنجاق - برداشتن پین
/قفل - قفل گروه
/بازکردن قفل - باز کردن قفل
/بکاپ - بکاپ‌گیری
/لاگ - نمایش لاگ‌ها

**نکته:** در دستورات می‌توانید به جای آیدی، به پیام کاربر ریپلای کنید.
━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['تنظیمات', 'settings'])
def settings_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    bot.reply_to(message, "⚙️ **تنظیمات پیشرفته گروه:**", reply_markup=settings_menu(group_id), parse_mode='HTML')

@bot.message_handler(commands=['آمار', 'stats'])
def stats_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    try:
        members = bot.get_chat_members_count(group_id)
    except:
        members = "نامشخص"
    
    total_warns = sum(len(user["warnings"].get(group_id, [])) for user in db.users.values())
    total_muted = sum(1 for user in db.users.values() if db.is_muted(user))
    
    text = f"""
📊 **آمار فوق‌پیشرفته گروه**
━━━━━━━━━━━━━━━━━━━━━━
👥 **تعداد اعضا:** {members}
📨 **پیام‌های کل:** {db.stats.get('total_messages', 0):,}
🚫 **اخراجی‌ها:** {db.stats.get('total_kicks', 0):,}
🔨 **بن‌ها:** {db.stats.get('total_bans', 0):,}
🔇 **میوت‌ها:** {db.stats.get('total_mutes', 0):,}
⚠️ **اخطارها:** {total_warns:,}
🔐 **کپچا موفق:** {db.stats.get('captcha_passed', 0):,}
❌ **کپچا ناموفق:** {db.stats.get('captcha_failed', 0):,}
🔇 **کاربران میوت:** {total_muted}
🎫 **تیکت‌ها:** {len(db.tickets.get(group_id, []))}
━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['قوانین', 'rules'])
def rules_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    settings = db.get_group(group_id)
    rules = settings.get('rules', 'قوانینی تنظیم نشده است.')
    bot.reply_to(message, f"📋 **قوانین گروه:**\n{rules}", parse_mode='HTML')

@bot.message_handler(commands=['رنکینگ', 'ranking'])
def ranking_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    
    try:
        members = bot.get_chat_members(group_id)
        rankings = []
        for member in members:
            if not member.user.is_bot:
                uid = member.user.id
                level = db.get_level(uid)
                xp = db.get_xp(uid)
                rankings.append((uid, level, xp))
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        text = "🏆 **رنکینگ کاربران**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, (uid, level, xp) in enumerate(rankings[:10], 1):
            try:
                user = bot.get_chat_member(group_id, uid).user
                name = user.first_name[:15]
                text += f"{i}. {name} - سطح {level} (XP: {xp})\n"
            except:
                continue
        
        if not text or text == "🏆 **رنکینگ کاربران**\n━━━━━━━━━━━━━━━━━━━━━━\n":
            text = "📭 هنوز داده‌ای برای نمایش وجود ندارد."
        
        bot.reply_to(message, text, parse_mode='HTML')
    except:
        bot.reply_to(message, "❌ خطا در دریافت رنکینگ.")

@bot.message_handler(commands=['رتبه', 'rank'])
def rank_command(message):
    user_id = message.from_user.id
    level = db.get_level(user_id)
    xp = db.get_xp(user_id)
    next_level_xp = int((level + 1) ** 2.5)
    progress = (xp / next_level_xp) * 100 if next_level_xp > 0 else 0
    
    text = f"""
🏆 **رتبه شما**
━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر:** {message.from_user.first_name}
📊 **سطح:** {level}
⭐ **امتیاز (XP):** {xp}
📈 **پیشرفت به سطح بعدی:** {progress:.1f}%
🔜 **XP مورد نیاز:** {next_level_xp}
━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['پروفایل', 'profile'])
def profile_command(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    is_verified = "✅" if user["verified"] else "❌"
    is_muted = "🔇" if db.is_muted(user_id) else "🔊"
    
    text = f"""
👤 **پروفایل کاربر**
━━━━━━━━━━━━━━━━━━━━━━
📛 **نام:** {message.from_user.first_name}
🆔 **آیدی:** `{user_id}`
🏆 **سطح:** {user["level"]}
⭐ **امتیاز:** {user["xp"]}
🔐 **تایید:** {is_verified}
🔇 **وضعیت میوت:** {is_muted}
📊 **اخطارها:** {user["warn_count"]}
📅 **تاریخ عضویت:** {datetime.fromtimestamp(user["join_date"]).strftime('%Y-%m-%d %H:%M') if user["join_date"] else 'نامشخص'}
━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['تیکت', 'ticket'])
def ticket_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ /تیکت [موضوع] - یک تیکت جدید ایجاد کنید.")
        return
    subject = " ".join(args[1:])
    ticket_id = db.add_ticket(group_id, message.from_user.id, subject)
    bot.reply_to(message, f"✅ تیکت شماره {ticket_id} با موضوع '{subject}' ایجاد شد.\nیک ادمین به زودی پاسخ خواهد داد.")

@bot.message_handler(commands=['تیکت‌ها', 'tickets'])
def tickets_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها می‌توانند تیکت‌ها را ببینند.")
        return
    tickets = db.tickets.get(group_id, [])
    if not tickets:
        bot.reply_to(message, "📭 هیچ تیکتی وجود ندارد.")
        return
    text = "🎫 **لیست تیکت‌ها**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for t in tickets:
        status = "🟢 باز" if t["status"] == "open" else "🔴 بسته"
        text += f"#{t['id']} - {t['subject']} ({status})\n"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['پاسخ', 'reply'])
def reply_ticket_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها می‌توانند پاسخ دهند.")
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ /پاسخ [شماره تیکت] [پاسخ]")
        return
    try:
        ticket_id = int(args[1])
        reply_text = " ".join(args[2:])
        if db.add_ticket_message(group_id, ticket_id, message.from_user.id, reply_text):
            bot.reply_to(message, f"✅ پاسخ به تیکت #{ticket_id} ارسال شد.")
        else:
            bot.reply_to(message, "❌ تیکت یافت نشد.")
    except:
        bot.reply_to(message, "❌ شماره تیکت نامعتبر.")

@bot.message_handler(commands=['بستن تیکت', 'close'])
def close_ticket_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها می‌توانند تیکت را ببندند.")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ /بستن تیکت [شماره]")
        return
    try:
        ticket_id = int(args[1])
        if db.close_ticket(group_id, ticket_id):
            bot.reply_to(message, f"✅ تیکت #{ticket_id} بسته شد.")
        else:
            bot.reply_to(message, "❌ تیکت یافت نشد.")
    except:
        bot.reply_to(message, "❌ شماره تیکت نامعتبر.")

# ========== دستورات مدیریت فارسی ==========
@bot.message_handler(commands=['بن', 'ban'])
def ban_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /بن [کاربر] - کاربر را بن کنید.\nنکته: می‌توانید به پیام کاربر ریپلای کنید.")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1:
        target = args[1]
        if target.isdigit():
            target_id = int(target)
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    try:
        bot.ban_chat_member(group_id, target_id)
        db.stats["total_bans"] += 1
        bot.reply_to(message, f"✅ کاربر {target_id} بن شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['آنبن', 'unban'])
def unban_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /آنبن [کاربر]")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    try:
        bot.unban_chat_member(group_id, target_id)
        bot.reply_to(message, f"✅ کاربر {target_id} آن‌بن شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['اخراج', 'kick'])
def kick_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /اخراج [کاربر]")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    try:
        bot.ban_chat_member(group_id, target_id)
        bot.unban_chat_member(group_id, target_id)
        db.stats["total_kicks"] += 1
        bot.reply_to(message, f"✅ کاربر {target_id} اخراج شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['میوت', 'mute'])
def mute_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /میوت [کاربر] [مدت به ثانیه]")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    duration = int(args[2]) if len(args) > 2 else 300
    
    try:
        db.set_mute(target_id, duration)
        db.stats["total_mutes"] += 1
        bot.reply_to(message, f"✅ کاربر {target_id} به مدت {format_duration(duration)} میوت شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['آنمیوت', 'unmute'])
def unmute_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /آنمیوت [کاربر]")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    try:
        db.remove_mute(target_id)
        bot.reply_to(message, f"✅ میوت کاربر {target_id} برداشته شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['اخطار', 'warn'])
def warn_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /اخطار [کاربر] [دلیل]")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    reason = " ".join(args[2:]) if len(args) > 2 else "تخلف"
    
    try:
        count = db.add_warning(group_id, target_id, reason)
        settings = db.get_group(group_id)
        if count >= settings['warn_limit']:
            action = settings['warn_action']
            if action == "mute":
                db.set_mute(target_id, settings['warn_duration'])
                db.stats["total_mutes"] += 1
                bot.reply_to(message, f"⚠️ کاربر {target_id} به دلیل {settings['warn_limit']} اخطار، {format_duration(settings['warn_duration'])} میوت شد.")
            elif action == "kick":
                bot.ban_chat_member(group_id, target_id)
                bot.unban_chat_member(group_id, target_id)
                db.stats["total_kicks"] += 1
                bot.reply_to(message, f"⚠️ کاربر {target_id} به دلیل {settings['warn_limit']} اخطار، اخراج شد.")
            elif action == "ban":
                bot.ban_chat_member(group_id, target_id)
                db.stats["total_bans"] += 1
                bot.reply_to(message, f"⚠️ کاربر {target_id} به دلیل {settings['warn_limit']} اخطار، بن شد.")
            db.clear_warnings(group_id, target_id)
        else:
            bot.reply_to(message, f"⚠️ کاربر {target_id} اخطار {count}/{settings['warn_limit']} دریافت کرد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['اخطارها', 'warnings'])
def warnings_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /اخطارها [کاربر]")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    try:
        warns = db.get_warnings(group_id, target_id)
        if warns:
            text = f"⚠️ **اخطارهای کاربر {target_id}:**\n"
            for i, w in enumerate(warns, 1):
                text += f"{i}. {w['reason']} ({datetime.fromtimestamp(w['time']).strftime('%Y-%m-%d %H:%M')})\n"
            bot.reply_to(message, text, parse_mode='HTML')
        else:
            bot.reply_to(message, f"✅ کاربر {target_id} هیچ اخطاری ندارد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['پاکسازی اخطارها', 'resetwarnings'])
def reset_warnings_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    args = message.text.split()
    if len(args) < 2 and not message.reply_to_message:
        bot.reply_to(message, "⚠️ /پاکسازی اخطارها [کاربر]")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
    
    if not target_id:
        bot.reply_to(message, "❌ کاربر را مشخص کنید.")
        return
    
    try:
        if db.clear_warnings(group_id, target_id):
            bot.reply_to(message, f"✅ اخطارهای کاربر {target_id} بازنشانی شد.")
        else:
            bot.reply_to(message, f"❌ کاربر {target_id} اخطاری ندارد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['پاکسازی', 'purge'])
def purge_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ به پیامی ریپلای کنید تا از آن به بعد حذف شود.")
        return
    
    try:
        msg_id = message.reply_to_message.message_id
        count = 0
        while msg_id < message.message_id and count < 100:
            bot.delete_message(group_id, msg_id)
            msg_id += 1
            count += 1
        bot.reply_to(message, f"✅ {count} پیام حذف شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['سنجاق', 'pin'])
def pin_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ به پیامی که می‌خواهید پین کنید ریپلای کنید.")
        return
    
    try:
        bot.pin_chat_message(group_id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 پیام پین شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['برداشتن سنجاق', 'unpin'])
def unpin_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    try:
        bot.unpin_chat_message(group_id)
        bot.reply_to(message, "📌 پین برداشته شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['قفل', 'lock'])
def lock_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    settings = db.get_group(group_id)
    settings['group_lock'] = True
    bot.reply_to(message, "🔒 گروه قفل شد. فقط ادمین‌ها می‌توانند پیام بفرستند.")

@bot.message_handler(commands=['بازکردن قفل', 'unlock'])
def unlock_command(message):
    if not message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "❌ این دستور فقط در گروه قابل استفاده است.")
        return
    group_id = message.chat.id
    if not is_admin(message.from_user.id, group_id) and not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ شما ادمین گروه نیستید!")
        return
    
    settings = db.get_group(group_id)
    settings['group_lock'] = False
    bot.reply_to(message, "🔓 قفل گروه باز شد.")

@bot.message_handler(commands=['بکاپ', 'backup'])
def backup_command(message):
    if not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین اصلی می‌تواند بکاپ بگیرد.")
        return
    try:
        # بکاپ ساده
        data = {
            "groups": db.groups,
            "users": dict(db.users),
            "stats": dict(db.stats),
            "timestamp": time.time()
        }
        with open(f"backup_{int(time.time())}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        bot.reply_to(message, "✅ بکاپ با موفقیت ذخیره شد.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(commands=['لاگ', 'logs'])
def logs_command(message):
    if not is_bot_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین اصلی می‌تواند لاگ ببیند.")
        return
    bot.reply_to(message, "📋 لاگ‌ها در فایل ذخیره می‌شوند.")

# ========== مدیریت اعضای جدید ==========
@bot.chat_member_handler()
def handle_new_member(chat_member_update: ChatMemberUpdated):
    chat = chat_member_update.chat
    if chat.type not in ['group', 'supergroup']:
        return
    group_id = chat.id
    new = chat_member_update.new_chat_member
    old = chat_member_update.old_chat_member
    
    if new.status == "member" and old.status in ["left", "kicked"]:
        user = new.user
        if user.is_bot:
            settings = db.get_group(group_id)
            if settings['anti_bot']:
                try:
                    bot.ban_chat_member(group_id, user.id)
                    db.stats["total_bans"] += 1
                    bot.send_message(group_id, f"🤖 ربات {user.first_name} شناسایی و بن شد.")
                except:
                    pass
            return
        
        user_id = user.id
        settings = db.get_group(group_id)
        db.add_join(group_id)
        db.users[user_id]["join_date"] = time.time()
        
        # ضد رید
        if settings['anti_raid']:
            join_count = db.get_join_count(group_id, 10)
            if join_count >= settings['raid_threshold']:
                action = settings['raid_action']
                try:
                    if action == "kick":
                        bot.ban_chat_member(group_id, user_id)
                        bot.unban_chat_member(group_id, user_id)
                        db.stats["total_kicks"] += 1
                    elif action == "ban":
                        bot.ban_chat_member(group_id, user_id)
                        db.stats["total_bans"] += 1
                except:
                    pass
                return
        
        # کپچا
        if settings['captcha']:
            num1 = random.randint(1, 15)
            num2 = random.randint(1, 15)
            answer = num1 + num2
            db.save_captcha(user_id, group_id, answer)
            
            bot.send_message(
                group_id,
                f"🔐 {get_user_mention(user)}، لطفاً برای اثبات اینکه ربات نیستی، پاسخ این معادله را بفرست:\n\n{num1} + {num2} = ?\n\n⏳ شما {settings['captcha_timeout']} ثانیه فرصت دارید.",
                parse_mode='HTML'
            )
            
            def captcha_timeout():
                captcha_data = db.get_captcha(user_id)
                if captcha_data and captcha_data["group"] == group_id:
                    try:
                        bot.ban_chat_member(group_id, user_id)
                        bot.unban_chat_member(group_id, user_id)
                        db.stats["captcha_failed"] += 1
                        bot.send_message(group_id, f"⏰ {get_user_mention(user)} زمان کپچا تمام شد، اخراج شد.", parse_mode='HTML')
                    except:
                        pass
                    db.delete_captcha(user_id)
            
            threading.Timer(settings['captcha_timeout'], captcha_timeout).start()
        
        # پیام خوش‌آمدگویی
        if settings['welcome_enabled']:
            welcome_text = settings['welcome'].replace("{user_name}", user.first_name)
            bot.send_message(group_id, welcome_text, parse_mode='HTML')

# ========== پاسخ به کپچا ==========
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'] and message.text and message.text.lstrip('-').isdigit())
def captcha_answer(message):
    user_id = message.from_user.id
    group_id = message.chat.id
    captcha_data = db.get_captcha(user_id)
    
    if not captcha_data:
        return
    
    if captcha_data["group"] != group_id:
        return
    
    if int(message.text) == captcha_data["answer"]:
        db.delete_captcha(user_id)
        db.stats["captcha_passed"] += 1
        db.verify_user(user_id)
        bot.reply_to(message, "✅ کپچا صحیح بود! خوش آمدید.")
    else:
        attempts = db.increment_captcha_attempts(user_id)
        settings = db.get_group(group_id)
        max_attempts = settings.get('captcha_max_attempts', 3)
        
        if attempts >= max_attempts:
            try:
                bot.ban_chat_member(group_id, user_id)
                bot.unban_chat_member(group_id, user_id)
                db.stats["captcha_failed"] += 1
                bot.reply_to(message, f"❌ تعداد تلاش‌های شما بیش از حد مجاز بود، اخراج شدید.")
            except:
                pass
            db.delete_captcha(user_id)
        else:
            bot.reply_to(message, f"❌ پاسخ نادرست! تلاش {attempts}/{max_attempts}")

# ========== مدیریت پیام‌ها ==========
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'])
def handle_message(message):
    if not message.chat.type in ['group', 'supergroup']:
        return
    
    group_id = message.chat.id
    user = message.from_user
    user_id = user.id
    
    # نادیده گرفتن ادمین‌ها و بات
    if is_admin(user_id, group_id) or user.is_bot:
        return
    
    settings = db.get_group(group_id)
    
    # قفل گروه
    if settings['group_lock']:
        try:
            bot.delete_message(group_id, message.message_id)
            bot.send_message(group_id, f"🔒 {get_user_mention(user)} گروه قفل است!", parse_mode='HTML')
        except:
            pass
        return
    
    # میوت
    if db.is_muted(user_id):
        try:
            bot.delete_message(group_id, message.message_id)
            remaining = db.get_mute_remaining(user_id)
            bot.send_message(group_id, f"🔇 {get_user_mention(user)} شما میوت هستید! ({format_duration(remaining)} باقی مانده)", parse_mode='HTML')
        except:
            pass
        return
    
    # بن موقت
    if db.is_temp_banned(user_id):
        try:
            bot.delete_message(group_id, message.message_id)
            bot.send_message(group_id, f"🔨 {get_user_mention(user)} شما بن موقت هستید!", parse_mode='HTML')
        except:
            pass
        return
    
    # ضد اسپم
    if settings['anti_spam'] and message.text:
        db.add_message(user_id)
        count = db.get_message_count(user_id, 1)
        if count >= settings['spam_threshold']:
            action = settings['spam_action']
            try:
                bot.delete_message(group_id, message.message_id)
                if action == "mute":
                    db.set_mute(user_id, settings['spam_duration'])
                    db.stats["total_mutes"] += 1
                    bot.send_message(group_id, f"🔇 {get_user_mention(user)} به دلیل اسپم به مدت {format_duration(settings['spam_duration'])} میوت شد.", parse_mode='HTML')
                elif action == "kick":
                    bot.ban_chat_member(group_id, user_id)
                    bot.unban_chat_member(group_id, user_id)
                    db.stats["total_kicks"] += 1
                    bot.send_message(group_id, f"👢 {get_user_mention(user)} به دلیل اسپم اخراج شد.", parse_mode='HTML')
                elif action == "ban":
                    bot.ban_chat_member(group_id, user_id)
                    db.stats["total_bans"] += 1
                    bot.send_message(group_id, f"🔨 {get_user_mention(user)} به دلیل اسپم بن شد.", parse_mode='HTML')
            except:
                pass
            return
    
    # ضد لینک
    if settings['anti_link'] and message.text and contains_link(message.text):
        links = extract_links(message.text)
        is_whitelisted = any(any(whitelist in link for whitelist in settings.get('anti_link_whitelist', [])) for link in links)
        if not is_whitelisted:
            try:
                bot.delete_message(group_id, message.message_id)
                action = settings['anti_link_action']
                if action == "warn":
                    count = db.add_warning(group_id, user_id, "ارسال لینک ممنوع")
                    bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً لینک نفرستید! (اخطار {count})", parse_mode='HTML')
                elif action == "mute":
                    db.set_mute(user_id, 300)
                    db.stats["total_mutes"] += 1
                    bot.send_message(group_id, f"🔇 {get_user_mention(user)} به دلیل ارسال لینک میوت شد.", parse_mode='HTML')
                elif action == "kick":
                    bot.ban_chat_member(group_id, user_id)
                    bot.unban_chat_member(group_id, user_id)
                    db.stats["total_kicks"] += 1
                    bot.send_message(group_id, f"👢 {get_user_mention(user)} به دلیل ارسال لینک اخراج شد.", parse_mode='HTML')
                elif action == "ban":
                    bot.ban_chat_member(group_id, user_id)
                    db.stats["total_bans"] += 1
                    bot.send_message(group_id, f"🔨 {get_user_mention(user)} به دلیل ارسال لینک بن شد.", parse_mode='HTML')
            except:
                pass
            return
    
    # ضد فحش
    if settings['anti_bad_words'] and message.text and contains_bad_words(message.text):
        try:
            bot.delete_message(group_id, message.message_id)
            action = settings['anti_bad_words_action']
            if action == "mute":
                db.set_mute(user_id, settings.get('anti_bad_words_duration', 600))
                db.stats["total_mutes"] += 1
                bot.send_message(group_id, f"🔇 {get_user_mention(user)} به دلیل استفاده از الفاظ نامناسب میوت شد.", parse_mode='HTML')
            elif action == "kick":
                bot.ban_chat_member(group_id, user_id)
                bot.unban_chat_member(group_id, user_id)
                db.stats["total_kicks"] += 1
                bot.send_message(group_id, f"👢 {get_user_mention(user)} به دلیل فحش اخراج شد.", parse_mode='HTML')
            elif action == "ban":
                bot.ban_chat_member(group_id, user_id)
                db.stats["total_bans"] += 1
                bot.send_message(group_id, f"🔨 {get_user_mention(user)} به دلیل فحش بن شد.", parse_mode='HTML')
            else:
                count = db.add_warning(group_id, user_id, "فحش و الفاظ نامناسب")
                bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً از الفاظ مناسب استفاده کنید! (اخطار {count})", parse_mode='HTML')
        except:
            pass
        return
    
    # ضد تبلیغات
    if settings['anti_advertising'] and message.text and contains_ad_keywords(message.text):
        try:
            bot.delete_message(group_id, message.message_id)
            action = settings['anti_advertising_action']
            if action == "kick":
                bot.ban_chat_member(group_id, user_id)
                bot.unban_chat_member(group_id, user_id)
                db.stats["total_kicks"] += 1
                bot.send_message(group_id, f"👢 {get_user_mention(user)} به دلیل تبلیغات اخراج شد.", parse_mode='HTML')
            elif action == "ban":
                bot.ban_chat_member(group_id, user_id)
                db.stats["total_bans"] += 1
                bot.send_message(group_id, f"🔨 {get_user_mention(user)} به دلیل تبلیغات بن شد.", parse_mode='HTML')
            else:
                count = db.add_warning(group_id, user_id, "تبلیغات")
                bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً تبلیغ نفرستید! (اخطار {count})", parse_mode='HTML')
        except:
            pass
        return
    
    # ضد منشن
    if settings['anti_mentions'] and message.text:
        mention_pattern = r'@\w+|tg://user\?id=\d+'
        mentions = len(re.findall(mention_pattern, message.text))
        if mentions > settings['mention_limit']:
            try:
                bot.delete_message(group_id, message.message_id)
                count = db.add_warning(group_id, user_id, f"منشن بیش از حد ({mentions} بار)")
                bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً منشن‌های زیاد نزنید! (اخطار {count})", parse_mode='HTML')
            except:
                pass
    
    # ضد کپس
    if settings['anti_caps'] and message.text:
        text = message.text
        letters = sum(1 for c in text if c.isalpha())
        if letters > 5:
            upper = sum(1 for c in text if c.isupper())
            ratio = (upper / letters) * 100 if letters > 0 else 0
            if ratio > settings['caps_limit']:
                try:
                    bot.delete_message(group_id, message.message_id)
                    count = db.add_warning(group_id, user_id, f"کپس بیش از حد ({ratio:.0f}%)")
                    bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً با حروف بزرگ پیام ندهید! (اخطار {count})", parse_mode='HTML')
                except:
                    pass
    
    # ضد ایموجی
    if settings['anti_emoji'] and message.text:
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002700-\U000027BF\U000024C2-\U0001F251]'
        emojis = len(re.findall(emoji_pattern, message.text))
        if emojis > settings['emoji_limit']:
            try:
                bot.delete_message(group_id, message.message_id)
                count = db.add_warning(group_id, user_id, f"ایموجی بیش از حد ({emojis} بار)")
                bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً از ایموجی زیاد استفاده نکنید! (اخطار {count})", parse_mode='HTML')
            except:
                pass
    
    # ضد خط جدید
    if settings['anti_newlines'] and message.text:
        newlines = message.text.count('\n')
        if newlines > settings['newline_limit']:
            try:
                bot.delete_message(group_id, message.message_id)
                count = db.add_warning(group_id, user_id, f"خط جدید بیش از حد ({newlines} بار)")
                bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً از خطوط جدید زیاد استفاده نکنید! (اخطار {count})", parse_mode='HTML')
            except:
                pass
    
    # ضد فوروارد
    if settings['anti_forward'] and is_forwarded(message):
        try:
            bot.delete_message(group_id, message.message_id)
            count = db.add_warning(group_id, user_id, "فوروارد پیام")
            bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً فوروارد نفرستید! (اخطار {count})", parse_mode='HTML')
        except:
            pass
    
    # ضد دستورات
    if settings['anti_commands'] and message.text:
        for cmd in settings['anti_commands_list']:
            if message.text.startswith(cmd):
                try:
                    bot.delete_message(group_id, message.message_id)
                    count = db.add_warning(group_id, user_id, f"استفاده از دستور {cmd}")
                    bot.send_message(group_id, f"⚠️ {get_user_mention(user)} لطفاً از دستورات مدیریتی استفاده نکنید! (اخطار {count})", parse_mode='HTML')
                    break
                except:
                    pass
    
    # سیستم سطح
    if settings['leveling']:
        if db.add_xp(user_id, 1):
            level = db.get_level(user_id)
            level_message = settings['level_message'].replace("{user_name}", user.first_name).replace("{level}", str(level))
            bot.send_message(group_id, level_message, parse_mode='HTML')
    
    # حذف خودکار (60 دقیقه)
    if settings['auto_delete']:
        def delete_later():
            try:
                bot.delete_message(group_id, message.message_id)
            except:
                pass
        threading.Timer(settings['auto_delete_seconds'], delete_later).start()

# ========== مدیریت کال‌بک‌ها ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data
    group_id = chat_id if call.message.chat.type in ['group', 'supergroup'] else None
    
    if data == "back_main":
        bot.edit_message_text(
            "✨ **منوی اصلی**",
            chat_id,
            call.message.message_id,
            reply_markup=main_menu(),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "settings":
        if not group_id:
            bot.answer_callback_query(call.id, "❌ این بخش فقط در گروه قابل استفاده است.")
            return
        if not is_admin(user_id, group_id) and not is_bot_admin(user_id):
            bot.answer_callback_query(call.id, "⛔ شما ادمین گروه نیستید!")
            return
        bot.edit_message_text(
            "⚙️ **تنظیمات پیشرفته:**",
            chat_id,
            call.message.message_id,
            reply_markup=settings_menu(group_id),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "stats":
        if not group_id:
            bot.answer_callback_query(call.id, "❌ این بخش فقط در گروه قابل استفاده است.")
            return
        if not is_admin(user_id, group_id) and not is_bot_admin(user_id):
            bot.answer_callback_query(call.id, "⛔ شما ادمین گروه نیستید!")
            return
        try:
            members = bot.get_chat_members_count(group_id)
        except:
            members = "نامشخص"
        total_warns = sum(len(user["warnings"].get(group_id, [])) for user in db.users.values())
        total_muted = sum(1 for user in db.users.values() if db.is_muted(user))
        text = f"""
📊 **آمار گروه**
━━━━━━━━━━━━━━━━━━━━━━
👥 اعضا: {members}
📨 پیام‌ها: {db.stats.get('total_messages', 0):,}
🚫 اخراجی‌ها: {db.stats.get('total_kicks', 0):,}
🔨 بن‌ها: {db.stats.get('total_bans', 0):,}
🔇 میوت‌ها: {db.stats.get('total_mutes', 0):,}
⚠️ اخطارها: {total_warns:,}
🔐 کپچا موفق: {db.stats.get('captcha_passed', 0):,}
❌ کپچا ناموفق: {db.stats.get('captcha_failed', 0):,}
🔇 میوت: {total_muted}
━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.edit_message_text(
            text,
            chat_id,
            call.message.message_id,
            reply_markup=back_button(),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "rules":
        if not group_id:
            bot.answer_callback_query(call.id, "❌ این بخش فقط در گروه قابل استفاده است.")
            return
        settings = db.get_group(group_id)
        rules = settings.get('rules', 'قوانینی تنظیم نشده است.')
        bot.edit_message_text(
            f"📋 **قوانین گروه:**\n{rules}",
            chat_id,
            call.message.message_id,
            reply_markup=back_button(),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "ranking":
        if not group_id:
            bot.answer_callback_query(call.id, "❌ این بخش فقط در گروه قابل استفاده است.")
            return
        try:
            members = bot.get_chat_members(group_id)
            rankings = []
            for member in members:
                if not member.user.is_bot:
                    uid = member.user.id
                    level = db.get_level(uid)
                    xp = db.get_xp(uid)
                    rankings.append((uid, level, xp))
            rankings.sort(key=lambda x: x[1], reverse=True)
            text = "🏆 **رنکینگ کاربران**\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, (uid, level, xp) in enumerate(rankings[:10], 1):
                try:
                    user = bot.get_chat_member(group_id, uid).user
                    name = user.first_name[:15]
                    text += f"{i}. {name} - سطح {level} (XP: {xp})\n"
                except:
                    continue
            if text == "🏆 **رنکینگ کاربران**\n━━━━━━━━━━━━━━━━━━━━━━\n":
                text = "📭 هنوز داده‌ای وجود ندارد."
            bot.edit_message_text(
                text,
                chat_id,
                call.message.message_id,
                reply_markup=back_button(),
                parse_mode='HTML'
            )
        except:
            bot.edit_message_text(
                "❌ خطا",
                chat_id,
                call.message.message_id,
                reply_markup=back_button()
            )
        bot.answer_callback_query(call.id)
        return
    
    if data == "profile":
        user = db.get_user(user_id)
        is_verified = "✅" if user["verified"] else "❌"
        is_muted = "🔇" if db.is_muted(user_id) else "🔊"
        text = f"""
👤 **پروفایل شما**
━━━━━━━━━━━━━━━━━━━━━━
📛 نام: {call.from_user.first_name}
🏆 سطح: {user["level"]}
⭐ امتیاز: {user["xp"]}
🔐 تایید: {is_verified}
🔇 میوت: {is_muted}
⚠️ اخطارها: {user["warn_count"]}
━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.edit_message_text(
            text,
            chat_id,
            call.message.message_id,
            reply_markup=back_button(),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "tickets":
        if not group_id:
            bot.answer_callback_query(call.id, "❌ این بخش فقط در گروه قابل استفاده است.")
            return
        tickets = db.tickets.get(group_id, [])
        if not tickets:
            bot.edit_message_text(
                "📭 هیچ تیکتی وجود ندارد.",
                chat_id,
                call.message.message_id,
                reply_markup=back_button()
            )
        else:
            text = "🎫 **تیکت‌ها**\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for t in tickets[-5:]:
                status = "🟢 باز" if t["status"] == "open" else "🔴 بسته"
                text += f"#{t['id']} - {t['subject']} ({status})\n"
            bot.edit_message_text(
                text,
                chat_id,
                call.message.message_id,
                reply_markup=back_button(),
                parse_mode='HTML'
            )
        bot.answer_callback_query(call.id)
        return
    
    if data == "help":
        text = """
📋 **راهنما**
━━━━━━━━━━━━━━━━━━━━━━
/start - منوی اصلی
/راهنما - این راهنما
/قوانین - قوانین
/رتبه - رتبه شما
/رنکینگ - رنکینگ گروه
/پروفایل - پروفایل
/تیکت [موضوع] - تیکت جدید

دستورات مدیریت:
/تنظیمات - تنظیمات
/آمار - آمار
/بن [کاربر] - بن
/آنبن [کاربر] - آن‌بن
/اخراج [کاربر] - اخراج
/میوت [کاربر] [مدت] - میوت
/آنمیوت [کاربر] - رفع میوت
/اخطار [کاربر] [دلیل] - اخطار
/اخطارها [کاربر] - نمایش اخطارها
/پاکسازی اخطارها [کاربر] - بازنشانی
/پاکسازی (ریپلای) - پاکسازی
/سنجاق (ریپلای) - پین
/برداشتن سنجاق - برداشتن پین
/قفل - قفل گروه
/بازکردن قفل - باز کردن قفل
/بکاپ - بکاپ
━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.edit_message_text(
            text,
            chat_id,
            call.message.message_id,
            reply_markup=back_button(),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data == "refresh":
        bot.edit_message_text(
            "🔄 بروزرسانی شد.",
            chat_id,
            call.message.message_id,
            reply_markup=main_menu(),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id, "✅ بروزرسانی انجام شد.")
        return
    
    # تنظیمات (زیرمنوها)
    if data.startswith("basic_"):
        gid = int(data.split("_")[1])
        bot.edit_message_text(
            "🔰 تنظیمات پایه",
            chat_id,
            call.message.message_id,
            reply_markup=basic_settings(gid),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("spam_"):
        gid = int(data.split("_")[1])
        bot.edit_message_text(
            "🛡️ تنظیمات ضد اسپم",
            chat_id,
            call.message.message_id,
            reply_markup=spam_settings(gid),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("restrict_"):
        gid = int(data.split("_")[1])
        bot.edit_message_text(
            "🚫 تنظیمات محدودیت",
            chat_id,
            call.message.message_id,
            reply_markup=restrict_settings(gid),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("security_"):
        gid = int(data.split("_")[1])
        bot.edit_message_text(
            "🔐 تنظیمات امنیت",
            chat_id,
            call.message.message_id,
            reply_markup=security_settings(gid),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("advanced_"):
        gid = int(data.split("_")[1])
        bot.edit_message_text(
            "🎯 تنظیمات پیشرفته",
            chat_id,
            call.message.message_id,
            reply_markup=advanced_settings(gid),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("rules_edit_"):
        gid = int(data.split("_")[2])
        bot.send_message(chat_id, "📝 لطفاً قوانین جدید را ارسال کنید.")
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("back_settings_"):
        gid = int(data.split("_")[2])
        bot.edit_message_text(
            "⚙️ تنظیمات پیشرفته",
            chat_id,
            call.message.message_id,
            reply_markup=settings_menu(gid),
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
        return
    
    # Toggle‌ها
    if data.startswith("toggle_"):
        if not group_id:
            bot.answer_callback_query(call.id, "❌ این بخش فقط در گروه قابل استفاده است.")
            return
        if not is_admin(user_id, group_id) and not is_bot_admin(user_id):
            bot.answer_callback_query(call.id, "⛔ شما ادمین گروه نیستید!")
            return
        
        parts = data.split("_")
        toggle = parts[1]
        gid = int(parts[2]) if parts[2].isdigit() else group_id
        settings = db.get_group(gid)
        
        if toggle == "welcome":
            settings['welcome_enabled'] = not settings['welcome_enabled']
        elif toggle == "captcha":
            settings['captcha'] = not settings['captcha']
        elif toggle == "autodelete":
            settings['auto_delete'] = not settings['auto_delete']
        elif toggle == "antispam":
            settings['anti_spam'] = not settings['anti_spam']
        elif toggle == "antiraid":
            settings['anti_raid'] = not settings['anti_raid']
        elif toggle == "mentions":
            settings['anti_mentions'] = not settings['anti_mentions']
        elif toggle == "caps":
            settings['anti_caps'] = not settings['anti_caps']
        elif toggle == "emoji":
            settings['anti_emoji'] = not settings['anti_emoji']
        elif toggle == "newlines":
            settings['anti_newlines'] = not settings['anti_newlines']
        elif toggle == "forward":
            settings['anti_forward'] = not settings['anti_forward']
        elif toggle == "bot":
            settings['anti_bot'] = not settings['anti_bot']
        elif toggle == "link":
            settings['anti_link'] = not settings['anti_link']
        elif toggle == "badwords":
            settings['anti_bad_words'] = not settings['anti_bad_words']
        elif toggle == "advert":
            settings['anti_advertising'] = not settings['anti_advertising']
        elif toggle == "lock":
            settings['group_lock'] = not settings['group_lock']
        elif toggle == "level":
            settings['leveling'] = not settings['leveling']
        else:
            bot.answer_callback_query(call.id, "❌ تنظیم نامعتبر.")
            return
        
        # بازگشت به منوی مناسب
        if toggle in ["welcome", "captcha", "autodelete"]:
            bot.edit_message_text(
                "🔰 تنظیمات پایه",
                chat_id,
                call.message.message_id,
                reply_markup=basic_settings(gid),
                parse_mode='HTML'
            )
        elif toggle in ["antispam", "antiraid"]:
            bot.edit_message_text(
                "🛡️ تنظیمات ضد اسپم",
                chat_id,
                call.message.message_id,
                reply_markup=spam_settings(gid),
                parse_mode='HTML'
            )
        elif toggle in ["mentions", "caps", "emoji", "newlines", "forward"]:
            bot.edit_message_text(
                "🚫 تنظیمات محدودیت",
                chat_id,
                call.message.message_id,
                reply_markup=restrict_settings(gid),
                parse_mode='HTML'
            )
        elif toggle in ["bot", "link", "badwords", "advert"]:
            bot.edit_message_text(
                "🔐 تنظیمات امنیت",
                chat_id,
                call.message.message_id,
                reply_markup=security_settings(gid),
                parse_mode='HTML'
            )
        elif toggle in ["lock", "level"]:
            bot.edit_message_text(
                "🎯 تنظیمات پیشرفته",
                chat_id,
                call.message.message_id,
                reply_markup=advanced_settings(gid),
                parse_mode='HTML'
            )
        
        bot.answer_callback_query(call.id, f"✅ تنظیمات ذخیره شد.")
        return
    
    # تنظیمات عددی
    if data.startswith("set_"):
        if not group_id:
            bot.answer_callback_query(call.id, "❌ این بخش فقط در گروه قابل استفاده است.")
            return
        if not is_admin(user_id, group_id) and not is_bot_admin(user_id):
            bot.answer_callback_query(call.id, "⛔ شما ادمین گروه نیستید!")
            return
        bot.answer_callback_query(call.id, "⚠️ این تنظیم در نسخه فعلی قابل تغییر نیست.")

# ========== پاسخ به پیام‌های معمولی ==========
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if message.chat.type in ['group', 'supergroup']:
        if message.text and message.text.lower() in ["سلام", "درود", "hi", "hello"]:
            bot.reply_to(message, f"✨ سلام {message.from_user.first_name} جان! به گروه خوش آمدی! 🛡️")
    else:
        if message.text:
            bot.reply_to(message, "👋 سلام! لطفاً من رو به گروه اضافه کنید تا بتونم محافظت کنم.")

# ========== اجرا ==========
if __name__ == "__main__":
    print("=" * 70)
    print("✨ ربات محافظ فوق‌پیشرفته Luffy Ultra v6.0 ✨")
    print("=" * 70)
    print(f"👥 ادمین‌ها: {ADMIN_IDS}")
    print("✅ حذف خودکار: 60 دقیقه")
    print("✅ دستورات فارسی: فعال")
    print("✅ تمام امکانات: فعال")
    print("=" * 70)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ خطا: {e}")
            print("🔄 راه‌اندازی مجدد در 5 ثانیه...")
            time.sleep(5)
            continue