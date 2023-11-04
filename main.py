
import os 
import openai
import telegram
import requests
import tempfile 

from dotenv import load_dotenv 
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler, ContextTypes, CallbackContext
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from utils import is_group_chat, get_thread_id, message_text, wrap_with_indicator, split_into_chunks, edit_message_with_retry, get_stream_cutoff_values, is_allowed, get_remaining_budget, is_admin, is_within_budget, get_reply_to_message_id, add_chat_request_to_usage_tracker, error_handler, is_direct_result, handle_direct_result, cleanup_intermediate_files 
import json
import model 
import logging
import telebot
import random
from pydub import AudioSegment
from ftlangdetect import detect

language_descriptions = {
    "english": {
        "description": "Set the language to English",
    },
    "chinese": {
        "description": "设置语言为中文",
    },
    "tamil": {
        "description": "மொழியை தமிழில் அமைக்கவும்",
    },
    "bengali": {
        "description": "ভাষা বাঙালি করুন",
    },
}

# Define predefined topics and related questions
topics = {
    "About Us 🇸🇬": ["What is HealthServe's mission?", "What are HealthServe's values?", "What are some recent achievements or milestones of HealthServe?", "Who are the key individuals behind HealthServe's success?", "Can you explain HealthServe's role in the migrant community in Singapore in more detail?"],
    "Services Offered 🛠️": ["What services does HealthServe offer?", "Can you elaborate on the medical services provided by HealthServe?", "Tell me about the mental health and counseling services provided by HealthServe.", "What types of services does HealthServe provide to migrant workers?"],
    "Best Practices 🙌": ["What are the best practices for volunteers?", "How can I be an effective volunteer?", "Are there any cultural sensitivity best practices that volunteers should follow?", "How can volunteers contribute to building a supportive community for migrants?", "How can one be more culturally aware when interacting with migrant workers?", "What are some suggested ways to interact and connect with migrant workers more effectively?", "How should one interact with a migrant worker appropriately and respectfully?"],
    "Registration 📋": ["How can I register as a volunteer?", "What is the volunteer registration process?", "Are there any specific language requirements for volunteering with HealthServe?"]
}

# Function to generate a random question for a selected topic
import random
def generate_question(topic):
    return random.choice(topics[topic])


load_dotenv() 
 
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAIKEY = os.getenv("OPENAI_API_KEY")

print(TOKEN) 
bot = telebot.TeleBot(TOKEN)

# Load translations from translations.json
with open('translations.json', 'r', encoding='utf-8') as translations_file:
    translations = json.load(translations_file)

#botcommand
commands = [
    BotCommand(command="start", description="Start the conversation"),
    BotCommand(command="reset", description="Reset the conversation"),
    BotCommand(command="help", description="Show this help message"),
    BotCommand(command="setlanguage", description="Set the language of the bot"),
]
 
def get_command_descriptions(language):
    if language == "chinese":
        return {
            "start_description": "开始对话",
            "help_description": "显示此帮助消息",
            "reset_description": "重置对话",
            "setlanguage_description": "设置语言",
        }
    elif language == "tamil":
        return {
            "start_description": "உரையாடலைத் துவங்கு",
            "help_description": "இந்த உதவி செய்தியைக் காட்டு",
            "reset_description": "உரையாடலை மீளமைக்க",
            "setlanguage_description": "மொழியை அமை",
        }
    elif language == "bengali":
        return {
            "start_description": "কথা বলা শুরু করুন",
            "help_description": "এই সাহায্য বার্তাটি দেখুন",
            "reset_description": "কথা বলার সাথে পুনরারম্ভ করুন",
            "setlanguage_description": "ভাষা নির্ধারণ করুন",
        }
    else:  # Default to English
        return {
            "start_description": "Start the conversation",
            "help_description": "Show this help message",
            "reset_description": "Reset the conversation",
            "setlanguage_description": "Set language",
        }


async def start(update, context):
    
    user_data = context.user_data

    # Check if the user has already seen the introduction
    if 'introduction_seen' in user_data:
        # User has already seen the introduction, so just provide a welcome message
        await update.message.reply_text("Welcome back! How can I assist you today?")
        # Generate inline keyboard markup with the available topics in a 2x2 grid
        available_topics = list(topics.keys())
        keyboard = []
        row = []  # Initialize an empty row
        for i, topic in enumerate(available_topics):
            row.append(InlineKeyboardButton(topic, callback_data=f"select_topic_{topic}"))
            if (i + 1) % 2 == 0:
                # Add the row to the keyboard when it has two buttons
                keyboard.append(row)
                row = []  # Start a new row

        if row:
            # Add any remaining buttons if the total count is not a multiple of 2
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the inline keyboard to the user after the introduction message
        await update.message.reply_text("Choose a topic:", reply_markup=reply_markup)
    else:
        # User is seeing the introduction for the first time
        introduction_message = (
            "Welcome!  I'm Jessie, your dedicated virtual assistant for HealthServe's volunteer services.\n\n"
            "Ask me anything in English, বাংলা, தமிழ், or 中文, through text or audio messages!\n\n"
            "Not sure where to start? Choose from our suggested topics, and I'll guide you through the information you're looking for.\n\n"
        )
        await update.message.reply_text(introduction_message)

        # Mark that the user has seen the introduction to avoid showing it again
        user_data['introduction_seen'] = True

        # Generate inline keyboard markup with the available topics in a 2x2 grid
        available_topics = list(topics.keys())
        keyboard = []
        row = []  # Initialize an empty row
        for i, topic in enumerate(available_topics):
            row.append(InlineKeyboardButton(topic, callback_data=f"select_topic_{topic}"))
            if (i + 1) % 2 == 0:
                # Add the row to the keyboard when it has two buttons
                keyboard.append(row)
                row = []  # Start a new row

        if row:
            # Add any remaining buttons if the total count is not a multiple of 2
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the inline keyboard to the user after the introduction message
        await update.message.reply_text("Choose a topic:", reply_markup=reply_markup)
        


