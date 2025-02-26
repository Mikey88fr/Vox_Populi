import os
import time
import schedule
import logging
from telegram import Bot, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import TelegramError
from dotenv import load_dotenv
import random
import json

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token and chat IDs
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MOD_CHAT_ID = os.getenv("MOD_CHAT_ID")

# Initialize the bot
bot = Bot(token=BOT_TOKEN)

# File to keep track of sent media files
SENT_FILES_LOG = "sent_files.json"

def load_sent_files():
    if os.path.exists(SENT_FILES_LOG):
        with open(SENT_FILES_LOG, "r") as file:
            return json.load(file)
    return []

def save_sent_file(file_path):
    sent_files = load_sent_files()
    sent_files.append(file_path)
    with open(SENT_FILES_LOG, "w") as file:
        json.dump(sent_files, file)

def send_media(file_path):
    try:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            with open(file_path, 'rb') as file:
                bot.send_photo(chat_id=CHAT_ID, photo=file)
                logger.info(f"Photo sent: {file_path}")
        elif file_path.lower().endswith('.mp4'):
            with open(file_path, 'rb') as file:
                bot.send_video(chat_id=CHAT_ID, video=file)
                logger.info(f"Video sent: {file_path}")
        else:
            logger.error(f"Unsupported file type: {file_path}")
        save_sent_file(file_path)
    except TelegramError as e:
        logger.error(f"Failed to send media: {e}")

def get_random_file_from_folder(folder_path):
    sent_files = load_sent_files()
    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file)) and os.path.join(folder_path, file) not in sent_files]
    if not files:
        logger.error(f"No new files found in folder: {folder_path}")
        return None
    return random.choice(files)

def job(folder_path):
    file_path = get_random_file_from_folder(folder_path)
    if file_path:
        send_media(file_path)

def set_schedule():
    # Schedule jobs for different days
    schedule.every().monday.at("10:00").do(job, folder_path="path/to/your/video/folder")
    schedule.every().friday.at("10:00").do(job, folder_path="path/to/your/image/folder")

def run_scheduler():
    set_schedule()
    while True:
        schedule.run_pending()
        time.sleep(1)

def start(update: Update, context: CallbackContext):
    buttons = [
        [KeyboardButton("Send Media for Review")],
        [KeyboardButton("Feedback")]
    ]
    context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the bot! Choose an option:", 
                             reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "Send Media for Review":
        context.bot.send_message(chat_id=update.effective_chat.id, text="Please send the media file you want to be reviewed.")
    elif text == "Feedback":
        context.bot.send_message(chat_id=update.effective_chat.id, text="Please send your feedback.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid option. Please choose from the menu.")

def handle_media(update: Update, context: CallbackContext):
    if update.message.photo:
        file = update.message.photo[-1].get_file()
        file_path = file.file_path
        file.download("received_media.jpg")
        context.bot.send_photo(chat_id=MOD_CHAT_ID, photo=open("received_media.jpg", "rb"), caption="Media for review")
        context.bot.send_message(chat_id=update.effective_chat.id, text="Media file has been sent for review.")
    elif update.message.video:
        file = update.message.video.get_file()
        file_path = file.file_path
        file.download("received_media.mp4")
        context.bot.send_video(chat_id=MOD_CHAT_ID, video=open("received_media.mp4", "rb"), caption="Media for review")
        context.bot.send_message(chat_id=update.effective_chat.id, text="Media file has been sent for review.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Unsupported media type.")

def handle_feedback(update: Update, context: CallbackContext):
    feedback = update.message.text
    context.bot.send_message(chat_id=MOD_CHAT_ID, text=f"Feedback received: {feedback}")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Your feedback has been sent.")

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Handler for the /start command
    dispatcher.add_handler(CommandHandler("start", start))

    # Handler for text messages
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Handler for media files
    dispatcher.add_handler(MessageHandler(Filters.photo | Filters.video, handle_media))

    # Handler for feedback (assuming feedback is sent as text after choosing the Feedback option)
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.reply, handle_feedback))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    # Run the scheduler in a separate thread
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
    
    # Run the main bot
    main()
