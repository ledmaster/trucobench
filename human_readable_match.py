#!/usr/bin/env python3
import os
import sys
import json
import argparse

# Mapping for suits: O = Ouros, C = Copas, E = Espadas, P = Paus
SUIT_MAP = {
    "O": "♦️",
    "C": "❤️",
    "E": "♠️",
    "P": "♣️"
}

def format_card(card):
    """Converts a card list [rank, suit] into a string with an emoji for the suit."""
    if not card or len(card) != 2:
        return "N/A"
    rank, suit = card
    return f"{rank}{SUIT_MAP.get(suit, suit)}"

def format_match_events(events):
    """Convert a list of match events into readable format"""
    output = []
    
    # Track state
    current_hand = {}
    current_round = {"betting": [], "plays": []}
    rounds = []
    round_num = 1

    # Process events sequentially
    hand_num = 1
    for event in events:
        event_type = event["type"]
        data = event["data"]
        
        if event_type == "match_start":
            output.append("🎮 **Truco Match Progression** 🎮")
            output.append("-----------------------------------")
            output.append(f"🕒 Timestamp: {event['timestamp']}")
            output.append(f"🤖 Player A Model: {data['model_a']}")
            output.append(f"🤖 Player B Model: {data['model_b']}")
            output.append("")
            
        elif event_type == "hand_start":
            output.append("\n====================")
            output.append(f"🃏 Starting Hand {hand_num}")
            output.append("====================")
            
            # Vira and Manilhas
            vira = data["vira"]
            vira_str = format_card(vira)
            output.append(f"Dealer turns up: {vira_str}")
            output.append(f"Manilhas for this hand: {', '.join(format_card(card) for card in data['manilhas'])}")
            
            # Initial hands
            output.append("\nCards dealt:")
            for player, cards in data["initial_hands"].items():
                cards_str = ", ".join(format_card(card) for card in cards)
                output.append(f"Player {player} receives: {cards_str}")
            output.append("")
            
            current_hand = data
            current_round = {"betting": [], "plays": []}
            rounds = []
            round_num = 1
            hand_num += 1
            
        elif event_type == "betting_action":
            current_round["betting"].append({
                "player": data["player"],
                "action": data["action"]
            })
            
        elif event_type == "card_play":
            current_round["plays"].append({
                "player": data["player"],
                "card": data["card"]
            })
            
        elif event_type == "round_end":
            current_round["winner"] = data["winner"]
            current_round["round_num"] = data["round_num"]
            rounds.append(current_round)
            
            # Print round details
            output.append(f"\n▶️ Round {data['round_num']}:")
            
            # Show betting phase if any bets were made
            if current_round["betting"]:
                output.append("Betting phase:")
                action_emojis = {"bet": "💰", "pass": "➡️", "accept": "✅", "run": "🏃"}
                for bet in current_round["betting"]:
                    emoji = action_emojis.get(bet['action'], '')
                    output.append(f"  • Player {bet['player']} chooses to {bet['action']} {emoji}")
            
            # Show card plays
            output.append("Cards played:")
            for play in current_round["plays"]:
                output.append(f"  • Player {play['player']} plays {format_card(play['card'])}")
            
            output.append(f"👑 Player {data['winner']} wins the round!")
            output.append("")
            
            # Reset for next round
            current_round = {"betting": [], "plays": []}
            
        elif event_type == "hand_end":
            output.append("\n📊 Betting Phase Summary:")
            # Find the betting actions for this hand
            betting_actions = [e for e in events if e["type"] == "betting_action" and 
                             e["timestamp"] <= event["timestamp"] and
                             (not current_hand or e["timestamp"] >= event["timestamp"])]
            
            # Show the betting sequence
            for bet in betting_actions[-2:]:  # Show last 2 actions that led to hand end
                player = bet["data"]["player"]
                action = bet["data"]["action"]
                output.append(f"  • Player {player} chose to {action}")
            
            output.append("\n🔚 Hand Complete!")
            output.append(f"🏆 Player {data['winner']} wins the hand")
            output.append("Current match score:")
            for player, score in data['scores'].items():
                output.append(f"  • Player {player}: {score} points")
            output.append("")
            
        elif event_type == "match_end":
            output.append("-----------------------------------")
            score_str = ", ".join(f"Player {p}: {s}" for p, s in data['final_scores'].items())
            output.append(f"🏁 **Match Final Scores:** {score_str}")
            output.append(f"🏆 **Match Winner:** Player {data['winner']} 🏆")
            
            if "llm_costs" in data:
                cost_str = f"Player A: ${float(data['llm_costs'].get('A', 0)):.10f}, Player B: ${float(data['llm_costs'].get('B', 0)):.10f}"
                output.append(f"💸 **LLM Costs:** {cost_str}")
            
            output.append("-----------------------------------")
    
    output.append("-----------------------------------")
    
    return "\n".join(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a match events JSONL file into a human-readable progression with emojis."
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        default="match_events/match_events_20250220_154525.jsonl",
        help="Path to the match events JSONL file"
    )
    args = parser.parse_args()
       
    if not os.path.exists(args.filepath):
        print(f"File not found: {args.filepath}")
        sys.exit(1)
       
    events = []
    with open(args.filepath, "r") as f:
        for line in f:
            events.append(json.loads(line))
       
    # Print the formatted match events
    print(format_match_events(events))
