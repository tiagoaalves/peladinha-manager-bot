class BotUser:
    def __init__(self, telegram_user, game_username=None):
        self.id = telegram_user.id
        self.first_name = telegram_user.first_name
        self.last_name = telegram_user.last_name
        self.username = game_username or telegram_user.username
