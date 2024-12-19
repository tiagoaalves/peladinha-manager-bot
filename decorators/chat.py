from functools import wraps
from telegram import Update, Chat
from telegram.ext import ContextTypes


def private_chat_only(func):
    """Decorator to restrict commands to private chats only"""

    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type != Chat.PRIVATE:
            await update.message.reply_text(
                "This command only works in private chat. Please message me directly."
            )
            return
        return await func(self, update, context)

    return wrapper
