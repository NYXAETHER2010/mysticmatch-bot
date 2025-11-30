# MysticMatch - Telegram Dating Bot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import config
import database as db

REGISTRATION_STATES = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    existing_user = db.get_user(user_id)
    if existing_user:
        await update.message.reply_text(
            "🔮 Welcome back to MysticMatch!\n\n"
            "Commands:\n"
            "/swipe - Start swiping\n"
            "/matches - See your matches\n"
            "/profile - View your profile"
        )
        return
    
    REGISTRATION_STATES[user_id] = {"step": "name"}
    await update.message.reply_text(
        "🔮 Welcome to MysticMatch\n\n"
        "Where chaotic energies collide...\n\n"
        "Let's create your profile.\n"
        "What's your name?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id in REGISTRATION_STATES:
        await handle_registration(update, context)
        return
    
    if 'chat_with' in context.user_data:
        await handle_chat(update, context)
        return
    
    await update.message.reply_text(
        "Use /swipe to start swiping or /matches to see your matches!"
    )

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = REGISTRATION_STATES[user_id]
    text = update.message.text
    
    if state["step"] == "name":
        state["name"] = text
        state["step"] = "age"
        await update.message.reply_text("What's your age?")
    
    elif state["step"] == "age":
        try:
            age = int(text)
            if age < 18 or age > 100:
                await update.message.reply_text("Please enter a valid age (18-100)")
                return
            state["age"] = age
            state["step"] = "gender"
            
            keyboard = [
                [InlineKeyboardButton("Male", callback_data="gender_male")],
                [InlineKeyboardButton("Female", callback_data="gender_female")],
                [InlineKeyboardButton("Other", callback_data="gender_other")]
            ]
            await update.message.reply_text(
                "What's your gender?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("Please enter a valid number for age")
    
    elif state["step"] == "city":
        state["city"] = text
        state["step"] = "bio"
        await update.message.reply_text(
            "Write a short bio about yourself\n"
            "(Keep it under 200 characters)"
        )
    
    elif state["step"] == "bio":
        if len(text) > 200:
            await update.message.reply_text("Bio is too long! Keep it under 200 characters")
            return
        state["bio"] = text
        state["step"] = "photo"
        await update.message.reply_text("Send me a photo of yourself")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in REGISTRATION_STATES:
        await update.message.reply_text("Use /start to begin registration")
        return
    
    state = REGISTRATION_STATES[user_id]
    
    if state["step"] == "photo":
        photo = update.message.photo[-1]
        photo_file_id = photo.file_id
        
        db.create_user(
            user_id=user_id,
            username=update.effective_user.username or "anonymous",
            name=state["name"],
            age=state["age"],
            gender=state["gender"],
            city=state["city"],
            bio=state["bio"],
            photo=photo_file_id
        )
        
        db.update_user(user_id, {"interested_in": state["interested_in"]})
        del REGISTRATION_STATES[user_id]
        
        await update.message.reply_text(
            "✅ Profile created successfully!\n\n"
            "🔮 Ready to find your match?\n\n"
            "Use /swipe to start swiping!"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data.startswith("gender_"):
        gender = data.replace("gender_", "")
        REGISTRATION_STATES[user_id]["gender"] = gender
        REGISTRATION_STATES[user_id]["step"] = "interested_in"
        
        keyboard = [
            [InlineKeyboardButton("Men", callback_data="interested_men")],
            [InlineKeyboardButton("Women", callback_data="interested_women")],
            [InlineKeyboardButton("Everyone", callback_data="interested_all")]
        ]
        await query.edit_message_text(
            "Who are you interested in?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("interested_"):
        interested = data.replace("interested_", "")
        if interested == "men":
            REGISTRATION_STATES[user_id]["interested_in"] = "male"
        elif interested == "women":
            REGISTRATION_STATES[user_id]["interested_in"] = "female"
        else:
            REGISTRATION_STATES[user_id]["interested_in"] = "all"
        
        REGISTRATION_STATES[user_id]["step"] = "city"
        await query.edit_message_text("What city are you from?")
    
    elif data.startswith("like_") or data.startswith("pass_"):
        await handle_swipe(update, context, data)
    
    elif data.startswith("chat_"):
        target_id = int(data.replace("chat_", ""))
        context.user_data['chat_with'] = target_id
        
        target_user = db.get_user(target_id)
        await query.edit_message_text(
            f"💬 Now chatting with {target_user['name']}\n\n"
            "Type your message below.\n"
            "Use /endchat to stop chatting"
        )

async def swipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please use /start to create your profile first!")
        return
    
    potential_matches = db.get_potential_matches(user_id)
    
    if not potential_matches:
        await update.message.reply_text(
            "No more profiles to show right now!\n"
            "Check back later when more people join 🔮"
        )
        return
    
    await show_profile(update.effective_chat.id, context, potential_matches[0], user_id)

async def show_profile(chat_id, context, profile, viewer_id):
    keyboard = [
        [
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{profile['user_id']}"),
            InlineKeyboardButton("💔 Pass", callback_data=f"pass_{profile['user_id']}")
        ]
    ]
    
    caption = (
        f"✨ {profile['name']}, {profile['age']}\n"
        f"📍 {profile['city']}\n\n"
        f"{profile['bio']}"
    )
    
    await context.bot.send_photo(
        chat_id=chat_id,
        photo=profile['photo'],
        caption=caption,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_swipe(update: Update, context: ContextTypes.DEFAULT_TYPE, data):
    query = update.callback_query
    user_id = update.effective_user.id
    
    action, target_id = data.split("_")
    target_id = int(target_id)
    
    liked = (action == "like")
    is_match = db.add_like(user_id, target_id, liked)
    
    if is_match:
        target_user = db.get_user(target_id)
        current_user = db.get_user(user_id)
        
        await query.edit_message_text(
            f"🔥 IT'S A MATCH!\n\n"
            f"You and {target_user['name']} liked each other!\n\n"
            f"Two chaotic energies collided today..."
        )
        
        keyboard = [[InlineKeyboardButton("💬 Start Chat", callback_data=f"chat_{user_id}")]]
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🔥 IT'S A MATCH!\n\nYou and {current_user['name']} liked each other!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        keyboard = [[InlineKeyboardButton("💬 Start Chat", callback_data=f"chat_{target_id}")]]
        await context.bot.send_message(
            chat_id=user_id,
            text="Start chatting now!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text("Next profile coming up...")
    
    potential_matches = db.get_potential_matches(user_id)
    if potential_matches:
        await show_profile(query.message.chat_id, context, potential_matches[0], user_id)
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="No more profiles for now! Check back later 🔮"
        )

async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please use /start to create your profile first!")
        return
    
    matches = db.get_matches(user_id)
    
    if not matches:
        await update.message.reply_text("No matches yet! Use /swipe to find someone 🔮")
        return
    
    await update.message.reply_text(f"You have {len(matches)} match(es)!")
    
    for match in matches:
        keyboard = [[InlineKeyboardButton("💬 Chat", callback_data=f"chat_{match['user_id']}")]]
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=match['photo'],
            caption=f"✨ {match['name']}, {match['age']}\n📍 {match['city']}\n\n{match['bio']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_id = context.user_data.get('chat_with')
    
    if not target_id:
        return
    
    if not db.is_matched(user_id, target_id):
        await update.message.reply_text("You can only chat with your matches!")
        del context.user_data['chat_with']
        return
    
    message = update.message.text
    db.save_message(user_id, target_id, message)
    
    current_user = db.get_user(user_id)
    await context.bot.send_message(
        chat_id=target_id,
        text=f"💬 {current_user['name']}: {message}"
    )
    
    await update.message.reply_text("✓ Sent")

async def endchat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'chat_with' in context.user_data:
        del context.user_data['chat_with']
        await update.message.reply_text("Chat ended. Use /matches to chat with someone else!")
    else:
        await update.message.reply_text("You're not in a chat right now")

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Please use /start to create your profile first!")
        return
    
    caption = (
        f"✨ Your Profile\n\n"
        f"Name: {user['name']}\n"
        f"Age: {user['age']}\n"
        f"Gender: {user['gender']}\n"
        f"City: {user['city']}\n"
        f"Bio: {user['bio']}"
    )
    
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=user['photo'],
        caption=caption
    )

def main():
    print("🔮 Starting MysticMatch...")
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("swipe", swipe))
    app.add_handler(CommandHandler("matches", matches_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("endchat", endchat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ MysticMatch is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
