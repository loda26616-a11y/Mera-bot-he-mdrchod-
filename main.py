import json
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL")

DATA_FILE = "data.json"


def load_data():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {"users":{}, "qr":None}


def save_data(data):
    with open(DATA_FILE,"w") as f:
        json.dump(data,f)


data = load_data()


async def check_force(update,context):
    user = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(FORCE_CHANNEL,user)
        if member.status in ["member","administrator","creator"]:
            return True
    except:
        pass
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    user_id = user.id

    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"expiry":0}
        save_data(data)

    if not await check_force(update,context):

        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("✅ Joined", callback_data="checkjoin")]
        ]

        await update.message.reply_text(
            "⚠️ Bot use karne ke liye channel join karo",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return


    keyboard = [
        [InlineKeyboardButton("💎 Buy Premium", callback_data="buy")],
        [InlineKeyboardButton("🛠 Support", url="https://t.me/nyrahelpcentre")]
    ]

    text = (
f"👋 Welcome {user.first_name}\n\n"
"🔥 NYRA PREMIUM MEMBERSHIP\n\n"
"💎 Exclusive Premium Access\n"
"⚡ Fast & Secure Service\n"
"📞 24x7 Support\n\n"
"━━━━━━━━━━━━━━━\n"
"💰 Premium Plans\n"
"15 Days — ₹99\n"
"45 Days — ₹299\n"
"Lifetime — ₹699\n"
"━━━━━━━━━━━━━━━\n\n"
"👇 Buy premium below"
)

    await update.message.reply_text(text,reply_markup=InlineKeyboardMarkup(keyboard))


async def buy(update,context):

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("15 Days ₹99", callback_data="plan_15")],
        [InlineKeyboardButton("45 Days ₹299", callback_data="plan_45")],
        [InlineKeyboardButton("Lifetime ₹699", callback_data="plan_life")]
    ]

    await query.edit_message_text(
        "💎 Select Premium Plan",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def plan(update,context):

    query = update.callback_query
    await query.answer()

    context.user_data["plan"] = query.data

    if data["qr"]:

        await query.message.reply_photo(
            data["qr"],
            caption="💳 Scan QR and pay\n\nThen send payment screenshot."
        )

    else:
        await query.message.reply_text("⚠️ Payment QR not set yet.")


async def screenshot(update,context):

    if "plan" not in context.user_data:
        return

    user = update.effective_user

    keyboard = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{context.user_data['plan']}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}")
    ]]

    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"💰 Payment Request\n\nUser: {user.first_name}\nID: {user.id}\nPlan: {context.user_data['plan']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("✅ Screenshot sent for verification")


async def decision(update,context):

    query = update.callback_query
    await query.answer()

    data_cb = query.data.split("_")

    action = data_cb[0]
    user_id = data_cb[1]

    if action == "approve":

        plan = data_cb[2]

        if plan == "plan_15":
            expiry = int(time.time()) + 15*86400
        elif plan == "plan_45":
            expiry = int(time.time()) + 45*86400
        else:
            expiry = 9999999999

        data["users"][str(user_id)]["expiry"] = expiry
        save_data(data)

        await context.bot.send_message(user_id,"✅ Payment Approved\nPremium Activated")

        await query.edit_message_caption("✅ Approved")

    else:

        await context.bot.send_message(user_id,"❌ Payment Rejected\nContact support")

        await query.edit_message_caption("❌ Rejected")


async def admin(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🖼 Change QR", callback_data="qr")]
    ]

    await update.message.reply_text(
        "⚙️ Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_buttons(update,context):

    query = update.callback_query
    await query.answer()

    if query.data == "stats":

        total = len(data["users"])

        await query.message.reply_text(f"👥 Total Users: {total}")

    elif query.data == "qr":

        context.user_data["setqr"] = True
        await query.message.reply_text("Send new QR image")

    elif query.data == "broadcast":

        context.user_data["broadcast"] = True
        await query.message.reply_text("Send message to broadcast")


async def setqr(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("setqr"):

        data["qr"] = update.message.photo[-1].file_id
        save_data(data)

        context.user_data["setqr"] = False

        await update.message.reply_text("✅ QR Updated")


async def broadcast(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("broadcast"):

        for user in data["users"]:
            try:
                await update.message.copy(chat_id=int(user))
            except:
                pass

        context.user_data["broadcast"] = False

        await update.message.reply_text("✅ Broadcast Sent")


def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(buy,pattern="buy"))
    app.add_handler(CallbackQueryHandler(plan,pattern="plan_"))
    app.add_handler(CallbackQueryHandler(decision,pattern="approve_|reject_"))
    app.add_handler(CallbackQueryHandler(admin_buttons,pattern="stats|broadcast|qr"))

    app.add_handler(MessageHandler(filters.PHOTO, screenshot))
    app.add_handler(MessageHandler(filters.PHOTO, setqr))
    app.add_handler(MessageHandler(filters.ALL, broadcast))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
