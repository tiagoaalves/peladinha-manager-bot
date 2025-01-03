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
        self.score = {"Team A": None, "Team B": None}
        self.db_game_id = None
        self.join_message_id = None
        self.teams_message_id = None
        self.team_b_white = None
        self.captain_selection_method = None
