import os
import sqlite3
import telebot
from telebot import types

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Channel များကို Comma (,) ခြားပြီး ထည့်ပါ
# ဥပမာ - "@channel1,@channel2,@channel3"
CHANNELS_RAW = os.environ.get("CHANNELS", "@channel1,@channel2")
CHANNELS = [ch.strip() for ch in CHANNELS_RAW.split(",") if ch.strip()]

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

REWARD_PER_REF = 100  # လူတစ်ယောက်ခေါ်လျှင် ရမည့် ပမာဏ
MIN_WITHDRAW = 1000   # အနည်းဆုံး ထုတ်ယူနိုင်သည့် ပမာဏ

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            referred_by INTEGER,
            is_verified INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# User မ Join ရသေးသည့် Channel များကို စစ်ဆေးရှာဖွေပေးသည့် Function
def get_unsubscribed_channels(user_id):
    unsub_list = []
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsub_list.append(ch)
        except Exception:
            # Bot ကို Admin မပေးထားပါက သို့မဟုတ် Channel ရှာမတွေ့ပါက မ Join ရသေးဟု သတ်မှတ်မည်
            unsub_list.append(ch)
    return unsub_list

# Channel များစွာအတွက် Join Buttons များ ပြုလုပ်ပေးခြင်း
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

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
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
        cursor.execute("INSERT INTO users (user_id, balance, referred_by, is_verified) VALUES (?, 0, ?, 0)", (user_id, referrer_id))
        conn.commit()

    conn.close()

    unsubscribed = get_unsubscribed_channels(user_id)
    if unsubscribed:
        bot.send_message(
            user_id,
            f"👋 မင်္ဂလာပါ {message.from_user.first_name}!\n\nBot ကို စတင်အသုံးပြုရန် အောက်ပါ Channel **အားလုံး** ကို Join ပေးပါနော်။",
            reply_markup=get_channels_keyboard()
        )
    else:
        bot.send_message(
            user_id,
            f"🎉 မင်္ဂလာပါ {message.from_user.first_name}!\n\nChannel များ Join ထားတာ အတည်ပြုပြီးပါပြီ။ မီနူးများမှတစ်ဆင့် စတင်အသုံးပြုနိုင်ပါပြီ။",
            reply_markup=get_main_keyboard()
        )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    user_id = call.from_user.id
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
                    bot.send_message(ref_id, f"🎉 သင့် Referral Link မှတစ်ဆင့် လူတစ်ယောက် Join သွားသဖြင့် {REWARD_PER_REF} ကျပ် ရရှိပါပြီ!")
                except Exception:
                    pass
            else:
                conn.commit()

        conn.close()
        bot.answer_callback_query(call.id, "✅ Channel များ အားလုံး Join ပြီးပါပြီ!")
        bot.send_message(user_id, "အဆင်ပြေပါပြီ! အောက်ပါ မီနူးများကို အသုံးပြုနိုင်ပါပြီ။", reply_markup=get_main_keyboard())
    else:
        # Join ရန် ကျန်နေသေးသော Channel အေရအတွက်ကို အသိပေးခြင်း
        bot.answer_callback_query(
            call.id, 
            f"❌ Channel {len(unsubscribed)} ခု Join ရန် ကျန်ပါသေးသည်။ အားလုံးကို Join ပြီးမှ နှိပ်ပါ!", 
            show_alert=True
        )

@bot.message_handler(func=lambda m: m.text == "🔗 Referral Link")
def show_ref_link(message):
    user_id = message.from_user.id
    if get_unsubscribed_channels(user_id):
        bot.send_message(user_id, "❌ ကျေးဇူးပြု၍ မဖြစ်မနေ Join ရမည့် Channel များကို အရင် Join ပေးပါ။", reply_markup=get_channels_keyboard())
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
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    balance = row[0] if row else 0
    if balance < MIN_WITHDRAW:
        bot.send_message(user_id, f"⚠️ အနည်းဆုံး **{MIN_WITHDRAW} ကျပ်** ပြည့်မှ ငွေထုတ်ယူနိုင်ပါမည်။\nသင့်လက်ကျန်: {balance} ကျပ်", parse_mode="Markdown")
    else:
        msg = bot.send_message(user_id, f"💳 ငွေထုတ်ယူရန် သင့် KBZPay သို့မဟုတ် WavePay ဖုန်းနံပါတ်နှင့် နာမည်ကို ရေးပို့ပေးပါ:\n(ဥပမာ - 09123456789 - U Ba)")
        bot.register_next_step_handler(msg, process_withdraw_request, balance)

def process_withdraw_request(message, balance):
    user_id = message.from_user.id
    payment_info = message.text
    
    if ADMIN_ID != 0:
        try:
            admin_msg = (
                f"🚨 **ငွေထုတ်ယူရန် တောင်းဆိုမှု!**\n\n"
                f"👤 User ID: `{user_id}`\n"
                f"👤 Name: {message.from_user.first_name}\n"
                f"💰 ပမာဏ: {balance} ကျပ်\n"
                f"📱 ထုတ်မည့်အကောင့်: {payment_info}"
            )
            bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
            
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()

            bot.send_message(user_id, "✅ ငွေထုတ်ယူရန် လျှောက်ထားမှု အောင်မြင်ပါသည်။ Admin မှ စစ်ဆေးပြီး မကြာမီ ငွေလွှဲပေးပါလိမ့်မည်။")
        except Exception:
            bot.send_message(user_id, "❌ အကြောင်းတစ်ခုခုကြောင့် မအောင်မြင်ပါ။ Admin ထံ တိုက်ရိုက် ဆက်သွယ်ပါ။")

@bot.message_handler(func=lambda m: m.text == "ℹ️ အကူအညီ")
def help_msg(message):
    bot.send_message(message.chat.id, "ဒီ Bot ကတော့ Channel Subscriber တိုးပွားရေးအတွက် Referral စနစ်နဲ့ မုန့်ဖိုးပေးတဲ့ Bot ဖြစ်ပါတယ်။")

if __name__ == "__main__":
    init_db()
    print("Bot is running...")
    bot.infinity_polling()
