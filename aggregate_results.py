#!/usr/bin/env python3
import os
import glob
import re
import json
from datetime import datetime

def calculate_elo_change(rating_a, rating_b, winner):
    """Calculate Elo rating changes for both players."""
    k_factor = 32
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    if winner == 'A':
        score_a = 1
    else:
        score_a = 0
        
    change = k_factor * (score_a - expected_a)
    return change, -change


def aggregate_results(match_dir='match_events'):
    # Aggregated results: { model: { 'wins': int, 'losses': int, 'cost': float, 'elo': float, 'matches': list } }
    results = {}
    positions = {
        'A': {'wins': 0, 'losses': 0, 'cost': 0.0},
        'B': {'wins': 0, 'losses': 0, 'cost': 0.0}
    }

    # Get all .jsonl files in the match events folder
    files = glob.glob(os.path.join(match_dir, '*.jsonl'))
    if not files:
        print(f"No match files found in directory: {match_dir}")
        return

    # Regex patterns to extract needed info from the match file:
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

        # Initialize an entry for each model if not already present.
        if model_a not in results:
            results[model_a] = {'wins': 0, 'losses': 0, 'cost': 0.0, 'elo': 1500, 'matches': []}
        if model_b not in results:
            results[model_b] = {'wins': 0, 'losses': 0, 'cost': 0.0, 'elo': 1500, 'matches': []}

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

        # Store match result for later Elo calculation
        results[model_a]['matches'].append({
            'opponent': model_b,
            'winner': winner == 'A'
        })
        results[model_b]['matches'].append({
            'opponent': model_a,
            'winner': winner == 'B'
        })

        # Aggregate LLM costs for player positions.
        positions['A']['cost'] += cost_a
        positions['B']['cost'] += cost_b

    # Extract timestamps and sort files chronologically
    file_timestamps = []
    for file in files:
        # Extract datetime from filename
        # Extract timestamp from match_events_YYYYMMDD_HHMMSS_uuid.jsonl format
        timestamp_match = re.search(r'match_events_(\d{8}_\d{6})_', os.path.basename(file))
        if timestamp_match:
            try:
                file_date = datetime.strptime(timestamp_match.group(1), '%Y%m%d_%H%M%S')
                file_timestamps.append((file_date, file))
            except ValueError:
                print(f"Could not parse timestamp from filename: {file}")
                continue
        else:
            print(f"No timestamp found in filename: {file}")
    
    # Sort files by timestamp
    file_timestamps.sort(key=lambda x: x[0])
    
    # Reset all Elo ratings
    for model in results:
        results[model]['elo'] = 1500

    # Process matches chronologically
    for _, file in file_timestamps:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        m_a = re.search(model_a_pattern, content)
        m_b = re.search(model_b_pattern, content)
        m_winner = re.search(winner_pattern, content)
        
        if m_a and m_b and m_winner:
            model_a = m_a.group(1).strip()
            model_b = m_b.group(1).strip()
            winner = m_winner.group(1).strip()
            
            # Calculate and apply Elo changes for both players
            elo_change, _ = calculate_elo_change(
                results[model_a]['elo'],
                results[model_b]['elo'],
                winner
            )
            
            if winner == 'A':
                results[model_a]['elo'] += elo_change
                results[model_b]['elo'] -= elo_change
            else:
                results[model_a]['elo'] -= elo_change
                results[model_b]['elo'] += elo_change

    # Output the aggregated results.
    print("\n🏆 Leaderboard (by Elo Rating):")
    print("-" * 80)
    print(f"{'Model':<40} {'Elo':>8} {'Wins':>6} {'Losses':>8} {'Cost':>12}")
    print("-" * 80)
    for model, data in sorted(results.items(), key=lambda item: (-item[1]['elo'], -item[1]['wins'])):
        print(f"{model:<40} {data['elo']:>8.1f} {data['wins']:>6} {data['losses']:>8} ${data['cost']:>11.2f}")
    print("\nAggregated Results by Player Position:")
    for pos, data in sorted(positions.items(), key=lambda item: (-item[1]['wins'], item[1]['losses'])):
        print(f"Player {pos} - Wins: {data['wins']}, Losses: {data['losses']}, Total Cost: ${data['cost']:.10f}")

if __name__ == '__main__':
    aggregate_results()
