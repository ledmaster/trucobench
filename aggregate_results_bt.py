#!/usr/bin/env python3
import os
import glob
import re
import json
import math
import numpy as np
from scipy import optimize

def bradley_terry_scores(wins_matrix):
    """Calculate Bradley-Terry scores from a wins matrix"""
    n_players = len(wins_matrix)
    
    def bt_likelihood(ratings):
        # Normalize ratings to sum to 0
        ratings = ratings - np.mean(ratings)
        total_ll = 0
        for i in range(n_players):
            for j in range(n_players):
                if i != j:
                    # Calculate probability of i beating j
                    p_ij = 1 / (1 + np.exp(-(ratings[i] - ratings[j])))
                    # Add to log likelihood
                    if wins_matrix[i][j] > 0:
                        total_ll += wins_matrix[i][j] * np.log(p_ij)
        return -total_ll  # Return negative since we're minimizing

    # Initial guess: all players equal
    initial_ratings = np.zeros(n_players)
    
    # Optimize to find maximum likelihood ratings
    result = optimize.minimize(
        bt_likelihood,
        initial_ratings,
        method='BFGS',
        options={'maxiter': 100}
    )
    
    # Return normalized ratings
    return result.x - np.mean(result.x)

def update_bt_ratings(results_dict):
    """Update Bradley-Terry ratings for all models"""
    models = list(results_dict.keys())
    n_models = len(models)
    
    # Create wins matrix
    wins = np.zeros((n_models, n_models))
    for i, model_i in enumerate(models):
        for j, model_j in enumerate(models):
            if i != j:
                # Count matches between these models
                pair = tuple(sorted([model_i, model_j]))
                total_matches = match_pairs.get(pair, 0)
                if total_matches > 0:
                    # Estimate wins based on overall win rate when they played
                    model_i_wins = (results_dict[model_i]['wins'] / 
                                  (results_dict[model_i]['wins'] + results_dict[model_i]['losses']))
                    wins[i][j] = total_matches * model_i_wins

    # Calculate Bradley-Terry scores
    bt_scores = bradley_terry_scores(wins)
    
    # Update ratings in results dictionary
    for i, model in enumerate(models):
        results_dict[model]['bt_rating'] = bt_scores[i]



def calculate_model_metrics(match_events_dir='match_events'):
    """Calculate betting patterns and luck metrics for each model"""
    model_stats = {}
    
    # Get all match event files
    files = glob.glob(os.path.join(match_events_dir, '*.jsonl'))
    
    for file in files:
        with open(file, 'r') as f:
            # Read the first line to get model names
            first_event = json.loads(f.readline())
            if first_event['type'] != 'match_start':
                continue
                
            model_a = first_event['data']['model_a'].split('/')[-1]
            model_b = first_event['data']['model_b'].split('/')[-1]
            
            # Initialize stats if needed
            for model in [model_a, model_b]:
                if model not in model_stats:
                    model_stats[model] = {
                        'total_betting_rounds': 0,
                        'bets_initiated': 0,
                        'runs': 0,
                        'accepts': 0,
                        'raises': 0,
                        'total_hands': 0,
                        'hands_with_manilha': 0
                    }
            
            # Process all events
            for line in f:
                event = json.loads(line)
                if event['type'] == 'hand_start':
                    # Count manilhas in initial hands
                    manilhas = set(tuple(card) for card in event['data']['manilhas'])
                    for player, hand in event['data']['initial_hands'].items():
                        model = model_a if player == 'A' else model_b
                        model_stats[model]['total_hands'] += 1
                        if any(tuple(card) in manilhas for card in hand):
                            model_stats[model]['hands_with_manilha'] += 1
                
                elif event['type'] == 'betting_action':
                    action = event['data']['action']
                    player = event['data']['player']
                    model = model_a if player == 'A' else model_b
                    
                    if action == 'bet':
                        model_stats[model]['bets_initiated'] += 1
                    elif action == 'run':
                        model_stats[model]['runs'] += 1
                    elif action == 'accept':
                        model_stats[model]['accepts'] += 1
                    elif action == 'raise':
                        model_stats[model]['raises'] += 1
                    
                    model_stats[model]['total_betting_rounds'] += 1
    
    # Calculate derived metrics
    for model in model_stats:
        stats = model_stats[model]
        total_rounds = stats['total_betting_rounds']
        total_hands = stats['total_hands']
        
        if total_rounds > 0:
            stats['aggression_score'] = (
                (stats['bets_initiated'] + stats['raises']) / total_rounds
            )
            stats['run_rate'] = stats['runs'] / total_rounds
            stats['accept_rate'] = stats['accepts'] / total_rounds
        
        if total_hands > 0:
            stats['manilha_rate'] = stats['hands_with_manilha'] / total_hands
    
    return model_stats

