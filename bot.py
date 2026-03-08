import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading, time, os, json
from flask import Flask
import requests
from datetime import datetime

================= إعدادات =================

BOT_TOKEN = "8562526168:AAF955_YWK9rhSAKgShvVdrlpqyuKNy9rP4"
ADMIN_ID = 5857668954

P2P_DOLLAR = 49.5
USD_COMMISSION = 0.1
TON_COMMISSION = 0.5

bot = telebot.TeleBot(BOT_TOKEN)

users_data = {}
prices = {"ton_usdt": 0.0}

================= الأرباح =================

profit_file = "profits.json"

if os.path.exists(profit_file):
with open(profit_file) as f:
profits = json.load(f)
else:
profits = {"total":0,"today":0,"date":str(datetime.now().date())}

def save_profit():
with open(profit_file,"w") as f:
json.dump(profits,f)

def add_profit(amount):

today = str(datetime.now().date())  

if profits["date"] != today:  
    profits["date"] = today  
    profits["today"] = 0  

profits["total"] += amount  
profits["today"] += amount  
save_profit()

================= Flask =================

app = Flask(name)

@app.route('/')
def home():
return "Bot Running"

def run_web():
port = int(os.environ.get("PORT",5000))
app.run(host='0.0.0.0',port=port)

threading.Thread(target=run_web).start()

================= تحديث السعر =================

def update_prices():
while True:
try:
data = requests.get("https://www.okx.com/api/v5/market/ticker?instId=TON-USDT").json()
prices["ton_usdt"] = float(data["data"][0]["last"])
except:
prices["ton_usdt"] = 0

time.sleep(60)

threading.Thread(target=update_prices,daemon=True).start()

================= start =================

@bot.message_handler(commands=['start'])
def start(message):

bot.send_message(  
    message.chat.id,  
    "💎 اهلا بك في بوت شراء العملات\n\n"  
    "اكتب /buy لشراء TON او USDT"  
)

================= buy =================

@bot.message_handler(commands=['buy'])
def buy(message):

markup = InlineKeyboardMarkup()  
markup.add(  
    InlineKeyboardButton("🟣 TON",callback_data="ton"),  
    InlineKeyboardButton("💵 USDT",callback_data="usdt")  
)  

bot.send_message(message.chat.id,"اختر العملة:",reply_markup=markup)

================= اختيار العملة =================

@bot.callback_query_handler(func=lambda c:c.data in ["ton","usdt"])
def choose(call):

users_data[call.message.chat.id] = {"currency":call.data}  

bot.send_message(call.message.chat.id,"💰 اكتب المبلغ بالجنيه")

================= المبلغ =================

@bot.message_handler(func=lambda m:m.chat.id in users_data and "amount" not in users_data[m.chat.id])
def amount(message):

try:  
    amount = float(message.text)  
except:  
    bot.reply_to(message,"❌ اكتب رقم صحيح")  
    return  

user = message.chat.id  
data = users_data[user]  

data["amount"] = amount  

ton_price = prices["ton_usdt"]  

final_usd_price = P2P_DOLLAR + USD_COMMISSION  
ton_price_egp = (ton_price * final_usd_price) + TON_COMMISSION  

if data["currency"] == "ton":  
    amount_received = amount / ton_price_egp if ton_price_egp!=0 else 0  
    currency = "TON"  
else:  
    amount_received = amount / final_usd_price  
    currency = "USDT"  

data["amount_received"] = amount_received  

markup = InlineKeyboardMarkup()  
markup.add(InlineKeyboardButton("✅ تأكيد",callback_data="confirm"))  

bot.send_message(  
    user,  
    f"ستحصل على {amount_received:.4f} {currency}",  
    reply_markup=markup  
)

================= confirm =================

@bot.callback_query_handler(func=lambda c:c.data=="confirm")
def confirm(call):

bot.send_message(call.message.chat.id,"ارسل عنوان محفظتك")

================= wallet =================

@bot.message_handler(func=lambda m:m.chat.id in users_data and "wallet" not in users_data[m.chat.id])
def wallet(message):

user = message.chat.id  
users_data[user]["wallet"] = message.text  

markup = InlineKeyboardMarkup()  
markup.add(InlineKeyboardButton("✅ تم الدفع",callback_data="paid"))  

bot.send_message(  
    user,  
    "حول المبلغ الى:\n01020143354",  
    reply_markup=markup  
)

================= paid =================

@bot.callback_query_handler(func=lambda c:c.data=="paid")
def paid(call):

user = call.message.chat.id  
data = users_data[user]  

markup = InlineKeyboardMarkup()  
markup.add(  
    InlineKeyboardButton("✅ قبول",callback_data=f"approve_{user}"),  
    InlineKeyboardButton("❌ رفض",callback_data=f"reject_{user}")  
)  

bot.send_message(  
    ADMIN_ID,  
    f"""

طلب جديد

المستخدم: {user}
المبلغ: {data['amount']}
الكمية: {data['amount_received']}
العملة: {data['currency']}
المحفظة: {data['wallet']}
""",
reply_markup=markup
)

bot.send_message(user,"⏳ جاري مراجعة الدفع")

================= قبول =================

@bot.callback_query_handler(func=lambda c:c.data.startswith("approve"))
def approve(call):

user = int(call.data.split("_")[1])  
data = users_data[user]  

ton_price = prices["ton_usdt"]  

if data["currency"] == "usdt":  
    cost = data["amount_received"] * P2P_DOLLAR  
else:  
    cost = data["amount_received"] * (ton_price * P2P_DOLLAR)  

profit = data["amount"] - cost  

add_profit(profit)  

bot.send_message(  
    user,  
    "✅ تم استلام عملاتك يرجى التأكد من محفظتك\n\n@D_4_5"  
)  

bot.send_message(  
    ADMIN_ID,  
    f"""

💰 ربح العملية: {profit:.2f}

📊 ربح اليوم: {profits['today']}

💎 اجمالي الربح: {profits['total']}
"""
)

del users_data[user]

================= رفض =================

@bot.callback_query_handler(func=lambda c:c.data.startswith("reject"))
def reject(call):

user = int(call.data.split("_")[1])  

bot.send_message(user,"❌ تم رفض الطلب")  

if user in users_data:  
    del users_data[user]

================= عرض الربح =================

@bot.message_handler(commands=['profit'])
def profit(message):

if message.chat.id == ADMIN_ID:  

    bot.send_message(  
        message.chat.id,  
        f"""

📊 ربح اليوم: {profits['today']}

💰 اجمالي الربح: {profits['total']}
"""
)

print("BOT RUNNING")

bot.infinity_polling()
