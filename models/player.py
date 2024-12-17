class Player:
    """
    Player model representing a user in the game system.
    Can be instantiated either from a Telegram user or from database records.
    """

    def __init__(self, telegram_user=None, display_name=None):
        if telegram_user:
            self.id = telegram_user.id
            self.username = telegram_user.username
            self.display_name = display_name
            self.elo_rating = 1200  # Default for new players
            self.games_played = 0
            self.games_won = 0
            self.games_lost = 0
            self.games_drawn = 0
            self.current_streak = 0
            self.best_streak = 0
            self.worst_streak = 0
            self.times_captain = 0
            self.times_mvp = 0
            self.last_played = None

    @classmethod
    def from_db(cls, db_record):
        """
        Create a Player instance from a database record.

        Args:
            db_record (dict): Player data from database

        Returns:
            Player: New Player instance with database values
        """
        player = cls()  # Create empty player instance
        player.id = db_record["id"]
        player.username = db_record["username"]
        player.elo_rating = db_record["elo_rating"]
        player.games_played = db_record["games_played"]
        player.games_won = db_record["games_won"]
        player.games_lost = db_record["games_lost"]
        player.games_drawn = db_record["games_drawn"]
        player.current_streak = db_record["current_streak"]
        player.best_streak = db_record["best_streak"]
        player.worst_streak = db_record["worst_streak"]
        player.times_captain = db_record["times_captain"]
        player.times_mvp = db_record["times_mvp"]
        player.last_played = db_record["last_played"]
        player.display_name = db_record["display_name"]
        return player

    def to_dict(self):
        """
        Convert player instance to dictionary for database storage.

        Returns:
            dict: Player data ready for database insertion/update
        """
        return {
            "id": self.id,
            "username": self.username,
            "elo_rating": self.elo_rating,
            "games_played": self.games_played,
            "games_won": self.games_won,
            "games_lost": self.games_lost,
            "games_drawn": self.games_drawn,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "worst_streak": self.worst_streak,
            "times_captain": self.times_captain,
            "times_mvp": self.times_mvp,
            "last_played": self.last_played,
            "display_name": self.display_name,
        }
