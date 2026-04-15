import os
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from yt_dlp import YoutubeDL
from shazamio import Shazam

# --- KONFIGURATSIYA ---
TOKEN = "8673913427:AAEKG283CJzFZxkVad53sLlyzrBnvpN9pxQ" 
ADMIN_ID = 7089893378 # O'zingizning ID raqamingiz
CHANNELS = ["@eduflow_news"] # Obuna uchun (ixtiyoriy)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('users.db')
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, join_date TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    conn.cursor().execute("INSERT OR IGNORE INTO users VALUES (?, ?)", 
                         (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# --- YUKLASH VA QIDIRUV LOGIKASI ---
async def search_songs(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch10', # 10 ta natija qidiradi
        'noplaylist': True,
        'quiet': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, query, download=False)
        return info['entries']

# --- START KOMANDASI (Chiroyli Salomlashish) ---
@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)
    welcome_text = (
        f"🌟 **Assalomu alaykum, {message.from_user.first_name}!**\n\n"
        "Siz eng universal musiqa va video yuklovchi botga kirdingiz.\n\n"
        "✨ **Nimalar qila olaman?**\n"
        "🔍 **Musiqa qidirish:** Shunchaki nomi yoki ijrochisini yozing.\n"
        "🎼 **Musiqa topish:** Ovozli xabar yuborsangiz, darrov taniyman.\n"
        "📹 **Video yuklash:** Instagram/YouTube linkini yuboring.\n\n"
        "🚀 *Marhamat, boshlaymiz!*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# --- MATNLI QIDIRUV (10 ta natija) ---
@dp.message(F.text & ~F.text.startswith("/") & ~F.text.contains("http"))
async def music_search(message: types.Message):
    wait = await message.answer("🔍 **Siz uchun eng yaxshi variantlarni qidiryapman...**")
    try:
        results = await search_songs(message.text)
        if not results:
            await wait.edit_text("😔 Afsuski, hech narsa topilmadi.")
            return

        keyboard = []
        text = "🎵 **Topilgan natijalar:**\n\n"
        
        for i, entry in enumerate(results, 1):
            title = entry.get('title')[:40] # Tugmaga sig'ishi uchun qisqartiramiz
            url = entry.get('webpage_url')
            text += f"{i}. 🎹 {title}\n"
            keyboard.append([InlineKeyboardButton(text=f"{i} - yuklash 📥", callback_data=f"dl_{entry['id']}")])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await wait.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        await wait.edit_text("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

# --- TUGMA BOSILGANDA YUKLASH ---
@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(call: CallbackQuery):
    video_id = call.data.replace("dl_", "")
    url = f"https://www.youtube.com/watch?v={video_id}"
    await call.message.edit_text("⚡️ **Yuklanmoqda...**")
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            path = ydl.prepare_filename(info)
            
            audio = FSInputFile(path)
            await bot.send_audio(call.message.chat.id, audio, caption="✅ @SizningBotNomingiz orqali yuklandi")
            os.remove(path)
            await call.message.delete()
    except:
        await call.message.answer("❌ Yuklashda xatolik!")

# --- OVOZLI XABARDAN TOPISH (SHAZAM) ---
@dp.message(F.voice | F.audio)
async def shazam_find(message: types.Message):
    wait = await message.answer("🎧 **Eshityapman... bir oz kuting...**")
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file = await bot.get_file(file_id)
    path = f"downloads/{file_id}.ogg"
    await bot.download_file(file.file_path, path)
    
    try:
        out = await shazam.recognize_song(path)
        if out.get('track'):
            t = out['track']
            text = f"🎵 **Topildi!**\n\n📌 **Nomi:** {t.get('title')}\n👤 **Ijrochi:** {t.get('subtitle')}"
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("😔 Kechirasiz, bu musiqani taniy olmadim.")
    finally:
        if os.path.exists(path): os.remove(path)
        await wait.delete()

# --- ADMIN PANEL ---
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    conn = sqlite3.connect('users.db')
    count = conn.cursor().execute("SELECT count(*) FROM users").fetchone()[0]
    conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Reklama (Xabar tarqatish)", callback_data="bc")]
    ])
    await message.answer(f"📊 **Bot Statistikasi:**\n\n👤 Foydalanuvchilar: {count}", reply_markup=kb)

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    init_db()
    if not os.path.exists('downloads'): os.makedirs('downloads')
    print("🚀 Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

