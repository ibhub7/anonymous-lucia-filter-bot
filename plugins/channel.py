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

# Expanded OTT Platform Dictionary
OTT_PLATFORMS = {
    "nf": "Netflix", "netflix": "Netflix",
    "sonyliv": "SonyLiv", "sony": "SonyLiv", "sliv": "SonyLiv",
    "amzn": "Amazon Prime Video", "prime": "Amazon Prime Video", "primevideo": "Amazon Prime Video",
    "hotstar": "Disney+ Hotstar", "hstr": "Disney+ Hotstar", "disney": "Disney+ Hotstar",
    "zee5": "Zee5", "zee": "Zee5",
    "jio": "JioHotstar", "jhs": "JioHotstar",
    "aha": "Aha", "hbo": "HBO Max", "max": "HBO Max", "paramount": "Paramount+",
    "apple": "Apple TV+", "atv": "Apple TV+", "hoichoi": "Hoichoi", "sunnxt": "Sun NXT", 
    "viki": "Viki", "mubi": "Mubi", "lionsgate": "Lionsgate Play", "lgp": "Lionsgate Play",
    "crunchyroll": "Crunchyroll", "cr": "Crunchyroll", "alt": "ALTBalaji", "cl": "Colors Lite"
}
#<b>🎥Qᴜᴀʟɪᴛʏ</b>: <b>{}</b>

INFINITY_UPLOAD_UPDATE_TEXT = """
<blockquote>🎬<b>「ɪɴꜰɪɴɪᴛʏ ᴘʀᴇᴍɪᴜᴍ ᴜᴘʟᴏᴀᴅ ᴜᴘᴅᴀᴛᴇ」</b>🎥</blockquote>

<b><u>{}</u></b> <b>#{}</b>

━━━━━━━━━━━━━━━━━━
<b>🔈 ᴀᴜᴅɪᴏ</b>: <b>{}</b>
<b>📺 ꜰᴏʀᴍᴀᴛ</b>: <b>{}</b>

━━━━━━━━━━━━━━━━━━
<b>📅 ʀᴇʟᴇᴀsᴇ</b>: <b>{}</b>
<b>⭐ ɪᴍᴅʙ</b>: {}/10 (<code>{}</code> votes)
<b>🏷️ ɢᴇɴʀᴇs</b>: <b>{}</b>
<b>🎭 ᴏᴛᴛ</b>: <b>{}</b>
━━━━━━━━━━━━━━━━━━

<b>⚡ ᴘᴏᴡᴇʀᴇᴅ ʙʏ <a href="https://t.me/+uyDUtZ8bmAVkZjM8">ɪɴꜰɪɴɪᴛʏ ᴍᴏᴠɪᴇ ᴊᴜɴᴄᴛɪᴏɴ</a></b>
"""
notified_movies = set()
media_filter = filters.document | filters.video | filters.audio

def extract_ott_platform(text: str) -> str:
    if not text:
        return "N/A"
    text = text.lower()
    # Find all matching platforms based on keys
    platforms = {plat for key, plat in OTT_PLATFORMS.items() if key in text}
    return " | ".join(platforms) if platforms else "N/A"

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
        ott = extract_ott_platform(f"{file_name} {caption}")

        year_match = re.search(r"\b(19|20)\d{2}\b", caption)
        year = year_match.group(0) if year_match else None      
        season_match = re.search(r"(?i)(?:s|season)0*(\d{1,2})", caption) or re.search(r"(?i)(?:s|season)0*(\d{1,2})", file_name)
        if year:
            file_name = file_name[:file_name.find(year) + 4]
        elif season_match:
            season = season_match.group(1)
            file_name = file_name[:file_name.find(season) + 1]
        quality = await get_qualities(caption) or "HDRip"
        pixel = await get_pixels(caption) or "720p"
        language = await get_languages(caption) or "Multi-Audio"
        if file_name in notified_movies:
            return 
        notified_movies.add(file_name)
        tmdb_data = await fetch_tmdb_data(file_name, year)
        search_movie = file_name.replace(" ", "-")
        if not tmdb_data:
            return 

        release_date = tmdb_data.get("release_date")
        release_year = release_date[:4] if release_date else (year or "N/A")
        full_caption = INFINITY_UPLOAD_UPDATE_TEXT.format(
            escape_html(tmdb_data["title"]),  # 1. Title
            tmdb_data["kind"],                # 2. Kind
            escape_html(language),            # 3. Audio
            escape_html(pixel),               # 4. Format (Resolution)
            escape_html(release_date),        # 5. Release
            tmdb_data["vote_average"],        # 6. Rating
            tmdb_data["vote_count"],          # 7. Votes
            escape_html(", ".join(tmdb_data["genres"][:3])),  # 8. Genres
            escape_html(ott)                  # 9. OTT
        )
       
        await send_with_visual(bot, full_caption, tmdb_data, search_movie)        
    except Exception as e:
        LOGGER.error(f"Error In Movie Update: {e}")