async def send_text(update, context):
    # Get the user's message
    
    user_message = update.message.text

    # Detect the language of the user's message
    detected_language = detect_language(user_message)
    print(detected_language)

    #simulate bot typing
    bot.send_chat_action(chat_id=update.effective_message.chat_id, action=telegram.constants.ChatAction.TYPING)

    response = model.getResponse(user_message, detected_language, context)

    print(f"User sent a text message: {update.message.text}")  # Print the user's text message

    # Get the available topics
    available_topics = list(topics.keys())

    # Generate inline keyboard markup with the available topics in a 2x2 grid
    keyboard = []
    row = []  # Initialize an empty row
    for i, topic in enumerate(available_topics):
        row.append(InlineKeyboardButton(topic, callback_data=f"select_topic_{topic}"))
        if (i + 1) % 2 == 0:
            # Add the row to the keyboard when it has two buttons
            keyboard.append(row)
            row = []  # Start a new row

    if row:
        # Add any remaining buttons if the total count is not a multiple of 2
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    print(f"Bot response to user: {response}")  # Print the bot's response to the user

    await update.message.reply_text(response, reply_markup=reply_markup)



async def reset(update, context):
    """Reset the conversation"""
    context.user_data.clear()  # Clear user-specific data
    await update.message.reply_text("The conversation has been reset.")

async def help_command(update, context):
    user_id = update.message.from_user.id
    user_data = context.user_data

    # Get the user's selected language
    language = user_data.get('language', 'english')

    descriptions = get_command_descriptions(language)

    help_text = "Available commands:\n\n"
    help_text += f"/start - {descriptions['start_description']}\n"
    help_text += f"/reset - {descriptions['reset_description']}\n"
    help_text += f"/help - {descriptions['help_description']}\n"
    help_text += f"/help - {descriptions['setlanguage_description']}\n"


    await update.message.reply_text(help_text)

