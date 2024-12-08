from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TelegramError

class GameHandlers:
    def __init__(self, game_manager):
        self.game_manager = game_manager

    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        self.game_manager.create_game(chat_id)
        await self.game_manager.update_join_message(chat_id, context)

    async def list_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        if not game:
            await update.message.reply_text("No active game!")
            return
            
        if game.game_state != "WAITING":
            await update.message.reply_text("Game already started!")
            return
            
        await self.game_manager.update_join_message(chat_id, context)

    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        if not game:
            await update.message.reply_text("No active game!")
            return
            
        if game.game_state != "IN_GAME":
            await update.message.reply_text("No active game to end!")
            return
        
        game.game_state = "SCORING"
        await update.message.reply_text(
            "Please enter the final score using the format: /score TeamA TeamB\n"
            "Example: /score 3 2"
        )

    async def handle_score(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        if not game:
            await update.message.reply_text("No active game!")
            return
            
        if game.game_state != "SCORING":
            await update.message.reply_text("No game waiting for score!")
            return
        
        try:
            if not context.args or len(context.args) != 2:
                raise ValueError
                
            score_a, score_b = map(int, context.args)
            if score_a < 0 or score_b < 0:
                raise ValueError
                
        except (ValueError, IndexError):
            await update.message.reply_text(
                "Invalid score format.\n"
                "Please use: /score TeamA TeamB\n"
                "Example: /score 3 2"
            )
            return

        game.score = {"Team A": score_a, "Team B": score_b}
        
        # Announce the final score before MVP voting
        await update.message.reply_text(
            f"Final Score:\n"
            f"Team A: {score_a}\n"
            f"Team B: {score_b}\n"
        )
        
        # Start MVP voting
        await self.start_mvp_voting(update, context)

    async def start_mvp_voting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        if not game:
            await update.message.reply_text("No active game!")
            return
        
        # Initialize voting state
        game.game_state = "VOTING"
        game.mvp_votes = {}
        
        # Create voting keyboard
        keyboard = []
        for player in game.players:
            player_name = (f"{player.first_name} {player.last_name}" 
                        if player.last_name 
                        else player.first_name)
            button = InlineKeyboardButton(
                player_name,
                callback_data=f"vote_{player.id}"
            )
            keyboard.append([button])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Inform group that voting is starting
        await update.message.reply_text(
            "Starting MVP voting! Check your private messages to cast your vote."
        )
        
        # Send private messages
        failed_players = []
        for player in game.players:
            try:
                await context.bot.send_message(
                    chat_id=player.id,
                    text=(
                        f"🏆 MVP Vote for game in {update.effective_chat.title} 🏆\n\n"
                        f"Final Score:\n"
                        f"Team A: {game.score['Team A']}\n"
                        f"Team B: {game.score['Team B']}\n\n"
                        "Choose the most valuable player:"
                    ),
                    reply_markup=reply_markup
                )
            except (BadRequest, TelegramError) as e:
                # Catch all possible Telegram API errors
                failed_players.append(player.first_name)
                continue
        
        # If any players couldn't receive messages, inform the group
        if failed_players:
            await update.message.reply_text(
                f"⚠️ Couldn't send voting message to: {', '.join(failed_players)}\n"
                "These players need to start a private chat with me first using /start"
            )

    async def test_fill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        if not game:
            await update.message.reply_text("Start a game first with /start_game")
            return

        # Create dummy users (simulating telegram User objects)
        class DummyUser:
            def __init__(self, id, first_name, last_name=None):
                self.id = id
                self.first_name = first_name
                self.last_name = last_name

        # Add dummy players until max_players is reached
        dummy_players = [
            DummyUser(1, "Test1"),
            DummyUser(2, "Test2"),
            DummyUser(3, "Test3"),
            DummyUser(4, "Test4"),
            DummyUser(5, "Test5"),
            DummyUser(6, "Test6"),
            DummyUser(7, "Test7"),
            DummyUser(8, "Test8"),
            DummyUser(9, "Test9"),
        ]

        game.players = dummy_players
        await self.game_manager.update_join_message(chat_id, context)