def list_model_matches(model_name, match_dir='match_history'):
    """List all matches for a specific model"""
    model_name = model_name.lower()
    files = glob.glob(os.path.join(match_dir, '*.txt'))
    if not files:
        print(f"No match files found in directory: {match_dir}")
        return

    # Regex patterns to extract needed info from the match file:
    model_a_pattern = r"🤖 Player A Model: (.+)"
    model_b_pattern = r"🤖 Player B Model: (.+)"
    scores_pattern = r"🏁 \*\*Match Final Scores:\*\* Player A: (\d+), Player B: (\d+)"
    winner_pattern = r"🏆 \*\*Match Winner:\*\* Player ([AB])"
    cost_pattern = r"💸 \*\*LLM Costs:\*\* Player A: \$([0-9.]+), Player B: \$([0-9.]+)"

    print(f"\nMatches for model: {model_name}")
    print("-" * 100)
    print(f"{'Match UUID':<20} {'Opponent':<40} {'Result':<10} {'Score':<15} {'Cost':<10}")
    print("-" * 100)

    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract both players' model names
        m_a = re.search(model_a_pattern, content)
        m_b = re.search(model_b_pattern, content)
        if not m_a or not m_b:
            continue
            
        model_a = m_a.group(1).strip().lower()
        model_b = m_b.group(1).strip().lower()

        # Extract base model names (remove provider prefix if present)
        model_a_base = model_a.split('/')[-1]
        model_b_base = model_b.split('/')[-1]
        model_name_base = model_name.split('/')[-1]

        # Check if this match involves our model
        if model_name_base not in [model_a_base, model_b_base]:
            continue

        # Extract match UUID from filename
        match_uuid = os.path.basename(file).split('_')[-1].split('.')[0]
        
        # Extract other match details
        m_scores = re.search(scores_pattern, content)
        m_winner = re.search(winner_pattern, content)
        m_cost = re.search(cost_pattern, content)
        
        if not all([m_scores, m_winner, m_cost]):
            continue

        # Determine if our model was player A or B
        is_player_a = model_name_base == model_a_base
        opponent = model_b if is_player_a else model_a
        score_a = int(m_scores.group(1))
        score_b = int(m_scores.group(2))
        cost = float(m_cost.group(1)) if is_player_a else float(m_cost.group(2))
        winner = m_winner.group(1)
        
        # Format the result
        if (winner == 'A' and is_player_a) or (winner == 'B' and not is_player_a):
            result = "Won"
        else:
            result = "Lost"
        
        # Format the score from our model's perspective
        our_score = score_a if is_player_a else score_b
        opp_score = score_b if is_player_a else score_a
        score_str = f"{our_score}-{opp_score}"
        
        print(f"{match_uuid:<20} {opponent:<40} {result:<10} {score_str:<15} ${cost:.2f}")

