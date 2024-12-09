class SoccerGame:
    def __init__(self):
        self.players = []
        self.max_players = 14
        self.captains = []
        self.teams = {"Team A": [], "Team B": []}
        self.current_selector = None
        self.game_state = "WAITING"
        self.mvp_votes = {}
        self.draft_method = None
        self.selection_round = 0
