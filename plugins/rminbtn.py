from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardRemove
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@Client.on_message(filters.command("remove"))
async def remove_keyboard(client, message: Message):
    try:
        # Send reply and remove keyboard
        reply = await message.reply_text(
            "✅ Keyboard removed.",
            reply_markup=ReplyKeyboardRemove()
        )
        await asyncio.sleep(120)

        # Try deleting both messages
        await reply.delete()
        await message.delete()

    except Exception as e:
        logger.warning(f"⚠️ Error deleting messages: {e}")