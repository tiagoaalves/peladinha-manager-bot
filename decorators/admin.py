import os
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes


def admin_only(func):
    """Decorator to restrict commands to admins listed in ADMIN_IDS env variable"""

    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        admin_ids = [
            int(id_str) for id_str in admin_ids_str.split(",") if id_str.strip()
        ]

        if update.effective_user.id not in admin_ids:
            await update.message.reply_text("This command is only available to admins.")
            return
        return await func(self, update, context)

    return wrapper
