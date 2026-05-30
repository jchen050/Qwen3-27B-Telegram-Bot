import os
import httpx
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_ID = os.environ["TELEGRAM_USER_ID"]
LLAMA_URL = "http://llama-server:8080/v1/chat/completions"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if TELEGRAM_ID != str(user_id):
        logging.exception(f"Received message from incorrect user id {user_id}")
        return
    
    user_text = update.message.text
    logging.debug(f"Received telegram message of {user_text}")
    await update.message.reply_text("Thinking...")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(LLAMA_URL, json={
                "model": "qwen",
                "messages": [{"role": "user", "content": user_text}],
                "temperature": 0.7,
                "max_tokens": 2048,
            })
            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.exception("Inference failed")
        reply = f"Error contacting model: {e}"

    await update.message.reply_text(reply)

# async def retrieve_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     user_id = update.effective_user.id
#     logging.info(f"Received user id: {user_id}")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, retrieve_user_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()