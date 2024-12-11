# peladinha-manager-bot 🤖⚽

Hey there! This is a Telegram bot I made to help organize our weekly football games with friends. It started because we were tired of the chaotic WhatsApp messages trying to sort out teams, so I built something to make our lives easier.

## What it does

- Organizes pickup games for 14 players (you can change this in the code)
- Handles player registration through Telegram
- Can add external players (for friends who don't use Telegram)
- Automatically picks team captains
- Supports two draft methods:
  - ABAB (classic alternating picks)
  - ABBA (snake draft for more fairness)
- Keeps track of scores
- Has an MVP voting system at the end of each game
- Tracks player stats:
  - Games won/lost/drawn
  - Win/loss streaks
  - Times as captain or MVP
  - And more!

## Setup

1. Create a bot through [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Set up a Supabase project (for storing game stats)
4. Clone this repo
5. Install requirements:
```bash
pip install python-telegram-bot supabase python-dotenv
```
6. Create a `.env` file with:
```
TELEGRAM_BOT_TOKEN=your_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```
7. Run it:
```bash
python main.py
```

## Bot Commands

- `/start_game` - Opens registration for a new game
- `/end_game` - Ends current game and starts MVP voting
- `/add_external PlayerName` - Adds a player who isn't on Telegram
- `/remove_external PlayerName` - Removes an external player
- `/list_players` - Shows current players
- `/score TeamA TeamB` - Records the final score

## Notes

This is a personal project I made in a hurry to use with friends, so:
- No tests (we're keeping it casual)
- Minimal error handling (we know how to use it)
- Code might be a bit messy (it works for us!)

Feel free to use it, modify it, or completely change it for your needs. If you make it better, that's awesome!

## Contributing

Found a bug? Want to add something cool? Just open a PR! I'm not precious about it - if it makes the bot better, I'm happy to merge it.

## License

MIT - do whatever you want with it! If it helps organize your games, that's a win in my book. 🎯

## Questions?

Just open an issue or reach out. Always happy to help fellow football enthusiasts! ⚽A Telegram bot to manage my football pickup games
