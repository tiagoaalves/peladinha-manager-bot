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
    goal_difference_factor: float = 0.25


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

        print(current_ratings)
        print(new_ratings)
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

            # Fetch player data
            result = (
                self.supabase.table("game_players")
                .select("*")
                .eq("game_id", game_id)
                .execute()
            )
            players_data = result.data if result.data else []

            # Separate players by team
            team_a = [p for p in players_data if p["team"] == "A"]
            team_b = [p for p in players_data if p["team"] == "B"]

            # Get current ratings
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
            # Calculate new ratings
            new_ratings = self.calculate_game_adjustments(
                team_a,
                team_b,
                game["score_team_a"],
                game["score_team_b"],
                current_ratings,
            )

            # Update ratings in database
            for player_id, new_rating in new_ratings.items():
                self.supabase.table("players").update({"elo_rating": new_rating}).eq(
                    "id", player_id
                ).execute()

            return True

        except Exception as e:
            self.logger.error(f"Error processing ratings for game {game_id}: {str(e)}")
            return False
