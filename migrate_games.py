from datetime import datetime
import logging
from typing import List, Dict
from database.game import GameDBManager
from database.elo import EloDBManager
from database.player import PlayerDBManager
from migrate_players import PlayerMigration

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameHistoryProcessor:
    def __init__(self):
        self.player_db_manager = PlayerDBManager()
        self.game_db_manager = GameDBManager()
        self.elo_db_manager = EloDBManager()
        self.player_migration = PlayerMigration()
        self.external_counter = 1
        self.external_players = {}

    def process_game_data(self, raw_data: str) -> List[Dict]:
        """Process raw game data into structured format"""
        games = []
        current_game = None

        for line in raw_data.split("\n"):
            line = line.strip()
            if not line or line == "-------------------":
                if current_game:
                    games.append(current_game)
                    current_game = None
                continue

            if line.startswith("Game"):
                current_game = self._init_game(line)
            elif current_game and line.startswith("Score:"):
                self._process_score(current_game, line)
            elif current_game and (
                line.startswith("Team A:") or line.startswith("Team B:")
            ):
                self._process_team(current_game, line)

        if current_game:
            games.append(current_game)

        return games

    def _init_game(self, line: str) -> Dict:
        """Initialize a new game record"""
        # Extract date from line like "Game 1 - 28/06/2024"
        date_str = line.split(" - ")[1].strip()
        date = datetime.strptime(date_str, "%d/%m/%Y")

        return {
            "date": date.isoformat(),
            "team_a": [],
            "team_b": [],
            "score_a": None,
            "score_b": None,
        }

    def _process_score(self, game: Dict, line: str):
        """Process score line"""
        score_text = line.split(": ")[1].split(" ")[0]  # Remove "(Draw)" if present
        score_a, score_b = map(int, score_text.split("-"))
        game["score_a"] = score_a
        game["score_b"] = score_b

    def _process_team(self, game: Dict, line: str):
        """Process team line"""
        is_team_a = line.startswith("Team A:")
        team_data = line.split(": ")[1].split(", ")

        players = []
        for player_info in team_data:
            player_info = player_info.strip()
            is_captain = "(cap)" in player_info.lower()
            is_external = "(ext)" in player_info.lower()

            # Clean player name
            clean_name = player_info.lower()
            clean_name = clean_name.replace("(cap)", "").replace("(ext)", "").strip()

            logger.debug(
                f"Processing player: '{player_info}' -> cleaned: '{clean_name}'"
            )

            # Resolve player ID
            if is_external:
                player_id = self._get_external_id(clean_name)
                logger.debug(
                    f"Resolved external player '{clean_name}' to ID: {player_id}"
                )
            else:
                player_id, canonical = self.player_migration.resolve_player_name(
                    clean_name
                )
                logger.debug(
                    f"Resolved regular player '{clean_name}' to ID: {player_id} (canonical: {canonical})"
                )
                if not player_id:
                    logger.warning(f"Unrecognized regular player: {clean_name}")
                    continue

            players.append(
                {
                    "player_id": player_id,
                    "is_captain": is_captain,
                    "is_external": is_external,
                }
            )

        if is_team_a:
            game["team_a"] = players
        else:
            game["team_b"] = players

    def _get_external_id(self, name: str) -> int:
        """Get or create external player ID"""
        if name not in self.external_players:
            self.external_players[name] = -self.external_counter
            self.external_counter += 1
        return self.external_players[name]

    def save_games(self, games: List[Dict]) -> Dict[str, List]:
        """Save all games to database"""
        results = {"success": [], "failed": []}

        HISTORICAL_IMPORT_CHAT_ID = 999999  # Special chat_id for historical games

        for game in games:
            try:
                # Prepare player data for database
                players_data = []
                team_a_external_count = 0
                team_b_external_count = 0
                for team, team_letter in [(game["team_a"], "A"), (game["team_b"], "B")]:
                    for player in team:
                        if player["player_id"] > 0:  # Only include registered players
                            players_data.append(
                                {
                                    "id": player["player_id"],
                                    "team": team_letter,
                                    "was_captain": player["is_captain"],
                                    "was_mvp": False,  # MVP data not available in historical data
                                }
                            )
                        else:
                            if team_letter == "A":
                                team_a_external_count += 1
                            else:
                                team_b_external_count += 1

                # Save game
                game_id = self.game_db_manager.save_game(
                    chat_id=HISTORICAL_IMPORT_CHAT_ID,
                    score_team_a=game["score_a"],
                    score_team_b=game["score_b"],
                    players_data=players_data,
                    team_a_external_count=team_a_external_count,
                    team_b_external_count=team_b_external_count,
                )

                if game_id:
                    # Update player stats
                    self.player_db_manager.update_player_stats(
                        score_team_a=game["score_a"],
                        score_team_b=game["score_b"],
                        players_data=players_data,
                    )

                    # Process ELO ratings
                    self.elo_db_manager.process_game_ratings(game_id)

                    results["success"].append(game)
                else:
                    results["failed"].append(game)

            except Exception as e:
                logger.error(f"Error saving game: {e}")
                results["failed"].append(game)

        return results


def validate_game(game: Dict) -> List[str]:
    """Validate a single game and return list of issues"""
    issues = []

    # Check basic game structure
    if not game.get("date"):
        issues.append("Missing game date")
    if game.get("score_a") is None or game.get("score_b") is None:
        issues.append("Missing game score")

    # Validate teams
    for team_name, team in [("Team A", game["team_a"]), ("Team B", game["team_b"])]:
        if not team:
            issues.append(f"{team_name} has no players")

        # Check for duplicate players
        player_ids = [p["player_id"] for p in team]
        if len(player_ids) != len(set(player_ids)):
            issues.append(f"Duplicate players found in {team_name}")

        # Check captain count
        captains = [p for p in team if p["is_captain"]]
        if len(captains) > 1:
            issues.append(f"Multiple captains found in {team_name}")

    return issues


