from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from models.player import Player
from decorators.chat import private_chat_only

# States for the conversation
ENTER_USERNAME = 1


class UserRegistrationHandler:
    def __init__(self, player_db_manager):
        self.player_db_manager = player_db_manager

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

    @private_chat_only
    async def start_registration(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start the registration process"""
        user = update.effective_user

        # Check if user is already registered
        existing_player = self.player_db_manager.get_player(user.id)
        if existing_player:
            await update.message.reply_text(
                f"Welcome back {existing_player.display_name}! You're already registered!"
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Welcome to FIEGSI Peladinhas! 🏆 \n\n"
            "To get started, please enter your preferred username.\n"
            "Try to use something that easily identifies you in the group chat."
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
        result = self.player_db_manager.create_player(player)

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
