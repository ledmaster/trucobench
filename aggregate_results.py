#!/usr/bin/env python3
import os
import glob
import re
import json
from datetime import datetime

def calculate_elo_change(winner_elo, loser_elo, k_factor=32):
    """Calculate ELO rating changes after a match"""
    expected_winner = 1 / (1 + 10**((loser_elo - winner_elo) / 400))
    elo_change = k_factor * (1 - expected_winner)
    return elo_change



def aggregate_results(match_dir='match_history'):
    # Aggregated results: { model: { 'wins': int, 'losses': int, 'cost': float, 'elo': float } }
    results = {}
    positions = {
        'A': {'wins': 0, 'losses': 0, 'cost': 0.0},
        'B': {'wins': 0, 'losses': 0, 'cost': 0.0}
    }

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
        score_a = int(m_scores.group(1))
        score_b = int(m_scores.group(2))
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
        match_timestamp = datetime.fromisoformat(m_timestamp.group(1))

        # Initialize an entry for each model if not already present
        if model_a not in results:
            results[model_a] = {'wins': 0, 'losses': 0, 'cost': 0.0, 'elo': 1000}
        if model_b not in results:
            results[model_b] = {'wins': 0, 'losses': 0, 'cost': 0.0, 'elo': 1000}

        # Calculate and update ELO ratings
        if winner == 'A':
            elo_change = calculate_elo_change(results[model_a]['elo'], results[model_b]['elo'])
            results[model_a]['elo'] += elo_change
            results[model_b]['elo'] -= elo_change
        else:
            elo_change = calculate_elo_change(results[model_b]['elo'], results[model_a]['elo'])
            results[model_b]['elo'] += elo_change
            results[model_a]['elo'] -= elo_change

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
    print("\n🏆 Leaderboard (by ELO):")
    print("-" * 100)
    print(f"{'Model':<40} {'ELO':>8} {'Wins':>6} {'Losses':>8} {'Win Rate':>10}")
    print("-" * 100)
    for model, data in sorted(results.items(), key=lambda item: -item[1]['elo']):
        total_games = data['wins'] + data['losses']
        win_rate = (data['wins'] / total_games * 100) if total_games > 0 else 0
        print(f"{model:<40} {data['elo']:>8.1f} {data['wins']:>6} {data['losses']:>8} {win_rate:>9.1f}%")
    print("\nAggregated Results by Player Position:")
    for pos, data in sorted(positions.items(), key=lambda item: (-item[1]['wins'], item[1]['losses'])):
        print(f"Player {pos} - Wins: {data['wins']}, Losses: {data['losses']}")

    print(f"Total matches: {positions['A']['wins'] + positions['A']['losses']}")

    # Save number of matches per model to JSON
    matches_per_model = {model: data['wins'] + data['losses'] 
                        for model, data in results.items()}
    
    with open('model_matches.json', 'w') as f:
        json.dump(matches_per_model, f, indent=2)

if __name__ == '__main__':
    aggregate_results()
