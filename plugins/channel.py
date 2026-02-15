import re
import io
import math
import random
import string
import aiohttp
import asyncio
import hashlib
import requests
from info import *
from utils import *
from utils import clean_filename
from logging_helper import LOGGER
from typing import Optional, Dict, Any
from datetime import datetime
from pyrogram import Client, filters
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

CAPTION_LANGUAGES = ["Bhojpuri", "Hindi", "Bengali", "Tamil", "English", "Bangla", "Telugu", "Malayalam", "Kannada", "Marathi", "Punjabi", "Bengoli", "Gujrati", "Korean", "Gujarati", "Spanish", "French", "German", "Chinese", "Arabic", "Portuguese", "Russian", "Japanese", "Odia", "Assamese", "Urdu"]

DEFAULT_IMAGE_URL = "https://te.legra.ph/file/88d845b4f8a024a71465d.jpg"

# --- FORMAT 1 (Small Caps Labels) ---
INFINITY_UPLOAD_UPDATE_TEXT = """
<blockquote>🎬 <b>「 ɪɴꜰɪɴɪᴛʏ ᴘʀᴇᴍɪᴜᴍ ᴜᴘᴅᴀᴛᴇ 」</b> 🎥</blockquote>

<b><u>{}</u></b> <b>#{}</b>

━━━━━━━━━━━━━━━━━━
<b>🔈 ᴀᴜᴅɪᴏ</b>: {}
<b>📺 ꜰᴏʀᴍᴀᴛ</b>: {}

━━━━━━━━━━━━━━━━━━
<b>🎭 ᴅɪʀᴇᴄᴛᴏʀ</b>: {}
<b>📅 ʀᴇʟᴇᴀsᴇ</b>: {}
<b>⭐ ɪᴍᴅʙ</b>: {}/10 (<code>{}</code> votes)
<b>🏷️ ɢᴇɴʀᴇs</b>: {}
━━━━━━━━━━━━━━━━━━

<b>⚡ ᴘᴏᴡᴇʀᴇᴅ ʙʏ <a href="https://t.me/+VdxxoOzGyzU1MzE0">ɪᴍᴊ</a></b>
"""

# --- FORMAT 2 (With Genres & OTT at Top) ---
INFINITY_UPLOAD_UPDATE_V2 = """
<blockquote>🎬 <b>「 ɪɴꜰɪɴɪᴛʏ ᴘʀᴇᴍɪᴜᴍ ᴜᴘᴅᴀᴛᴇ 」</b> 🎥</blockquote>

<b><u>{}</u></b> <b>#{}</b>

<b>🎭 ɢᴇɴʀᴇs : {}</b>
<b>📺 ᴏᴛᴛ : {}</b>

━━━━━━━━━━━━━━━━━━
<b>📽️ ꜰᴏʀᴍᴀᴛ : {}</b>
<b>🔊 ᴀᴜᴅɪᴏ : {}</b>
<b>⭐ ɪᴍᴅʙ ʀᴀᴛɪɴɢ : {}/10</b>
━━━━━━━━━━━━━━━━━━

<b>⚡ ᴘᴏᴡᴇʀᴇᴅ ʙʏ <a href="https://t.me/+VdxxoOzGyzU1MzE0">ɪᴍᴊ</a></b>
"""

notified_movies = set()
media_filter = filters.document | filters.video | filters.audio

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return
    media.file_type = file_type
    media.caption = message.caption
    success, silentxbotz = await save_file(media)
    try:  
        if success and silentxbotz == 1 and await get_status(bot.me.id):            
            await send_movie_update(bot, file_name=media.file_name, caption=media.caption)
    except Exception as e:
        LOGGER.error(f"Error In Movie Update - {e}")
        pass

async def send_movie_update(bot, file_name, caption):
    try:
        file_name = clean_filename(file_name)
        caption = clean_filename(caption)
        year_match = re.search(r"\b(19|20)\d{2}\b", caption)
        year = year_match.group(0) if year_match else "ɴ/ᴀ"      
        
        quality = await get_qualities(caption) or "ʜᴅʀɪᴘ"
        language = await get_languages(caption) or "ᴍᴜʟᴛɪ-ᴀᴜᴅɪᴏ"      
        ott_platform = await extract_ott_platform(f"{file_name} {caption}")

        if file_name in notified_movies:
            return 
        notified_movies.add(file_name)      
        
        tmdb_data = await fetch_tmdb_data(file_name, year)
        search_movie = file_name.replace(" ", "-")
        if not tmdb_data:
            return 

        director = tmdb_data.get("director", "ɴ/ᴀ")
        genres = ", ".join(tmdb_data.get("genres", [])[:3]) or "ɴ/ᴀ"
        rating = tmdb_data.get("vote_average", "ɴ/ᴀ")
        votes = tmdb_data.get("vote_count", "0")
        release = tmdb_data.get("release_date", "ᴛʙᴀ")
        title = tmdb_data.get("title", file_name)

        # --- RANDOMIZER LOGIC ---
        choice = random.choice([1, 2])
        
        if choice == 1:
            full_caption = INFINITY_UPLOAD_UPDATE_TEXT.format(
                escape_html(title), year, escape_html(language), quality,
                escape_html(director), escape_html(release), rating, votes, escape_html(genres)
            )
        else:
            full_caption = INFINITY_UPLOAD_UPDATE_V2.format(
                escape_html(title), year, escape_html(genres), ott_platform,
                quality, escape_html(language), rating
            )
            
        await send_with_visual(bot, full_caption, tmdb_data, search_movie)         
    except Exception as e:
        LOGGER.error(f"Error In Movie Update: {e}")