def dry_run(raw_data: str) -> Dict:
    """Perform a dry run of the game import process"""
    processor = GameHistoryProcessor()

    # Process games
    logger.info("Processing game data...")
    games = processor.process_game_data(raw_data)

    # Initialize results
    results = {
        "total_games": len(games),
        "valid_games": 0,
        "games_with_issues": 0,
        "total_players": set(),
        "external_players": set(),
        "issues_found": [],
        "games": [],
    }

    # Analyze each game
    for i, game in enumerate(games, 1):
        game_report = {
            "game_number": i,
            "date": game["date"],
            "score": f"{game['score_a']}-{game['score_b']}",
            "team_a": [],
            "team_b": [],
            "issues": validate_game(game),
        }

        # Track players
        for team, team_letter in [(game["team_a"], "A"), (game["team_b"], "B")]:
            for player in team:
                player_id = player["player_id"]

                # Get player name
                if player_id > 0:
                    # Get canonical name from player_data dictionary instead of resolving by ID
                    player_name = processor.player_migration.player_data.get(
                        player_id, {}
                    ).get("name", f"Unknown_{player_id}")
                    results["total_players"].add(player_id)
                else:
                    results["external_players"].add(player_id)
                    player_name = f"External_{-player_id}"

                logger.debug(f"Resolved player_id {player_id} to name {player_name}")

                # Add to game report
                player_info = {
                    "name": player_name,
                    "captain": player["is_captain"],
                    "external": player["is_external"],
                }

                if team_letter == "A":
                    game_report["team_a"].append(player_info)
                else:
                    game_report["team_b"].append(player_info)

        if game_report["issues"]:
            results["games_with_issues"] += 1
            results["issues_found"].extend(game_report["issues"])
        else:
            results["valid_games"] += 1

        results["games"].append(game_report)

    return results


def print_dry_run_results(results: Dict):
    """Print formatted results of the dry run"""
    logger.info("\n=== DRY RUN RESULTS ===")
    logger.info(f"\nSummary:")
    logger.info(f"Total games found: {results['total_games']}")
    logger.info(f"Valid games: {results['valid_games']}")
    logger.info(f"Games with issues: {results['games_with_issues']}")
    logger.info(f"Unique registered players: {len(results['total_players'])}")
    logger.info(f"Unique external players: {len(results['external_players'])}")

    if results["issues_found"]:
        logger.info("\nIssues Found:")
        for issue in set(results["issues_found"]):
            logger.info(f"- {issue}")

    logger.info("\nGame Details:")
    for game in results["games"]:
        logger.info(
            f"\nGame {game['game_number']} - {game['date']} (Score: {game['score']})"
        )

        logger.info("Team A:")
        for player in game["team_a"]:
            captain_mark = "(C)" if player["captain"] else ""
            external_mark = "(EXT)" if player["external"] else ""
            logger.info(f"  - {player['name']} {captain_mark} {external_mark}")

        logger.info("Team B:")
        for player in game["team_b"]:
            captain_mark = "(C)" if player["captain"] else ""
            external_mark = "(EXT)" if player["external"] else ""
            logger.info(f"  - {player['name']} {captain_mark} {external_mark}")

        if game["issues"]:
            logger.info("Issues:")
            for issue in game["issues"]:
                logger.info(f"  ! {issue}")


def test_name_resolution():
    """Test the player name resolution system"""
    processor = GameHistoryProcessor()

    # Test some sample names
    test_names = ["pantera", "Tsubastos", "NELSON", "gus", "tilhas", "bravo"]
    logger.info("\nTesting name resolution:")
    for name in test_names:
        player_id, canonical = processor.player_migration.resolve_player_name(name)
        logger.info(f"'{name}' -> ID: {player_id}, Canonical: {canonical}")

    # Show some name mappings
    logger.info("\nSample of name mappings:")
    mappings = list(processor.player_migration.name_mapping.items())[:5]
    for name, player_id in mappings:
        logger.info(f"{name} -> {player_id}")

    logger.info(f"\nTotal mappings: {len(processor.player_migration.name_mapping)}")


def main():
    # Test name resolution first
    test_name_resolution()

    # Read raw game data
    with open("game_history.txt", "r", encoding="utf-8") as f:
        raw_data = f.read()

    # Perform dry run
    results = dry_run(raw_data)
    print_dry_run_results(results)

    # Ask for confirmation before proceeding
    logger.warning(
        "\nIssues were found in the game data. Please review before proceeding."
    )
    proceed = input("\nWould you like to proceed with the import anyway? (yes/no): ")
    if proceed.lower() != "yes":
        logger.info("Import cancelled.")
        return

    # Proceed with actual import if confirmed
    logger.info("\nProceeding with database import...")
    processor = GameHistoryProcessor()
    games = processor.process_game_data(raw_data)
    results = processor.save_games(games)

    # Log final results
    logger.info(f"\nImport completed:")
    logger.info(f"Successfully saved {len(results['success'])} games")
    if results["failed"]:
        logger.error(f"Failed to save {len(results['failed'])} games")
        for game in results["failed"]:
            logger.error(f"Failed game from {game['date']}")


if __name__ == "__main__":
    main()
