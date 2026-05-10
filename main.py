import os
import io
import csv
import json
import asyncio
import shutil
import tempfile
import threading
import base64
from functools import partial
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        pass


def run_ping_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()


threading.Thread(target=run_ping_server, daemon=True).start()

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# ── COOKIES ────────────────────────────────────────────────────────────────────
_COOKIES_B64 = "IyBOZXRzY2FwZSBIVFRQIENvb2tpZSBGaWxlCiMgaHR0cHM6Ly9jdXJsLmhheHguc2UvcmZjL2Nvb2tpZV9zcGVjLmh0bWwKIyBUaGlzIGlzIGEgZ2VuZXJhdGVkIGZpbGUhIERvIG5vdCBlZGl0LgoKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE3OTI2Njk4MzcJX19TZWN1cmUtQlVDS0VUCUNMQUQKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE4MTI4ODM1MDcJUFJFRglmND00MDAwMDAwJmY2PTQwMDAwMDAwJnR6PUFzaWEuU2VvdWwKLnlvdXR1YmUuY29tCVRSVUUJLwlGQUxTRQkxODEyODgzNTAxCUhTSUQJQVR6MWhjNzFYMFpWWnpYVmIKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE4MTI4ODM1MDEJU1NJRAlBUjRmV1k3RVQwRk9JUkUzVQoueW91dHViZS5jb20JVFJVRQkvCUZBTFNFCTE4MTI4ODM1MDEJQVBJU0lECTE4WHpGUHdwODNZOVRhOUcvQWl3eFZOT01MSnFWX0tvZHIKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE4MTI4ODM1MDEJU0FQSVNJRAlMcFAxb3VOQmJPQU5mVFRsL0FRei1wRUdNbjhGTUtRcUlCCi55b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkxODEyODgzNTAxCV9fU2VjdXJlLTFQQVBJU0lECUxwUDFvdU5CYk9BTmZUVGwvQVF6LXBFR01uOEZNS1FxSUIKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE4MTI4ODM1MDEJX19TZWN1cmUtM1BBUElTSUQJTHBQMW91TkJiT0FOZlRUbC9BUXotcEVHTW44Rk1LUXFJQgoueW91dHViZS5jb20JVFJVRQkvCUZBTFNFCTE4MTI4ODM1MDEJU0lECWcuYTAwMDl3aDczell1Q0xOYkV1UEM1V3pOY3lRZkxFY19qeGZGNFdvczZoTDJMa3R2emwtcC1kVk5FaTZkUnE5RTFsWU5PR042QVFBQ2dZS0FkNFNBUkVTRlFIR1gyTWlhQWk5TzR0NWNPQ3Q1d0JsUTRlRDd4b1ZBVUY4eUtwTEhzUklPVWRkc0ZrZEV5a3NJSU5EMDA3NgoueW91dHViZS5jb20JVFJVRQkvCVRSVUUJMTgxMjg4MzUwMQlfX1NlY3VyZS0xUFNJRAlnLmEwMDA5d2g3M3pZdUNMTmJFdVBDNVd6TmN5UWZMRWNfanhmRjRXb3M2aEwyTGt0dnpsLXBFSWlFUDh0cm9ENlk0QUpsaHRobGZBQUNnWUtBU3dTQVJFU0ZRSEdYMk1pYUd6VTVlSlF6QkNxQjRBMHgza0RYUm9WQVVGOHlLcVNkSEdUZ3ZNbDlGUmF6RTZ3VHpSdzAwNzYKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE4MTI4ODM1MDEJX19TZWN1cmUtM1BTSUQJZy5hMDAwOXdoNzN6WXVDTE5iRXVQQzVXek5jeVFmTEVjX2p4ZkY0V29zNmhMMkxrdHZ6bC1wbDYzd3BJRFFYbHdHbTQ2U282WGh0Z0FDZ1lLQVVzU0FSRVNGUUhHWDJNaUV3Tklnd3UzNEx4eTJPMHpVU3d0b3hvVkFVRjh5S3JhQzhFLVFBUy05RHhLMENiRmtnaEswMDc2Ci55b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkxODEyODgzNTAyCUxPR0lOX0lORk8JQUZtbUYyc3dSUUlnZGZta294anJESnVmSzNtdFBRMXJYeTRmSVNCODUwakhPLThSeV9kcnZfUUNJUUN6andEeFNpVV96UEZOMVNCOVVJd0lWYS1kNkZQTEdfVW83UGVfQXVncS1BOlFVUTNNak5tZVhwc2VFVlJMV3B4WVhKcFdUSldMVFUzZVZRMlJGSkRjWE13VWxaSGQxTnhjRWRoUmxkTGJ6RmtWM2N0U0Mxa1VWUnlVelk1YkVwcGFWUXdjbGQzU25Ob1h6TlNUVFpJVWxKdlEwaFJaMUJ6UzBoUFUwdHRVVVpxU21wSVNFMXhUek4xVUdORVFraFViRWsyYW1OT1FXcE9VRGxuZVZaR1VEQlVZa2t6VTFOMVVqaFJXV3RXWTBSNFdYbElRa2RXYzNGc1J6WnZWVUpxT1dGUgoueW91dHViZS5jb20JVFJVRQkvCVRSVUUJMTgwOTg2NzIyOAlfX1NlY3VyZS0xUFNJRFRTCXNpZHRzLUNqUUJoa2VSZDBSeF81aEtWc1ZZek9zM0o1ajhzNjdrRWFGaEZYVmxDOUlmOFZsYWQtMi1nWkxJRUNJM1phUFFEbXJQMDBRWUVBQQoueW91dHViZS5jb20JVFJVRQkvCVRSVUUJMTgwOTg2NzIyOAlfX1NlY3VyZS0zUFNJRFRTCXNpZHRzLUNqUUJoa2VSZDBSeF81aEtWc1ZZek9zM0o1ajhzNjdrRWFGaEZYVmxDOUlmOFZsYWQtMi1nWkxJRUNJM1phUFFEbXJQMDBRWUVBQQoueW91dHViZS5jb20JVFJVRQkvCUZBTFNFCTE4MDk4NjcyMjgJU0lEQ0MJQUtFeVh6WFQyNFFWM1p3LXN4Q0p3VFdKT0w2S0cyYUNJcmpBREdIOVJGbUp2UGE5MVE1cS1ZU0VNcWJidmFNUjEwNUZXSVg4Ci55b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkxODA5ODY3MjI4CV9fU2VjdXJlLTFQU0lEQ0MJQUtFeVh6Vnd3NU83b2xicGZqc24yblRNN1BtSjVXYU5mb2I1cjV2WXo0UzdvWXpNbUlBb1RrbWxQVzZTRU9qVWlSYXlfeUV6Ci55b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkxODA5ODc3NjUyCV9fU2VjdXJlLTNQU0lEQ0MJQUtFeVh6WHNDeVJBdzhuYWVSRFRlc214T0hzMzByREJiSFZydWFWVXFTTHJoU2dKZEIzZmN5aVY1YkRvclpzeTRITkpidFhHTWcKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE3OTM4NzU1MTAJVklTSVRPUl9JTkZPMV9MSVZFCTlPX3ZXZXNJQ3NzCi55b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkxNzkzODc1NTEwCVZJU0lUT1JfUFJJVkFDWV9NRVRBREFUQQlDZ0pMVWhJRUdnQWdIdyUzRCUzRAoueW91dHViZS5jb20JVFJVRQkvCVRSVUUJMAlZU0MJUl9xWGsyTHI4ZEkKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE3OTM4NzUzOTcJX19TZWN1cmUtUk9MTE9VVF9UT0tFTglDTUdwdE1MWTA1V3gtd0VRdjZfaTZ2ZUlsQU1ZcHRicTg0S3NsQU0lM0QKLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE3OTM4NzUzOTgJX19TZWN1cmUtWU5JRAkxOC5ZVD1zbTFsblIxS0wxdEFqQXdmd01pUHhpR01yeXdDbU14U05wUkNkT09zdjNMdGJCc29FdDhuenJvUllxTy1Zc3JjRmFxWWwwYXpEa0xGaFFvNm5pU1RhLUg1V1BPSWJ2OHF4bkdKcjgxc0pfWTd6Z3NXVmFtNU1mTm9iUmZlak1iLXFUWWxTbTZVa2pJMEJlWHJVVWI5Y05fc0x3MTRSc0t5eTJ4SWQyOW81S09IanpYQm56WnJteDJ6ZUFvdmNmS2lsQVMwVjJaQWNJOVVMRm9adU1Hc1NDR3laQ2FJbDlGT2lQczE3THh5dXUxOW5iak9GSHdBMldfeWpJYjFEU3ZIZXJyS3k3X3lyTHlQNU4yOEZmTEIzN09SM0x4VVNzYnRsMldBMjJEbG5BRWpXMG15OE5VVWVPdloyWm04SjhSQnhlaFhMZUk2Y25WNnk1b05ZZ21hT0EK"

