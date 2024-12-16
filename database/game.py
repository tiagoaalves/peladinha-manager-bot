from datetime import datetime

from database.base import BaseManager


class GameDBManager(BaseManager):
    def save_game(self, chat_id, score_team_a, score_team_b, players_data):
        """Save game results and player participations"""
        game_data = {
            "chat_id": str(chat_id),
            "score_team_a": score_team_a,
            "score_team_b": score_team_b,
            "played_at": datetime.utcnow().isoformat(),
        }

        try:
            result = self.supabase.table("games").insert(game_data).execute()
            if not result.data:
                return None

            game_id = result.data[0]["id"]
            self._save_player_participations(game_id, players_data)
            return game_id
        except Exception as e:
            print(f"Error saving game: {e}")
            return None

    def _save_player_participations(self, game_id, players_data):
        """Helper method to save player participations"""
        for player_data in players_data:
            participation_data = {
                "game_id": game_id,
                "player_id": player_data["id"],
                "team": player_data["team"],
                "was_captain": player_data["was_captain"],
                "was_mvp": player_data["was_mvp"],
            }
            self.supabase.table("game_players").insert(participation_data).execute()

    def update_game_score(self, game_id, score_a, score_b):
        """Update the score for a game"""
        try:
            self.supabase.table("games").update(
                {"score_team_a": score_a, "score_team_b": score_b}
            ).eq("id", game_id).execute()
            return True
        except Exception as e:
            print(f"Error updating game score: {e}")
            return False
