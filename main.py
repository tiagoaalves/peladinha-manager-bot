from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import random
import logging
import asyncio
import nest_asyncio
#
# # Enable nested event loops
# nest_asyncio.apply()
#
# # Set up logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
#
# # Your SoccerGame class remains the same
# class SoccerGame:
#     def __init__(self):
#         self.players = []
#         self.max_players = 3
#         self.captains = []
#         self.teams = {"Team A": [], "Team B": []}
#         self.current_selector = None
#         self.game_state = "WAITING"
#         self.mvp_votes = {}
#
# # Your SoccerBot class remains the same
# class SoccerBot:
#     def __init__(self):
#         self.games = {}
#
#     async def start_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         chat_id = update.effective_chat.id
#         self.games[chat_id] = SoccerGame()
#         await self.update_join_message(chat_id, context)
#
#     async def update_join_message(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
#         game = self.games[chat_id]
#
#         if hasattr(game, 'join_message_id'):
#             try:
#                 await context.bot.delete_message(chat_id=chat_id, message_id=game.join_message_id)
#             except:
#                 pass
#
#         players_text = "Players joined:\n\n"
#         for i, player in enumerate(game.players, 1):
#             players_text += f"{i}. {player.first_name} {player.last_name}\n"
#
#         players_text += f"\n{len(game.players)}/{game.max_players} players"
#
#         keyboard = [
#             [
#                 InlineKeyboardButton("Join Game ⚽", callback_data="join"),
#                 InlineKeyboardButton("Leave Game 🚪", callback_data="leave")
#             ]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#
#         message = await context.bot.send_message(
#             chat_id=chat_id,
#             text=players_text,
#             reply_markup=reply_markup if len(game.players) < game.max_players else None
#         )
#         game.join_message_id = message.message_id
#
#     async def list_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         chat_id = update.effective_chat.id
#         game = self.games.get(chat_id)
#
#         if not game:
#             await update.message.reply_text("No active game!")
#             return
#
#         if game.game_state != "WAITING":
#             await update.message.reply_text("Game already started!")
#             return
#
#         await self.update_join_message(chat_id, context)
#
#     async def handle_leave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         query = update.callback_query
#         chat_id = query.message.chat_id
#         user = query.from_user
#         game = self.games.get(chat_id)
#
#         if not game or game.game_state != "WAITING":
#             await query.answer("No active game!")
#             return
#
#         if user.id not in [p.id for p in game.players]:
#             await query.answer("You haven't joined the game!")
#             return
#
#         game.players = [p for p in game.players if p.id != user.id]
#         await self.update_join_message(chat_id, context)
#         await query.answer("You left the game!")
#
#     async def handle_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         query = update.callback_query
#         chat_id = query.message.chat_id
#         user = query.from_user
#         game = self.games.get(chat_id)
#
#         if not game or game.game_state != "WAITING":
#             await query.answer("No active game!")
#             return
#
#         if user.id in [p.id for p in game.players]:
#             await query.answer("You already joined!")
#             return
#
#         if len(game.players) >= game.max_players:
#             await query.answer("Game is full!")
#             return
#
#         game.players.append(user)
#         await self.update_join_message(chat_id, context)
#         await query.answer("You joined the game!")
#
#         if len(game.players) == game.max_players:
#             await self.select_captains(chat_id, context)
#
#     async def select_captains(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         chat_id = update.effective_chat.id
#         game = self.games[chat_id]
#
#         # Randomly select two captains
#         game.captains = random.sample(game.players, 2)
#         game.game_state = "SELECTION"
#         game.current_selector = game.captains[0]
#
#         remaining_players = [p for p in game.players if p not in game.captains]
#
#         # Create inline keyboard for player selection
#         keyboard = [[InlineKeyboardButton(p.first_name, callback_data=f"select_{p.id}")] 
#                    for p in remaining_players]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#
#         await update.message.reply_text(
#             f"Captains selected!\n"
#             f"Team A Captain: {game.captains[0].first_name}\n"
#             f"Team B Captain: {game.captains[1].first_name}\n\n"
#             f"{game.current_selector.first_name}, select your first player:",
#             reply_markup=reply_markup
#         )
#
#     async def handle_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         query = update.callback_query
#         chat_id = query.message.chat_id
#         game = self.games[chat_id]
#
#         selected_id = int(query.data.split('_')[1])
#         selected_player = next(p for p in game.players if p.id == selected_id)
#
#         # Add player to current captain's team
#         team_name = "Team A" if game.current_selector == game.captains[0] else "Team B"
#         game.teams[team_name].append(selected_player)
#
#         # Switch selector
#         game.current_selector = game.captains[1] if game.current_selector == game.captains[0] else game.captains[0]
#
#         # Check if selection is complete
#         if all(len(team) == (game.max_players - 2) // 2 for team in game.teams.values()):
#             game.game_state = "IN_GAME"
#             await query.message.reply_text(
#                 "Teams are complete!\n"
#                 f"Team A: {', '.join(p.first_name for p in game.teams['Team A'])}\n"
#                 f"Team B: {', '.join(p.first_name for p in game.teams['Team B'])}\n\n"
#                 "Good luck! Use /end_game when finished."
#             )
#         else:
#             # Update selection keyboard
#             remaining_players = [p for p in game.players 
#                               if p not in game.captains 
#                               and p not in game.teams["Team A"]
#                               and p not in game.teams["Team B"]]
#
#             keyboard = [[InlineKeyboardButton(p.first_name, callback_data=f"select_{p.id}")] 
#                        for p in remaining_players]
#             reply_markup = InlineKeyboardMarkup(keyboard)
#
#             await query.message.edit_text(
#                 f"{game.current_selector.first_name}, select your player:",
#                 reply_markup=reply_markup
#             )
#
#     async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         chat_id = update.effective_chat.id
#         game = self.games[chat_id]
#         game.game_state = "VOTING"
#
#         # Create voting keyboard
#         keyboard = [[InlineKeyboardButton(p.first_name, callback_data=f"vote_{p.id}")] 
#                    for p in game.players]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#
#         await update.message.reply_text(
#             "Game ended! Vote for MVP:",
#             reply_markup=reply_markup
#         )
#
#     async def handle_score(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         chat_id = update.effective_chat.id
#         game = self.games.get(chat_id)
#
#         if not game or game.game_state != "SCORING":
#             await update.message.reply_text("No game waiting for score!")
#             return
#
#         try:
#             score_a, score_b = map(int, context.args)
#             if score_a < 0 or score_b < 0:
#                 raise ValueError
#         except (ValueError, IndexError):
#             await update.message.reply_text("Invalid score format. Use: /score 3 2")
#             return
#
#         game.score = {"Team A": score_a, "Team B": score_b}
#         game.game_state = "VOTING"
#
#         # Update stats and start MVP voting
#         # await self.update_player_stats(chat_id, score_a, score_b)
#         await self.start_mvp_voting(update, context)
#
#
#     async def start_mvp_voting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         chat_id = update.effective_chat.id
#         game = self.games[chat_id]
#
#         # Create voting keyboard
#         keyboard = []
#         for player in game.players:
#             button = InlineKeyboardButton(
#                 f"{player.first_name} {player.last_name}",
#                 callback_data=f"vote_{player.id}"
#             )
#             keyboard.append([button])
#
#         reply_markup = InlineKeyboardMarkup(keyboard)
#
#         await update.message.reply_text(
#             "Vote for MVP:",
#             reply_markup=reply_markup
#         )
#
#     async def handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         query = update.callback_query
#         chat_id = query.message.chat_id
#         game = self.games[chat_id]
#
#         voter = query.from_user
#         voted_id = int(query.data.split('_')[1])
#
#         if voter.id in game.mvp_votes:
#             await query.answer("You already voted!")
#             return
#
#         game.mvp_votes[voter.id] = voted_id
#
#         if len(game.mvp_votes) == len(game.players):
#             # Count votes
#             vote_count = {}
#             for voted_id in game.mvp_votes.values():
#                 vote_count[voted_id] = vote_count.get(voted_id, 0) + 1
#
#             mvp_id = max(vote_count.keys(), key=lambda k: vote_count[k])
#             mvp = next(p for p in game.players if p.id == mvp_id)
#
#             await query.message.edit_text(
#                 f"MVP of the game: {mvp.first_name} "
#                 f"with {vote_count[mvp_id]} votes! 🏆"
#             )
#             # Clean up game
#             del self.games[chat_id]
#         else:
#             await query.answer("Vote recorded!")
#
# async def main():
#     bot = SoccerBot()
#     app = Application.builder().token('7739022678:AAGjqlpYKMJ9BV0Dux4uN7jAbKGRlTtZgU0').build()
#
#     app.add_handler(CommandHandler("start_game", bot.start_game))
#     app.add_handler(CallbackQueryHandler(bot.handle_join, pattern="^join"))
#     app.add_handler(CommandHandler("end_game", bot.end_game))
#     app.add_handler(CommandHandler("list", bot.list_players))
#     app.add_handler(CallbackQueryHandler(bot.handle_leave, pattern="^leave"))
#     app.add_handler(CallbackQueryHandler(bot.handle_selection, pattern="^select_"))
#     app.add_handler(CallbackQueryHandler(bot.handle_vote, pattern="^vote_"))
#
#     print("Soccer Bot started! Press Ctrl+C to exit.")
#     await app.run_polling(allowed_updates=Update.ALL_TYPES)
#
# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("Bot stopped!")
#     except Exception as e:
#         print(f"Error occurred: {e}")

