from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import random
import logging
import asyncio
import nest_asyncio
from config import TOKEN
from handlers.game_handlers import GameHandlers
from handlers.player_handlers import PlayerHandlers
from services.game_manager import GameManager
from database.supabase import SupabaseManager

nest_asyncio.apply()

async def main():
    app = Application.builder().token(TOKEN).build()
    
    # Initialize services and handlers
    game_manager = GameManager()
    db_manager = SupabaseManager()
    game_handlers = GameHandlers(game_manager=game_manager, db_manager=db_manager)
    player_handlers = PlayerHandlers(game_manager=game_manager, db_manager=db_manager)
    
    # Register handlers
    app.add_handler(CommandHandler("start_game", game_handlers.start_game))
    app.add_handler(CommandHandler("end_game", game_handlers.end_game))
    app.add_handler(CommandHandler("score", game_handlers.handle_score))
    app.add_handler(CommandHandler("list", game_handlers.list_players))
    app.add_handler(CommandHandler("test_fill", game_handlers.test_fill))
    app.add_handler(CommandHandler("add_external", game_handlers.add_external))
    app.add_handler(CommandHandler("remove_external", game_handlers.remove_external))
    
    app.add_handler(CallbackQueryHandler(player_handlers.handle_join, pattern="^join"))
    app.add_handler(CallbackQueryHandler(player_handlers.handle_leave, pattern="^leave"))
    app.add_handler(CallbackQueryHandler(player_handlers.handle_selection, pattern="^select_"))
    app.add_handler(CallbackQueryHandler(player_handlers.handle_vote, pattern="^vote_"))
    app.add_handler(CallbackQueryHandler(player_handlers.handle_draft_choice, pattern=r"^draft_"))
    
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
