from datetime import datetime
from database.base import BaseManager
from models.user import Player


class PlayerDBManager(BaseManager):
    def create_player(self, user):
        """Create or update player record"""
        try:
            player_data = user.to_dict()
            result = self.supabase.table("players").upsert(player_data).execute()
            return Player.from_db(result.data[0]) if result.data else None
        except Exception as e:
            print(f"Error saving player: {e}")
            return None

    def get_player(self, player_id):
        """Get player statistics"""
        try:
            result = (
                self.supabase.table("players").select("*").eq("id", player_id).execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting player stats: {e}")
            return None

    def get_leaderboard(self, min_games=5):
        """Get top players by ELO rating"""
        return (
            self.supabase.table("players")
            .select("*")
            .gte("games_played", min_games)
            .order("elo_rating", desc=True)
            .limit(10)
            .execute()
        )

    def update_player_stats(self, score_team_a, score_team_b, players_data):
        """Update statistics for all players in a game"""
        for player_data in players_data:
            player = self.get_player(player_data["id"])
            if not player:
                continue

            new_stats = self._calculate_player_stats(
                player, player_data, score_team_a, score_team_b
            )

            try:
                self.supabase.table("players").update(new_stats).eq(
                    "id", player_data["id"]
                ).execute()
            except Exception as e:
                print(f"Error updating stats for player {player_data['id']}: {e}")

    def _calculate_player_stats(self, player, player_data, score_team_a, score_team_b):
        """Helper method to calculate new player stats"""
        is_team_a = player_data["team"] == "A"
        player_score = score_team_a if is_team_a else score_team_b
        opponent_score = score_team_b if is_team_a else score_team_a

        won = player_score > opponent_score
        tied = player_score == opponent_score

        new_stats = dict(player)
        new_stats["games_played"] = player["games_played"] + 1
        new_stats["last_played"] = datetime.utcnow().isoformat()

        if tied:
            new_stats["games_drawn"] = player["games_drawn"] + 1
            new_stats["current_streak"] = 0
        elif won:
            new_stats["games_won"] = player["games_won"] + 1
            new_stats["current_streak"] = max(1, player["current_streak"] + 1)
        else:
            new_stats["games_lost"] = player["games_lost"] + 1
            new_stats["current_streak"] = min(-1, player["current_streak"] - 1)

        if player_data["was_captain"]:
            new_stats["times_captain"] = player["times_captain"] + 1
        if player_data["was_mvp"]:
            new_stats["times_mvp"] = player["times_mvp"] + 1

        new_stats["best_streak"] = max(
            player["best_streak"], new_stats["current_streak"]
        )
        new_stats["worst_streak"] = min(
            player["worst_streak"], new_stats["current_streak"]
        )

        new_stats.pop("id", None)
        new_stats.pop("created_at", None)

        return new_stats
