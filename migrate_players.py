import logging
from typing import Dict, List, Set

from database.base import BaseManager
from database.player import PlayerDBManager
from models.player import Player

# Set up logging
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlayerMigration:
    def __init__(self):
        self.base_manager = BaseManager()
        self.player_db_manager = PlayerDBManager()

        # Core player data with IDs and name mappings
        self.player_data = {
            2001: {"name": "Barrote", "aliases": {"barrote"}},
            2002: {"name": "Beiças", "aliases": {"beiças", "beicas"}},
            2003: {"name": "Bravo", "aliases": {"bravo"}},
            2004: {"name": "Brocas", "aliases": {"brocas"}},
            2005: {"name": "C4", "aliases": {"c4"}},
            2006: {
                "name": "Camélias",
                "aliases": {"camelias", "camélias", "camelias", "mira"},
            },
            2007: {"name": "Carvas", "aliases": {"carvas"}},
            2008: {"name": "Gus", "aliases": {"gus"}},
            2009: {"name": "Harlem", "aliases": {"harlem"}},
            2010: {"name": "Lagosta", "aliases": {"lagosta"}},
            2011: {"name": "Luís Lima", "aliases": {"luis lima", "luís lima"}},
            2012: {"name": "Miguel Keeper", "aliases": {"miguel keeper"}},
            2014: {"name": "Nelson", "aliases": {"nelson"}},
            2015: {"name": "Pantera", "aliases": {"pantera"}},
            2016: {"name": "Perineo", "aliases": {"perineo"}},
            2017: {"name": "Picasso", "aliases": {"picasso"}},
            2018: {"name": "Potro", "aliases": {"potro"}},
            2019: {
                "name": "SaCanhao",
                "aliases": {"sacanhao", "sa canhao", "sá canhao"},
            },
            2020: {"name": "Seringas", "aliases": {"seringas"}},
            2021: {"name": "Stennis", "aliases": {"stennis", "stenis"}},
            2022: {"name": "Teres", "aliases": {"teres"}},
            2023: {"name": "Tilhas", "aliases": {"tilhas"}},
            2024: {"name": "Toine", "aliases": {"toine"}},
            2025: {"name": "Tsubastos", "aliases": {"tsubastos"}},
            2026: {"name": "Zé Fernandes", "aliases": {"zé fernandes", "ze fernandes"}},
        }

        # Create reverse mapping for name resolution
        self.name_mapping = {}
        for player_id, data in self.player_data.items():
            for alias in data["aliases"]:
                self.name_mapping[alias] = player_id
            # Also map the canonical name
            self.name_mapping[data["name"].lower()] = player_id

    def register_players(self) -> Dict[str, List[str]]:
        """Register all players in the database"""
        results = {"success": [], "failed": []}

        for player_id, player_data in self.player_data.items():
            try:
                # Create mock telegram user
                class MockTelegramUser:
                    def __init__(self, user_id, username):
                        self.id = user_id
                        self.username = username

                # Create mock user with canonical name as username
                mock_user = MockTelegramUser(
                    user_id=player_id,
                    username=player_data["name"].lower().replace(" ", "_"),
                )

                # Create player instance
                player = Player(
                    telegram_user=mock_user, display_name=player_data["name"]
                )

                # Attempt to register
                if self.player_db_manager.create_player(player):
                    results["success"].append(player_data["name"])
                    logger.info(f"Successfully registered {player_data['name']}")
                else:
                    results["failed"].append(player_data["name"])
                    logger.error(f"Failed to register {player_data['name']}")

            except Exception as e:
                results["failed"].append(player_data["name"])
                logger.error(f"Error registering {player_data['name']}: {e}")

        return results

    def resolve_player_name(self, name: str) -> tuple[int | None, str | None]:
        """
        Resolve a player name to their ID and canonical name
        Returns (player_id, canonical_name) or (None, None) if not found
        """
        player_id = self.name_mapping.get(name.lower())
        if player_id:
            return player_id, self.player_data[player_id]["name"]
        return None, None

    def get_all_known_names(self) -> Set[str]:
        """Get set of all known player names and aliases"""
        return set(self.name_mapping.keys())


def main():
    migration = PlayerMigration()

    # Register players
    logger.info("Starting player registration...")
    results = migration.register_players()

    # Log results
    logger.info(f"Successfully registered {len(results['success'])} players:")
    for player in results["success"]:
        logger.info(f"✓ {player}")

    if results["failed"]:
        logger.error(f"\nFailed to register {len(results['failed'])} players:")
        for player in results["failed"]:
            logger.error(f"✗ {player}")

    # Example of name resolution
    test_names = ["camelias", "Luís Lima", "stennis", "stenis"]
    logger.info("\nTesting name resolution:")
    for name in test_names:
        player_id, canonical = migration.resolve_player_name(name)
        logger.info(f"'{name}' -> {canonical} (ID: {player_id})")


if __name__ == "__main__":
    main()