def escape_html(text: str) -> str:
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

#def get_trailer_button(tmdb_data: Dict) -> list:
#    videos = tmdb_data.get("videos", [])
#    yt_videos = [v for v in videos if "youtube" in v.get("url", "").lower()]    
#    if yt_videos:
#        return [InlineKeyboardButton("▶️ Watch Trailer", url=yt_videos[0]["url"])]
#    return []
    
async def send_with_visual(bot, caption: str, tmdb_data: Dict, search_movie):
    try:
        visual_url = await get_best_visual(tmdb_data)
        get_file = f'https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏷️  ɢᴇᴛ ᴀʟʟ ꜰɪʟᴇꜱ  🏷️", url=get_file)],
            #get_trailer_button(tmdb_data)
        ])
        
        if visual_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(visual_url, timeout=aiohttp.ClientTimeout(total=20)) as img_resp:
                    if img_resp.status == 200:
                        img_bytes = await img_resp.read()
                        photo_file = io.BytesIO(img_bytes)
                        photo_file.name = await generate_premium_filename(tmdb_data["title"])
                        
                        await bot.send_photo(
                            chat_id=MOVIE_UPDATE_CHANNEL, 
                            photo=photo_file, 
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=keyboard,
                            has_spoiler=True
                        )
                        return       
        # Fallback if no visual_url or download fails
        await bot.send_photo(
            chat_id=MOVIE_UPDATE_CHANNEL, 
            photo=DEFAULT_IMAGE_URL, 
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            has_spoiler=True
        )       
    except Exception as e:
        LOGGER.error(f"Visual Send Error: {e}")

async def generate_premium_filename(title: str, extension=".jpg") -> str:
    clean_title = re.sub(r'[^\w\s-]', '', title)[:20].strip()
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    unique_id = hashlib.md5(title.encode()).hexdigest()[:6]
    return f"silentx_{clean_title}_{timestamp}_{unique_id}{extension}"

async def get_languages(text: str) -> str:
    found_langs = [lang for lang in CAPTION_LANGUAGES if lang.lower().replace(" ", "") in text.lower().replace(" ", "")]
    return ", ".join(found_langs[:2]) if found_langs else "Multi-Audio"

async def get_qualities(text): 
    qualities = ["ORG", "org", "hdcam", "HDCAM", "HQ", "hq", "HDRip", "hdrip", "camrip", "WEB-DL", "CAMRip", "hdtc", "predvd", "DVDscr", "dvdscr", "dvdrip", "HDTC", "dvdscreen", "HDTS", "hdts"]
    return ", ".join([q for q in qualities if q.lower() in text.lower()])

async def get_pixels(caption):
    pixels = ["480p", "480p HEVC", "720p", "720p HEVC", "1080p", "1080p HEVC", "2160p", "2K", "4K"]
    return ", ".join([p for p in pixels if p.lower() in caption.lower()])