async def set_language(update, context):
    user_id = update.message.from_user.id
    user_data = context.user_data

    if 'language' in user_data:
        current_language = user_data['language']
    else:
        current_language = 'english'  # Default to English

    buttons = [
        [
            InlineKeyboardButton(
                text=f"English 🇺🇸 - {language_descriptions['english']['description']}",
                callback_data="set_language_english"
            ),
            InlineKeyboardButton(
                text=f"中文 🇨🇳 - {language_descriptions['chinese']['description']}",
                callback_data="set_language_chinese"
            ),
        
            InlineKeyboardButton(
                text=f"தமிழ் 🇮🇳 - {language_descriptions['tamil']['description']}",
                callback_data="set_language_tamil"
            ),
            InlineKeyboardButton(
                text=f"বাঙালি 🇧🇩 - {language_descriptions['bengali']['description']}",
                callback_data="set_language_bengali"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    message_text = (
        f"Current language: {language_descriptions[current_language]['description']}\n"
        "Select your preferred language:"
    )

    await update.message.reply_text(message_text, reply_markup=reply_markup)


async def set_language_callback(update, context):
    query = update.callback_query
    user_data = context.user_data

    language_code = query.data.replace("set_language_","")

    if language_code in language_descriptions:
        user_data['language'] = language_code

        # Update bot commands and descriptions
        descriptions = get_command_descriptions(language_code)
        updated_commands = [
            BotCommand(command="start", description=descriptions["start_description"]),
            BotCommand(command="reset", description=descriptions["reset_description"]),
            BotCommand(command="help", description=descriptions["help_description"]),
            BotCommand(command="setlanguage", description=descriptions["setlanguage_description"]),
        ]
        await query.message.edit_text(f"{language_descriptions[language_code]['description']}")
        
        await context.bot.set_my_commands(updated_commands)  # Update bot commands

    else:
        await query.message.edit_text("Invalid language selection")

    await query.answer()  # Close the inline keyboard


def transcribe_audio(audio_path):
    try:
        # Use OpenAI's Whisper API to transcribe the audio
        audio_file = open(audio_path, 'rb')
        print(audio_file)
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

        transcription = transcript['text']
        return transcription

    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None
    
async def transcribe(filename):
        """
        Transcribes the audio file using the Whisper model.
        """
        try:
            with open(filename, "rb") as audio:
                result = await openai.Audio.atranscribe("whisper-1", audio)
                return result.text
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

async def handle_audio(update: Update, context: CallbackContext):
    #simulate bot typing
    bot.send_chat_action(chat_id=update.effective_message.chat_id, action=telegram.constants.ChatAction.TYPING)

    file_info = update.message.voice.file_id
    downloaded_file = bot.download_file(bot.get_file(file_info).file_path)

    # Save the Ogg file to a local directory
    ogg_filename = "audio.ogg"
    mp3_filename = f"{ogg_filename}.mp3"

    with open(ogg_filename, "wb") as audio_file:
        audio_file.write(downloaded_file)

    # Convert the Ogg file to MP3
    audio_track = AudioSegment.from_file(ogg_filename)
    audio_track.export(mp3_filename, format="mp3")
    logging.info(f'New transcribe request received from user {update.message.from_user.name} '
                 f'(id: {update.message.from_user.id})')

    # Clean up by removing the temporary Ogg file
    os.remove(ogg_filename)

    # Open the MP3 file and pass it to the transcribe function
    openai.api_key = OPENAIKEY 
    with open(mp3_filename, 'rb') as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        print(transcript)

    # Clean up by removing the temporary MP3 file
    os.remove(mp3_filename)

    # Extract the transcript text from the JSON object
    transcript_text = transcript.get("text", "")

    #language
    detected_language = detect_language(transcript_text)
    print(detected_language)


    # Now you can use the 'transcript' variable for further processing
    response = model.getResponse(str(transcript), detected_language, context)
    response_text = (f"_Transcript_:\n'{transcript_text}'\n\n_Answer_:\n{response}")
    await update.message.reply_text(response_text, parse_mode=constants.ParseMode.MARKDOWN)


async def downloader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Download file
    new_file = await update.message.effective_attachment[-1].get_file()
    file = await new_file.download_to_drive()



async def handle_selected_topic(update: Update, context: CallbackContext):

    #simulate bot typing
    bot.send_chat_action(chat_id=update.effective_message.chat_id, action=telegram.constants.ChatAction.TYPING)

    query = update.callback_query
    selected_topic = query.data.replace("select_topic_", "")

    print(f"User selected topic: {selected_topic}")  # Print the selected topic

    # Retrieve the related questions for the selected topic from the topics dictionary
    related_questions = topics.get(selected_topic, [])

    if related_questions:
        # Select a related question randomly from the list
        suggested_question = random.choice(related_questions)

        print(f"Suggested question: {suggested_question}")  # Print the suggested question

        # Send the suggested question to the user
        suggested_question_text = (f"_Suggested question_:\n\n'{suggested_question}'")
        await query.message.reply_text(suggested_question_text, parse_mode=constants.ParseMode.MARKDOWN)

        # Retrieve the model's response for the suggested question
        detected_language = detect_language(suggested_question_text)
        print(detected_language)
        response = model.getResponse(suggested_question,detected_language, context)

        print(f"Bot response to suggested question: {response}")  # Print the bot's response

        # Generate inline keyboard markup with the available topics in a 2x2 grid
        available_topics = list(topics.keys())
        keyboard = []
        row = []  # Initialize an empty row
        for i, topic in enumerate(available_topics):
            row.append(InlineKeyboardButton(topic, callback_data=f"select_topic_{topic}"))
            if (i + 1) % 2 == 0:
                # Add the row to the keyboard when it has two buttons
                keyboard.append(row)
                row = []  # Start a new row

        if row:
            # Add any remaining buttons if the total count is not a multiple of 2
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the response to the user with the inline keyboard
        await query.message.reply_text(response, reply_markup=reply_markup)
    else:
        response = f"No related questions found for the selected topic: {selected_topic}"
        await query.message.reply_text(response)

def detect_language(text):
    try:
        result = detect(text)
        language = result['lang'] if 'lang' in result else "en"  # Default to English if language detection fails
        print(language)
        return language
    except Exception:
        return "en"  # Default to English if language detection fails


async def post_init(application: Application) -> None:
        """
        Post initialization hook for the bot.
        """
        await application.bot.set_my_commands(commands)

def main(): 
    """Runs the Telegram Bot""" 
    print('Loading configuration...') 
    print('Successfully loaded! Starting bot...') 
 
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build() 
 
    application.add_handler(CommandHandler('start', start)) 
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_text)) 
    application.add_handler(CommandHandler('reset', reset))
    application.add_handler(CommandHandler('help', help_command))

    # Add the setlanguage command
    application.add_handler(CommandHandler('setlanguage', set_language))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern="^set_language_"))

    application.add_handler(MessageHandler(filters.VOICE, handle_audio))

    # Add the CallbackQueryHandler to handle inline keyboard interactions
    application.add_handler(CallbackQueryHandler(handle_selected_topic, pattern="^select_topic_"))

    application.add_error_handler(error_handler)

    application.run_polling()
 
if __name__ == '__main__': 
    main()



