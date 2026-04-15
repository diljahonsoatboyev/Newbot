import os
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL
from shazamio import Shazam

# --- KONFIGURATSIYA ---
TOKEN = "8673913427:AAEKG283CJzFZxkVad53sLlyzrBnvpN9pxQ"
ADMIN_ID = 7089893378  # O'zingizning Telegram ID'ingizni yozing
CHANNELS = ["@eduflow_news"] # Majburiy obuna (ixtiyoriy)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

# --- MA'LUMOTLAR BAZASI (SQLite) ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, join_date TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", 
                   (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

# --- YUKLASH FUNKSIYASI ---
async def download_media(url):
    output_dir = 'downloads'
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'max_filesize': 50 * 1024 * 1024 # 50MB cheklov (Telegram bot limiti uchun)
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url, download=True)
        return ydl.prepare_filename(info)

# --- ADMIN PANEL UCHUN FILTR ---
class AdminFilter:
    def __init__(self, admin_id):
        self.admin_id = admin_id
    def __call__(self, message: types.Message):
        return message.from_user.id == self.admin_id

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)
    await message.answer(f"Salom {message.from_user.first_name}!\n\nLink yuboring yoki musiqa qidirish uchun ovozli xabar tashlang.")

# --- ADMIN PANEL ---
@dp.message(Command("admin"), AdminFilter(ADMIN_ID))
async def admin_panel(message: types.Message):
    users_count = len(get_all_users())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="send_ad")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")]
    ])
    await message.answer(f"💻 **Admin Panel**\n\nJami foydalanuvchilar: {users_count}", reply_markup=kb)

@dp.callback_query(F.data == "stats", AdminFilter(ADMIN_ID))
async def show_stats(call: types.CallbackQuery):
    users_count = len(get_all_users())
    await call.answer(f"Jami foydalanuvchilar: {users_count}", show_alert=True)

@dp.callback_query(F.data == "send_ad", AdminFilter(ADMIN_ID))
async def start_ad(call: types.CallbackQuery):
    await call.message.answer("Reklama xabarini yuboring (Text, rasm yoki video).")
    # Bu yerda oddiy xabar kutish logikasi bo'ladi

# --- ASOSIY ISHCHI QISM (MEDIA) ---
@dp.message(F.text.contains("http"))
async def handle_links(message: types.Message):
    wait = await message.answer("⏳ Ishlanmoqda...")
    try:
        file_path = await download_media(message.text)
        if os.path.exists(file_path):
            await message.answer_document(FSInputFile(file_path), caption="✅ @SizningBotNomingiz")
            os.remove(file_path)
    except Exception as e:
        await message.answer("❌ Xatolik: Media yuklab bo'lmadi.")
    finally:
        await wait.delete()

@dp.message(F.voice | F.audio)
async def handle_shazam(message: types.Message):
    wait = await message.answer("🔍 Qidirilmoqda...")
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file = await bot.get_file(file_id)
    file_on_disk = f"downloads/{file_id}.ogg"
    await bot.download_file(file.file_path, file_on_disk)
    
    try:
        out = await shazam.recognize_song(file_on_disk)
        if out.get('track'):
            t = out['track']
            await message.answer(f"🎵 Topildi!\n\nNomi: {t.get('title')}\nIjrochi: {t.get('subtitle')}")
        else:
            await message.answer("😔 Musiqa topilmadi.")
    finally:
        if os.path.exists(file_on_disk): os.remove(file_on_disk)
        await wait.delete()

async def main():
    init_db()
    if not os.path.exists('downloads'): os.makedirs('downloads')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