_cookies_path = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
_raw_env = os.environ.get("YOUTUBE_COOKIES", "")
if _raw_env:
    with open(_cookies_path, "w") as _f:
        _f.write(base64.b64decode(_raw_env + "==").decode("utf-8"))
else:
    with open(_cookies_path, "wb") as _f:
        _f.write(base64.b64decode(_COOKIES_B64))
COOKIES_FILE = _cookies_path
print("Cookies loaded OK.")
# ───────────────────────────────────────────────────────────────────────────────

user_lang = {}
user_results = {}
user_page = {}
user_search_query = {}
user_history = defaultdict(list)
user_favourites = defaultdict(list)
user_last_download = {}
user_profiles = {}
admin_state = {}

HISTORY_LIMIT = 5
FAV_LIMIT = 20
PAGE_SIZE = 5
FETCH_STEP = 5
STATS_FILE = "stats.json"
PROFILES_FILE = "profiles.json"


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            data = json.load(f)
        data["users"] = set(data.get("users", []))
        return data
    return {"users": set(), "downloads": 0}


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump({"users": list(stats["users"]), "downloads": stats["downloads"]}, f)


stats = load_stats()


def load_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "r") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}
    return {}


def save_profiles(profiles):
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f)


user_profiles = load_profiles()


def track_user(user_id):
    if user_id not in stats["users"]:
        stats["users"].add(user_id)
        save_stats(stats)


