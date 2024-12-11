from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TelegramError

class GameHandlers:
    def __init__(self, game_manager, db_manager):
        self.game_manager = game_manager
        self.db_manager = db_manager

    async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        # Check if there's an active game
        if chat_id in self.game_manager.games:
            await context.bot.send_message(
                chat_id=chat_id,
                text="A game is already active. End it first to start a new one."
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
            await update.message.reply_text("Game already started!")
            return
            
        await self.game_manager.update_join_message(chat_id, context)

    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        print("\n=== Starting end_game process ===")
        print(f"Chat ID: {chat_id}")
        print(f"Game exists: {game is not None}")
        
        if not game:
            await update.message.reply_text("No active game!")
            return
            
        print(f"Game state: {game.game_state}")
        print(f"Number of players: {len(game.players)}")
        print(f"Teams A size: {len(game.teams['Team A'])}")
        print(f"Teams B size: {len(game.teams['Team B'])}")
        
        if game.game_state != "IN_GAME":
            await update.message.reply_text("No active game to end!")
            return

        try:
            # Save all non-external players to database
            print("\nSaving players to database...")
            telegram_players = [p for p in game.players if p.id > 0]
            print(f"Found {len(telegram_players)} non-external players")
            
            for player in telegram_players:
                print(f"Saving player: {player.first_name} (ID: {player.id})")
                self.db_manager.create_player(player)
            
            # Prepare player data
            print("\nPreparing player data for game record...")
            players_data = []
            for player in telegram_players:
                team = 'A' if player in game.teams["Team A"] else 'B'
                was_captain = player in game.captains
                print(f"Player {player.first_name}: Team {team}, Captain: {was_captain}")
                
                player_data = {
                    'id': player.id,
                    'team': team,
                    'was_captain': was_captain,
                    'was_mvp': False
                }
                players_data.append(player_data)
            
            print(f"\nSaving game with {len(players_data)} players...")
            game.db_game_id = self.db_manager.save_game(
                chat_id=chat_id,
                score_team_a=None,
                score_team_b=None,
                players_data=players_data
            )
            print(f"Game saved with ID: {game.db_game_id}")
            
        except Exception as e:
            print(f"Database error during end_game: {e}")
            import traceback
            traceback.print_exc()
        
        game.game_state = "SCORING"
        await update.message.reply_text(
            "Please enter the final score using the format: /score TeamA TeamB\n"
            "Example: /score 3 2"
        )
        print("\n=== End game process completed ===")

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
        game.voting_players = []  # Track players who can vote
        
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
                    reply_markup=reply_markup
                )
                game.voting_players.append(player)  # Add to voting players list
            except (BadRequest, TelegramError) as e:
                failed_players.append(player.first_name)
                continue
        
        # If any players couldn't receive messages, inform the group
        if failed_players:
            await update.message.reply_text(
                f"⚠️ Couldn't send voting message to: {', '.join(failed_players)}\n"
                "These players won't participate in the MVP voting."
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
                self.username = "dummy"

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

    async def add_external(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        if not game:
            await context.bot.send_message(
                chat_id=chat_id,
                text="No active game!"
            )
            return
            
        if game.game_state != "WAITING":
            await context.bot.send_message(
                chat_id=chat_id,
                text="Can't add players after game has started!"
            )
            return
            
        if not context.args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Please provide the player name.\nUsage: /add_external PlayerName"
            )
            return
        
        player_name = " ".join(context.args)
        
        if len(game.players) >= game.max_players:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Game is full!"
            )
            return
            
        # Create unique negative ID for external player
        external_id = -1 * (len([p for p in game.players if p.id < 0]) + 1)
        external_player = ExternalPlayer(external_id, player_name)
        
        # Check if player with same name already exists
        if any(p.first_name == player_name for p in game.players):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Player named '{player_name}' already exists!"
            )
            return
        
        game.players.append(external_player)
        await self.game_manager.update_join_message(chat_id, context)

    async def remove_external(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        game = self.game_manager.get_game(chat_id)
        
        if not game:
            await context.bot.send_message(
                chat_id=chat_id,
                text="No active game!"
            )
            return
            
        if game.game_state != "WAITING":
            await context.bot.send_message(
                chat_id=chat_id,
                text="Can't remove players after game has started!"
            )
            return
            
        if not context.args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Please provide the player name.\nUsage: /remove_external PlayerName"
            )
            return
        
        player_name = " ".join(context.args)
        
        # Find and remove external player
        external_player = None
        for player in game.players:
            if player.first_name == player_name and player.id < 0:
                external_player = player
                break
        
        if not external_player:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"No external player found with name: {player_name}"
            )

class ExternalPlayer:
    def __init__(self, id: int, first_name: str):
        self.id = id  # We'll use negative IDs for external players to avoid conflicts
        self.first_name = first_name
        self.last_name = None
