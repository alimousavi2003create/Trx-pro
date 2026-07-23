"""TRX PRO - Extra Reaction Bots (react to every group message with random emoji)"""
import asyncio
import logging
import random
import os
import threading

from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

REACTION_BOT_TOKENS_ENV = "REACTION_BOT_TOKENS"

REACTION_EMOJIS = [
    "\U0001F44D", "\u2764", "\U0001F525", "\U0001F970", "\U0001F44F",
    "\U0001F389", "\U0001F60D", "\U0001F929", "\U0001F3C6", "\U0001F4AF",
    "\u26A1", "\U0001F60E", "\U0001F973", "\U0001F440", "\U0001F64F",
    "\U0001F44C", "\U0001F31A", "\U0001F923", "\U0001F914", "\U0001F62D",
]


def get_reaction_bot_tokens():
    raw = os.environ.get(REACTION_BOT_TOKENS_ENV, "")
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    return tokens


async def make_reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    try:
        emoji = random.choice(REACTION_EMOJIS)
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction=[ReactionTypeEmoji(emoji)]
        )
    except TelegramError as e:
        logger.error(f"reaction bot error: {e}")


async def run_single_reaction_bot(token):
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, make_reaction_handler))
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info(f"Reaction bot started: ...{token[-6:]}")
    return app


async def run_all_reaction_bots():
    tokens = get_reaction_bot_tokens()
    if not tokens:
        logger.info("No reaction bot tokens configured, skipping.")
        return
    apps = []
    for token in tokens:
        try:
            app = await run_single_reaction_bot(token)
            apps.append(app)
        except Exception as e:
            logger.error(f"Failed to start reaction bot ...{token[-6:]}: {e}")
    logger.info(f"{len(apps)} reaction bots running.")
    await asyncio.Event().wait()


def start_reaction_bots_thread():
    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_all_reaction_bots())

    t = threading.Thread(target=runner, daemon=True)
    t.start()