def track_user_profile(user_id, first_name, last_name=None, username=None):
    user_profiles[user_id] = {
        "first_name": first_name or "Unknown",
        "last_name": last_name or "",
        "username": username or "",
    }
    save_profiles(user_profiles)


def track_download():
    stats["downloads"] += 1
    save_stats(stats)


lang_keyboard = ReplyKeyboardMarkup(
    [["O'zbek 🇺🇿", "Русский 🇷🇺", "English 🇬🇧"]], resize_keyboard=True
)

TEXTS = {
    "choose_lang": {"en": "Choose language:", "ru": "Выберите язык:", "uz": "Tilni tanlang:"},
    "searching": {"en": "🔍 Searching...", "ru": "🔍 Поиск...", "uz": "🔍 Qidirilmoqda..."},
    "no_results": {"en": "❌ No results found", "ru": "❌ Ничего не найдено", "uz": "❌ Hech narsa topilmadi"},
    "top_results": {
        "en": "🎵 Top results — tap to download:",
        "ru": "🎵 Лучшие результаты — нажмите для скачивания:",
        "uz": "🎵 Eng yaxshi natijalar — bosib yuklab oling:",
    },
    "page_info": {"en": "Page {page} of {total}", "ru": "Страница {page} из {total}", "uz": "{page}/{total} sahifa"},
    "no_more": {"en": "✅ No more results.", "ru": "✅ Результатов больше нет.", "uz": "✅ Boshqa natijalar yo'q."},
    "downloading": {"en": "⬇️ Downloading... please wait.", "ru": "⬇️ Загрузка... подождите.", "uz": "⬇️ Yuklanmoqda... iltimos kuting."},
    "download_error": {
        "en": "❌ Failed to download. Try another result.",
        "ru": "❌ Не удалось скачать. Попробуйте другой результат.",
        "uz": "❌ Yuklab bo'lmadi. Boshqa natijani sinab ko'ring.",
    },
    "history_header": {
        "en": "🕐 Your last downloads — tap to re-download:",
        "ru": "🕐 Ваши последние загрузки — нажмите для повторного скачивания:",
        "uz": "🕐 Oxirgi yuklamalaringiz — bosib qayta yuklab oling:",
    },
    "history_empty": {
        "en": "🎵 You haven't downloaded any songs yet. Search for music to get started!",
        "ru": "🎵 Вы ещё не скачали ни одной песни. Найдите музыку, чтобы начать!",
        "uz": "🎵 Siz hali hech qanday qo'shiq yuklamagansiz. Boshlash uchun musiqa qidiring!",
    },
    "save_hint": {
        "en": "⭐ Send /save to add this to your favourites.",
        "ru": "⭐ Отправьте /save, чтобы добавить в избранное.",
        "uz": "⭐ Sevimlilariga qo'shish uchun /save yuboring.",
    },
    "saved": {"en": "⭐ Added to your favourites!", "ru": "⭐ Добавлено в избранное!", "uz": "⭐ Sevimlilarga qo'shildi!"},
    "already_saved": {
        "en": "✅ This song is already in your favourites.",
        "ru": "✅ Эта песня уже в избранном.",
        "uz": "✅ Bu qo'shiq allaqachon sevimlilarda.",
    },
    "nothing_to_save": {
        "en": "⚠️ Download a song first, then send /save to favourite it.",
        "ru": "⚠️ Сначала скачайте песню, затем отправьте /save, чтобы добавить в избранное.",
        "uz": "⚠️ Avval qo'shiq yuklab oling, keyin /save yuboring.",
    },
    "fav_header": {
        "en": "⭐ Your favourites — tap to download:",
        "ru": "⭐ Ваше избранное — нажмите для скачивания:",
        "uz": "⭐ Sevimlilaringiz — bosib yuklab oling:",
    },
    "fav_empty": {
        "en": "🎵 No favourites yet. Download a song and send /save to add it!",
        "ru": "🎵 Избранное пусто. Скачайте песню и отправьте /save, чтобы добавить!",
        "uz": "🎵 Sevimlilar bo'sh. Qo'shiq yuklab, /save yuboring!",
    },
    "fav_limit": {
        "en": f"⚠️ Favourites list is full (20 songs max). Remove one with /unfav first.",
        "ru": f"⚠️ Список избранного заполнен (макс. 20 песен). Сначала удалите одну через /unfav.",
        "uz": f"⚠️ Sevimlilar ro'yxati to'ldi (maks. 20 ta). Avval /unfav orqali birini o'chiring.",
    },
    "unfav_header": {
        "en": "🗑 Tap a song to remove it from favourites:",
        "ru": "🗑 Нажмите на песню, чтобы удалить из избранного:",
        "uz": "🗑 Sevimlilardan o'chirish uchun qo'shiqni bosing:",
    },
    "unfav_done": {"en": "🗑 Removed from favourites.", "ru": "🗑 Удалено из избранного.", "uz": "🗑 Sevimlilardan o'chirildi."},
    "unfav_empty": {
        "en": "🎵 Your favourites list is already empty.",
        "ru": "🎵 Ваш список избранного уже пуст.",
        "uz": "🎵 Sevimlilar ro'yxatingiz allaqachon bo'sh.",
    },
    "help": {
        "en": (
            "🎵 *Music Bot — Commands*\n\n"
            "Just type any song name to search.\n\n"
            "Tap a button from the results to download.\n\n"
            "/history — your last 5 downloads\n"
            "/save — save last download to favourites\n"
            "/fav — view & re-download favourites\n"
            "/unfav — remove a song from favourites\n"
            "/help — show this message\n\n"
            "Need help? Contact the developer 👇"
        ),
        "ru": (
            "🎵 *Музыкальный бот — Команды*\n\n"
            "Просто напишите название песни для поиска.\n\n"
            "Нажмите на кнопку из результатов для скачивания.\n\n"
            "/history — последние 5 загрузок\n"
            "/save — сохранить последнюю загрузку в избранное\n"
            "/fav — просмотр и повторная загрузка избранного\n"
            "/unfav — удалить песню из избранного\n"
            "/help — показать это сообщение\n\n"
            "Нужна помощь? Свяжитесь с разработчиком 👇"
        ),
        "uz": (
            "🎵 *Musiqa boti — Buyruqlar*\n\n"
            "Qo'shiq nomini yozing va qidiring.\n\n"
            "Natijalardan kerakli qo'shiqni bosib yuklab oling.\n\n"
            "/history — oxirgi 5 ta yuklab olish\n"
            "/save — oxirgi yuklab olingan qo'shiqni sevimlilarga saqlash\n"
            "/fav — sevimlilarni ko'rish va qayta yuklab olish\n"
            "/unfav — sevimlilardan qo'shiqni o'chirish\n"
            "/help — bu xabarni ko'rsatish\n\n"
            "Yordam kerakmi? Dasturchi bilan bog'laning 👇"
        ),
    },
}


