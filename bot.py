import os
import sqlite3
import random
import telebot
from telebot import types

# ==========================================
# ⚙️ CONFIGURATION & ENVIRONMENT VARIABLES
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Channel များကို Comma (,) ခြားပြီး ထည့်ပါ (ဥပမာ - "@channel1,@channel2")
CHANNELS_RAW = os.environ.get("CHANNELS", "@channel1,@channel2")
CHANNELS = [ch.strip() for ch in CHANNELS_RAW.split(",") if ch.strip()]

# Proof Channel (ငွေလွှဲပြေစာ သက်သေပြရန် Channel)
PROOF_CHANNEL = os.environ.get("PROOF_CHANNEL", "")  # ဥပမာ - "@my_proof_channel"

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
REWARD_PER_REF = int(os.environ.get("REWARD_PER_REF", "100"))
MIN_WITHDRAW = int(os.environ.get("MIN_WITHDRAW", "1000"))

bot = telebot.TeleBot(TOKEN)

# Temporary memory for Math Captcha answers {user_id: answer}
captcha_store = {}

# ==========================================
# 🗄️ DATABASE SETUP
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

def get_unsubscribed_channels(user_id):
    unsub_list = []
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsub_list.append(ch)
        except Exception as e:
            print(f"❌ Error checking channel {ch}: {e}")
            unsub_list.append(ch)
    return unsub_list

def get_channels_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for index, ch in enumerate(CHANNELS, 1):
        clean_username = ch.replace('@', '')
        btn = types.InlineKeyboardButton(f"📢 Join Channel {index} ({ch})", url=f"https://t.me/{clean_username}")
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
    btn2 = types.KeyboardButton("📢 Broadcast စာပို့မည်")
    btn3 = types.KeyboardButton("🚫 User Ban/Unban")
    btn4 = types.KeyboardButton("🔙 Main Menu သို့")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# ==========================================
# 🤖 START & CAPTCHA SYSTEM
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
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        possible_ref = int(args[1])
        if possible_ref != user_id:
            referrer_id = possible_ref

    if not user:
        cursor.execute("INSERT INTO users (user_id, balance, referred_by, is_verified, is_banned) VALUES (?, 0, ?, 0, 0)", (user_id, referrer_id))
        conn.commit()

    conn.close()

    # Math Captcha ဖန်တီးခြင်း
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    captcha_store[user_id] = num1 + num2

    msg = bot.send_message(
        user_id, 
        f"🤖 **Anti-Bot Verification**\n\nကျေးဇူးပြု၍ အောက်ပါ သင်္ချာပုစ္ဆာ၏ အဖြေကို ရေးပို့ပေးပါ:\n\n👉 `{num1} + {num2} = ?`", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_captcha)

def process_captcha(message):
    user_id = message.from_user.id
    correct_ans = captcha_store.get(user_id)

    try:
        user_ans = int(message.text.strip())
        if user_ans == correct_ans:
            del captcha_store[user_id]
            unsubscribed = get_unsubscribed_channels(user_id)
            if unsubscribed:
                bot.send_message(
                    user_id,
                    f"✅ Verification အောင်မြင်ပါသည်။\n\nBot ကို စတင်အသုံးပြုရန် အောက်ပါ Channel **အားလုံး** ကို Join ပေးပါနော်။",
                    reply_markup=get_channels_keyboard()
                )
            else:
                bot.send_message(user_id, f"🎉 မင်္ဂလာပါ {message.from_user.first_name}!\n\nအောက်ပါ မီနူးများမှတစ်ဆင့် စတင်အသုံးပြုနိုင်ပါပြီ။", reply_markup=get_main_keyboard())
        else:
            msg = bot.send_message(user_id, "❌ အဖြေ မှားယွင်းနေပါသည်။ ထပ်မံ ကြိုးစားကြည့်ပါ:")
            bot.register_next_step_handler(msg, process_captcha)
    except Exception:
        msg = bot.send_message(user_id, "⚠️ ဂဏန်းသီးသန့်သာ ရေးပို့ပေးပါ။ ဥပမာ - 12")
        bot.register_next_step_handler(msg, process_captcha)

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
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REWARD_PER_REF, ref_id))
                conn.commit()
                try:
                    bot.send_message(ref_id, f"🎉 သင့် Referral Link မှတစ်ဆင့် လူတစ်ယောက် Join သွားသဖြင့် **{REWARD_PER_REF} ကျပ်** ရရှိပါပြီ!", parse_mode="Markdown")
                except Exception:
                    pass
            else:
                conn.commit()

        conn.close()
        bot.answer_callback_query(call.id, "✅ Channel များ အားလုံး Join ပြီးပါပြီ!")
        bot.send_message(user_id, "အဆင်ပြေပါပြီ! အောက်ပါ မီနူးများကို အသုံးပြုနိုင်ပါပြီ။", reply_markup=get_main_keyboard())
    else:
        bot.answer_callback_query(call.id, f"❌ Channel {len(unsubscribed)} ခု Join ရန် ကျန်ပါသေးသည်။", show_alert=True)

