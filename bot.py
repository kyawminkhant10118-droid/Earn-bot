import os
import sqlite3
import telebot
from telebot import types

# ==========================================
# ⚙️ INITIAL CONFIGURATION
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 🗄️ DATABASE SETUP & SETTINGS SYSTEM
# ==========================================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            referred_by INTEGER,
            is_verified INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            account_info TEXT,
            status TEXT DEFAULT 'PENDING'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Dynamic Settings Default သတ်မှတ်ခြင်း
    defaults = {
        'REWARD_PER_REF': '100',
        'MIN_WITHDRAW': '5000',
        'CHANNELS': '@channel1,@channel2',
        'PROOF_CHANNEL': '@daily_cashmmproof',
        'PROOF_IMAGE_URL': 'https://i.ibb.co/3s3KqV7/reward-logo.png'
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

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def is_user_banned(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def get_channels_list():
    raw = get_setting('CHANNELS', '')
    return [ch.strip() for ch in raw.split(",") if ch.strip()]

def get_unsubscribed_channels(user_id):
    unsub_list = []
    channels = get_channels_list()
    for ch in channels:
        ch_target = ch.strip()
        if not ch_target:
            continue
            
        if "t.me/" in ch_target:
            if not "+" in ch_target and not "joinchat" in ch_target:
                ch_target = "@" + ch_target.split("t.me/")[-1].replace("+", "").strip()
        elif not ch_target.startswith("@") and not ch_target.startswith("-100"):
            ch_target = "@" + ch_target

        try:
            member = bot.get_chat_member(ch_target, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsub_list.append(ch)
        except Exception as e:
            print(f"❌ Error checking channel '{ch_target}': {e}")
            unsub_list.append(ch)
            
    return unsub_list

def get_channels_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    channels = get_channels_list()
    for index, ch in enumerate(channels, 1):
        ch_clean = ch.strip()
        if ch_clean.startswith("http://") or ch_clean.startswith("https://"):
            url = ch_clean
        elif ch_clean.startswith("@"):
            url = f"https://t.me/{ch_clean[1:]}"
        else:
            url = f"https://t.me/{ch_clean}"
            
        btn = types.InlineKeyboardButton(f"📢 Join Channel {index}", url=url)
        markup.add(btn)
    
    btn_check = types.InlineKeyboardButton("အတည်ပြုမည် ✅", callback_data="check_sub")
    markup.add(btn_check)
    return markup

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🔗 Referral Link")
    btn2 = types.KeyboardButton("💰 မုန့်ဖိုး လက်ကျန်")
    btn3 = types.KeyboardButton("💸 ငွေထုတ်မည်")
    btn4 = types.KeyboardButton("ℹ️ အကူအညီ")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("📊 စာရင်းဇယားကြည့်ရန်")
    btn2 = types.KeyboardButton("💰 User မုန့်ဖိုး ပြင်ရန်")
    btn3 = types.KeyboardButton("⚙️ Bot Settings ပြင်ရန်")
    btn4 = types.KeyboardButton("🔍 User စစ်မည်")
    btn5 = types.KeyboardButton("📢 Broadcast စာပို့မည်")
    btn6 = types.KeyboardButton("🚫 User Ban/Unban")
    btn7 = types.KeyboardButton("🔙 Main Menu သို့")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    return markup

def get_settings_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🎁 Ref Reward ပြင်ရန်")
    btn2 = types.KeyboardButton("💸 Min Withdraw ပြင်ရန်")
    btn3 = types.KeyboardButton("📢 Join Channels ပြင်ရန်")
    btn4 = types.KeyboardButton("🖼️ Proof Image URL ပြင်ရန်")
    btn5 = types.KeyboardButton("🔙 Admin Menu သို့")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

# ==========================================
# 🤖 START SYSTEM
# ==========================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    
    if is_user_banned(user_id):
        bot.send_message(user_id, "🚫 သင့်အကောင့်အား စည်းကမ်းဖောက်ဖျက်မှုကြောင့် ပိတ်ပင် (Ban) ထားပါသည်။")
        return

    args = message.text.split()
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, is_verified, referred_by FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        possible_ref = int(args[1])
        if possible_ref != user_id:
            referrer_id = possible_ref

    if not user:
        cursor.execute("INSERT INTO users (user_id, balance, referred_by, is_verified, is_banned) VALUES (?, 0, ?, 0, 0)", (user_id, referrer_id))
        conn.commit()
    else:
        if user[1] == 0 and not user[2] and referrer_id:
            cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
            conn.commit()

    conn.close()

    unsubscribed = get_unsubscribed_channels(user_id)
    if unsubscribed:
        bot.send_message(
            user_id,
            f"🎉 မင်္ဂလာပါ {message.from_user.first_name}!\n\nBot ကို စတင်အသုံးပြုရန် အောက်ပါ Channel **အားလုံး** ကို Join ပေးပါနော်။",
            reply_markup=get_channels_keyboard()
        )
    else:
        bot.send_message(user_id, f"🎉 မင်္ဂလာပါ {message.from_user.first_name}!\n\nအောက်ပါ မီနူးများမှတစ်ဆင့် စတင်အသုံးပြုနိုင်ပါပြီ။", reply_markup=get_main_keyboard())

# ==========================================
# 📢 CHANNEL SUBSCRIPTION CHECKER
# ==========================================
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
                
                try:
                    bot.send_message(ref_id, f"🎉 သင့် Referral Link မှတစ်ဆင့် လူတစ်ယောက် Join သွားသဖြင့် **{reward} ကျပ်** ရရှိပါပြီ!", parse_mode="Markdown")
                except Exception as e:
                    print(f"Error sending ref message: {e}")
            else:
                conn.commit()

        conn.close()
        bot.answer_callback_query(call.id, "✅ Channel များ အားလုံး Join ပြီးပါပြီ!")
        bot.send_message(user_id, "အဆင်ပြေပါပြီ! အောက်ပါ မီနူးများကို အသုံးပြုနိုင်ပါပြီ။", reply_markup=get_main_keyboard())
    else:
        bot.answer_callback_query(call.id, f"❌ Channel {len(unsubscribed)} ခု Join ရန် ကျန်ပါသေးသည်။", show_alert=True)

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
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    balance = row[0] if row else 0
    bot.send_message(user_id, f"💰 သင့်လက်ရှိ မုန့်ဖိုး လက်ကျန်: **{balance} ကျပ်**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💸 ငွေထုတ်မည်")
def request_withdraw(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    balance = row[0] if row else 0
    min_withdraw = int(get_setting('MIN_WITHDRAW', '5000'))
    
    if balance < min_withdraw:
        bot.send_message(user_id, f"⚠️ အနည်းဆုံး **{min_withdraw} ကျပ်** ပြည့်မှ ငွေထုတ်ယူနိုင်ပါမည်။\nသင့်လက်ကျန်: {balance} ကျပ်", parse_mode="Markdown")
    else:
        msg = bot.send_message(user_id, f"💳 ငွေထုတ်ယူရန် သင့် KBZPay / WavePay ဖုန်းနံပါတ်နှင့် နာမည် ရေးပို့ပေးပါ:\n(ဥပမာ - 09123456789 - U Ba)")
        bot.register_next_step_handler(msg, process_withdraw_request, balance)

def process_withdraw_request(message, balance):
    user_id = message.from_user.id
    payment_info = message.text

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (balance, user_id))
    cursor.execute("INSERT INTO withdrawals (user_id, amount, account_info) VALUES (?, ?, ?)", (user_id, balance, payment_info))
    wd_id = cursor.lastrowid
    conn.commit()
    conn.close()

    bot.send_message(user_id, "✅ ငွေထုတ်ယူရန် လျှောက်ထားပြီးပါပြီ။ Admin မှ စစ်ဆေးပြီး လွှဲပေးပါလိမ့်မည်။")

    if ADMIN_ID != 0:
        markup = types.InlineKeyboardMarkup()
        btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"wd_app_{wd_id}")
        btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"wd_rej_{wd_id}")
        markup.add(btn_approve, btn_reject)

        admin_msg = (
            f"🚨 **ငွေထုတ်ယူရန် တောင်းဆိုမှု (#WD{wd_id})**\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"💰 ပမာဏ: **{balance} ကျပ်**\n"
            f"📱 အကောင့်: `{payment_info}`"
        )
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 💳 ADMIN WITHDRAWAL APPROVAL (PROOF CHANNEL ONLY)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_"))
def handle_withdrawal_action(call):
    if call.from_user.id != ADMIN_ID: return

    action, wd_id = call.data.split("_")[1], int(call.data.split("_")[2])
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount, status FROM withdrawals WHERE id = ?", (wd_id,))
    wd = cursor.fetchone()

    if not wd or wd[2] != 'PENDING':
        bot.answer_callback_query(call.id, "⚠️ ဒီ တောင်းဆိုမှုကို လုပ်ဆောင်ပြီးပါပြီ။", show_alert=True)
        conn.close()
        return

    user_id, amount = wd[0], wd[1]

    if action == "app":
        cursor.execute("UPDATE withdrawals SET status = 'APPROVED' WHERE id = ?", (wd_id,))
        conn.commit()
        bot.edit_message_text(f"{call.message.text}\n\n✅ **ADMIN APPROVED**", chat_id=ADMIN_ID, message_id=call.message.message_id, parse_mode="Markdown")
        
        # User ထံ စာမပို့ပါ (User ကို မပြပါ)

        # 📢 PROOF CHANNEL သို့သာ စာ/ပုံ အလိုအလျောက် သွားတင်ခြင်း
        proof_channel = get_setting('PROOF_CHANNEL', '@daily_cashmmproof')
        proof_img = get_setting('PROOF_IMAGE_URL', '')
        
        try:
            u_str = str(user_id)
            masked_id = u_str[:4] + "****" if len(u_str) > 4 else u_str
            bot_username = bot.get_me().username
            
            proof_msg = (
                f"🚀 **မုန့်ဖိုး လွှဲပြောင်းပေးမှု အောင်မြင်ပါပြီ!**\n\n"
                f"👤 **User ID:** `{masked_id}`\n"
                f"💰 **ထုတ်ယူသည့် မုန့်ဖိုး:** **{amount:,} ကျပ်**\n"
                f"💳 **ငွေလွှဲစနစ်:** KBZPay / WavePay\n"
                f"⚡ **အခြေအနေ:** **ငွေလွှဲပြီးပါပြီ (PAID) ✅**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎁 **လူတိုင်း နေ့စဉ် မုန့်ဖိုး အလွယ်တကူ ရှာယူနိုင်ပါပြီ!**\n\n"
                f"🤖 **မုန့်ဖိုး သွားရောက်ထုတ်ယူရန် Bot Link:**\n"
                f"👉 @{bot_username}"
            )
            
            if proof_img:
                bot.send_photo(proof_channel, proof_img, caption=proof_msg, parse_mode="Markdown")
            else:
                bot.send_message(proof_channel, proof_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Error posting to Proof Channel: {e}")

    elif action == "rej":
        cursor.execute("UPDATE withdrawals SET status = 'REJECTED' WHERE id = ?", (wd_id,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        bot.edit_message_text(f"{call.message.text}\n\n❌ **ADMIN REJECTED (Refunded)**", chat_id=ADMIN_ID, message_id=call.message.message_id, parse_mode="Markdown")

    conn.close()

# ==========================================
# 👑 ADMIN CONTROL PANEL & BOT SETTINGS
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(ADMIN_ID, "👑 **Admin Control Panel**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⚙️ Bot Settings ပြင်ရန်")
def bot_settings_menu(message):
    if message.from_user.id != ADMIN_ID: return
    
    current_reward = get_setting('REWARD_PER_REF', '100')
    current_min = get_setting('MIN_WITHDRAW', '5000')
    current_channels = get_setting('CHANNELS', '')
    current_proof_img = get_setting('PROOF_IMAGE_URL', '')
    
    msg = (
        f"⚙️ **လက်ရှိ Bot Settings များ:**\n\n"
        f"🎁 **Ref Reward:** {current_reward} ကျပ်\n"
        f"💸 **Min Withdraw:** {current_min} ကျပ်\n"
        f"📢 **Channels:** `{current_channels}`\n"
        f"🖼️ **Proof Image URL:** `{current_proof_img}`\n\n"
        f"အောက်ပါ Button များမှတစ်ဆင့် စိတ်ကြိုက် ပြင်ဆင်နိုင်ပါသည်။"
    )
    bot.send_message(ADMIN_ID, msg, reply_markup=get_settings_keyboard(), parse_mode="Markdown")

# --- SETTINGS EDIT HANDLERS ---
@bot.message_handler(func=lambda m: m.text == "🎁 Ref Reward ပြင်ရန်")
def edit_ref_reward(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🎁 လူတစ်ယောက်ခေါ်ရင် ပေးမည့် မုန့်ဖိုး ပမာဏသစ်ကို ရေးပို့ပါ (ဥပမာ - 150):")
    bot.register_next_step_handler(msg, save_ref_reward)

def save_ref_reward(message):
    if message.text.isdigit():
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
    if message.text.isdigit():
        set_setting('MIN_WITHDRAW', message.text.strip())
        bot.send_message(ADMIN_ID, f"✅ Min Withdraw ကို **{message.text.strip()} ကျပ်** သို့ ပြောင်းလဲလိုက်ပါပြီ။", reply_markup=get_settings_keyboard())
    else:
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့်သာ ရေးပို့ပါ။")

@bot.message_handler(func=lambda m: m.text == "📢 Join Channels ပြင်ရန်")
def edit_channels(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "📢 User များကို Join ခိုင်းမည့် Channel များကို Comma (,) ခြားပြီး ရေးပို့ပါ:\n(ဥပမာ - `@channel1,@channel2,@channel3`)")
    bot.register_next_step_handler(msg, save_channels)

def save_channels(message):
    set_setting('CHANNELS', message.text.strip())
    bot.send_message(ADMIN_ID, f"✅ Channel များကို ပြောင်းလဲပြီးပါပြီ:\n`{message.text.strip()}`", parse_mode="Markdown", reply_markup=get_settings_keyboard())

@bot.message_handler(func=lambda m: m.text == "🖼️ Proof Image URL ပြင်ရန်")
def edit_proof_img(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🖼️ Proof Channel တွင် တင်မည့် ပုံရုပ်ထွက် (Direct Image Link URL) ကို ရေးပို့ပါ:")
    bot.register_next_step_handler(msg, save_proof_img)

def save_proof_img(message):
    set_setting('PROOF_IMAGE_URL', message.text.strip())
    bot.send_message(ADMIN_ID, "✅ Proof Image URL ကို ပြောင်းလဲပြီးပါပြီ။", reply_markup=get_settings_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔙 Admin Menu သို့")
def back_to_admin(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(ADMIN_ID, "Admin Menu သို့ ပြန်ရောက်ပါပြီ။", reply_markup=get_admin_keyboard())

# --- USER MANAGEMENT ---
@bot.message_handler(func=lambda m: m.text == "💰 User မုန့်ဖိုး ပြင်ရန်")
def set_balance_prompt(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "💰 မုန့်ဖိုး ပြင်ဆင်ချင်သော `User ID` ကို ရေးပို့ပါ:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_set_balance_user)

def process_set_balance_user(message):
    if not message.text.isdigit():
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")
        return
    target_id = int(message.text.strip())
    msg = bot.send_message(ADMIN_ID, f"ထည့်သွင်းလိုသော မုန့်ဖိုး ပမာဏ (Amount) ကို ရေးပို့ပါ (User ID: `{target_id}`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_set_balance_amount, target_id)

def process_set_balance_amount(message, target_id):
    if not message.text.isdigit():
        bot.send_message(ADMIN_ID, "❌ ဂဏန်းသီးသန့် ရိုက်ထည့်ပါ။")
        return
    new_balance = int(message.text.strip())
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, target_id))
    conn.commit()
    conn.close()
    
    bot.send_message(ADMIN_ID, f"✅ User `{target_id}` ၏ မုန့်ဖိုးကို **{new_balance} ကျပ်** သို့ ပြင်ဆင်ပြီးပါပြီ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 User စစ်မည်")
def lookup_user_prompt(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(ADMIN_ID, "🔍 စစ်ဆေးချင်သည့် `User ID` ကို ရေးပို့ပါ:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_lookup_user)

def process_lookup_user(message):
    if not message.text.isdigit():
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
            f"💰 မုန့်ဖိုး လက်ကျန်: **{row[0]} ကျပ်**\n"
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

    bot.send_message(ADMIN_ID, f"📊 **Bot Stats**\n\n👥 စုစုပေါင်း User: **{total_users}**\n💰 ပေးရန်ကျန် မုန့်ဖိုး: **{total_balance} ကျပ်**", parse_mode="Markdown")

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
    msg = bot.send_message(ADMIN_ID, " Ban သို့မဟုတ် Unban လုပ်ချင်သည့် `User_ID` ကို ရေးပို့ပါ:", parse_mode="Markdown")
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
    bot.send_message(message.chat.id, "ဒီ Bot ကတော့ Channel Subscriber တိုးပွားရေးအတွက် Referral စနစ်နဲ့ မုန့်ဖိုးပေးတဲ့ Bot ဖြစ်ပါတယ်။")

# ==========================================
# 🚀 BOT STARTUP
# ==========================================
if __name__ == "__main__":
    init_db()
    print("🚀 Fully Controllable Bot is running...")
    bot.infinity_polling()
