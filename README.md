# Peladinha Manager Bot 🤖⚽

Hey there! This is a Telegram bot I made to help organize our weekly football games with friends. It started because we were tired of the chaotic WhatsApp messages trying to sort out teams, so I built something to make our lives easier.

## What it does

- Organizes pickup games for 14 players (you can change this in the code)
- Handles player registration through Telegram
- Can add external players (for friends who don't use Telegram)
- Automatically picks team captains
- Supports two draft methods:
  - ABAB (classic alternating picks)
  - ABBA (snake draft for more fairness)
- Keeps track of scores and maintains ELO ratings
- Has an MVP voting system at the end of each game
- Tracks player stats:
  - Games won/lost/drawn
  - Win/loss streaks
  - Times as captain or MVP
  - ELO rating
  - And more!

## The ELO System 📈

We use an ELO rating system (like in chess) to track player skill levels. Here's how it works:

### Basic Concept
- Everyone starts at 1200 rating points
- Win games = gain points, lose games = lose points
- Rating changes depend on:
  - How surprising the result was (beating a stronger team = more points)
  - How decisive the victory was (winning by more goals = more points)
  - How experienced the players are (newer players' ratings change faster)
  - Whether there are external players (reduces rating changes for uncertainty)

### How Ratings Change

#### The K-Factor
This controls how much ratings can change in a single game:
- First 10 games: K = 48 (big changes to find your true level quickly)
- Games 11-20: K = 32 (medium changes as you settle in)
- After 20 games: K = 16 (smaller changes for experienced players)

#### Goal Difference Impact
The more goals you win by, the more points you get:
- 1 goal difference: 1.5x multiplier
- 2 goal difference: 2x multiplier
- 3 goal difference: 2.5x multiplier
- And so on...

#### External Players
When friends who aren't registered join the game:
- They're assumed to have 1200 rating
- Each external player halves the K-factor for that game
- Example: 1 external player reduces K from 32 to 16

### Example Calculations

#### Example 1: Simple Game
```
Team A (average 1300) vs Team B (average 1100)
- Team A is expected to win (about 75% chance)
- If Team A wins 2-0:
  * Goal multiplier: 2x
  * Rating change ≈ +16 for Team A, -16 for Team B
- If Team B wins 1-0 (upset!):
  * Goal multiplier: 1.5x
  * Rating change ≈ +36 for Team B, -36 for Team A
```

#### Example 2: Game with External Player
```
Team A (1300, 1200, external) vs Team B (1200, 1150, 1250)
- External player counts as 1200
- Team A average = 1233, Team B average = 1200
- K-factor is halved due to external player
- If Team A wins 2-0:
  * Regular K-factor would give ±24 points
  * Halved K-factor gives ±12 points
```

#### Example 3: Tie Game
```
Team A (1300) vs Team B (1100)
- Team A expected to win (75% chance = 0.75 expected score)
- Game ends in a tie (0.5 actual score)
- Team A loses points: (0.5 - 0.75) * K = -8 points
- Team B gains points: (0.5 - 0.25) * K = +8 points
```

### Key Points to Remember
1. **Balanced System**: Points gained by winners = points lost by losers
2. **Uncertainty Protection**: External players reduce rating changes
3. **Quick Adjustment**: New players' ratings change faster
4. **Performance Reward**: Bigger wins = bigger rating changes
5. **Fair Ties**: In ties, the stronger team loses some points while the weaker team gains some

This means that over time:
- Active players find their true skill level
- Upsets are rewarded more than expected wins
- Dominant victories count more than close ones
- The system stays fair and balanced even with external players

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
- `/my_stats` - Shows your stats including ELO rating

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

Just open an issue or reach out!
