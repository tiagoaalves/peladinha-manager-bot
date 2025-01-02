from models.player import Player
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TelegramError
from decorators.admin import admin_only


class GameHandlers:
    def __init__(
        self, game_manager, player_db_manager, game_db_manager, elo_db_manager
    ):
        self.game_manager = game_manager
        self.player_db_manager = player_db_manager
        self.game_db_manager = game_db_manager
        self.elo_db_manager = elo_db_manager

    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        # Check if there's an active game
        if chat_id in self.game_manager.games:
            await context.bot.send_message(
                chat_id=chat_id,
                text="A game is already active. End it first to start a new one.",
            )
            return

        # If no active game exists, create a new one
        self.game_manager.create_game(chat_id)
        await self.game_manager.update_join_message(chat_id, context)

    async def list_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)

        if not game:
            await update.message.reply_text("No active game!")
            return

        if game.game_state != "WAITING":
            await update.message.reply_text("Teams already made!")
            return

        await self.game_manager.update_join_message(chat_id, context)

    @admin_only
    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)

        if not game:
            await update.message.reply_text("No active game!")
            return

        if game.game_state != "IN_GAME":
            await update.message.reply_text("No active game to end!")
            return

        try:
            # Handle player records
            telegram_players = [p for p in game.players if p.id > 0]

            team_a_external_count = len([p for p in game.teams["Team A"] if p.id < 0])
            team_b_external_count = len([p for p in game.teams["Team B"] if p.id < 0])

            # Prepare player data
            players_data = []
            for player in telegram_players:
                team = "A" if player in game.teams["Team A"] else "B"
                was_captain = player in game.captains

                player_data = {
                    "id": player.id,
                    "team": team,
                    "was_captain": was_captain,
                    "was_mvp": False,
                }
                players_data.append(player_data)

            game.db_game_id = self.game_db_manager.save_game(
                chat_id=chat_id,
                score_team_a=None,
                score_team_b=None,
                players_data=players_data,
                team_a_external_count=team_a_external_count,
                team_b_external_count=team_b_external_count,
            )

        except Exception as e:
            print(f"Database error during end_game: {e}")
            import traceback

            traceback.print_exc()

        game.game_state = "SCORING"
        await update.message.reply_text(
            "Please enter the final score using the format: /score TeamA TeamB\n"
            "Example: /score 3 2"
        )

    @admin_only
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

        # Update game object
        game.score = {"Team A": score_a, "Team B": score_b}

        # Update game record in database
        try:
            if hasattr(game, "db_game_id"):
                self.game_db_manager.update_game_score(
                    game.db_game_id, score_a, score_b
                )
                # Process ELO ratings after updating score
                self.elo_db_manager.process_game_ratings(game.db_game_id)
            else:
                print("Warning: No db_game_id found for game")

        except Exception as e:
            print(f"Error updating game score: {e}")

        # Announce the final score
        await update.message.reply_text(
            f"Final Score:\n" f"Team A: {score_a}\n" f"Team B: {score_b}"
        )

        # Start MVP voting
        await self.start_mvp_voting(update, context)

    async def start_mvp_voting(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)

        if not game:
            await update.message.reply_text("No active game!")
            return

        # Initialize voting state
        game.game_state = "VOTING"
        game.mvp_votes = {}
        game.voting_players = []  # Track players who can vote

        # Create voting keyboard
        keyboard = []
        for player in game.players:
            player_name = f"{player.display_name}"
            button = InlineKeyboardButton(
                player_name, callback_data=f"vote_{player.id}"
            )
            keyboard.append([button])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Inform group that voting is starting
        await update.message.reply_text(
            "Starting MVP voting! Check your private messages to cast your vote.\n"
            "If you haven't received a message, please start a private chat with me first."
        )

        # Send private messages and track successful sends
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
                    reply_markup=reply_markup,
                )
                game.voting_players.append(player)  # Add to voting players list
            except (BadRequest, TelegramError) as e:
                failed_players.append(player.display_name)
                continue

        # If any players couldn't receive messages, inform the group
        if failed_players:
            await update.message.reply_text(
                f"⚠️ Couldn't send voting message to: {', '.join(failed_players)}\n"
                "These players won't participate in the MVP voting."
            )

    @admin_only
    async def test_fill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Fill the game with a specified number of dummy players for testing purposes.
        Usage: /test_fill <number_of_players>
        """
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)

        # Validate command arguments
        if not context.args or len(context.args) != 1:
            await update.message.reply_text("Usage: /test_fill <number_of_players>")
            return

        if not game:
            await update.message.reply_text("Start a game first with /start_game")
            return

        try:
            number_of_dummies = int(context.args[0])
            if number_of_dummies < 0:
                await update.message.reply_text("Number of players must be positive")
                return
        except ValueError:
            await update.message.reply_text("Please provide a valid number")
            return

        # Create dummy players
        dummy_players = []
        for i in range(number_of_dummies):
            # Create a mock telegram user with minimal required attributes
            class MockTelegramUser:
                def __init__(self, user_id, username):
                    self.id = user_id
                    self.username = username

            # Create mock telegram user and convert to Player
            mock_user = MockTelegramUser(
                user_id=i - 1000,  # Use offset to avoid potential ID conflicts
                username=f"user{i}",
            )
            player = Player(telegram_user=mock_user, display_name=f"Test Player {i}")
            dummy_players.append(player)

        # Set the game's players to our dummy list
        game.players = dummy_players

        # Update the join message
        await self.game_manager.update_join_message(chat_id, context)

    async def add_external(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)

        if not game:
            await context.bot.send_message(chat_id=chat_id, text="No active game!")
            return

        if game.game_state != "WAITING":
            await context.bot.send_message(
                chat_id=chat_id, text="Can't add players after game has started!"
            )
            return

        if not context.args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Please provide the player name.\nUsage: /add_external PlayerName",
            )
            return

        player_name = " ".join(context.args)

        if len(game.players) >= game.max_players:
            await context.bot.send_message(chat_id=chat_id, text="Game is full!")
            return

        # Create unique negative ID for external player
        external_id = -1 * (len([p for p in game.players if p.id < 0]) + 1)
        external_player = ExternalPlayer(external_id, player_name)

        # Check if player with same name already exists
        if any(p.display_name == player_name for p in game.players):
            await context.bot.send_message(
                chat_id=chat_id, text=f"Player named '{player_name}' already exists!"
            )
            return

        game.players.append(external_player)
        await self.game_manager.update_join_message(chat_id, context)

    async def remove_external(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)

        if not game:
            await context.bot.send_message(chat_id=chat_id, text="No active game!")
            return

        if game.game_state != "WAITING":
            await context.bot.send_message(
                chat_id=chat_id, text="Can't remove players after game has started!"
            )
            return

        if not context.args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Please provide the player name.\nUsage: /remove_external PlayerName",
            )
            return

        player_name = " ".join(context.args)

        # Find and remove external player
        external_player = None
        for player in game.players:
            if player.display_name == player_name and player.id < 0:
                external_player = player
                break

        if external_player:
            game.players.remove(external_player)
            await self.game_manager.update_join_message(chat_id, context)
            await context.bot.send_message(
                chat_id=chat_id, text=f"Removed external player: {player_name}"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"No external player found with name: {player_name}",
            )

    async def show_teams(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command handler to show current teams"""
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)

        if not game or game.game_state == "WAITING":
            await update.message.reply_text("No active game with teams!")
            return

        await self.game_manager.update_teams_message(chat_id, context, force_new=True)


class ExternalPlayer:
    def __init__(self, id: int, display_name: str):
        self.id = id  # We'll use negative IDs for external players to avoid conflicts
        self.display_name = display_name
