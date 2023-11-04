# HealthServe Virtual Assistant

The HealthServe Virtual Assistant, Jessie, is a Python-based Telegram bot designed to assist volunteers interested in HealthServe's services for the migrant community in Singapore. This virtual assistant can answer questions, provide information, and help users navigate the volunteering onboarding process.

## Features

- Multilingual Support: The bot can interact with users in multiple languages, including English, Bengali, Tamil, and Chinese.
- Question Answering: It can provide answers to questions related to HealthServe's services and mission.
- Interactive Topics: Users can choose from predefined topics to receive information and guidance.
- Audio Support: The bot can transcribe voice messages and provide responses.
- Language Selection: Users can set their preferred language for interaction with the bot.

## Prerequisites

Before running the bot, you need to set up the following:

- A Telegram Bot Token: You should have a Telegram bot token, which you can obtain by [creating a new bot with the BotFather](https://core.telegram.org/bots#botfather).
- OpenAI API Key: You need an OpenAI API key for the language model used in the bot. You can get one by signing up with OpenAI.
- Python Environment: Make sure you have a Python environment set up. You can use a tool like `virtualenv` to manage dependencies.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/healthserve-virtual-assistant.git
    cd healthserve-virtual-assistant
    ```

2. Create a virtual environment (optional but recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use: venv\Scripts\activate
    ```

3. Install project dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Configure your environment variables. Create a `.env` file in the project root and set your Telegram bot token and OpenAI API key:

    ```plaintext
        TELEGRAM_BOT_TOKEN=your_telegram_bot_token
        OPENAI_API_KEY=your_openai_api_key
        LANGSMITH_API_KEY=your_langsmith_api_key
    ```

5. Run the bot:

    ```bash
    python main.py
    ```

## Usage

- Start a conversation with the bot on Telegram by searching for it or using your bot's invite link.
- Type `/start` to begin the conversation or use other available commands like `/help` and `/setlanguage` to explore the features.

## Customization

You can customize the predefined topics and responses by editing the `topics` dictionary in the `main.py` file. You can also adjust language-specific response templates and the document directory in the `model.py` file.

## Acknowledgments

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [OpenAI GPT-3](https://beta.openai.com/signup/)
- [Langchain](https://github.com/smileychris/langchain)