import asyncio
import nest_asyncio
from config import TOKEN
from handlers.game_handlers import GameHandlers
from handlers.player_handlers import PlayerHandlers
from services.game_manager import GameManager

nest_asyncio.apply()

async def main():
    app = Application.builder().token(TOKEN).build()
    
    # Initialize services and handlers
    game_manager = GameManager()
    game_handlers = GameHandlers(game_manager)
    player_handlers = PlayerHandlers(game_manager)
    
    # Register handlers
    app.add_handler(CommandHandler("start_game", game_handlers.start_game))
    app.add_handler(CommandHandler("end_game", game_handlers.end_game))
    app.add_handler(CommandHandler("score", game_handlers.handle_score))
    app.add_handler(CommandHandler("list", game_handlers.list_players))
    
    app.add_handler(CallbackQueryHandler(player_handlers.handle_join, pattern="^join"))
    app.add_handler(CallbackQueryHandler(player_handlers.handle_leave, pattern="^leave"))
    app.add_handler(CallbackQueryHandler(player_handlers.handle_selection, pattern="^select_"))
    app.add_handler(CallbackQueryHandler(player_handlers.handle_vote, pattern="^vote_"))
    
    print("Soccer Bot started! Press Ctrl+C to exit.")
    
    # Start the bot
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")
    except Exception as e:
        print(f"Error occurred: {e}")
