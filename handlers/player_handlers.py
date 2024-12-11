from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

class PlayerHandlers:
    def __init__(self, game_manager, db_manager):
        self.game_manager = game_manager
        self.db_manager=db_manager

    async def handle_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.message.chat_id
        user = query.from_user
        game = self.game_manager.get_game(chat_id)
        
        if not game or game.game_state != "WAITING":
            await query.answer("No active game!")
            return
            
        if user.id in [p.id for p in game.players]:
            await query.answer("You already joined!")
            return
            
        if len(game.players) >= game.max_players:
            await query.answer("Game is full!")
            return
            
        game.players.append(user)
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
        await self.game_manager.update_join_message(chat_id, context)
        await query.answer("You left the game!")

    async def handle_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.message.chat_id
        game = self.game_manager.get_game(chat_id)
        
        if not game or game.game_state != "SELECTION":
            await query.answer("No active team selection!")
            return
            
        selected_id = int(query.data.split('_')[1])
        selected_player = next(p for p in game.players if p.id == selected_id)
        
        # Determine current team and add player
        team_name = "Team A" if game.current_selector == game.captains[0] else "Team B"
        game.teams[team_name].append(selected_player)
        
        # Switch to other captain for next selection
        game.current_selector = game.captains[1] if game.current_selector == game.captains[0] else game.captains[0]
        
        # Calculate players per team excluding captains
        players_per_team = (game.max_players - 2) // 2
        
        # Check if teams are complete
        if len(game.teams["Team A"]) == players_per_team and len(game.teams["Team B"]) == players_per_team:
            game.game_state = "IN_GAME"
            # Show final teams including captains
            team_a_players = [game.captains[0]] + game.teams["Team A"]
            team_b_players = [game.captains[1]] + game.teams["Team B"]
            
            # First delete the selection message
            await query.message.delete()
            
            # Format teams with one player per line
            team_a_list = "\n".join(p.first_name for p in team_a_players)
            team_b_list = "\n".join(p.first_name for p in team_b_players)
            
            # Then send a new message with the final teams
            await context.bot.send_message(
                chat_id=chat_id,
                text="Teams are complete!\n\n"
                    f"Team A (Captain: {game.captains[0].first_name}):\n"
                    f"{team_a_list}\n\n"
                    f"Team B (Captain: {game.captains[1].first_name}):\n"
                    f"{team_b_list}\n\n"
                    "Good luck! Use /end_game when finished."
            )
        else:
            # Get remaining players (excluding captains and already selected players)
            remaining_players = [p for p in game.players 
                            if p not in game.captains 
                            and p not in game.teams["Team A"] 
                            and p not in game.teams["Team B"]]
            
            keyboard = [[InlineKeyboardButton(p.first_name, callback_data=f"select_{p.id}")] 
                    for p in remaining_players]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Format current teams status with one player per line
            team_a_text = f"Team A (Captain: {game.captains[0].first_name}):"
            if game.teams["Team A"]:
                team_a_text += "\n" + "\n".join(p.first_name for p in game.teams["Team A"])
            else:
                team_a_text += "\nNo players"
            
            team_b_text = f"Team B (Captain: {game.captains[1].first_name}):"
            if game.teams["Team B"]:
                team_b_text += "\n" + "\n".join(p.first_name for p in game.teams["Team B"])
            else:
                team_b_text += "\nNo players"
            
            await query.message.edit_text(
                f"{team_a_text}\n\n"
                f"{team_b_text}\n\n"
                f"{game.current_selector.first_name}'s turn to select:",
                reply_markup=reply_markup
            )
        
        await query.answer()

    async def start_mvp_voting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        voter = query.from_user
        voted_id = int(query.data.split('_')[1])
        
        # Find the game where this player is participating
        game = None
        game_chat_id = None
        for chat_id, g in self.game_manager.games.items():
            if g.game_state == "VOTING" and voter.id in [p.id for p in g.voting_players]:
                game = g
                game_chat_id = chat_id
                break
        
        if not game:
            await query.answer("No active voting session found!")
            return
        
        if voter.id in game.mvp_votes:
            await query.answer("You already voted!")
            return
            
        game.mvp_votes[voter.id] = voted_id
        voted_player = next(p for p in game.players if p.id == voted_id)
        
        # Delete the original message with the keyboard
        await query.message.delete()
        
        # Check if all players who received the message have voted
        if len(game.mvp_votes) == len(game.voting_players):
            vote_count = {}
            for voted_id in game.mvp_votes.values():
                vote_count[voted_id] = vote_count.get(voted_id, 0) + 1
            
            # Find highest vote count and all players with that count
            max_votes = max(vote_count.values())
            mvp_ids = [pid for pid, votes in vote_count.items() if votes == max_votes]
            
            # Get MVP player objects and format announcement
            mvps = [next(p for p in game.players if p.id == mvp_id) for mvp_id in mvp_ids]
            
            if len(mvps) == 1:
                result_text = f"🏆 MVP of the game: {mvps[0].first_name} with {max_votes} votes!"
            else:
                names = ", ".join(p.first_name for p in mvps)
                result_text = f"🏆 It's a tie! MVPs of the game: {names}\nEach with {max_votes} votes!"
            
            # Send results to the group chat
            await context.bot.send_message(
                chat_id=game_chat_id,
                text=result_text
            )
            
            # Send new message in private chat
            await context.bot.send_message(
                chat_id=voter.id,
                text=f"🏆 MVP Vote for game in {query.message.chat.title} 🏆\n\n"
                    f"Final Score:\n"
                    f"Team A: {game.score['Team A']}\n"
                    f"Team B: {game.score['Team B']}\n\n"
                    f"✅ Voting complete! Results have been announced in the group."
            )
            
            self.game_manager.remove_game(game_chat_id)
        else:
            # Send new message in private chat
            await context.bot.send_message(
                chat_id=voter.id,
                text=f"🏆 MVP Vote for game in {query.message.chat.title} 🏆\n\n"
                    f"Final Score:\n"
                    f"Team A: {game.score['Team A']}\n"
                    f"Team B: {game.score['Team B']}\n\n"
                    f"✅ You voted for: {voted_player.first_name}"
            )
            await query.answer("Vote recorded!")

    async def select_captains(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        game = self.game_manager.get_game(chat_id)
        
        # Filter out external players (who have negative IDs)
        telegram_players = [p for p in game.players if p.id > 0]
        
        # Check if we have enough Telegram players to be captains
        if len(telegram_players) < 2:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Not enough Telegram users to select captains. Need at least 2 non-external players."
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
                InlineKeyboardButton("ABBAA", callback_data="draft_abba")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Captains selected!\n"
                f"Team A Captain: {game.captains[0].first_name}\n"
                f"Team B Captain: {game.captains[1].first_name}\n\n"
                f"Captain {game.captains[0].first_name}, choose the draft method:",
            reply_markup=reply_markup
        )

    async def handle_draft_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.message.chat_id
        game = self.game_manager.get_game(chat_id)
        
        if not game or game.game_state != "DRAFT_CHOICE":
            await query.answer("No active draft choice!")
            return
        
        draft_method = query.data.split('_')[1]  # 'abab' or 'abba'
        game.draft_method = draft_method
        game.game_state = "SELECTION"
        game.current_selector = game.captains[0]
        game.selection_round = 0  # Track the selection round
        
        # Get players available for selection
        remaining_players = [p for p in game.players if p not in game.captains]
        keyboard = [[InlineKeyboardButton(p.first_name, callback_data=f"select_{p.id}")] 
                    for p in remaining_players]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        method_name = "Alternating (ABAB)" if draft_method == "abab" else "Snake Draft (ABBA)"
        await query.message.edit_text(
            f"Draft Method: {method_name}\n\n"
            f"Team A Captain: {game.captains[0].first_name}\n"
            f"Team B Captain: {game.captains[1].first_name}\n\n"
            f"{game.current_selector.first_name}, select your first player:",
            reply_markup=reply_markup
        )

    async def handle_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.message.chat_id
        game = self.game_manager.get_game(chat_id)
        
        if not game or game.game_state != "SELECTION":
            await query.answer("No active team selection!")
            return
            
        # if query.from_user.id != game.current_selector.id:
        #     await query.answer("It's not your turn to select!")
        #     return
            
        selected_id = int(query.data.split('_')[1])
        selected_player = next(p for p in game.players if p.id == selected_id)
        
        # Determine current team and add player
        team_name = "Team A" if game.current_selector == game.captains[0] else "Team B"
        game.teams[team_name].append(selected_player)
        
        # Calculate total players selected (excluding captains)
        total_selected = len(game.teams["Team A"]) + len(game.teams["Team B"])
        
        # Determine next selector based on draft method
        if game.draft_method == "abab":
            game.current_selector = game.captains[1] if game.current_selector == game.captains[0] else game.captains[0]
        else:  # abba pattern
            position_in_sequence = total_selected % 4
            if position_in_sequence == 0:    # First pick of sequence
                game.current_selector = game.captains[0]  # Goes to A
            elif position_in_sequence == 1:   # Second pick of sequence
                game.current_selector = game.captains[1]  # Goes to B
            elif position_in_sequence == 2:   # Third pick of sequence
                game.current_selector = game.captains[1]  # Stays with B
            else:                            # Fourth pick of sequence
                game.current_selector = game.captains[0]  # Goes back to A
        
        # Check if teams are complete
        players_per_team = (game.max_players - 2) // 2
        if len(game.teams["Team A"]) == players_per_team and len(game.teams["Team B"]) == players_per_team:
            game.game_state = "IN_GAME"
            
            # First delete the selection message
            await query.message.delete()
            
            # Show final teams in a new message without any keyboard
            team_a_players = [game.captains[0]] + game.teams["Team A"]
            team_b_players = [game.captains[1]] + game.teams["Team B"]
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="Teams are complete!\n\n"
                    f"Team A (Captain: {game.captains[0].first_name}):\n"
                    f"{chr(10).join(p.first_name for p in team_a_players)}\n\n"
                    f"Team B (Captain: {game.captains[1].first_name}):\n"
                    f"{chr(10).join(p.first_name for p in team_b_players)}\n\n"
                    "Good luck! Use /end_game when finished."
            )
        else:
            remaining_players = [p for p in game.players 
                            if p not in game.captains 
                            and p not in game.teams["Team A"]
                            and p not in game.teams["Team B"]]
            
            keyboard = [[InlineKeyboardButton(p.first_name, callback_data=f"select_{p.id}")] 
                    for p in remaining_players]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show current teams status
            team_a_list = [game.captains[0].first_name] + [p.first_name for p in game.teams["Team A"]]
            team_b_list = [game.captains[1].first_name] + [p.first_name for p in game.teams["Team B"]]
            
            await query.message.edit_text(
                f"Team A:\n{chr(10).join(team_a_list)}\n\n"
                f"Team B:\n{chr(10).join(team_b_list)}\n\n"
                f"{game.current_selector.first_name}'s turn to select:",
                reply_markup=reply_markup
            )
        
        await query.answer()
