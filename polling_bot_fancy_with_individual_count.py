
import os
import json
import time
import requests
from datetime import datetime

BOT_TOKEN = "8156469002:AAH5g7qbriqUELpNI_mKKLPx3mHYvqEavDA"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
EXERCISE_FILE = "simple_exercise_data.json"
PROGRESS_FILE = "progress.json"

# Load exercise data
with open(EXERCISE_FILE, "r") as f:
    exercise_data = json.load(f)

# Load or initialize user progress
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r") as f:
        user_progress = json.load(f)
else:
    user_progress = {}


def log_user_info(user):
    user_id = user["id"]
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    username = user.get("username", "")

    log_entry = {
        "id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username
    }

    # Save to a JSON file
    try:
        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                data = json.load(f)
        else:
            data = {}

        if str(user_id) not in data:
            data[str(user_id)] = log_entry
            with open("users.json", "w") as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error logging user info: {e}")


import threading
progress_lock = threading.Lock()

def save_progress():
    with progress_lock:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(user_progress, f, indent=2)


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    return requests.post(f"{BASE_URL}/sendMessage", data=payload)

def send_photo(chat_id, photo_path, caption=None):
    with open(photo_path, 'rb') as photo_file:
        payload = {
            "chat_id": chat_id,
        }
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        files = {'photo': photo_file}
        return requests.post(f"{BASE_URL}/sendPhoto", data=payload, files=files)

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    return requests.post(f"{BASE_URL}/editMessageText", data=payload)

def get_main_menu():
    icons = {
        "Bicep": "💪", "Tricep": "💪", "Shoulder": "💪",
        "Chest": "🏋️", "Back": "🏋️"
    }
    return {
        "inline_keyboard": [
            [{"text": f"{icons.get(cat, '')} {cat}", "callback_data": f"cat|{cat}"}] for cat in 
            ["Bicep", "Tricep", "Shoulder", "Chest", "Back"]
        ] + [
            [{"text": "📋 View Status", "callback_data": "status"}],
            [{"text": "📊 View Chart", "callback_data": "chart"}],
            [{"text": "🔁 Reset Progress", "callback_data": "reset"}]
        ]
    }

def get_exercise_menu(user_id, category):
    buttons = []
    done_ex = user_progress.get(user_id, {}).get(category, {})
    for ex in exercise_data[category]:
        status = "✅" if done_ex.get(ex, False) else "❌"
        buttons.append([{
            "text": f"{status} {ex}",
            "callback_data": f"done|{category}|{ex}"
        }])
    buttons.append([{"text": "⬅️ Back to Main Menu", "callback_data": "back"}])
    return { "inline_keyboard": buttons }
def generate_chart(user_id):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from collections import defaultdict

    history = user_progress.get(user_id, {}).get("history", {})
    daily_counts = defaultdict(int)
    for date_str, count in history.items():
        daily_counts[date_str] = count

    sorted_dates = sorted(daily_counts)
    counts = [daily_counts[date] for date in sorted_dates]

    if not sorted_dates:
        return None

    plt.figure(figsize=(10, 4))
    plt.plot(sorted_dates, counts, marker="o", linestyle="-")
    plt.title("Exercise Sessions Over Time")
    plt.xlabel("Date")
    plt.ylabel("Number of Exercises")
    plt.xticks(rotation=45)
    plt.ylim(0, 25)
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.grid(True)
    plt.tight_layout()

    # 💡 Save to a temp path instead of current folder
    path = "/tmp/exercise_stats_chart.png"
    plt.savefig(path)
    return path

def process_update(update):
    print("📩 Received update:", json.dumps(update, indent=2))

    def log_user_info(user):
        user_id = user["id"]
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        username = user.get("username", "")

        log_entry = {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username
        }

        try:
            if os.path.exists("users.json"):
                with open("users.json", "r") as f:
                    data = json.load(f)
            else:
                data = {}

            if str(user_id) not in data:
                data[str(user_id)] = log_entry
                with open("users.json", "w") as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Error logging user info: {e}")

    if "message" in update:
        user = update["message"]["from"]
        log_user_info(user)

        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")
        if text == "/start":
            send_message(
                chat_id,
                "💥 <b>Welcome to Ahmad's Workout Bot!</b> 💥\n"
                "Track your daily exercises, mark them as done ✅, and stay fit! 💪\n"
                "Choose a category below to begin 👇",
                get_main_menu()
            )

    elif "callback_query" in update:
        query = update["callback_query"]
        user = query["from"]
        log_user_info(user)

        data = query["data"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        user_id = str(user["id"])

        parts = data.split("|")

        if data == "reset":
            user_progress[user_id] = {}
            save_progress()
            edit_message(chat_id, message_id, "🔄 Progress has been reset.", get_main_menu())

        elif data == "status":
            msg = "<b>📋 Your Progress:</b>\n"
            for cat, exercises in exercise_data.items():
                msg += f"\n<b>{cat}</b>\n"
                for ex in exercises:
                    done = user_progress.get(user_id, {}).get(cat, {}).get(ex, False)
                    status = "✅" if done else "❌"
                    msg += f"  {status} {ex}\n"
            edit_message(chat_id, message_id, msg.strip(), get_main_menu())

        elif data == "chart":
            chart_path = generate_chart(user_id)
            if chart_path:
                send_photo(chat_id, chart_path, caption="📊 <b>Your Exercise Activity Over Time</b>")
            else:
                send_message(chat_id, "ℹ️ No exercise data found yet.", get_main_menu())

        elif data == "back":
            edit_message(chat_id, message_id, "🏋️ Choose a category:", get_main_menu())

        elif parts[0] == "cat":
            category = parts[1]
            edit_message(chat_id, message_id, f"📂 <b>{category}</b> Exercises:", get_exercise_menu(user_id, category))

        elif parts[0] == "done":
            category = parts[1]
            exercise = parts[2]
            today = datetime.now().strftime("%Y-%m-%d")

            user_progress.setdefault(user_id, {}).setdefault(category, {})
            current = user_progress[user_id][category].get(exercise, False)
            user_progress[user_id][category][exercise] = not current

            hist = user_progress[user_id].setdefault("history", {})
            hist.setdefault(today, 0)
            if not current:
                hist[today] += 1

            save_progress()
            edit_message(chat_id, message_id, f"📂 <b>{category}</b> Exercises Updated:", get_exercise_menu(user_id, category))

def run_bot():
    last_update_id = None
    print("🤖 Bot is now polling...")
    while True:
        try:
            params = {"timeout": 100, "offset": last_update_id + 1 if last_update_id else None}
            response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=120)
            data = response.json()
            print("🔍 Raw API response:", json.dumps(data, indent=2))

            if not data.get("ok"):
                print("⚠️ Telegram API error:", data)
                time.sleep(3)
                continue

            updates = data.get("result", [])
            for update in updates:
                last_update_id = update["update_id"]
                process_update(update)

        except Exception as e:
            print(f"⚠️ Exception: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
