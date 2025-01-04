from dataclasses import dataclass
from typing import List, Dict, Tuple
import math
import logging

from database.base import BaseManager


@dataclass
class EloConfig:
    base_k: int = 32
    min_k: int = 16
    max_k: int = 48
    default_rating: int = 1200
    goal_difference_factor: float = 0.1


class EloDBManager(BaseManager):
    def __init__(self):
        super().__init__()
        self.config = EloConfig()
        self.logger = logging.getLogger(__name__)

    def calculate_game_adjustments(
        self,
        team_a_players: List[Dict],
        team_b_players: List[Dict],
        team_a_score: int,
        team_b_score: int,
        current_ratings: Dict[int, int],
    ) -> Dict[int, int]:
        """Calculate ELO adjustments for all players in a game"""
        # Count external players (negative IDs)
        num_external = len(
            [p for p in team_a_players + team_b_players if p["player_id"] < 0]
        )
        print(f"External players: {num_external}")

        # Calculate team ratings including assumed external player ratings
        team_a_rating = self._calculate_team_rating(team_a_players, current_ratings)
        team_b_rating = self._calculate_team_rating(team_b_players, current_ratings)
        print(f"Team A rating: {team_a_rating}")
        print(f"Team B rating: {team_b_rating}")

        # Calculate expected scores
        exp_score_a = self._expected_score(team_a_rating, team_b_rating)
        exp_score_b = 1 - exp_score_a
        print(f"Expected scores: {exp_score_a}, {exp_score_b}")
        print(f"Actual scores: {team_a_score}, {team_b_score}")

        # Calculate actual scores and goal difference factor
        actual_score_a, actual_score_b = self._calculate_actual_scores(
            team_a_score, team_b_score
        )
        goal_diff_factor = self._calculate_goal_difference_factor(
            team_a_score, team_b_score
        )

        new_ratings = {}

        # Process Team A registered players
        for player in team_a_players:
            if player["player_id"] > 0:  # Only process registered players
                k_factor = self._calculate_k_factor(
                    player.get("games_played", 0), num_external
                )
                rating_change = (
                    k_factor * goal_diff_factor * (actual_score_a - exp_score_a)
                )
                current_rating = current_ratings.get(
                    player["player_id"], self.config.default_rating
                )
                new_ratings[player["player_id"]] = round(current_rating + rating_change)

        # Process Team B registered players
        for player in team_b_players:
            if player["player_id"] > 0:  # Only process registered players
                k_factor = self._calculate_k_factor(
                    player.get("games_played", 0), num_external
                )
                rating_change = (
                    k_factor * goal_diff_factor * (actual_score_b - exp_score_b)
                )
                current_rating = current_ratings.get(
                    player["player_id"], self.config.default_rating
                )
                new_ratings[player["player_id"]] = round(current_rating + rating_change)

        print(f"Current ratings: {current_ratings}")
        print(f"New ratings: {new_ratings}")

        return new_ratings

    def _calculate_team_rating(
        self, players: List[Dict], current_ratings: Dict[int, int]
    ) -> float:
        """Calculate average rating for a team, including external players"""
        if not players:
            return self.config.default_rating

        total_rating = 0
        for player in players:
            if player["player_id"] > 0:
                total_rating += current_ratings.get(
                    player["player_id"], self.config.default_rating
                )
            else:
                total_rating += self.config.default_rating  # External player

        return total_rating / len(players)

    def _expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score using ELO formula"""
        return 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))

    def _calculate_actual_scores(
        self, score_a: int, score_b: int
    ) -> Tuple[float, float]:
        """Calculate actual scores based on match result"""
        if score_a > score_b:
            return 1.0, 0.0
        elif score_b > score_a:
            return 0.0, 1.0
        return 0.5, 0.5

    def _calculate_goal_difference_factor(self, score_a: int, score_b: int) -> float:
        """Calculate multiplier based on goal difference"""
        goal_diff = abs(score_a - score_b)
        return 1 + (goal_diff * self.config.goal_difference_factor)

    def _calculate_k_factor(self, games_played: int, num_external: int) -> float:
        """Calculate K-factor based on experience and number of external players"""
        # Base K-factor based on experience
        if games_played < 10:
            base_k = self.config.max_k
        elif games_played < 20:
            base_k = self.config.base_k
        else:
            base_k = self.config.min_k

        # Reduce K-factor for external players
        return base_k * (0.5**num_external)

    def process_game_ratings(self, game_id: int) -> bool:
        """Process ELO rating changes for a completed game"""
        try:
            # Fetch game data
            result = (
                self.supabase.table("games").select("*").eq("id", game_id).execute()
            )
            game = result.data[0] if result.data else None
            if not game:
                self.logger.error(f"Game {game_id} not found")
                return False

            print(f"Date: {game['played_at']}")

            # Fetch player data
            result = (
                self.supabase.table("game_players")
                .select("*")
                .eq("game_id", game_id)
                .execute()
            )
            players_data = result.data if result.data else []

            # Create virtual players for external players
            external_players = []
            if game.get("team_a_external_count", 0) > 0:
                for i in range(game["team_a_external_count"]):
                    external_player = {
                        "player_id": -(
                            game_id * 100 + i + 1
                        ),  # Ensures unique negative IDs
                        "team": "A",
                        "is_captain": False,
                        "is_mvp": False,
                    }
                    players_data.append(external_player)
                    external_players.append(external_player["player_id"])

            if game.get("team_b_external_count", 0) > 0:
                for i in range(game["team_b_external_count"]):
                    external_player = {
                        "player_id": -(game_id * 100 + len(external_players) + i + 1),
                        "team": "B",
                        "is_captain": False,
                        "is_mvp": False,
                    }
                    players_data.append(external_player)
                    external_players.append(external_player["player_id"])

            # Separate players by team
            team_a = [p for p in players_data if p["team"] == "A"]
            team_b = [p for p in players_data if p["team"] == "B"]

            # Get current ratings for registered players
            all_player_ids = [
                p["player_id"] for p in players_data if p["player_id"] > 0
            ]
            result = (
                self.supabase.table("players")
                .select("id,elo_rating")
                .in_("id", all_player_ids)
                .execute()
            )
            current_ratings = (
                {p["id"]: p["elo_rating"] for p in result.data} if result.data else {}
            )

            # Add ratings for external players
            for external_id in external_players:
                current_ratings[external_id] = (
                    1200  # Default rating for external players
                )

            # Calculate new ratings
            new_ratings = self.calculate_game_adjustments(
                team_a,
                team_b,
                game["score_team_a"],
                game["score_team_b"],
                current_ratings,
            )

            # Update ratings in database (only for registered players)
            for player_id, new_rating in new_ratings.items():
                if player_id > 0:  # Only update ratings for registered players
                    self.supabase.table("players").update(
                        {"elo_rating": new_rating}
                    ).eq("id", player_id).execute()

            print("--- Ratings updated ---\n\n")

            return True

        except Exception as e:
            self.logger.error(f"Error processing ratings for game {game_id}: {str(e)}")
            return False

    def get_pregame_analysis(
        self,
        team_a_players: List[Dict],
        team_b_players: List[Dict],
        current_ratings: Dict[int, int],
    ) -> Dict:
        """
        Calculate pre-game analysis including team ratings and expected outcomes.

        Args:
            team_a_players: List of player dictionaries for team A
            team_b_players: List of player dictionaries for team B
            current_ratings: Dictionary of current ELO ratings for all players

        Returns:
            Dictionary containing team ratings and expected outcomes
        """
        # Calculate team ratings
        team_a_rating = self._calculate_team_rating(team_a_players, current_ratings)
        team_b_rating = self._calculate_team_rating(team_b_players, current_ratings)

        # Calculate expected score
        expected_score_a = self._expected_score(team_a_rating, team_b_rating)
        expected_score_b = 1 - expected_score_a

        # Expected goals (rough approximation based on average goals per game)
        avg_goals_per_game = 12  # Can be adjusted based on league average
        expected_goals_a = round(expected_score_a * avg_goals_per_game, 1)
        expected_goals_b = round(expected_score_b * avg_goals_per_game, 1)

        return {
            "team_a_rating": round(team_a_rating),
            "team_b_rating": round(team_b_rating),
            "team_a_win_prob": round(expected_score_a * 100),
            "team_b_win_prob": round(expected_score_b * 100),
            "expected_goals_a": expected_goals_a,
            "expected_goals_b": expected_goals_b,
        }

    def get_pregame_analysis_from_game(self, game) -> Dict:
        """
        Get pre-game analysis for a game, handling all data preparation internally.

        Args:
            game: Game object with teams and players

        Returns:
            Dictionary containing team ratings and expected outcomes
        """
        # Convert game teams to the format needed for calculations
        team_a_players = [
            {"player_id": p.id, "team": "A"} for p in game.teams["Team A"]
        ]
        team_b_players = [
            {"player_id": p.id, "team": "B"} for p in game.teams["Team B"]
        ]

        # Get current ratings for all players
        all_player_ids = [p.id for p in game.players if p.id > 0]
        result = (
            self.supabase.table("players")
            .select("id,elo_rating")
            .in_("id", all_player_ids)
            .execute()
        )
        current_ratings = (
            {p["id"]: p["elo_rating"] for p in result.data} if result.data else {}
        )

        return self.get_pregame_analysis(
            team_a_players, team_b_players, current_ratings
        )