def get_text(user_id, key):
    lang = user_lang.get(user_id, "uz")
    return TEXTS[key][lang]


def add_to_history(user_id, title, url, duration):
    history = user_history[user_id]
    history = [h for h in history if h[1] != url]
    history.insert(0, (title, url, duration))
    user_history[user_id] = history[:HISTORY_LIMIT]


def build_keyboard(all_results, page=0, action="dl"):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_results = all_results[start:end]
    buttons = []
    for i, (title, url, duration) in enumerate(page_results):
        global_idx = start + i
        dur = f" [{format_duration(duration)}]" if duration else ""
        icon = "🗑" if action == "rm" else "🎵"
        label = f"{icon} {title[:45]}{dur}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"{action}:{global_idx}")])
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀ Prev", callback_data=f"page:{page - 1}"))
    if end < len(all_results):
        nav_row.append(InlineKeyboardButton("Next ▶", callback_data=f"page:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)
    return InlineKeyboardMarkup(buttons)


def _search_sync(query, count, prefix):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "source_address": "0.0.0.0",
        "socket_timeout": 30,
    }
    if prefix == "ytsearch" and COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE
    if prefix == "ytsearch":
        ydl_opts["extractor_args"] = {
            "youtube": {
                "player_client": ["ios", "tv_embedded", "mweb"],
                "skip": ["dash", "hls"],
            }
        }
    results_list = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"{prefix}{count}:{query}", download=False)
        if result and "entries" in result:
            for video in result["entries"]:
                if not video:
                    continue
                title = video.get("title")
                url = video.get("webpage_url")
                duration = video.get("duration", 0)
                if title and url:
                    results_list.append((title, url, duration))
    return results_list