async def extract_ott_platform(text: str) -> str:
    # OTT Logic integrated from previous request
    OTT_PLATFORMS = {
        "nf": "ɴᴇᴛꜰʟɪx", "netflix": "ɴᴇᴛꜰʟɪx",
        "sonyliv": "sᴏɴʏʟɪᴠ", "sony": "sᴏɴʏʟɪᴠ", "sliv": "sᴏɴʏʟɪᴠ",
        "amzn": "ᴀᴍᴀᴢᴏɴ ᴘʀɪᴍᴇ", "prime": "ᴀᴍᴀᴢᴏɴ ᴘʀɪᴍᴇ",
        "hotstar": "ᴅɪsɴᴇʏ+ ʜᴏᴛsᴛᴀʀ", "zee5": "ᴢᴇᴇ5",
        "jio": "ᴊɪᴏʜᴏᴛsᴛᴀʀ", "aha": "ᴀʜᴀ", "hbo": "ʜʙᴏ ᴍᴀx"
    }
    text = text.lower()
    platforms = [plat for key, plat in OTT_PLATFORMS.items() if key in text]
    return " | ".join(platforms) if platforms else "ɴ/ᴀ"

def escape_html(text: str) -> str:
    if not text: return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def get_trailer_button(tmdb_data: Dict) -> list:
    videos = tmdb_data.get("videos", [])
    yt_videos = [v for v in videos if "youtube" in v.get("url", "").lower()]    
    if yt_videos:
        return [InlineKeyboardButton("▶️ ᴡᴀᴛᴄʜ ᴛʀᴀɪʟᴇʀ", url=yt_videos[0]["url"])]
    return []
    
async def send_with_visual(bot, caption: str, tmdb_data: Dict, search_movie):
    try:
        visual_url = await get_best_visual(tmdb_data)
        get_file = f'https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 ɢᴇᴛ ꜰɪʟᴇ", url=get_file)],
            get_trailer_button(tmdb_data)
        ])
        
        target_url = visual_url or DEFAULT_IMAGE_URL
        async with aiohttp.ClientSession() as session:
            async with session.get(target_url, timeout=20) as img_resp:
                if img_resp.status == 200:
                    img_bytes = await img_resp.read()
                    photo_file = io.BytesIO(img_bytes)
                    photo_file.name = await generate_premium_filename(tmdb_data.get("title", "movie"))
                    
                    await bot.send_photo(
                        chat_id=MOVIE_UPDATE_CHANNEL, 
                        photo=photo_file, 
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard,
                        has_spoiler=True # Added tap-to-reveal blur
                    )
                    return       
    except Exception as e:
        LOGGER.error(f"Visual Send Error: {e}")

async def generate_premium_filename(title: str, extension=".jpg") -> str:
    clean_title = re.sub(r'[^\w\s-]', '', title)[:20].strip()
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    unique_id = hashlib.md5(title.encode()).hexdigest()[:6]
    return f"silentx_{clean_title}_{timestamp}_{unique_id}{extension}"

async def get_languages(text: str) -> str:
    found_langs = [lang for lang in CAPTION_LANGUAGES if lang.lower().replace(" ", "") in text.lower().replace(" ", "")]
    mapping = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ")
    return ", ".join(found_langs[:2]).translate(mapping) if found_langs else "ᴍᴜʟᴛɪ-ᴀᴜᴅɪᴏ"

async def get_qualities(text): 
    qualities = ["ORG", "HDCAM", "HDRip", "WEB-DL", "BluRay"]
    found = [q for q in qualities if q.lower() in text.lower()]
    mapping = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ")
    return ", ".join(found).translate(mapping) if found else "ʜᴅʀɪᴘ"

async def get_pixels(caption):
    pixels = ["360p", "480p", "720p", "1080p", "2160p", "4K"]
    found = [p for p in pixels if p.lower() in caption.lower()]
    return ", ".join(found) if found else "720ᴘ"