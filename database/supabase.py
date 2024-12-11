from supabase import create_client
import os
from datetime import datetime

class SupabaseManager:
    def __init__(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        try:
            self.supabase = create_client(supabase_url, supabase_key)
            print("Supabase client created successfully")
        except Exception as e:
            print(f"Error creating Supabase client: {e}")
            raise

    def create_player(self, user):
        """Create or update player record"""
        print(f"\nCreating/updating player: {user.first_name}")
        
        # Safely get attributes that might not exist
        player_data = {
            'id': user.id,
            'username': getattr(user, 'username', None),
            'first_name': user.first_name,
            'last_name': getattr(user, 'last_name', None),
            'elo_rating': 1200,
            'games_played': 0,
            'games_won': 0,
            'games_lost': 0,
            'games_drawn': 0,
            'current_streak': 0,
            'best_streak': 0,
            'worst_streak': 0,
            'times_captain': 0,
            'times_mvp': 0,
            'last_played': datetime.utcnow().isoformat()
        }
        
        try:
            result = self.supabase.table('players').upsert(player_data).execute()
            print(f"Player save result: {result.data}")
            return result
        except Exception as e:
            print(f"Error saving player: {e}")
            # Log the error but don't raise it
            return None

    def save_game(self, chat_id, score_team_a, score_team_b, players_data):
        """Save game results and player participations"""
        game_data = {
            'chat_id': str(chat_id),
            'score_team_a': score_team_a,
            'score_team_b': score_team_b,
            'played_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Insert game record
            result = self.supabase.table('games').insert(game_data).execute()
            if not result.data:
                return None
                
            game_id = result.data[0]['id']
            
            # Save player participations
            for player_data in players_data:
                participation_data = {
                    'game_id': game_id,
                    'player_id': player_data['id'],
                    'team': player_data['team'],
                    'was_captain': player_data['was_captain'],
                    'was_mvp': player_data['was_mvp']
                }
                self.supabase.table('game_players').insert(participation_data).execute()
            
            return game_id
            
        except Exception as e:
            print(f"Error saving game: {e}")
            return None
        
    def _update_player_stats(self, score_team_a, score_team_b, players_data):
        """Update statistics for all players in a game"""
        for player_data in players_data:
            player = self.get_player_stats(player_data['id'])
            
            is_team_a = player_data['team'] == 'A'
            player_score = score_team_a if is_team_a else score_team_b
            opponent_score = score_team_b if is_team_a else score_team_a
            
            # Calculate result
            won = player_score > opponent_score
            tied = player_score == opponent_score
            
            # Update stats
            new_stats = {
                'games_played': player['games_played'] + 1,
                'last_played': datetime.utcnow().isoformat()
            }
            
            if tied:
                new_stats['games_drawn'] = player['games_drawn'] + 1
                new_stats['current_streak'] = 0
            elif won:
                new_stats['games_won'] = player['games_won'] + 1
                new_stats['current_streak'] = max(1, player['current_streak'] + 1)
            else:
                new_stats['games_lost'] = player['games_lost'] + 1
                new_stats['current_streak'] = min(-1, player['current_streak'] - 1)
            
            if player_data['was_captain']:
                new_stats['times_captain'] = player['times_captain'] + 1
            if player_data['was_mvp']:
                new_stats['times_mvp'] = player['times_mvp'] + 1
                
            # Update streaks
            new_stats['best_streak'] = max(player['best_streak'], new_stats['current_streak'])
            new_stats['worst_streak'] = min(player['worst_streak'], new_stats['current_streak'])
            
            # Update player record
            self.supabase.table('players').update(new_stats).eq('id', player_data['id']).execute()

    def get_player_stats(self, player_id):
        """Get player statistics"""
        result = self.supabase.table('players').select('*').eq('id', player_id).execute()
        return result.data[0] if result.data else None

    def get_leaderboard(self, min_games=5):
        """Get top players by ELO rating"""
        return self.supabase.table('players')\
            .select('*')\
            .gte('games_played', min_games)\
            .order('elo_rating', desc=True)\
            .limit(10)\
            .execute()

    def calculate_elo_changes(self, game_id):
        """Calculate and apply ELO changes for a game"""
        k_factor = 32  # Standard chess K-factor
        
        # Get game data
        game = self.supabase.table('games').select('*').eq('id', game_id).execute().data[0]
        
        # Get players by team
        players_data = self.supabase.table('game_players').select('*').eq('game_id', game_id).execute().data
        team_a = [p for p in players_data if p['team'] == 'A']
        team_b = [p for p in players_data if p['team'] == 'B']
        
        # Calculate team ratings
        rating_a = sum(self.get_player_stats(p['player_id'])['elo_rating'] for p in team_a) / len(team_a)
        rating_b = sum(self.get_player_stats(p['player_id'])['elo_rating'] for p in team_b) / len(team_b)
        
        # Calculate expected scores
        exp_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        exp_b = 1 - exp_a
        
        # Calculate actual scores
        if game['score_team_a'] > game['score_team_b']:
            actual_a, actual_b = 1, 0
        elif game['score_team_a'] < game['score_team_b']:
            actual_a, actual_b = 0, 1
        else:
            actual_a = actual_b = 0.5
        
        # Update each player's ELO
        for player in team_a:
            delta = k_factor * (actual_a - exp_a)
            player_stats = self.get_player_stats(player['player_id'])
            new_elo = player_stats['elo_rating'] + round(delta)
            self.supabase.table('players').update({'elo_rating': new_elo}).eq('id', player['player_id']).execute()
            
        for player in team_b:
            delta = k_factor * (actual_b - exp_b)
            player_stats = self.get_player_stats(player['player_id'])
            new_elo = player_stats['elo_rating'] + round(delta)
            self.supabase.table('players').update({'elo_rating': new_elo}).eq('id', player['player_id']).execute()

    def update_mvp(self, game_id, mvp_ids):
        """Update MVP status for players in a game"""
        try:
            for mvp_id in mvp_ids:
                # Skip external players
                if mvp_id < 0:
                    continue
                    
                # Update game_players table
                self.supabase.table('game_players')\
                    .update({'was_mvp': True})\
                    .eq('game_id', game_id)\
                    .eq('player_id', mvp_id)\
                    .execute()
                
                # Get and update player MVP count
                player_result = self.supabase.table('players')\
                    .select('times_mvp')\
                    .eq('id', mvp_id)\
                    .single()\
                    .execute()
                
                if player_result.data:
                    current_mvp_count = player_result.data['times_mvp']
                    self.supabase.table('players')\
                        .update({'times_mvp': current_mvp_count + 1})\
                        .eq('id', mvp_id)\
                        .execute()
            
            return True
        except Exception as e:
            print(f"Error updating MVP status: {e}")
            return False

    def update_game_score(self, game_id, score_a, score_b):
        """Update the score for a game"""
        try:
            self.supabase.table('games')\
                .update({
                    'score_team_a': score_a,
                    'score_team_b': score_b
                })\
                .eq('id', game_id)\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error updating game score: {e}")
            return False
