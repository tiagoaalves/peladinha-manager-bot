from database.base_manager import BaseManager


class EloManager(BaseManager):
    def __init__(self, player_manager):
        super().__init__()
        self.player_manager = player_manager
        self.k_factor = 32

    def calculate_elo_changes(self, game_id):
        """Calculate and apply ELO changes for a game"""
        game = (
            self.supabase.table("games").select("*").eq("id", game_id).execute().data[0]
        )
        players_data = (
            self.supabase.table("game_players")
            .select("*")
            .eq("game_id", game_id)
            .execute()
            .data
        )

        team_a = [p for p in players_data if p["team"] == "A"]
        team_b = [p for p in players_data if p["team"] == "B"]

        rating_a, rating_b = self._calculate_team_ratings(team_a, team_b)
        exp_a, exp_b = self._calculate_expected_scores(rating_a, rating_b)
        actual_a, actual_b = self._calculate_actual_scores(game)

        self._update_team_elo(team_a, actual_a, exp_a)
        self._update_team_elo(team_b, actual_b, exp_b)

    def _calculate_team_ratings(self, team_a, team_b):
        """Calculate average ratings for each team"""
        rating_a = sum(
            self.player_manager.get_player(p["player_id"])["elo_rating"] for p in team_a
        ) / len(team_a)
        rating_b = sum(
            self.player_manager.get_player(p["player_id"])["elo_rating"] for p in team_b
        ) / len(team_b)
        return rating_a, rating_b

    def _calculate_expected_scores(self, rating_a, rating_b):
        """Calculate expected scores based on ELO ratings"""
        exp_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        return exp_a, 1 - exp_a

    def _calculate_actual_scores(self, game):
        """Calculate actual scores based on game result"""
        if game["score_team_a"] > game["score_team_b"]:
            return 1, 0
        elif game["score_team_a"] < game["score_team_b"]:
            return 0, 1
        return 0.5, 0.5

    def _update_team_elo(self, team, actual, expected):
        """Update ELO ratings for all players in a team"""
        for player in team:
            delta = self.k_factor * (actual - expected)
            player_stats = self.player_manager.get_player(player["player_id"])
            new_elo = player_stats["elo_rating"] + round(delta)
            self.supabase.table("players").update({"elo_rating": new_elo}).eq(
                "id", player["player_id"]
            ).execute()
