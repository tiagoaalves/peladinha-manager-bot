from database.base import BaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlayerIdUpdater(BaseManager):
    def __init__(self):
        super().__init__()
        self.old_id = 2015
        self.new_id = 7979760985

    def validate_player(self):
        """Verify player exists and get their current data"""
        try:
            result = (
                self.supabase.table("players")
                .select("*")
                .eq("id", self.old_id)
                .execute()
            )
            if not result.data:
                raise Exception(f"No player found with ID {self.old_id}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error validating player: {e}")
            raise

    def check_new_id_conflicts(self):
        """Check if new ID exists and get its data if it does"""
        try:
            result = (
                self.supabase.table("players")
                .select("*")
                .eq("id", self.new_id)
                .execute()
            )
            if result.data:
                logger.warning(f"Found existing player with ID {self.new_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error checking for ID conflicts: {e}")
            raise

    def update_player_id(self):
        """Update player ID across all relevant tables"""
        try:
            # Start by validating the player exists
            player_data = self.validate_player()
            logger.info(f"Found player to update: {player_data['display_name']}")

            # Check for existing new ID
            existing_player = self.check_new_id_conflicts()

            if existing_player:
                logger.info(
                    f"Found existing player with ID {self.new_id}: {existing_player['display_name']}"
                )

                # We'll keep the existing player's display_name
                player_data["display_name"] = existing_player["display_name"]
                player_data["username"] = existing_player.get(
                    "username"
                )  # Also update username if available

                # Remove existing player's games first
                logger.info(
                    f"Removing existing game participations for ID {self.new_id}..."
                )
                self.supabase.table("game_players").delete().eq(
                    "player_id", self.new_id
                ).execute()

                # Remove existing player record
                logger.info(f"Removing existing player record for ID {self.new_id}...")
                self.supabase.table("players").delete().eq("id", self.new_id).execute()

            # 1. Create new player record first
            logger.info("Creating new player record...")
            # Remove the id from player_data as we're changing it
            player_data.pop("id", None)
            # Insert new record with potentially updated display_name
            self.supabase.table("players").insert(
                {"id": self.new_id, **player_data}
            ).execute()

            # 2. Update game_players table (foreign key references)
            logger.info("Updating game participations...")
            self.supabase.table("game_players").update({"player_id": self.new_id}).eq(
                "player_id", self.old_id
            ).execute()

            # 3. Delete old player record
            logger.info("Removing old player record...")
            self.supabase.table("players").delete().eq("id", self.old_id).execute()

            logger.info(
                f"Successfully updated player ID from {self.old_id} to {self.new_id}"
            )
            if existing_player:
                logger.info(f"Updated display_name to: {player_data['display_name']}")
            return True

        except Exception as e:
            logger.error(f"Error updating player ID: {e}")
            return False


def main():
    updater = PlayerIdUpdater()

    # Perform validation and conflict checks
    try:
        logger.info("Performing validation checks...")

        # Check source player
        player_data = updater.validate_player()
        logger.info(f"\nPlayer to update:")
        logger.info(f"Name: {player_data['display_name']}")
        logger.info(f"Current stats:")
        logger.info(f"- Games played: {player_data['games_played']}")
        logger.info(
            f"- Wins/Losses/Draws: {player_data['games_won']}/{player_data['games_lost']}/{player_data['games_drawn']}"
        )
        logger.info(f"- ELO Rating: {player_data['elo_rating']}")

        # Check for ID conflicts
        existing_player = updater.check_new_id_conflicts()
        if existing_player:
            logger.info(f"\nFound existing player with new ID:")
            logger.info(f"Name: {existing_player['display_name']}")
            logger.info(f"Stats: (These will be replaced)")
            logger.info(f"- Games played: {existing_player['games_played']}")
            logger.info(
                f"- Wins/Losses/Draws: {existing_player['games_won']}/{existing_player['games_lost']}/{existing_player['games_drawn']}"
            )
            logger.info(f"- ELO Rating: {existing_player['elo_rating']}")
            logger.info(f"\nWill use display name: {existing_player['display_name']}")

        proceed = input(
            f"\nProceed with ID update{' and name update' if existing_player else ''}? (yes/no): "
        )
        if proceed.lower() == "yes":
            if updater.update_player_id():
                logger.info("Player ID updated successfully!")
            else:
                logger.error("Failed to update player ID")
        else:
            logger.info("Update cancelled")

    except Exception as e:
        logger.error(f"Validation failed: {e}")


if __name__ == "__main__":
    main()
