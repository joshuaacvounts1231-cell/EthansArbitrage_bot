import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
# Set these as Environment Variables on Railway (do NOT hardcode them here)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/+PMZT4DC4fTowZjk0")
CHANNEL_BUTTON_TEXT = os.environ.get("CHANNEL_BUTTON_TEXT", "📈 Join the Channel")

# Direct URL to the welcome image
WELCOME_IMAGE_URL = os.environ.get(
    "WELCOME_IMAGE_URL",
    "https://i.ibb.co/MxwP07dB/private-jet-640x360.png"
)

WELCOME_MESSAGE = (
    "🚀 *Welcome to the Crypto Arbitrage Community*\n\n"
    "We track the crypto market every day to identify price differences, "
    "arbitrage opportunities and interesting market movements across multiple "
    "platforms.\n\n"
    "Inside the private channel you'll get:\n\n"
    "⚡️ Real-time arbitrage analyses\n"
    "📊 Market opportunities & price gaps\n"
    "🔎 Clear explanations and actionable insights\n"
    "🌍 Updates throughout the day\n"
    "🎁 100% FREE ACCESS\n\n"
    "No courses. No subscription. No unnecessary hype.\n"
    "Just crypto enthusiasts sharing opportunities and market analysis.\n\n"
    "Ready to see the latest opportunities?\n\n"
    "👇 Join the private channel now"
)

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the welcome photo + caption with a button linking to the channel."""
    keyboard = [
        [InlineKeyboardButton(CHANNEL_BUTTON_TEXT, url=CHANNEL_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=WELCOME_MESSAGE,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Failed to send photo from URL: {e}, sending text only.")
        await update.message.reply_text(
            WELCOME_MESSAGE,
            parse_mode="Markdown",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any other message the same way as /start (optional, keeps it simple)."""
    await start(update, context)


# ---------------- MAIN ----------------
def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. "
            "Add it in Railway under Variables."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    logger.info("Bot is starting with polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