# ==========================================
# 👤 USER FEATURES (Menu Actions)
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
    msg = (
        f"🔗 **သင့်ရဲ့ သီးသန့် Referral Link:**\n`{ref_link}`\n\n"
        f"🎁 ဒီ Link ကို သူငယ်ချင်းတွေဆီ ပို့ပေးပါ။ လူတစ်ယောက် Join တိုင်း **{REWARD_PER_REF} ကျပ်** ရရှိပါမည်။"
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
    if balance < MIN_WITHDRAW:
        bot.send_message(user_id, f"⚠️ အနည်းဆုံး **{MIN_WITHDRAW} ကျပ်** ပြည့်မှ ငွေထုတ်ယူနိုင်ပါမည်။\nသင့်လက်ကျန်: {balance} ကျပ်", parse_mode="Markdown")
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
# 💳 ADMIN WITHDRAWAL APPROVAL & PROOF SYSTEM
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
        
        try:
            bot.send_message(user_id, f"🎉 သင့်ငွေထုတ်ယူမှု **{amount} ကျပ်** အား Admin မှ အတည်ပြုပြီး ငွေလွှဲပေးလိုက်ပါပြီ။")
        except Exception: pass

        # 📢 PROOF CHANNEL သို့ အလိုအလျောက် သက်သေစာ ပို့ပေးခြင်း
        if PROOF_CHANNEL:
            try:
                u_str = str(user_id)
                masked_id = u_str[:4] + "****" if len(u_str) > 4 else u_str
                bot_username = bot.get_me().username
                
                proof_msg = (
                    f"🎉 **ငွေထုတ်ယူမှု အောင်မြင်ကြောင်း သက်သေ!**\n\n"
                    f"👤 User: `{masked_id}`\n"
                    f"💰 ထုတ်ယူသည့် ပမာဏ: **{amount} ကျပ်**\n"
                    f"⚡ အခြေအနေ: **လွှဲပြောင်းပြီးပါပြီ (PAID) ✅**\n\n"
                    f"🤖 သင်လည်း မုန့်ဖိုးများ ရှာယူရန် Bot ကို စတင်လိုက်ပါ:\n👉 @{bot_username}"
                )
                bot.send_message(PROOF_CHANNEL, proof_msg, parse_mode="Markdown")
            except Exception as e:
                print(f"❌ Error posting to Proof Channel: {e}")

    elif action == "rej":
        cursor.execute("UPDATE withdrawals SET status = 'REJECTED' WHERE id = ?", (wd_id,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        bot.edit_message_text(f"{call.message.text}\n\n❌ **ADMIN REJECTED (Refunded)**", chat_id=ADMIN_ID, message_id=call.message.message_id, parse_mode="Markdown")
        
        try:
            bot.send_message(user_id, f"❌ သင့်ငွေထုတ်ယူမှု **{amount} ကျပ်** ကို Admin မှ ငြင်းပယ်လိုက်သဖြင့် သင့်အကောင့်ထဲ မုန့်ဖိုး ပြန်လည်ထည့်ပေးလိုက်ပါသည်။")
        except Exception: pass

    conn.close()

# ==========================================
# 👑 ADMIN CONTROL PANEL
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(ADMIN_ID, "👑 **Admin Control Panel**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

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
    print("🚀 Full Referral Bot is running...")
    bot.infinity_polling()
