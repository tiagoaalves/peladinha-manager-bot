from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from models.game import SoccerGame

class GameManager:
    def __init__(self):
        self.games = {}

    def create_game(self, chat_id):
        self.games[chat_id] = SoccerGame()
        return self.games[chat_id]

    def get_game(self, chat_id):
        return self.games.get(chat_id)

    def remove_game(self, chat_id):
        if chat_id in self.games:
            del self.games[chat_id]

    async def update_join_message(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        game = self.get_game(chat_id)

        if hasattr(game, 'join_message_id'):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=game.join_message_id)
            except:
                pass

        players_text = "Players joined:\n\n"
        for i, player in enumerate(game.players, 1):
            players_text += f"{i}. {player.first_name} {player.last_name}\n"

        players_text += f"\n{len(game.players)}/{game.max_players} players"

        keyboard = [
            [
                InlineKeyboardButton("Join Game ⚽", callback_data="join"),
                InlineKeyboardButton("Leave Game 🚪", callback_data="leave")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = await context.bot.send_message(
            chat_id=chat_id,
            text=players_text,
            reply_markup=reply_markup if len(game.players) < game.max_players else None
        )
        game.join_message_id = message.message_id
