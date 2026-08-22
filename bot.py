import html
import json
import logging
import os
from datetime import time as dtime
from pathlib import Path

import feedparser
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATA_FILE = Path(__file__).parent / "user_data.json"
DEFAULT_CATEGORY = "world"
DEFAULT_COUNT = 5

# Google News RSS topic IDs (no API key needed)
CATEGORIES = {
    "world": "WORLD",
    "business": "BUSINESS",
    "tech": "TECHNOLOGY",
    "sports": "SPORTS",
    "science": "SCIENCE",
    "health": "HEALTH",
    "entertainment": "ENTERTAINMENT",
}

TOPIC_FEED_URL = "https://news.google.com/rss/headlines/section/topic/{topic}?hl=en-US&gl=US&ceid=US:en"
SEARCH_FEED_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


# ---------------------------------------------------------------------------
# Simple JSON-backed storage: { user_id: {"category": "tech", "subscribe_time": "08:00", "chat_id": 123} }
# NOTE: Railway's filesystem is ephemeral across redeploys/restarts. For
# preferences/subscriptions to survive redeploys, add a Railway Volume or
# swap this for a small database.
# ---------------------------------------------------------------------------
def _load_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2))


def get_user(user_id: int) -> dict:
    return _load_data().get(str(user_id), {})


def update_user(user_id: int, **fields) -> None:
    data = _load_data()
    user = data.get(str(user_id), {})
    user.update(fields)
    data[str(user_id)] = user
    _save_data(data)


def remove_user_field(user_id: int, field: str) -> None:
    data = _load_data()
    user = data.get(str(user_id))
    if user and field in user:
        del user[field]
        _save_data(data)


# ---------------------------------------------------------------------------
# News fetching / formatting
# ---------------------------------------------------------------------------
def fetch_headlines(category: str = None, query: str = None, count: int = DEFAULT_COUNT):
    if query:
        url = SEARCH_FEED_URL.format(query=query.replace(" ", "+"))
    else:
        topic = CATEGORIES.get(category, CATEGORIES[DEFAULT_CATEGORY])
        url = TOPIC_FEED_URL.format(topic=topic)

    feed = feedparser.parse(url)
    entries = feed.entries[:count]

    items = []
    for e in entries:
        title = e.title
        source = getattr(getattr(e, "source", None), "title", None)
        # Google News titles are usually "Headline - Source"; strip duplicate source if present
        if source and title.endswith(f" - {source}"):
            title = title[: -(len(source) + 3)]
        link = e.link
        items.append({"title": title, "source": source or "Unknown", "link": link})
    return items


def format_digest(items: list, header: str) -> str:
    if not items:
        return f"📰 <b>{html.escape(header)}</b>\n\nNo headlines found right now — try again shortly."

    lines = [f"📰 <b>{html.escape(header)}</b>\n"]
    for i, item in enumerate(items, 1):
        title = html.escape(item["title"])
        source = html.escape(item["source"])
        lines.append(f'{i}. <a href="{item["link"]}">{title}</a>\n   <i>{source}</i>')
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📰 <b>News Digest Bot</b>\n\n"
        "Get headlines on demand, or subscribe to a daily digest.\n\n"
        "<b>Commands</b>\n"
        "/digest — get headlines now (your default category)\n"
        "/category &lt;name&gt; — set your default category\n"
        "/mycategory — show your current category\n"
        "/search &lt;keywords&gt; — search news by keyword\n"
        "/subscribe &lt;HH:MM&gt; — get a daily digest at this UTC time\n"
        "/unsubscribe — stop the daily digest\n"
        "/categories — list available categories\n"
        "/help — show this message",
        parse_mode=ParseMode.HTML,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def list_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    names = ", ".join(f"<code>{c}</code>" for c in CATEGORIES)
    await update.message.reply_text(
        f"Available categories:\n{names}", parse_mode=ParseMode.HTML
    )


async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /category <name>\nSee /categories for options.")
        return

    cat = context.args[0].lower()
    if cat not in CATEGORIES:
        await update.message.reply_text(f"⚠️ Unknown category '{cat}'. See /categories.")
        return

    update_user(update.effective_user.id, category=cat)
    await update.message.reply_text(f"✅ Default category set to {cat}.")


async def my_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cat = get_user(update.effective_user.id).get("category", DEFAULT_CATEGORY)
    await update.message.reply_text(f"Your default category is: {cat}")


async def digest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cat = get_user(update.effective_user.id).get("category", DEFAULT_CATEGORY)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    items = fetch_headlines(category=cat)
    text = format_digest(items, header=f"Top {cat.title()} Headlines")
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /search <keywords>\nExample: /search elections in Nigeria")
        return

    query = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    items = fetch_headlines(query=query)
    text = format_digest(items, header=f'Results for "{query}"')
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def send_scheduled_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback run by the JobQueue for a subscribed user."""
    job = context.job
    user_id = job.data["user_id"]
    chat_id = job.data["chat_id"]
    cat = get_user(user_id).get("category", DEFAULT_CATEGORY)

    items = fetch_headlines(category=cat)
    text = format_digest(items, header=f"Your Daily {cat.title()} Digest")
    await context.bot.send_message(
        chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


def schedule_user_job(app: Application, user_id: int, chat_id: int, hh: int, mm: int) -> None:
    job_name = f"digest_{user_id}"
    for job in app.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()
    app.job_queue.run_daily(
        send_scheduled_digest,
        time=dtime(hour=hh, minute=mm),
        name=job_name,
        data={"user_id": user_id, "chat_id": chat_id},
    )


async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <HH:MM>\nExample: /subscribe 08:00 (UTC time)")
        return

    try:
        hh, mm = map(int, context.args[0].split(":"))
        assert 0 <= hh <= 23 and 0 <= mm <= 59
    except (ValueError, AssertionError):
        await update.message.reply_text("⚠️ Please use HH:MM 24-hour format, e.g. /subscribe 08:00")
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    update_user(user_id, subscribe_time=f"{hh:02d}:{mm:02d}", chat_id=chat_id)
    schedule_user_job(context.application, user_id, chat_id, hh, mm)

    await update.message.reply_text(
        f"✅ Subscribed! You'll get a daily digest at {hh:02d}:{mm:02d} UTC.\n"
        f"Use /category to change what it covers, /unsubscribe to stop."
    )


async def unsubscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    job_name = f"digest_{user_id}"
    jobs = context.application.job_queue.get_jobs_by_name(job_name)
    if not jobs:
        await update.message.reply_text("You're not currently subscribed.")
        return

    for job in jobs:
        job.schedule_removal()
    remove_user_field(user_id, "subscribe_time")
    await update.message.reply_text("✅ Unsubscribed from the daily digest.")


async def restore_jobs(app: Application) -> None:
    """On startup, re-create scheduled jobs for anyone previously subscribed."""
    data = _load_data()
    for uid_str, user in data.items():
        sub_time = user.get("subscribe_time")
        chat_id = user.get("chat_id")
        if sub_time and chat_id:
            hh, mm = map(int, sub_time.split(":"))
            schedule_user_job(app, int(uid_str), chat_id, hh, mm)
            logger.info(f"Restored subscription for user {uid_str} at {sub_time}")


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Not sure what you mean — try /digest, /search <keywords>, or /help."
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(BOT_TOKEN).post_init(restore_jobs).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("categories", list_categories))
    app.add_handler(CommandHandler("category", set_category))
    app.add_handler(CommandHandler("mycategory", my_category))
    app.add_handler(CommandHandler("digest", digest_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe_cmd))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

    logger.info("Bot starting (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
