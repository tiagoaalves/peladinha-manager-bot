from models.game_player import GamePlayer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random


class PlayerHandlers:
    def __init__(self, game_manager, player_db_manager, game_db_manager):
        self.game_manager = game_manager
        self.player_db_manager = player_db_manager
        self.game_db_manager = game_db_manager

    async def handle_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.message.chat_id
        telegram_user = query.from_user
        player = GamePlayer(telegram_user.id, telegram_user, "")
        game = self.game_manager.get_game(chat_id)

        if not game or game.game_state != "WAITING":
            await query.answer("No active game!")
            return

        # Check if user is registered
        display_name = self.player_db_manager.get_player_display_name(player.id)
        if not display_name:
            await query.answer(
                "You need to register first! Start a private chat with me and use /start",
                show_alert=True,
            )
            return
        else:
            player.display_name = display_name

        if player.id in [p.id for p in game.players]:
            await query.answer("You already joined!")
            return

        if len(game.players) >= game.max_players:
            await query.answer("Game is full!")
            return

        game.players.append(player)
        self.game_db_manager.save_active_game_players(chat_id, game.players)
        await self.game_manager.update_join_message(chat_id, context)
        await query.answer("You joined the game!")

        if len(game.players) == game.max_players:
            await self.select_captains(chat_id, context)

    async def handle_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.message.chat_id
        user = query.from_user
        game = self.game_manager.get_game(chat_id)

        if not game or game.game_state != "WAITING":
            await query.answer("No active game!")
            return

        if user.id not in [p.id for p in game.players]:
            await query.answer("You haven't joined the game!")
            return

        game.players = [p for p in game.players if p.id != user.id]
        self.game_db_manager.save_active_game_players(chat_id, game.players)
        await self.game_manager.update_join_message(chat_id, context)
        await query.answer("You left the game!")

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
        game.voting_players = []

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

    async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming MVP votes"""
        query = update.callback_query
        voter = query.from_user
        voted_id = int(query.data.split("_")[1])

        # Find active game and validate vote
        game, game_chat_id = self._find_active_voting_game(voter.id)
        if not game:
            await query.answer("No active voting session found!")
            return

        if voter.id in game.mvp_votes:
            await query.answer("You already voted!")
            return

        # Record vote and notify voter
        voted_player = self._record_vote(game, voter.id, voted_id)
        await query.message.delete()

        # Check if voting is complete
        if len(game.mvp_votes) == len(game.voting_players):
            await self._handle_voting_completion(game, game_chat_id, context)
        else:
            await self._send_vote_confirmation(context, voter.id, voted_player)
            await query.answer("Vote recorded!")

    def _find_active_voting_game(self, voter_id):
        """Find the game where the voter is participating"""
        for chat_id, game in self.game_manager.games.items():
            if game.game_state == "VOTING" and voter_id in [
                p.id for p in game.voting_players
            ]:
                return game, chat_id
        return None, None

    def _record_vote(self, game, voter_id, voted_id):
        """Record a vote and return the voted player"""
        game.mvp_votes[voter_id] = voted_id
        return next(p for p in game.players if p.id == voted_id)

    def _count_votes(self, game):
        """Count votes and determine MVP(s)"""
        vote_count = {}
        for voted_id in game.mvp_votes.values():
            vote_count[voted_id] = vote_count.get(voted_id, 0) + 1

        max_votes = max(vote_count.values())
        mvp_ids = [pid for pid, votes in vote_count.items() if votes == max_votes]
        mvps = [next(p for p in game.players if p.id == mvp_id) for mvp_id in mvp_ids]

        return mvps, max_votes

    async def _handle_voting_completion(self, game, chat_id, context):
        """Handle the completion of MVP voting"""
        mvps, max_votes = self._count_votes(game)

        try:
            # Prepare final player data with MVP information
            players_data = []
            for player in game.players:
                if player.id < 0:  # Skip external players
                    continue

                player_data = {
                    "id": player.id,
                    "team": "A" if player in game.teams["Team A"] else "B",
                    "was_captain": player in game.captains,
                    "was_mvp": player in mvps,
                }
                players_data.append(player_data)

            # Update all player stats now that we have complete information
            self.player_db_manager.update_player_stats(
                score_team_a=game.score["Team A"],
                score_team_b=game.score["Team B"],
                players_data=players_data,
            )

        except Exception as e:
            print(f"Error updating player stats: {e}")

        # Announce results
        result_text = self._format_mvp_announcement(mvps, max_votes)
        await context.bot.send_message(chat_id=chat_id, text=result_text)

        # Notify voters
        await self._notify_voters_completion(game, context)

        # Clean up
        self.game_db_manager.remove_active_game(chat_id)
        self.game_manager.remove_game(chat_id)

    def _format_mvp_announcement(self, mvps, max_votes):
        """Format the MVP announcement message"""
        if len(mvps) == 1:
            return f"🏆 MVP of the game: {mvps[0].display_name} with {max_votes} votes!"
        else:
            names = ", ".join(p.display_name for p in mvps)
            return f"🏆 It's a tie! MVPs of the game: {names}\nEach with {max_votes} votes!"

    async def _notify_voters_completion(self, game, context):
        """Send completion notifications to all voters"""
        for voter_id in game.mvp_votes.keys():
            await context.bot.send_message(
                chat_id=voter_id,
                text="✅ Voting complete! Results have been announced in the group.",
            )

    async def _send_vote_confirmation(self, context, voter_id, voted_player):
        """Send confirmation message to the voter"""
        await context.bot.send_message(
            chat_id=voter_id, text=f"✅ You voted for: {voted_player.display_name}"
        )

    async def select_captains(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        game = self.game_manager.get_game(chat_id)

        # Filter out external players (who have negative IDs)
        telegram_players = [p for p in game.players if p.id > 0]

        # Check if we have enough Telegram players to be captains
        if len(telegram_players) < 2:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Not enough Telegram users to select captains. Need at least 2 non-external players.",
            )
            # Reset game state
            self.game_manager.remove_game(chat_id)
            return

        game.captains = random.sample(telegram_players, 2)
        game.game_state = "DRAFT_CHOICE"

        # Create method selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("ABAB", callback_data="draft_abab"),
                InlineKeyboardButton("ABBAA", callback_data="draft_abba"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Captains selected!\n"
            f"Team A Captain: {game.captains[0].display_name}\n"
            f"Team B Captain: {game.captains[1].display_name}\n\n",
            reply_markup=reply_markup,
        )

    async def handle_draft_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        chat_id = query.message.chat_id
        game = self.game_manager.get_game(chat_id)

        if not game or game.game_state != "DRAFT_CHOICE":
            await query.answer("No active draft choice!")
            return

        draft_method = query.data.split("_")[1]  # 'abab' or 'abba'
        game.draft_method = draft_method
        game.game_state = "SELECTION"
        game.current_selector = game.captains[0]
        game.selection_round = 0  # Track the selection round

        # Get players available for selection
        remaining_players = [p for p in game.players if p not in game.captains]
        keyboard = [
            [InlineKeyboardButton(p.display_name, callback_data=f"select_{p.id}")]
            for p in remaining_players
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        method_name = (
            "Alternating (ABAB)" if draft_method == "abab" else "Snake Draft (ABBA)"
        )
        await query.message.edit_text(
            f"Draft Method: {method_name}\n\n"
            f"Team A Captain: {game.captains[0].display_name}\n"
            f"Team B Captain: {game.captains[1].display_name}\n\n"
            f"{game.current_selector.display_name}, select your first player:",
            reply_markup=reply_markup,
        )

    async def handle_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        chat_id = query.message.chat_id
        game = self.game_manager.get_game(chat_id)

        if not game or game.game_state != "SELECTION":
            await query.answer("No active team selection!")
            return

        if query.from_user.id != game.current_selector.id:
            await query.answer("It's not your turn to select!")
            return

        selected_id = int(query.data.split("_")[1])
        selected_player = next(p for p in game.players if p.id == selected_id)

        # Determine current team and add player
        team_name = "Team A" if game.current_selector == game.captains[0] else "Team B"
        game.teams[team_name].append(selected_player)

        # Calculate total players selected (excluding captains)
        total_selected = len(game.teams["Team A"]) + len(game.teams["Team B"])

        # Determine next selector based on draft method
        if game.draft_method == "abab":
            game.current_selector = (
                game.captains[1]
                if game.current_selector == game.captains[0]
                else game.captains[0]
            )
        else:  # abba pattern
            position_in_sequence = total_selected % 4
            if position_in_sequence == 0:  # First pick of sequence
                game.current_selector = game.captains[0]  # Goes to A
            elif position_in_sequence == 1:  # Second pick of sequence
                game.current_selector = game.captains[1]  # Goes to B
            elif position_in_sequence == 2:  # Third pick of sequence
                game.current_selector = game.captains[1]  # Stays with B
            else:  # Fourth pick of sequence
                game.current_selector = game.captains[0]  # Goes back to A

        # Check if teams are complete
        players_per_team = (game.max_players - 2) // 2
        if (
            len(game.teams["Team A"]) == players_per_team
            and len(game.teams["Team B"]) == players_per_team
        ):
            game.game_state = "IN_GAME"

            # First delete the selection message
            await query.message.delete()

            # Show final teams in a new message without any keyboard
            team_a_players = [game.captains[0]] + game.teams["Team A"]
            team_b_players = [game.captains[1]] + game.teams["Team B"]

            await context.bot.send_message(
                chat_id=chat_id,
                text="Teams are complete!\n\n"
                f"Team A (Captain: {game.captains[0].display_name}):\n"
                f"{chr(10).join(p.display_name for p in team_a_players)}\n\n"
                f"Team B (Captain: {game.captains[1].display_name}):\n"
                f"{chr(10).join(p.display_name for p in team_b_players)}\n\n"
                "Good luck! Use /end_game when finished.",
            )
        else:
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

            # Show current teams status
            team_a_list = [game.captains[0].display_name] + [
                p.display_name for p in game.teams["Team A"]
            ]
            team_b_list = [game.captains[1].display_name] + [
                p.display_name for p in game.teams["Team B"]
            ]

            await query.message.edit_text(
                f"Team A:\n{chr(10).join(team_a_list)}\n\n"
                f"Team B:\n{chr(10).join(team_b_list)}\n\n"
                f"{game.current_selector.display_name}'s turn to select:",
                reply_markup=reply_markup,
            )

        await query.answer()

    async def show_player_stats(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user = update.effective_user
        player = self.player_db_manager.get_player(user.id)

        if not player:
            await update.message.reply_text("You haven't played any games yet!")
            return

        win_rate = (
            (player.games_won / player.games_played * 100)
            if player.games_played > 0
            else 0
        )

        stats = (
            f"📋 Stats for {player.display_name}:\n\n"
            f"🏆 ELO Rating: {player.elo_rating}\n"
            f"📈 Win Rate: {win_rate:.1f}%\n"
            f"🌟 Best Streak: {player.best_streak}\n"
            f"🔥 Current Streak: {player.current_streak}\n"
            f"✅ Wins: {player.games_won}\n"
            f"💔 Losses: {player.games_lost}\n"
            f"🤝 Draws: {player.games_drawn}\n"
            f"⚽ Games Played: {player.games_played}\n"
            f"👑 Times MVP: {player.times_mvp}\n"
            f"🫡 Times Captain: {player.times_captain}\n"
        )

        await update.message.reply_text(stats)
