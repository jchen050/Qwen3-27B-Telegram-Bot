import os
import httpx
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.memory import MemorySaver
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_ID = os.environ["TELEGRAM_USER_ID"]
LLAMA_URL = "http://llama-server:8080/v1/chat/completions"

chat_llm = ChatOpenAI(
    base_url="http://llama-server:8080/v1",
    api_key="not-needed",
    model="qwen",
    temperature=0.7,
    max_tokens=2048,
)

chain = ChatPromptTemplate.from_messages([("user", "{input}")]) | chat_llm | StrOutputParser()


def call_model(state: MessagesState):
    return {"messages": [chat_llm.invoke(state["messages"])]}


graph_builder = StateGraph(MessagesState)
graph_builder.add_node("model", call_model)
graph_builder.add_edge(START, "model")
graph = graph_builder.compile(checkpointer=MemorySaver())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if TELEGRAM_ID != str(user_id):
        logging.exception(f"Received message from incorrect user id {user_id}")
        return

    user_text = update.message.text
    mode = "raw"
    logging.debug(f"Received: {user_text}")
    if user_text.startswith("//chain "):
        mode, user_text = "chain", user_text[len("//chain "):]
    elif user_text.startswith("//graph "):
        mode, user_text = "graph", user_text[len("//graph "):]

    logging.debug(f"Received telegram message (mode={mode}): {user_text}")
    await update.message.reply_text("Thinking...")

    try:
        if mode == "chain":
            logging.info("Attempting to use langchain")
            reply = await chain.ainvoke({"input": user_text})
        elif mode == "graph":
            logging.info("Attempting to use langgraph")
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_text)]},
                config={"configurable": {"thread_id": str(update.effective_chat.id)}},
            )
            reply = result["messages"][-1].content
        else:
            logging.info("Attempting to use raw model inference")
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
