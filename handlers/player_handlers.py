from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

class PlayerHandlers:
    def __init__(self, game_manager):
        self.game_manager = game_manager

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
        
        selected_id = int(query.data.split('_')[1])
        selected_player = next(p for p in game.players if p.id == selected_id)
        
        team_name = "Team A" if game.current_selector == game.captains[0] else "Team B"
        game.teams[team_name].append(selected_player)
        
        game.current_selector = game.captains[1] if game.current_selector == game.captains[0] else game.captains[0]
        
        if all(len(team) == (game.max_players - 2) // 2 for team in game.teams.values()):
            game.game_state = "IN_GAME"
            await query.message.reply_text(
                "Teams are complete!\n"
                f"Team A: {', '.join(p.first_name for p in game.teams['Team A'])}\n"
                f"Team B: {', '.join(p.first_name for p in game.teams['Team B'])}\n\n"
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
            
            await query.message.edit_text(
                f"{game.current_selector.first_name}, select your player:",
                reply_markup=reply_markup
            )

    async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.message.chat_id
        game = self.game_manager.get_game(chat_id)
        
        voter = query.from_user
        voted_id = int(query.data.split('_')[1])
        
        if voter.id in game.mvp_votes:
            await query.answer("You already voted!")
            return
            
        game.mvp_votes[voter.id] = voted_id
        
        if len(game.mvp_votes) == len(game.players):
            vote_count = {}
            for voted_id in game.mvp_votes.values():
                vote_count[voted_id] = vote_count.get(voted_id, 0) + 1
            
            mvp_id = max(vote_count.keys(), key=lambda k: vote_count[k])
            mvp = next(p for p in game.players if p.id == mvp_id)
            
            await query.message.edit_text(
                f"MVP of the game: {mvp.first_name} "
                f"with {vote_count[mvp_id]} votes! 🏆"
            )
            self.game_manager.remove_game(chat_id)
        else:
            await query.answer("Vote recorded!")

    async def select_captains(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        game = self.game_manager.get_game(chat_id)
        game.captains = random.sample(game.players, 2)
        game.game_state = "SELECTION"
        game.current_selector = game.captains[0]
        
        remaining_players = [p for p in game.players if p not in game.captains]
        keyboard = [[InlineKeyboardButton(p.first_name, callback_data=f"select_{p.id}")] 
                   for p in remaining_players]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Captains selected!\n"
                 f"Team A Captain: {game.captains[0].first_name}\n"
                 f"Team B Captain: {game.captains[1].first_name}\n\n"
                 f"{game.current_selector.first_name}, select your first player:",
            reply_markup=reply_markup
        )
