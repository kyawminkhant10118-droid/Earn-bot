import os
import sqlite3
import datetime
import telebot
from telebot import types

# ==========================================
# ⚙️ INITIAL CONFIGURATION
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 🗄️ DATABASE SETUP & MIGRATION
# ==========================================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            referred_by INTEGER,
            is_verified INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            last_daily_bonus TEXT
        )
    ''')
    
    # Withdrawals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            account_info TEXT,
            status TEXT DEFAULT 'APPROVED',
            created_at TEXT
        )
    ''')
    
    # Promo Codes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            reward INTEGER,
            max_claims INTEGER,
            claimed_count INTEGER DEFAULT 0
        )
    ''')
    
    # Promo Claims Table (To prevent duplicate claims)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promo_claims (
            code TEXT,
            user_id INTEGER,
            PRIMARY KEY (code, user_id)
        )
    ''')
    
    # Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    defaults = {
        'REWARD_PER_REF': '100',
        'DAILY_BONUS': '50',
        'MIN_WITHDRAW': '5000',
        'CHANNELS': '@daily_cashmmproof',
        'PROOF_CHANNEL': '@daily_cashmmproof',
        'PROOF_IMAGE_URL': ''
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def is_user_banned(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def clean_channel_username(ch):
    ch = ch.strip()
    if not ch: return None
    if "t.me/" in ch:
        if "+" in ch or "joinchat" in ch: return None
        ch = ch.split("t.me/")[-1].split("/")[0].split("?")[0]
    ch = ch.strip()
    if ch.startswith("@"): return ch
    elif ch.startswith("-100"):
        try: return int(ch)
        except ValueError: return ch
    else: return "@" + ch

def get_channels_list():
    raw = get_setting('CHANNELS', '@daily_cashmmproof')
    return [ch.strip() for ch in raw.split(",") if ch.strip()]

def get_unsubscribed_channels(user_id):
    unsub_list = []
    channels = get_channels_list()
    for ch in channels:
        ch_clean = ch.strip()
        if not ch_clean: continue
        target = clean_channel_username(ch_clean)
        if not target: continue
        try:
            member = bot.get_chat_member(target, user_id)
            if member.status in ['left', 'kicked']:
                unsub_list.append(ch_clean)
        except Exception:
            continue
    return unsub_list

# ==========================================
# ⌨️ KEYBOARDS
# ==========================================
def get_channels_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    channels = get_channels_list()
    for index, ch in enumerate(channels, 1):
        ch_clean = ch.strip()
        if not ch_clean: continue
        if ch_clean.startswith("http://") or ch_clean.startswith("https://"): url = ch_clean
        elif ch_clean.startswith("@"): url = f"https://t.me/{ch_clean[1:]}"
        else: url = f"https://t.me/{ch_clean}"
        markup.add(types.InlineKeyboardButton(f"📢 Join Channel {index}", url=url))
    markup.add(types.InlineKeyboardButton("အတည်ပြုမည် ✅", callback_data="check_sub"))
    return markup

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🔗 Referral Link")
    btn2 = types.KeyboardButton("💰 မုန့်ဖိုး လက်ကျန်")
    btn3 = types.KeyboardButton("📅 Daily Bonus")
    btn4 = types.KeyboardButton("🎟️ Promo Code")
    btn5 = types.KeyboardButton("💸 ငွေထုတ်မည်")
    btn6 = types.KeyboardButton("🏆 Leaderboard")
    btn7 = types.KeyboardButton("📜 ငွေထုတ်မှတ်တမ်း")
    btn8 = types.KeyboardButton("ℹ️ အကူအညီ")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("📊 စာရင်းဇယားကြည့်ရန်")
    btn2 = types.KeyboardButton("💰 User မုန့်ဖိုး ပြင်ရန်")
    btn3 = types.KeyboardButton("🎟️ Promo Code သစ်လုပ်ရန်")
    btn4 = types.KeyboardButton("⚙️ Bot Settings ပြင်ရန်")
    btn5 = types.KeyboardButton("🔍 User စစ်မည်")
    btn6 = types.KeyboardButton("📢 Broadcast စာပို့မည်")
    btn7 = types.KeyboardButton("🚫 User Ban/Unban")
    btn8 = types.KeyboardButton("🔙 Main Menu သို့")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    return markup

def get_settings_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🎁 Ref Reward ပြင်ရန်")
    btn2 = types.KeyboardButton("📅 Daily Bonus ပြင်ရန်")
    btn3 = types.KeyboardButton("💸 Min Withdraw ပြင်ရန်")
    btn4 = types.KeyboardButton("📢 Join Channels ပြင်ရန်")
    btn5 = types.KeyboardButton("🖼️ Proof Image URL ပြင်ရန်")
    btn6 = types.KeyboardButton("🔙 Admin Menu သို့")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

# ==========================================
# 🤖 START & SUBSCRIPTION CHECK
# ==========================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        bot.send_message(user_id, "🚫 သင့်အကောင့်အား ပိတ်ပင် (Ban) ထားပါသည်။")
        return

    args = message.text.split()
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, is_verified, referred_by FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        possible_ref = int(args[1])
        if possible_ref != user_id: referrer_id = possible_ref

    if not user:
        cursor.execute("INSERT INTO users (user_id, balance, referred_by, is_verified, is_banned) VALUES (?, 0, ?, 0, 0)", (user_id, referrer_id))
        conn.commit()
    elif user[1] == 0 and not user[2] and referrer_id:
        cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
        conn.commit()
    conn.close()

    unsubscribed = get_unsubscribed_channels(user_id)
    if unsubscribed:
        bot.send_message(user_id, f"🎉 မင်္ဂလာပါ {message.from_user.first_name}!\n\nBot ကို စတင်အသုံးပြုရန် အောက်ပါ Channel များကို Join ပေးပါနော်။", reply_markup=get_channels_keyboard())
    else:
        bot.send_message(user_id, f"🎉 မင်္ဂလာပါ {message.from_user.first_name}!\n\nအောက်ပါ မီနူးများမှတစ်ဆင့် စတင်အသုံးပြုနိုင်ပါပြီ။", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    user_id = call.from_user.id
    if is_user_banned(user_id): return
    unsubscribed = get_unsubscribed_channels(user_id)
    if not unsubscribed:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT referred_by, is_verified FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row and row[1] == 0:
            cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
            ref_id = row[0]
            if ref_id:
                reward = int(get_setting('REWARD_PER_REF', '100'))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, ref_id))
                conn.commit()
                try: bot.send_message(ref_id, f"🎉 သင့် Referral Link မှတစ်ဆင့် လူတစ်ယောက် Join သွားသဖြင့် **{reward} ကျပ်** ရရှိပါပြီ!", parse_mode="Markdown")
                except Exception: pass
            else: conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ Channel များ အားလုံး Join ပြီးပါပြီ!")
        bot.send_message(user_id, "အဆင်ပြေပါပြီ! အောက်ပါ မီနူးများကို အသုံးပြုနိုင်ပါပြီ။", reply_markup=get_main_keyboard())
    else:
        bot.answer_callback_query(call.id, f"❌ Channel {len(unsubscribed)} ခု Join ရန် ကျန်ပါသေးသည်။", show_alert=True)