def _search_youtube_sync(query, count):
    results = _search_sync(query, count, "ytsearch")
    if not results:
        results = _search_sync(query, count, "scsearch")
    return results


async def search_youtube_async(query, count):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_search_youtube_sync, query, count))


def _get_ffmpeg_dir():
    # Try shutil.which first (works on Railway with nixpacks)
    found = shutil.which("ffmpeg")
    if found:
        return os.path.dirname(found)
    # Search common nix store paths
    nix_store = "/nix/store"
    if os.path.exists(nix_store):
        for entry in os.listdir(nix_store):
            if "ffmpeg" in entry:
                candidate = os.path.join(nix_store, entry, "bin")
                if os.path.exists(os.path.join(candidate, "ffmpeg")):
                    return candidate
    # Common fallback paths
    for path in ["/usr/bin", "/usr/local/bin", "/bin"]:
        if os.path.exists(os.path.join(path, "ffmpeg")):
            return path
    return ""


def _download_audio_sync(url):
    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, "audio.%(ext)s")
    ffmpeg_dir = _get_ffmpeg_dir()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "128"}],
        "ffmpeg_location": ffmpeg_dir,
        "concurrent_fragment_downloads": 4,
        "extractor_args": {"youtube": {"player_client": ["ios", "tv_embedded", "mweb"]}},
        "source_address": "0.0.0.0",
        "socket_timeout": 30,
    }
    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    for ext in ("m4a", "mp3", "webm", "opus"):
        p = os.path.join(tmp_dir, f"audio.{ext}")
        if os.path.exists(p):
            return p
    for f in os.listdir(tmp_dir):
        full = os.path.join(tmp_dir, f)
        if os.path.isfile(full):
            return full
    raise FileNotFoundError("Audio file not found after download")


async def download_audio_async(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_download_audio_sync, url))


def format_duration(seconds):
    if not seconds:
        return ""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


