from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from models.user import Player

# States for the conversation
ENTER_USERNAME = 1


class UserRegistrationHandler:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_registration_handler(self):
        """Returns a ConversationHandler for the registration process"""
        return ConversationHandler(
            entry_points=[CommandHandler("start", self.start_registration)],
            states={
                ENTER_USERNAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.handle_username
                    )
                ]
            },
            fallbacks=[],
        )

    async def start_registration(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start the registration process"""
        user = update.effective_user

        # Check if user is already registered
        existing_player = self.db_manager.get_player_stats(user.id)
        if existing_player:
            await update.message.reply_text(
                f"Welcome back {existing_player}! You're already registered with username: {existing_player['username']}"
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Welcome to FIEGSI Peladinhas! 🏆 \n\n"
            "To get started, please enter your preferred username.\n"
            "This will be used to identify you in games and statistics."
        )

        return ENTER_USERNAME

    async def handle_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the username input"""
        display_name = update.message.text.strip()
        telegram_user = update.effective_user

        # Validate username
        if len(display_name) < 3 or len(display_name) > 20:
            await update.message.reply_text(
                "Username must be between 3 and 20 characters.\n" "Please try again:"
            )
            return ENTER_USERNAME

        # Create our custom user object
        player = Player(telegram_user, display_name)
        result = self.db_manager.create_player(player)

        if result:
            await update.message.reply_text(
                f"Registration successful! Welcome {display_name}! 🎉\n\n"
                f"You can now join games in the group chat.\n"
            )
        else:
            await update.message.reply_text(
                "Sorry, there was an error during registration. Please try entering your username again:"
            )
            return ENTER_USERNAME

        return ConversationHandler.END
