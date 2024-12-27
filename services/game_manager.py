from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database.game import GameDBManager
from models.game import SoccerGame


class GameManager:
    def __init__(self, game_db_manager: GameDBManager):
        self.game_db_manager = game_db_manager
        self.games = self.game_db_manager.load_active_games()

    def create_game(self, chat_id) -> SoccerGame:
        game = SoccerGame()
        self.games[chat_id] = game
        self.game_db_manager.save_active_game_players(chat_id, game.players)
        return game

    def get_game(self, chat_id) -> SoccerGame:
        return self.games.get(chat_id)

    def remove_game(self, chat_id):
        if chat_id in self.games:
            self.game_db_manager.remove_active_game(chat_id)
            del self.games[chat_id]

    async def update_join_message(
        self, chat_id: int, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        game = self.get_game(chat_id)

        if game.join_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=game.join_message_id
                )
            except:
                pass

        players_text = "Players joined:\n\n"
        for i, player in enumerate(game.players, 1):
            players_text += f"{i}. {player.display_name}\n"

        players_text += f"\n{len(game.players)}/{game.max_players} players"

        keyboard = [
            [
                InlineKeyboardButton("Join Game ⚽", callback_data="join"),
                InlineKeyboardButton("Leave Game 🚪", callback_data="leave"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = await context.bot.send_message(
            chat_id=chat_id,
            text=players_text,
            reply_markup=reply_markup if len(game.players) < game.max_players else None,
        )
        game.join_message_id = message.message_id

    async def update_teams_message(
        self, chat_id: int, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        game = self.get_game(chat_id)
        if not game:
            return

        if game.teams_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=game.teams_message_id
                )
            except:
                pass

        # Format teams message
        teams_text = "Current Teams:\n\n"

        # Add team colors only after color selection
        if game.game_state == "IN_GAME":
            team_a_color = "Colored 🔵" if game.team_b_white else "White ⚪"
            team_b_color = "White ⚪" if game.team_b_white else "Colored 🔵"
        else:
            team_a_color = team_b_color = ""

        # Team A
        teams_text += f"Team A (Captain: {game.captains[0].display_name}){' - ' + team_a_color if team_a_color else ''}:\n"
        team_a_players = [game.captains[0]] + game.teams["Team A"]
        teams_text += "\n".join(f"• {p.display_name}" for p in team_a_players)

        # Team B
        teams_text += f"\n\nTeam B (Captain: {game.captains[1].display_name}){' - ' + team_b_color if team_b_color else ''}:\n"
        team_b_players = [game.captains[1]] + game.teams["Team B"]
        teams_text += "\n".join(f"• {p.display_name}" for p in team_b_players)

        # Add selection prompt if in selection state
        if game.game_state == "SELECTION":
            teams_text += f"\n\n{game.current_selector.display_name}'s turn to select"
            remaining_players = [
                p
                for p in game.players
                if p not in game.captains
                and p not in game.teams["Team A"]
                and p not in game.teams["Team B"]
            ]
            keyboard = [
                [InlineKeyboardButton(p.display_name, callback_data=f"select_{p.id}")]
                for p in remaining_players
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None

        message = await context.bot.send_message(
            chat_id=chat_id, text=teams_text, reply_markup=reply_markup
        )
        game.teams_message_id = message.message_id
