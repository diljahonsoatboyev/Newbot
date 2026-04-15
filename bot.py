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
CHANNELS = ["@eduflow_news"] # Majburiy obuna kanali

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

def get_all_users():
    conn = sqlite3.connect('users.db')
    users = conn.cursor().execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [u[0] for u in users]

# --- OBUNA TEKSHIRISH (Tuzatilgan) ---
async def check_sub(user_id):
    for channel in CHANNELS:
        try:
            # Kanal nomini @ belgisiz ham, bilan ham tekshirish uchun formatlash
            chat_id = channel if channel.startswith('-100') else channel
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            
            # Agar status 'left' yoki 'kicked' bo'lsa, demak a'zo emas
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.error(f"Obuna tekshirishda xato: {e}")
            # Agar xato chiqsa (masalan bot admin emas), xavfsizlik uchun False qaytaramiz
            return False
    return True

# --- START KOMANDASI (Yangi Dizayn) ---
@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)
    
    if not await check_sub(message.from_user.id):
        # Kanal havolasini chiroyli qilish
        channel_link = f"https://t.me/{CHANNELS[0].replace('@','')}"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Obuna bo'lish 🚀", url=channel_link)],
            [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="check_subscription")]
        ])
        
        text = (
            f"👋 **Assalomu alaykum, {message.from_user.first_name}!**\n\n"
            "Botimizdan to'liq foydalanish va eng yangi musiqalarni yuklash uchun "
            "quyidagi kanalimizga a'zo bo'lishingizni so'raymiz. 👇\n\n"
            "🎁 *Bu bizning mehnatimizni qo'llab-quvvatlash uchun kichik yordam!*"
        )
        return await message.answer(text, reply_markup=kb, parse_mode="Markdown")

    welcome_text = (
        f"🌟 **Xush kelibsiz, {message.from_user.full_name}!**\n\n"
        "Botingiz tayyor holatda. Musiqa nomini yozing yoki audio yuboring!"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# --- OBUNA TASDIQLASH ---
@dp.callback_query(F.data == "check_subscription")
async def verify_sub(call: CallbackQuery):
    is_sub = await check_sub(call.from_user.id)
    if is_sub:
        await call.message.delete()
        await call.message.answer(
            "🎉 **Tabriklaymiz!**\n\nSiz muvaffaqiyatli ro'yxatdan o'tdingiz. "
            "Endi xohlagan musiqangizni qidirib yuklab olishingiz mumkin! 🔥",
            parse_mode="Markdown"
        )
    else:
        # Xabarni yangilab qo'yish
        await call.answer("❌ Kechirasiz, hali ham kanalga a'zo emassiz!", show_alert=True)


# --- YUKLASH VA QIDIRUV LOGIKASI ---
async def search_songs(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch10',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'source_address': '0.0.0.0', # IPv6 bloklarini chetlab o'tish
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, query, download=False)
        return info['entries']

# --- START KOMANDASI ---
@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)
    
    # Obunani tekshirish
    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga a'zo bo'lish 📢", url=f"https://t.me/{CHANNELS[0].replace('@','')}")],
            [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="check_subscription")]
        ])
        return await message.answer(f"⚠️ **Botdan foydalanish uchun kanalimizga obuna bo'ling!**", reply_markup=kb, parse_mode="Markdown")

    welcome_text = (
        f"🌟 **Assalomu alaykum, {message.from_user.full_name}!**\n\n"
        "Siz eng universal musiqa va video yuklovchi botga kirdingiz.\n\n"
        "✨ **Imkoniyatlar:**\n"
        "🔍 **Musiqa qidirish:** Shunchaki nomi yoki ijrochisini yozing.\n"
        "🎼 **Musiqa topish:** Ovozli xabar yuborsangiz, taniy olaman.\n"
        "📹 **Video yuklash:** YouTube linkini yuboring.\n\n"
        "🚀 *Marhamat, biron bir qo'shiq nomini yozing!*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# --- OBUNA TASDIQLASH ---
@dp.callback_query(F.data == "check_subscription")
async def verify_sub(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")
    else:
        await call.answer("❌ Siz hali kanalga a'zo emassiz!", show_alert=True)

# --- MATNLI QIDIRUV (10 ta natija) ---
@dp.message(F.text & ~F.text.startswith("/") & ~F.text.contains("http"))
async def music_search(message: types.Message):
    if not await check_sub(message.from_user.id):
        return await start(message)

    wait = await message.answer("🔍 **Siz uchun eng yaxshi variantlarni qidiryapman...**")
    try:
        results = await search_songs(message.text)
        if not results:
            await wait.edit_text("😔 Afsuski, hech narsa topilmadi.")
            return

        keyboard = []
        text = "🎵 **Topilgan natijalar:**\n\n"
        
        for i, entry in enumerate(results, 1):
            title = entry.get('title')[:45]
            text += f"{i}. 🎹 {title}\n"
            keyboard.append([InlineKeyboardButton(text=f"{i} - yuklash 📥", callback_data=f"dl_{entry['id']}")])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await wait.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(e)
        await wait.edit_text("❌ Xatolik yuz berdi. Iltimos birozdan so'ng urinib ko'ring.")

# --- YUKLASH HANDLER ---
@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(call: CallbackQuery):
    video_id = call.data.replace("dl_", "")
    url = f"https://www.youtube.com/watch?v={video_id}"
    await call.message.edit_text("⚡️ **Musiqa tayyorlanmoqda...**")
    
    if not os.path.exists('downloads'): os.makedirs('downloads')

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            path = ydl.prepare_filename(info)
            audio = FSInputFile(path)
            await bot.send_audio(call.message.chat.id, audio, caption=f"✅ {info.get('title')}\n\n📥 @Bot_Username")
            if os.path.exists(path): os.remove(path)
            await call.message.delete()
    except Exception as e:
        await call.message.answer(f"❌ Yuklashda xatolik: {e}")

# --- SHAZAM ---
@dp.message(F.voice | F.audio)
async def shazam_find(message: types.Message):
    if not await check_sub(message.from_user.id):
        return await start(message)
    
    wait = await message.answer("🎧 **Musiqani taniyapman...**")
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file = await bot.get_file(file_id)
    path = f"downloads/{file_id}.ogg"
    await bot.download_file(file.file_path, path)
    
    try:
        out = await shazam.recognize_song(path)
        if out.get('track'):
            t = out['track']
            text = f"🎵 **Musiqa topildi!**\n\n📌 **Nomi:** {t.get('title')}\n👤 **Ijrochi:** {t.get('subtitle')}"
            await message.answer(text)
        else:
            await message.answer("😔 Kechirasiz, musiqani aniqlab bo'lmadi.")
    finally:
        if os.path.exists(path): os.remove(path)
        await wait.delete()

# --- ADMIN PANEL ---
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    users = get_all_users()
    await message.answer(f"📊 **Statistika:**\n\n👤 Foydalanuvchilar soni: {len(users)}")

# --- ASOSIY ---
async def main():
    init_db()
    if not os.path.exists('downloads'): os.makedirs('downloads')
    print("🚀 Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