# ==========================================
# 📅 DAILY BONUS SYSTEM
# ==========================================
@bot.message_handler(func=lambda m: m.text == "📅 Daily Bonus")
def claim_daily_bonus(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    if get_unsubscribed_channels(user_id):
        bot.send_message(user_id, "❌ ကျေးဇူးပြု၍ Channel များကို အရင် Join ပေးပါ။", reply_markup=get_channels_keyboard())
        return

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT last_daily_bonus FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    now = datetime.datetime.now()
    bonus_amount = int(get_setting('DAILY_BONUS', '50'))
    
    if row and row[0]:
        last_claim = datetime.datetime.fromisoformat(row[0])
        time_diff = now - last_claim
        if time_diff.total_seconds() < 86400:  # 24 Hours = 86400 seconds
            remaining = datetime.timedelta(seconds=86400 - time_diff.total_seconds())
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            bot.send_message(user_id, f"⏳ သင် ဒီနေ့အတွက် Daily Bonus ရယူပြီးပါပြီ!\n\nနောက်တစ်ကြိမ် ယူနိုင်ရန် **{hours} နာရီ {minutes} မိနစ်** လိုပါသေးသည်။")
            conn.close()
            return

    cursor.execute("UPDATE users SET balance = balance + ?, last_daily_bonus = ? WHERE user_id = ?", (bonus_amount, now.isoformat(), user_id))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, f"🎉 ယနေ့အတွက် Daily Bonus **{bonus_amount} ကျပ်** လက်ခံရရှိပါပြီ! ✨", parse_mode="Markdown")

