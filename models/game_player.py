class GamePlayer:
    """
    Game Player model representing a loaded Player in the game.
    """

    def __init__(self, id, telegram_user=None, display_name=None):
        self.id = telegram_user.id
        self.telegram_user = telegram_user
        self.display_name = display_name