def aggregate_results(match_dir='match_history'):
    # Aggregated results: { model: { 'wins': int, 'losses': int, 'cost': float, 'elo': float } }
    results = {}
    positions = {
        'A': {'wins': 0, 'losses': 0, 'cost': 0.0},
        'B': {'wins': 0, 'losses': 0, 'cost': 0.0}
    }
    
    # Track match pairs and their frequency
    match_pairs = {}

    # Get all .jsonl files in the match events folder
    files = glob.glob(os.path.join(match_dir, '*.txt'))
    if not files:
        print(f"No match files found in directory: {match_dir}")
        return

    # Sort files by timestamp to process matches chronologically
    files.sort()

    # Regex patterns to extract needed info from the match file:
    timestamp_pattern = r"🕒 Timestamp: (.+)"
    model_a_pattern = r"🤖 Player A Model: (.+)"
    model_b_pattern = r"🤖 Player B Model: (.+)"
    scores_pattern = r"🏁 \*\*Match Final Scores:\*\* Player A: (\d+), Player B: (\d+)"
    winner_pattern = r"🏆 \*\*Match Winner:\*\* Player ([AB])"
    cost_pattern = r"💸 \*\*LLM Costs:\*\* Player A: \$([0-9.]+), Player B: \$([0-9.]+)"

    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract both players' model names
        m_a = re.search(model_a_pattern, content)
        m_b = re.search(model_b_pattern, content)
        if not m_a or not m_b:
            print(f"Model information missing in file {file}. Skipping.")
            continue
        model_a = m_a.group(1).strip()
        model_b = m_b.group(1).strip()
        model_a = model_a.split('/')[-1]
        model_b = model_b.split('/')[-1]

        # Extract final scores and winner
        m_scores = re.search(scores_pattern, content)
        m_winner = re.search(winner_pattern, content)
        if not m_scores or not m_winner:
            print(f"Match scores/winner not found in file {file}. Skipping.")
            continue
        winner = m_winner.group(1).strip()

        # Extract LLM costs for both players
        m_cost = re.search(cost_pattern, content)
        if not m_cost:
            print(f"LLM Costs not found in file {file}. Skipping.")
            continue
        cost_a = float(m_cost.group(1))
        cost_b = float(m_cost.group(2))

        # Extract timestamp
        m_timestamp = re.search(timestamp_pattern, content)
        if not m_timestamp:
            print(f"Timestamp not found in file {file}. Skipping.")
            continue

        # Initialize an entry for each model if not already present
        if model_a not in results:
            results[model_a] = {'wins': 0, 'losses': 0, 'cost': 0.0, 'bt_rating': 0.0}
        if model_b not in results:
            results[model_b] = {'wins': 0, 'losses': 0, 'cost': 0.0, 'bt_rating': 0.0}
            
        # Track this match pair
        pair = tuple(sorted([model_a, model_b]))
        match_pairs[pair] = match_pairs.get(pair, 0) + 1

        # Update wins/losses based on the match winner.
        if winner == 'A':
            results[model_a]['wins'] += 1
            results[model_b]['losses'] += 1
        elif winner == 'B':
            results[model_a]['losses'] += 1
            results[model_b]['wins'] += 1

        # Update wins/losses for player positions.
        if winner == 'A':
            positions['A']['wins'] += 1
            positions['B']['losses'] += 1
        elif winner == 'B':
            positions['A']['losses'] += 1
            positions['B']['wins'] += 1

        # Add up the LLM costs.
        results[model_a]['cost'] += cost_a
        results[model_b]['cost'] += cost_b


        # Aggregate LLM costs for player positions.
        positions['A']['cost'] += cost_a
        positions['B']['cost'] += cost_b


    # Output the aggregated results.
    # Calculate Bradley-Terry ratings
    update_bt_ratings(results)
    
    print("\nLeaderboard (by Bradley-Terry Rating) - Models with 10+ matches:")
    print("-" * 100)
    print(f"{'Model':<40} {'BT Rating':>8} {'Wins':>6} {'Losses':>8} {'Win Rate':>10}")
    print("-" * 100)
    for model, data in sorted(results.items(), key=lambda item: -item[1]['bt_rating']):
        total_games = data['wins'] + data['losses']
        if total_games < 20:
            continue
        total_games = data['wins'] + data['losses']
        win_rate = (data['wins'] / total_games * 100) if total_games > 0 else 0
        model_display = model
        if total_games >= 30:
            model_display = f"✅ {model}"
        else:
            model_display = f"❌ {model}"
        print(f"{model_display:<40} {data['bt_rating']:>8.2f} {data['wins']:>6} {data['losses']:>8} {win_rate:>9.1f}%")
    print("\nAggregated Results by Player Position:")
    for pos, data in sorted(positions.items(), key=lambda item: (-item[1]['wins'], item[1]['losses'])):
        print(f"Player {pos} - Wins: {data['wins']}, Losses: {data['losses']}")

    print(f"Total matches: {positions['A']['wins'] + positions['A']['losses']}")
    
    # Find and display the most frequent match pair
    if match_pairs:
        most_frequent_pair = max(match_pairs.items(), key=lambda x: x[1])
        print(f"\nMost frequent match: {most_frequent_pair[0][0]} vs {most_frequent_pair[0][1]} "
              f"({most_frequent_pair[1]} matches)")

    if True:
        # Calculate and display model metrics
        print("\nModel Metrics (sorted by aggression):")
        print("-" * 120)
        print(f"{'Model':<40} {'Aggr Score':>12} {'Bet Rate':>10} {'Run Rate':>10} {'Accept Rate':>12} {'Manilha Rate':>12}")
        print("-" * 120)
        
        model_stats = calculate_model_metrics()
        
        # Sort models by aggression score (only those with 10+ matches)
        sorted_models = sorted(
            [m for m in results.keys() 
            if m in model_stats 
            and model_stats[m]['total_betting_rounds'] > 0
            and (results[m]['wins'] + results[m]['losses']) >= 20],
            key=lambda m: model_stats[m]['aggression_score'],
            reverse=True
        )
        
        for model in sorted_models:
            stats = model_stats[model]
            total_rounds = stats['total_betting_rounds']
            bet_rate = stats['bets_initiated'] / total_rounds * 100
            print(f"{model:<40} {stats['aggression_score']:>11.1%} {bet_rate:>9.1f}% "
                f"{stats['run_rate']:>9.1%} {stats['accept_rate']:>11.1%} "
                f"{stats['manilha_rate']:>11.1%}")

    # Save number of matches per model to JSON
    matches_per_model = {model: data['wins'] + data['losses'] 
                        for model, data in results.items()}
    
    with open('model_matches.json', 'w') as f:
        json.dump(matches_per_model, f, indent=2)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Truco match results')
    parser.add_argument('--model', type=str, help='List all matches for a specific model')
    args = parser.parse_args()
    
    if args.model:
        list_model_matches(args.model)
    else:
        aggregate_results()
