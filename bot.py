import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
# Set these as Environment Variables on Railway (do NOT hardcode them here)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/+PMZT4DC4fTowZjk0")
CHANNEL_BUTTON_TEXT = os.environ.get("CHANNEL_BUTTON_TEXT", "📈 Join the Channel")

WELCOME_MESSAGE = (
    "📊 *Daily Forex Analysis & Trading Insights*\n\n"
    "Stay updated with the latest Forex market movements, technical analysis, "
    "important price levels, and potential trading setups. Our channel provides "
    "regular market insights covering major currency pairs, market trends, and "
    "key opportunities to help traders make more informed decisions.\n\n"
    "Whether you're an experienced trader or looking to understand the Forex "
    "market better, join us for consistent analysis and useful trading information.\n\n"
    "👇 Make money while sleeping 😴"
)

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the welcome message with a button linking to the channel."""
    keyboard = [
        [InlineKeyboardButton(CHANNEL_BUTTON_TEXT, url=CHANNEL_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

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
