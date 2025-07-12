
import os
import json
import time
import requests

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

def save_progress():
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

def get_main_menu():
    return {
        "inline_keyboard": [
            [{"text": "💪 Bicep", "callback_data": "cat|Bicep"}],
            [{"text": "🏋️ Tricep", "callback_data": "cat|Tricep"}],
            [{"text": "🔥 Chest", "callback_data": "cat|Chest"}],
            [{"text": "🌀 Back", "callback_data": "cat|Back"}],
            [{"text": "🏹 Shoulder", "callback_data": "cat|Shoulder"}],
            [{"text": "📋 View Status", "callback_data": "status"}],
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

def process_update(update):
    print("📩 Received update:", json.dumps(update, indent=2))  # Debug print
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip().lower()
        if text == "/start":
            welcome_msg = (
                "🏋️‍♂️ <b>Welcome to Ahmad's Workout Bot!</b> 💥\n\n"
                "Track your daily exercises, mark them as done ✅, and stay fit! 💪\n"
                "Choose a category below to begin 👇"
            )
            send_message(chat_id, welcome_msg, get_main_menu())
        else:
            send_message(chat_id, "👋 Type /start to begin using Ahmad's Workout Bot.")

    elif "callback_query" in update:
        query = update["callback_query"]
        data = query["data"]
        chat_id = query["message"]["chat"]["id"]
        user_id = str(query["from"]["id"])

        parts = data.split("|")

        if data == "reset":
            user_progress[user_id] = {}
            save_progress()
            send_message(chat_id, "🔄 <b>Your progress has been reset.</b>", get_main_menu())

        elif data == "status":
            msg = "📊 <b>Your Workout Progress:</b>\n"
            for cat, exercises in exercise_data.items():
                msg += f"\n<b>{cat}</b>\n"
                for ex in exercises:
                    done = user_progress.get(user_id, {}).get(cat, {}).get(ex, False)
                    status = "✅" if done else "❌"
                    msg += f"{status} {ex}\n"
            send_message(chat_id, msg, get_main_menu())

        elif data == "back":
            send_message(chat_id, "⬅️ Returning to main menu...", get_main_menu())

        elif parts[0] == "cat":
            category = parts[1]
            send_message(chat_id, f"📂 <b>{category}</b> Exercises:", get_exercise_menu(user_id, category))

        elif parts[0] == "done":
            category = parts[1]
            exercise = parts[2]

            user_progress.setdefault(user_id, {}).setdefault(category, {})
            current = user_progress[user_id][category].get(exercise, False)
            user_progress[user_id][category][exercise] = not current
            save_progress()
            send_message(chat_id, f"🔁 <b>{exercise}</b> marked as {'done ✅' if not current else 'not done ❌'}", get_exercise_menu(user_id, category))

def run_bot():
    last_update_id = None
    print("🤖 Ahmad's Workout Bot is now polling...")
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