async def track_any_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        track_user(user.id)
        track_user_profile(user.id, user.first_name, user.last_name, user.username)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    track_user(user_id)
    track_user_profile(user_id, query.from_user.first_name, query.from_user.last_name, query.from_user.username)
    data = query.data

    if data.startswith("dl:"):
        index = int(data.split(":")[1])
        results = user_results.get(user_id, [])
        if 0 <= index < len(results):
            title, url, duration = results[index]
            wait_msg = await query.message.reply_text(get_text(user_id, "downloading"))
            try:
                audio_path = await download_audio_async(url)
                with open(audio_path, "rb") as audio_file:
                    await query.message.reply_audio(audio=audio_file, title=title, caption=f"🎵 {title}")
                os.remove(audio_path)
                add_to_history(user_id, title, url, duration)
                user_last_download[user_id] = (title, url, duration)
                track_download()
                await wait_msg.delete()
                await query.message.reply_text(get_text(user_id, "save_hint"))
            except Exception as e:
                print(f"Download error: {e}")
                await wait_msg.delete()
                await query.message.reply_text(get_text(user_id, "download_error"))

    elif data.startswith("page:"):
        page = int(data.split(":")[1])
        results = user_results.get(user_id, [])
        if not results:
            return
        needed = (page + 1) * PAGE_SIZE
        if needed > len(results):
            stored_query = user_search_query.get(user_id)
            if stored_query:
                fetch_count = needed + FETCH_STEP
                more = await search_youtube_async(stored_query, fetch_count)
                user_results[user_id] = more
                results = more
        user_page[user_id] = page
        total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
        lang = user_lang.get(user_id, "uz")
        page_label = TEXTS["page_info"][lang].format(page=page + 1, total=total_pages)
        header = get_text(user_id, "top_results") + f"\n{page_label}"
        await query.message.edit_text(header, reply_markup=build_keyboard(results, page=page))

    elif data.startswith("rm:"):
        index = int(data.split(":")[1])
        favs = user_favourites[user_id]
        if 0 <= index < len(favs):
            user_favourites[user_id] = [f for i, f in enumerate(favs) if i != index]
            await query.message.reply_text(get_text(user_id, "unfav_done"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    track_user(user_id)
    track_user_profile(user_id, update.message.from_user.first_name, update.message.from_user.last_name, update.message.from_user.username)
    first_name = update.message.from_user.first_name or "there"
    contact_button = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Contact Developer", url="https://t.me/mexrojiddin_7o7")]])
    safe_name = first_name.replace("*", "").replace("_", "").replace("`", "").replace("[", "")
    welcome = (
        f"👋 Salom {safe_name}! Music Botga xush kelibsiz\n\n"
        "🎵 Istalgan qo'shiq nomini yozing va MP3 yuklab oling — tez va bepul.\n\n"
        "Nima qila olaman:\n"
        "🔍 Qidirish — qo'shiq nomini yozing\n"
        "⬇️ Natijadan kerakli qo'shiqni bosib yuklab oling\n"
        "/history — oxirgi 5 ta yuklab olish\n"
        "/save — qo'shiqni sevimlilarga saqlash\n"
        "/fav — sevimlilarni ko'rish\n"
        "/unfav — sevimlilardan o'chirish\n"
        "/help — yordam\n\n"
        "👇 Tilni tanlang:"
    )
    await update.message.reply_text(welcome, reply_markup=lang_keyboard)
    await update.message.reply_text("📩 Yordam kerakmi? Dasturchi bilan bog'laning.", reply_markup=contact_button)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    hist = user_history[user_id]
    if not hist:
        await update.message.reply_text(get_text(user_id, "history_empty"))
        return
    user_results[user_id] = hist
    await update.message.reply_text(get_text(user_id, "history_header"), reply_markup=build_keyboard(hist))


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    last = user_last_download.get(user_id)
    if not last:
        await update.message.reply_text(get_text(user_id, "nothing_to_save"))
        return
    title, url, duration = last
    favs = user_favourites[user_id]
    if any(f[1] == url for f in favs):
        await update.message.reply_text(get_text(user_id, "already_saved"))
        return
    if len(favs) >= FAV_LIMIT:
        await update.message.reply_text(get_text(user_id, "fav_limit"))
        return
    favs.insert(0, (title, url, duration))
    await update.message.reply_text(get_text(user_id, "saved"))


async def fav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    favs = user_favourites[user_id]
    if not favs:
        await update.message.reply_text(get_text(user_id, "fav_empty"))
        return
    user_results[user_id] = favs
    await update.message.reply_text(get_text(user_id, "fav_header"), reply_markup=build_keyboard(favs))


async def unfav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    favs = user_favourites[user_id]
    if not favs:
        await update.message.reply_text(get_text(user_id, "unfav_empty"))
        return
    await update.message.reply_text(get_text(user_id, "unfav_header"), reply_markup=build_keyboard(favs, action="rm"))


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Bot ishlayapti! (Online)")


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="adm:stats"), InlineKeyboardButton("👥 Users", callback_data="adm:users")],
        [InlineKeyboardButton("📥 Export CSV", callback_data="adm:export"), InlineKeyboardButton("📢 Broadcast", callback_data="adm:broadcast")],
        [InlineKeyboardButton("🔄 Ping", callback_data="adm:ping")],
    ])


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return
    await update.message.reply_text("🔧 *Admin Panel*\n\nQuyidagi tugmalardan birini tanlang:", parse_mode="Markdown", reply_markup=admin_keyboard())


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await query.message.reply_text("❌ Ruxsat yo'q.")
        return
    action = query.data.split(":")[1]

    if action == "stats":
        total_users = len(stats["users"])
        total_downloads = stats["downloads"]
        await query.message.reply_text(
            f"📊 *Bot Statistics*\n\n👥 Foydalanuvchilar: *{total_users}*\n⬇️ Yuklab olishlar: *{total_downloads}*",
            parse_mode="Markdown", reply_markup=admin_keyboard())

    elif action == "users":
        users = sorted(stats["users"])
        if not users:
            await query.message.reply_text("🎵 Hozircha foydalanuvchilar yo'q.", reply_markup=admin_keyboard())
            return
        lines = [f"👥 *Foydalanuvchilar ({len(users)} ta):*"]
        for uid in users[:50]:
            profile = user_profiles.get(uid, {})
            name = profile.get("first_name", "Unknown")
            last_name = profile.get("last_name", "")
            username = profile.get("username", "")
            full_name = f"{name} {last_name}".strip()
            lines.append(f"• {full_name} (@{username})" if username else f"• {full_name}")
        if len(users) > 50:
            lines.append(f"... va {len(users) - 50} ta boshqa")
        await query.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=admin_keyboard())

    elif action == "export":
        users = sorted(stats["users"])
        if not users:
            await query.message.reply_text("🎵 Foydalanuvchilar yo'q.", reply_markup=admin_keyboard())
            return
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "first_name", "last_name", "username"])
        for uid in users:
            profile = user_profiles.get(uid, {})
            writer.writerow([uid, profile.get("first_name", ""), profile.get("last_name", ""), profile.get("username", "")])
        csv_bytes = output.getvalue().encode("utf-8")
        await query.message.reply_document(document=io.BytesIO(csv_bytes), filename="users.csv", caption=f"👥 Jami: {len(users)} ta foydalanuvchi")
        await query.message.reply_text("🔧 *Admin Panel*", parse_mode="Markdown", reply_markup=admin_keyboard())

    elif action == "broadcast":
        admin_state[user_id] = "awaiting_broadcast"
        await query.message.reply_text(
            "📢 *Broadcast xabari*\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n_(Bekor qilish uchun /cancel yuboring)_",
            parse_mode="Markdown")

    elif action == "ping":
        await query.message.reply_text("🟢 Bot ishlayapti! (Online)", reply_markup=admin_keyboard())


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text(f"❌ Bu buyruq faqat bot egasi uchun.\n\n🔍 Sizning Telegram ID: {user_id}")
        return
    total_users = len(stats["users"])
    total_downloads = stats["downloads"]
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n👥 Jami foydalanuvchilar: *{total_users}*\n⬇️ Jami yuklab olishlar: *{total_downloads}*",
        parse_mode="Markdown")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("❌ Bu buyruq faqat bot egasi uchun.")
        return
    if not context.args:
        await update.message.reply_text("📢 Ishlatish:\n/broadcast Salom hammaga!\n\nXabar barcha foydalanuvchilarga yuboriladi.")
        return
    message_text = " ".join(context.args)
    all_users = list(stats["users"])
    sent = 0
    failed = 0
    status_msg = await update.message.reply_text(f"📢 Yuborilmoqda... 0/{len(all_users)}")
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=message_text)
            sent += 1
        except Exception:
            failed += 1
    await status_msg.edit_text(f"✅ Broadcast tugadi!\n\n📨 Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("❌ Bu buyruq faqat bot egasi uchun.")
        return
    users = sorted(stats["users"])
    if not users:
        await update.message.reply_text("🎵 Hozircha foydalanuvchilar yo'q.")
        return
    lines = ["👥 *Bot users:*"]
    for uid in users[:50]:
        profile = user_profiles.get(uid, {})
        name = profile.get("first_name", "Unknown")
        last_name = profile.get("last_name", "")
        username = profile.get("username", "")
        full_name = f"{name} {last_name}".strip()
        lines.append(f"• {full_name} (@{username})" if username else f"• {full_name}")
    if len(users) > 50:
        lines.append(f"\n... and {len(users) - 50} more")
    await update.message.reply_text("\n".join(lines))


async def exportusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("❌ Bu buyruq faqat bot egasi uchun.")
        return
    users = sorted(stats["users"])
    if not users:
        await update.message.reply_text("🎵 Hozircha foydalanuvchilar yo'q.")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "first_name", "last_name", "username"])
    for uid in users:
        profile = user_profiles.get(uid, {})
        writer.writerow([uid, profile.get("first_name", ""), profile.get("last_name", ""), profile.get("username", "")])
    csv_bytes = output.getvalue().encode("utf-8")
    await update.message.reply_document(document=io.BytesIO(csv_bytes), filename="users.csv", caption=f"👥 Jami foydalanuvchilar: {len(users)} ta")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact_button = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Contact Developer", url="https://t.me/mexrojiddin_7o7")]])
    await update.message.reply_text(get_text(user_id, "help"), parse_mode="Markdown", reply_markup=contact_button)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    track_user(user_id)
    track_user_profile(user_id, update.message.from_user.first_name, update.message.from_user.last_name, update.message.from_user.username)

    if admin_state.get(user_id) == "awaiting_broadcast":
        admin_state.pop(user_id)
        all_users = list(stats["users"])
        sent = 0
        failed = 0
        status_msg = await update.message.reply_text(f"📢 Yuborilmoqda... 0/{len(all_users)}")
        for uid in all_users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent += 1
            except Exception:
                failed += 1
        await status_msg.edit_text(f"✅ Broadcast tugadi!\n\n📨 Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")
        await update.message.reply_text("🔧 *Admin Panel*", parse_mode="Markdown", reply_markup=admin_keyboard())
        return

    if text == "English 🇬🇧":
        user_lang[user_id] = "en"
        await update.message.reply_text("Send music name 🎵")
        return
    elif text == "Русский 🇷🇺":
        user_lang[user_id] = "ru"
        await update.message.reply_text("Отправьте название музыки 🎵")
        return
    elif text == "O'zbek 🇺🇿":
        user_lang[user_id] = "uz"
        await update.message.reply_text("Musiqa nomini yuboring 🎵")
        return

    search_msg = await update.message.reply_text(get_text(user_id, "searching"))
    results = await search_youtube_async(text, FETCH_STEP)
    await search_msg.delete()
    if results:
        user_results[user_id] = results
        user_search_query[user_id] = text
        user_page[user_id] = 0
        total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
        lang = user_lang.get(user_id, "uz")
        page_label = TEXTS["page_info"][lang].format(page=1, total=total_pages)
        header = get_text(user_id, "top_results") + f"\n{page_label}"
        await update.message.reply_text(header, reply_markup=build_keyboard(results, page=0))
    else:
        await update.message.reply_text(get_text(user_id, "no_results"))


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if admin_state.pop(user_id, None):
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=admin_keyboard())
    else:
        await update.message.reply_text("❌ Bekor qilish uchun hech narsa yo'q.")


async def post_init(application):
    await application.bot.delete_webhook(drop_pending_updates=True)


app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
app.add_handler(MessageHandler(filters.ALL, track_any_user), group=-1)
app.add_handler(CallbackQueryHandler(track_any_user), group=-1)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("admin", admin_command))
app.add_handler(CommandHandler("cancel", cancel_command))
app.add_handler(CommandHandler("stats", stats_command))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("users", users_command))
app.add_handler(CommandHandler("exportusers", exportusers_command))
app.add_handler(CommandHandler("history", history))
app.add_handler(CommandHandler("save", save))
app.add_handler(CommandHandler("fav", fav))
app.add_handler(CommandHandler("unfav", unfav))
app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^adm:"))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot running...")
app.run_polling(drop_pending_updates=True)