from datetime import datetime

from database.base import BaseManager
from models.game import SoccerGame
from models.game_player import GamePlayer


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

    def save_active_game_players(self, chat_id: str, players: list):
        """Save just the players in an active game"""
        game_state = {
            "chat_id": str(chat_id),
            "player_ids": [p.id for p in players],
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self.supabase.table("active_games").upsert(game_state).execute()
        except Exception as e:
            print(f"Error saving game players: {e}")

    def load_active_games(self) -> dict:
        """Load active games and reconstruct GamePlayer objects"""
        try:
            result = self.supabase.table("active_games").select("*").execute()
            games = {}

            for game_data in result.data:
                game = SoccerGame()
                if game_data["player_ids"]:
                    players_result = (
                        self.supabase.table("players")
                        .select("id, display_name")
                        .in_("id", game_data["player_ids"])
                        .execute()
                    )

                    for player_info in players_result.data:
                        game_player = GamePlayer(
                            id=player_info["id"],
                            telegram_user=None,
                            display_name=player_info["display_name"],
                        )
                        game.players.append(game_player)

                games[game_data["chat_id"]] = game
            return games
        except Exception as e:
            print(f"Error loading active games: {e}")
            return {}

    def remove_active_game(self, chat_id):
        """Remove game from active games when completed"""
        try:
            self.supabase.table("active_games").delete().eq(
                "chat_id", str(chat_id)
            ).execute()
        except Exception as e:
            print(f"Error removing active game: {e}")
