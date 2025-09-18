import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.web_app import WebApp
from telegram.ext import Application, CommandHandler, ContextTypes
import json

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user IDs for broadcasting
USERS_FILE = 'users.json'

def load_users():
    """Load user IDs from file"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return set()

def save_users(users):
    """Save user IDs to file"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(list(users), f)
    except Exception as e:
        logger.error(f"Error saving users: {e}")

# Load users on startup
users = load_users()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    
    # Add user to our list for broadcasting
    users.add(user_id)
    save_users(users)
    
    # Create inline keyboard with Watch Now button (Web App)
    keyboard = [
        [InlineKeyboardButton(
            "Watch Now", 
            web_app=WebApp(url="https://study-material-testing.vercel.app/")
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send welcome message with user's name and ID (for setup purposes)
    welcome_text = f"Hey {user.first_name}, To watch the episode please click Watch Now.\n\n🆔 Your User ID: `{user_id}`"
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin command for broadcasting"""
    user_id = update.effective_user.id
    admin_id = int(os.getenv('ADMIN_ID', '0'))  # Get admin ID from environment variable
    
    if user_id != admin_id:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Check if there's a message to broadcast
    if context.args:
        broadcast_message = ' '.join(context.args)
        await broadcast_to_users(update, context, broadcast_message)
    else:
        await update.message.reply_text(
            "📢 Admin Panel\n\n"
            "To broadcast a message, use:\n"
            "/admin Your message here\n\n"
            f"Total users: {len(users)}"
        )

async def broadcast_to_users(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    """Broadcast message to all users"""
    successful_sends = 0
    failed_sends = 0
    
    # Send initial status message
    status_message = await update.message.reply_text("📤 Broadcasting message...")
    
    for user_id in users.copy():  # Use copy to avoid modification during iteration
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            successful_sends += 1
        except Exception as e:
            failed_sends += 1
            logger.warning(f"Failed to send message to user {user_id}: {e}")
            # Remove inactive users
            if "bot was blocked" in str(e).lower() or "user not found" in str(e).lower():
                users.discard(user_id)
    
    # Save updated user list
    save_users(users)
    
    # Update status message with results
    result_text = (
        f"✅ Broadcast completed!\n\n"
        f"📊 Results:\n"
        f"• Successful: {successful_sends}\n"
        f"• Failed: {failed_sends}\n"
        f"• Active users: {len(users)}"
    )
    
    await status_message.edit_text(result_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")

def main() -> None:
    """Start the bot."""
    # Get bot token from environment variable
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN environment variable is not set!")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_error_handler(error_handler)
    
    # Get port from environment variable (for Render)
    port = int(os.environ.get('PORT', 8443))
    
    # Run the bot using webhooks (required for Render)
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=f"https://sm-testing-bot-v2.onrender.com/{token}"  # Replace with your actual Render URL
    )

if __name__ == '__main__':
    main()