# ==========================================
# 🎟️ PROMO CODE SYSTEM
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🎟️ Promo Code")
def promo_code_prompt(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    msg = bot.send_message(user_id, "🎟️ ကျေးဇူးပြု၍ သင့်ထံတွင်ရှိသော **Promo Code** ကို ရိုက်ထည့်ပေးပါ:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_promo_code)

def process_promo_code(message):
    user_id = message.from_user.id
    code = message.text.strip().upper() if message.text else ""
    
    if not code:
        bot.send_message(user_id, "❌ Promo Code မှားယွင်းနေပါသည်။")
        return

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT reward, max_claims, claimed_count FROM promo_codes WHERE code = ?", (code,))
    promo = cursor.fetchone()
    
    if not promo:
        bot.send_message(user_id, "❌ အဆိုပါ Promo Code မရှိပါ သို့မဟုတ် သက်တမ်းကုန်သွားပါပြီ။")
        conn.close()
        return

    reward, max_claims, claimed_count = promo
    
    if claimed_count >= max_claims:
        bot.send_message(user_id, "⚠️ ဒီ Promo Code ကို လူပြည့်သွားပါပြီ!")
        conn.close()
        return

    cursor.execute("SELECT * FROM promo_claims WHERE code = ? AND user_id = ?", (code, user_id))
    if cursor.fetchone():
        bot.send_message(user_id, "⚠️ သင် ဒီ Promo Code ကို သုံးစွဲပြီးသားဖြစ်ပါသည်။")
        conn.close()
        return

    # Grant Reward
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
    cursor.execute("UPDATE promo_codes SET claimed_count = claimed_count + 1 WHERE code = ?", (code,))
    cursor.execute("INSERT INTO promo_claims (code, user_id) VALUES (?, ?)", (code, user_id))
    conn.commit()
    conn.close()

    bot.send_message(user_id, f"🎉 ဂုဏ်ယူပါတယ်! Promo Code ကြောင့် မုန့်ဖိုး **{reward:,} ကျပ်** ရရှိပါပြီ! ✨", parse_mode="Markdown")

# ==========================================
# 🏆 LEADERBOARD & 📜 HISTORY
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🏆 Leaderboard")
def show_leaderboard(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT referred_by, COUNT(*) as ref_count 
        FROM users 
        WHERE referred_by IS NOT NULL 
        GROUP BY referred_by 
        ORDER BY ref_count DESC 
        LIMIT 10
    ''')
    top_users = cursor.fetchall()
    conn.close()

    if not top_users:
        bot.send_message(user_id, "🏆 ထိပ်တန်း Ref ခေါ်သူ စာရင်း မရှိသေးပါ။")
        return

    text = "🏆 **Top 10 Referral ခေါ်သူများ စာရင်း** 🏆\n\n"
    badges = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for idx, (ref_id, count) in enumerate(top_users):
        u_str = str(ref_id)
        masked_id = u_str[:4] + "****" if len(u_str) > 4 else u_str
        badge = badges[idx] if idx < len(badges) else "🔹"
        text += f"{badge} User ID: `{masked_id}` — **{count} ယောက်**\n"

    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📜 ငွေထုတ်မှတ်တမ်း")
def show_history(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT amount, account_info, created_at FROM withdrawals WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(user_id, "📜 သင့်တွင် ငွေထုတ်ယူခဲ့သည့် မှတ်တမ်း မရှိသေးပါ။")
        return

    text = "📜 **သင့်၏ နောက်ဆုံး ငွေထုတ်ယူမှု မှတ်တမ်း (၅) ခု:**\n\n"
    for amount, info, date_str in rows:
        d = date_str if date_str else "N/A"
        text += f"💰 ပမာဏ: **{amount:,} ကျပ်**\n💳 အကောင့်: `{info}`\n📅 အချိန်: {d}\n⚡ အခြေအနေ: **PAID ✅**\n━━━━━━━━━━━━━━━━━━━━\n"

    bot.send_message(user_id, text, parse_mode="Markdown")

# ==========================================
# 💸 WITHDRAWAL SYSTEM
# ==========================================
@bot.message_handler(func=lambda m: m.text == "💸 ငွေထုတ်မည်")
def request_withdraw(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    
    balance = get_user_balance(user_id)
    min_withdraw = int(get_setting('MIN_WITHDRAW', '5000'))
    
    if balance < min_withdraw:
        bot.send_message(user_id, f"⚠️ အနည်းဆုံး **{min_withdraw:,} ကျပ်** ပြည့်မှ ငွေထုတ်ယူနိုင်ပါမည်။\nသင့်လက်ရှိ မုန့်ဖိုး လက်ကျန်: **{balance:,} ကျပ်**", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_kpay = types.InlineKeyboardButton("📱 KBZPay", callback_data="pay_KBZPay")
    btn_wave = types.InlineKeyboardButton("📱 WavePay", callback_data="pay_WavePay")
    markup.add(btn_kpay, btn_wave)
    
    bot.send_message(user_id, f"💳 **ငွေထုတ်ယူမည့် Payment Method ကို ရွေးချယ်ပါ:**\n\n💰 သင့်လက်ကျန်: **{balance:,} ကျပ်**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def select_payment_method(call):
    user_id = call.from_user.id
    method = call.data.split("_")[1]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    msg = bot.send_message(
        user_id, 
        f"📱 ရွေးချယ်ထားသော စနစ်: **{method}**\n\n"
        f"ကျေးဇူးပြု၍ ငွေထုတ်ယူမည့် **{method} အကောင့်အမည်** နှင့် **ဖုန်းနံပါတ်** ကို ရေးပို့ပေးပါ:\n\n"
        f"💡 **E.g. (ဥပမာ) -** `U Aung Aung - 09123456789`",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_account_info, method)

def process_account_info(message, method):
    user_id = message.from_user.id
    account_info = message.text.strip() if message.text else "N/A"
    
    balance = get_user_balance(user_id)
    min_withdraw = int(get_setting('MIN_WITHDRAW', '5000'))
    
    msg = bot.send_message(
        user_id,
        f"💰 ထုတ်ယူလိုသည့် **မုန့်ဖိုး ပမာဏ (Amount)** ကို ဂဏန်းသီးသန့် ရိုက်ထည့်ပေးပါ:\n"
        f"(အနည်းဆုံး: **{min_withdraw:,} ကျပ်** | သင့်လက်ကျန်: **{balance:,} ကျပ်**)",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_withdraw_amount, method, account_info)

def process_withdraw_amount(message, method, account_info):
    user_id = message.from_user.id
    
    if not message.text or not message.text.strip().isdigit():
        bot.send_message(user_id, "❌ ပမာဏကို ဂဏန်းသီးသန့်သာ ရိုက်ထည့်ပါ။ ပြန်လည်စတင်ရန် '💸 ငွေထုတ်မည်' ကို နှိပ်ပါ။")
        return
        
    amount = int(message.text.strip())
    balance = get_user_balance(user_id)
    min_withdraw = int(get_setting('MIN_WITHDRAW', '5000'))
    
    if amount < min_withdraw:
        bot.send_message(user_id, f"❌ ထုတ်ယူလိုသည့် ပမာဏသည် အနည်းဆုံး **{min_withdraw:,} ကျပ်** ရှိရပါမည်။", parse_mode="Markdown")
        return
        
    if amount > balance:
        bot.send_message(user_id, f"❌ သင့် မုန့်ဖိုး လက်ကျန် (**{balance:,} ကျပ်**) ထက် ပိုထုတ်၍ မရပါ။", parse_mode="Markdown")
        return
        
    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    cursor.execute("INSERT INTO withdrawals (user_id, amount, account_info, status, created_at) VALUES (?, ?, ?, 'APPROVED', ?)", (user_id, amount, f"{method}: {account_info}", date_now))
    conn.commit()
    conn.close()
    
    bot.send_message(
        user_id, 
        f"✅ **ငွေထုတ်ယူမှု တောင်းဆိုပြီးပါပြီ!**\n\n"
        f"💰 ထုတ်ယူသည့် ပမာဏ: **{amount:,} ကျပ်**\n"
        f"📱 ငွေလွှဲစနစ်: **{method}**\n"
        f"💳 အကောင့်အချက်အလက်: `{account_info}`\n\n"
        f"📢 Proof Channel တွင် သွားရောက် စစ်ဆေးနိုင်ပါသည်။", 
        parse_mode="Markdown"
    )
    
    # Auto Post to Proof Channel
    proof_channel = get_setting('PROOF_CHANNEL', '@daily_cashmmproof')
    proof_img = get_setting('PROOF_IMAGE_URL', '')
    
    u_str = str(user_id)
    masked_id = u_str[:4] + "****" if len(u_str) > 4 else u_str
    bot_username = bot.get_me().username
    
    proof_msg = (
        f"🚀 **မုန့်ဖိုး လွှဲပြောင်းပေးမှု အောင်မြင်ပါပြီ!**\n\n"
        f"👤 **User ID:** `{masked_id}`\n"
        f"💰 **ထုတ်ယူသည့် မုန့်ဖိုး:** **{amount:,} ကျပ်**\n"
        f"💳 **ငွေလွှဲစနစ်:** **{method}**\n"
        f"⚡ **အခြေအနေ:** **ငွေလွှဲပြီးပါပြီ (PAID) ✅**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 **လူတိုင်း နေ့စဉ် မုန့်ဖိုး အလွယ်တကူ ရှာယူနိုင်ပါပြီ!**\n\n"
        f"🤖 **မုန့်ဖိုး သွားရောက်ထုတ်ယူရန် Bot Link:**\n"
        f"👉 @{bot_username}"
    )
    
    try:
        if proof_img:
            try: bot.send_photo(proof_channel, proof_img, caption=proof_msg, parse_mode="Markdown")
            except Exception: bot.send_message(proof_channel, proof_msg, parse_mode="Markdown")
        else:
            bot.send_message(proof_channel, proof_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Proof Channel Posting Error: {e}")

# ==========================================
# 👤 USER FEATURES
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🔗 Referral Link")
def show_ref_link(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    if get_unsubscribed_channels(user_id):
        bot.send_message(user_id, "❌ ကျေးဇူးပြု၍ Channel များကို အရင် Join ပေးပါ။", reply_markup=get_channels_keyboard())
        return

    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    reward = get_setting('REWARD_PER_REF', '100')
    msg = (
        f"🔗 **သင့်ရဲ့ သီးသန့် Referral Link:**\n`{ref_link}`\n\n"
        f"🎁 ဒီ Link ကို သူငယ်ချင်းတွေဆီ ပို့ပေးပါ။ လူတစ်ယောက် Join တိုင်း **{reward} ကျပ်** ရရှိပါမည်။"
    )
    bot.send_message(user_id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💰 မုန့်ဖိုး လက်ကျန်")
def show_balance(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    balance = get_user_balance(user_id)
    bot.send_message(user_id, f"💰 သင့်လက်ရှိ မုန့်ဖိုး လက်ကျန်: **{balance:,} ကျပ်**", parse_mode="Markdown")

# ==========================================
# 👑 ADMIN PANEL & PROMO CODE CREATION
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(ADMIN_ID, "👑 **Admin Control Panel**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎟️ Promo Code သစ်လုပ်ရန်")
def create_promo_prompt(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🎟️ ပြုလုပ်ချင်သော **Promo Code နာမည်** ကို ရေးပို့ပါ (ဥပမာ- `LUCKY100`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_promo_name)

def process_promo_name(message):
    code = message.text.strip().upper() if message.text else ""
    if not code:
        bot.send_message(ADMIN_ID, "❌ Code မမှန်ပါ။")
        return
    msg = bot.send_message(ADMIN_ID, f"💰 Code: `{code}` အတွက် **ပေးမည့် မုန့်ဖိုး ပမာဏ** ရေးပို့ပါ (ဥပမာ - `100`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_promo_reward, code)

def process_promo_reward(message, code):
    if not message.text or not message.text.strip().isdigit():
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")
        return
    reward = int(message.text.strip())
    msg = bot.send_message(ADMIN_ID, f"👥 ဒီ Code ကို **လူဦးရေ မည်မျှ ရယူနိုင်မလဲ** ရေးပို့ပါ (ဥပမာ - `50`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_promo_limit, code, reward)

def process_promo_limit(message, code, reward):
    if not message.text or not message.text.strip().isdigit():
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")
        return
    limit = int(message.text.strip())

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO promo_codes (code, reward, max_claims, claimed_count) VALUES (?, ?, ?, 0)", (code, reward, limit))
    conn.commit()
    conn.close()

    bot.send_message(
        ADMIN_ID, 
        f"✅ **Promo Code အသစ် ဖန်တီးပြီးပါပြီ!** 🎉\n\n"
        f"🎟️ Code: `{code}`\n"
        f"💰 မုန့်ဖိုး: **{reward:,} ကျပ်**\n"
        f"👥 ကန့်သတ်ချက်: **{limit} ယောက်**",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )

# --- ADMIN SETTINGS ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Bot Settings ပြင်ရန်")
def bot_settings_menu(message):
    if message.from_user.id != ADMIN_ID: return
    
    current_reward = get_setting('REWARD_PER_REF', '100')
    current_daily = get_setting('DAILY_BONUS', '50')
    current_min = get_setting('MIN_WITHDRAW', '5000')
    current_channels = get_setting('CHANNELS', '@daily_cashmmproof')
    current_proof_img = get_setting('PROOF_IMAGE_URL', '')
    
    msg = (
        f"⚙️ **လက်ရှိ Bot Settings များ:**\n\n"
        f"🎁 **Ref Reward:** {current_reward} ကျပ်\n"
        f"📅 **Daily Bonus:** {current_daily} ကျပ်\n"
        f"💸 **Min Withdraw:** {current_min} ကျပ်\n"
        f"📢 **Channels:** `{current_channels}`\n"
        f"🖼️ **Proof Image Status:** {'✅ ပုံ သတ်မှတ်ပြီးပါပြီ' if current_proof_img else '❌ မသတ်မှတ်ရသေးပါ'}"
    )
    bot.send_message(ADMIN_ID, msg, reply_markup=get_settings_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📅 Daily Bonus ပြင်ရန်")
def edit_daily_bonus(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "📅 နေ့စဉ် ပေးမည့် Daily Bonus ပမာဏသစ်ကို ရေးပို့ပါ (ဥပမာ - 50):")
    bot.register_next_step_handler(msg, save_daily_bonus)

def save_daily_bonus(message):
    if message.text and message.text.strip().isdigit():
        set_setting('DAILY_BONUS', message.text.strip())
        bot.send_message(ADMIN_ID, f"✅ Daily Bonus ကို **{message.text.strip()} ကျပ်** သို့ ပြောင်းလဲလိုက်ပါပြီ။", reply_markup=get_settings_keyboard())
    else:
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့်သာ ရေးပို့ပါ။")

@bot.message_handler(func=lambda m: m.text == "🎁 Ref Reward ပြင်ရန်")
def edit_ref_reward(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🎁 Ref တစ်ယောက်ခေါ်ရင် ပေးမည့် မုန့်ဖိုး ရေးပို့ပါ (ဥပမာ - 100):")
    bot.register_next_step_handler(msg, save_ref_reward)

def save_ref_reward(message):
    if message.text and message.text.strip().isdigit():
        set_setting('REWARD_PER_REF', message.text.strip())
        bot.send_message(ADMIN_ID, f"✅ Ref Reward ကို **{message.text.strip()} ကျပ်** သို့ ပြောင်းလဲလိုက်ပါပြီ။", reply_markup=get_settings_keyboard())
    else:
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့်သာ ရေးပို့ပါ။")

@bot.message_handler(func=lambda m: m.text == "💸 Min Withdraw ပြင်ရန်")
def edit_min_withdraw(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "💸 အနည်းဆုံး ငွေထုတ်ယူနိုင်သည့် ပမာဏသစ်ကို ရေးပို့ပါ (ဥပမာ - 3000):")
    bot.register_next_step_handler(msg, save_min_withdraw)

def save_min_withdraw(message):
    if message.text and message.text.strip().isdigit():
        set_setting('MIN_WITHDRAW', message.text.strip())
        bot.send_message(ADMIN_ID, f"✅ Min Withdraw ကို **{message.text.strip()} ကျပ်** သို့ ပြောင်းလဲလိုက်ပါပြီ။", reply_markup=get_settings_keyboard())
    else:
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့်သာ ရေးပို့ပါ။")

@bot.message_handler(func=lambda m: m.text == "📢 Join Channels ပြင်ရန်")
def edit_channels(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "📢 User များကို Join ခိုင်းမည့် Channel များကို Comma (,) ခြားပြီး ရေးပို့ပါ:")
    bot.register_next_step_handler(msg, save_channels)

def save_channels(message):
    if message.text:
        set_setting('CHANNELS', message.text.strip())
        bot.send_message(ADMIN_ID, f"✅ Channel များကို ပြောင်းလဲပြီးပါပြီ:\n`{message.text.strip()}`", parse_mode="Markdown", reply_markup=get_settings_keyboard())

@bot.message_handler(func=lambda m: m.text == "🖼️ Proof Image URL ပြင်ရန်")
def edit_proof_img(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🖼️ Proof Channel တွင် တင်မည့် **ပုံကို Bot ထဲသို့ တိုက်ရိုက် Send (Photo) ပို့ပေးပါ**:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_proof_img)

def save_proof_img(message):
    if message.photo:
        file_id = message.photo[-1].file_id
        set_setting('PROOF_IMAGE_URL', file_id)
        bot.send_message(ADMIN_ID, "✅ Proof Image ကို Bot ထဲတွင် **တိုက်ရိုက် သိမ်းဆည်းလိုက်ပါပြီ!** ✨", reply_markup=get_settings_keyboard(), parse_mode="Markdown")
    elif message.text:
        set_setting('PROOF_IMAGE_URL', message.text.strip())
        bot.send_message(ADMIN_ID, "✅ Proof Image URL ကို ပြောင်းလဲပြီးပါပြီ။", reply_markup=get_settings_keyboard())
    else:
        bot.send_message(ADMIN_ID, "❌ ကျေးဇူးပြု၍ ပုံ သို့မဟုတ် Link တစ်ခုခု ပို့ပေးပါ။")

@bot.message_handler(func=lambda m: m.text == "🔙 Admin Menu သို့")
def back_to_admin(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(ADMIN_ID, "Admin Menu သို့ ပြန်ရောက်ပါပြီ။", reply_markup=get_admin_keyboard())

# --- USER MANAGEMENT & BROADCAST ---
@bot.message_handler(func=lambda m: m.text == "💰 User မုန့်ဖိုး ပြင်ရန်")
def set_balance_prompt(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "💰 မုန့်ဖိုး ပြင်ဆင်ချင်သော `User ID` ကို ရေးပို့ပါ:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_set_balance_user)

def process_set_balance_user(message):
    if not message.text or not message.text.strip().isdigit():
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")
        return
    target_id = int(message.text.strip())
    msg = bot.send_message(ADMIN_ID, f"ထည့်သွင်းလိုသော မုန့်ဖိုး ပမာဏ ကို ရေးပို့ပါ (User ID: `{target_id}`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_set_balance_amount, target_id)

def process_set_balance_amount(message, target_id):
    if not message.text or not message.text.strip().isdigit():
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")
        return
    new_balance = int(message.text.strip())
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, target_id))
    conn.commit()
    conn.close()
    
    bot.send_message(ADMIN_ID, f"✅ User `{target_id}` ၏ မုန့်ဖိုးကို **{new_balance:,} ကျပ်** သို့ ပြင်ဆင်ပြီးပါပြီ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 User စစ်မည်")
def lookup_user_prompt(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🔍 စစ်ဆေးချင်သည့် `User ID` ကို ရေးပို့ပါ:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_lookup_user)

def process_lookup_user(message):
    if not message.text or not message.text.strip().isdigit():
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")
        return
    target_id = int(message.text.strip())
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, is_verified, is_banned FROM users WHERE user_id = ?", (target_id,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (target_id,))
        ref_count = cursor.fetchone()[0]
        conn.close()
        
        status_ban = "🚫 Banned" if row[2] == 1 else "🟢 Active"
        verified = "✅ Verified" if row[1] == 1 else "❌ Unverified"
        
        info = (
            f"👤 **User Info (#`{target_id}`)**\n\n"
            f"💰 မုန့်ဖိုး လက်ကျန်: **{row[0]:,} ကျပ်**\n"
            f"👥 ခေါ်ထားသော လူဦးရေ: **{ref_count} ယောက်**\n"
            f"⚡ အခြေအနေ: {verified} | {status_ban}"
        )
        bot.send_message(ADMIN_ID, info, parse_mode="Markdown")
    else:
        conn.close()
        bot.send_message(ADMIN_ID, "❌ အဆိုပါ User ရှာမတွေ့ပါ။")

@bot.message_handler(func=lambda m: m.text == "📊 စာရင်းဇယားကြည့်ရန်")
def show_stats(message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    conn.close()

    bot.send_message(ADMIN_ID, f"📊 **Bot Stats**\n\n👥 စုစုပေါင်း User: **{total_users}**\n💰 ပေးရန်ကျန် မုန့်ဖိုး: **{total_balance:,} ကျပ်**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast စာပို့မည်")
def broadcast_start(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "📢 သုံးစွဲသူများထံ ပို့ချင်သည့် စာ သို့မဟုတ် Photo/Video ကို ပို့ပေးပါ:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    conn.close()

    success, failed = 0, 0
    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=ADMIN_ID, message_id=message.message_id)
            success += 1
        except Exception:
            failed += 1

    bot.send_message(ADMIN_ID, f"✅ Broadcast ပို့ပြီးပါပြီ။\n🟢 အောင်မြင်: {success}\n🔴 မအောင်မြင်: {failed}")

@bot.message_handler(func=lambda m: m.text == "🚫 User Ban/Unban")
def ban_prompt(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🚫 Ban သို့မဟုတ် Unban လုပ်ချင်သည့် `User_ID` ကို ရေးပို့ပါ:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_ban_unban)

def process_ban_unban(message):
    try:
        target_id = int(message.text.strip())
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (target_id,))
        row = cursor.fetchone()

        if row:
            new_status = 0 if row[0] == 1 else 1
            cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, target_id))
            conn.commit()
            status_str = "Unban လုပ်ပြီးပါပြီ ✅" if new_status == 0 else "Ban လိုက်ပါပြီ 🚫"
            bot.send_message(ADMIN_ID, f"User `{target_id}` ကို {status_str}", parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, "❌ User ရှာမတွေ့ပါ။")
        conn.close()
    except Exception:
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")

@bot.message_handler(func=lambda m: m.text == "🔙 Main Menu သို့")
def back_to_main(message):
    bot.send_message(message.chat.id, "Main Menu သို့ ပြန်ရောက်ပါပြီ။", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "ℹ️ အကူအညီ")
def help_msg(message):
    bot.send_message(message.chat.id, "ဒီ Bot ကတော့ Referral စနစ်၊ Daily Bonus နဲ့ Promo Code များမှတစ်ဆင့် မုန့်ဖိုး အလွယ်တကူ ရှာယူနိုင်သော Bot ဖြစ်ပါတယ်။")

# ==========================================
# 🚀 BOT STARTUP
# ==========================================
if __name__ == "__main__":
    init_db()
    print("🚀 All-in-One Daily Cash Bot is running...")
    bot.infinity_polling()
