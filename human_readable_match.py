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

def format_match_history(match_data):
    output = []
    output.append("🎮 **Truco Match Progression** 🎮")
    output.append("-----------------------------------")
    output.append(f"🕒 Timestamp: {match_data.get('timestamp', 'Unknown')}")
    output.append(f"🤖 Player A Model: {match_data.get('model_A', 'Unknown')}")
    output.append(f"🤖 Player B Model: {match_data.get('model_B', 'Unknown')}")
    output.append("")

    rounds = match_data.get("rounds", [])
    for hand_index, hand in enumerate(rounds, start=1):
        output.append("-----------------------------------")
        output.append(f"🃏 **Hand {hand_index}** 🃏")

        # Vira and Manilhas
        vira = hand.get("vira", [])
        vira_str = format_card(vira) if len(vira) == 2 else "N/A"
        manilhas = hand.get("manilhas", [])
        manilhas_str = ", ".join(format_card(card) for card in manilhas)
        output.append(f"**Vira:** {vira_str}    **Manilhas:** {manilhas_str}")

        # Initial hands
        output.append("**Initial Hands:**")
        for player, cards in hand.get("initial_hands", {}).items():
            cards_str = ", ".join(format_card(card) for card in cards)
            output.append(f"  Player {player}: {cards_str}")
        output.append("")

        # Trick rounds
        trick_rounds = hand.get("rounds", [])
        for trick in trick_rounds:
            trick_num = trick.get("round_num", "?")
            output.append(f"--> **Trick {trick_num}:**")
            action_emojis = {"bet": "💰", "pass": "➡️", "accept": "✅", "run": "🏃"}
            betting = trick.get("betting", [])
            betting_str = " | ".join(
                f"Player {b['player']}: {b['action']} {action_emojis.get(b['action'], '')}"
                for b in betting
            )
            output.append(f"    Betting: {betting_str}")

            plays = trick.get("plays", [])
            for play in plays:
                player = play.get("player", "?")
                card = play.get("card", [])
                output.append(f"    Player {player} plays: {format_card(card)}")
            
            output.append(f"    Trick Winner: Player {trick.get('winner', 'N/A')} 🎉")
            output.append("")  
            
        # Hand winner and scores
        hand_winner = hand.get("winner", "N/A")
        scores = hand.get("final_scores", {})
        score_str = ", ".join(f"Player {p}: {s}" for p, s in scores.items())
        output.append(f"**Hand Winner:** Player {hand_winner} 🏆")
        output.append(f"**Hand Final Scores:** {score_str}")
        output.append("")

    overall_scores = match_data.get("final_scores", {})
    overall_score_str = ", ".join(f"Player {p}: {s}" for p, s in overall_scores.items())
    overall_winner = match_data.get("winner", "N/A")
    output.append("-----------------------------------")
    output.append(f"🏁 **Match Final Scores:** {overall_score_str}")
    output.append(f"🏆 **Match Winner:** Player {overall_winner} 🏆")
    output.append("-----------------------------------")
    
    return "\n".join(output)

def main(json_filepath):
    if not os.path.exists(json_filepath):
        print(f"File not found: {json_filepath}")
        sys.exit(1)

    with open(json_filepath, "r") as f:
        match_data = json.load(f)

    # Header info for the match.
    print("🎮 **Truco Match Progression** 🎮")
    print("-----------------------------------")
    print(f"🕒 Timestamp: {match_data.get('timestamp', 'Unknown')}")
    print(f"🤖 Player A Model: {match_data.get('model_A', 'Unknown')}")
    print(f"🤖 Player B Model: {match_data.get('model_B', 'Unknown')}")
    print()

    # Iterate through each "hand" (match round)
    rounds = match_data.get("rounds", [])
    for hand_index, hand in enumerate(rounds, start=1):
        print("-----------------------------------")
        print(f"🃏 **Hand {hand_index}** 🃏")

        # Vira and Manilhas
        vira = hand.get("vira", [])
        vira_str = format_card(vira) if len(vira) == 2 else "N/A"
        manilhas = hand.get("manilhas", [])
        manilhas_str = ", ".join(format_card(card) for card in manilhas)
        print(f"**Vira:** {vira_str}    **Manilhas:** {manilhas_str}")

        # Initial hands
        print("**Initial Hands:**")
        for player, cards in hand.get("initial_hands", {}).items():
            cards_str = ", ".join(format_card(card) for card in cards)
            print(f"  Player {player}: {cards_str}")
        print()

        # Loop through each trick (inner rounds)
        trick_rounds = hand.get("rounds", [])
        for trick in trick_rounds:
            trick_num = trick.get("round_num", "?")
            print(f"--> **Trick {trick_num}:**")

            # Betting phase: add simple emojis for actions.
            action_emojis = {"bet": "💰", "pass": "➡️", "accept": "✅", "run": "🏃"}
            betting = trick.get("betting", [])
            betting_str = " | ".join(
                f"Player {b['player']}: {b['action']} {action_emojis.get(b['action'], '')}"
                for b in betting
            )
            print(f"    Betting: {betting_str}")

            # Plays
            plays = trick.get("plays", [])
            for play in plays:
                player = play.get("player", "?")
                card = play.get("card", [])
                print(f"    Player {player} plays: {format_card(card)}")
            
            # Trick winner
            print(f"    Trick Winner: Player {trick.get('winner', 'N/A')} 🎉\n")

        # Hand winner and final score for the hand
        hand_winner = hand.get("winner", "N/A")
        scores = hand.get("final_scores", {})
        score_str = ", ".join(f"Player {p}: {s}" for p, s in scores.items())
        print(f"**Hand Winner:** Player {hand_winner} 🏆")
        print(f"**Hand Final Scores:** {score_str}\n")

    # Final match summary
    overall_scores = match_data.get("final_scores", {})
    overall_score_str = ", ".join(f"Player {p}: {s}" for p, s in overall_scores.items())
    overall_winner = match_data.get("winner", "N/A")
    print("-----------------------------------")
    print(f"🏁 **Match Final Scores:** {overall_score_str}")
    print(f"🏆 **Match Winner:** Player {overall_winner} 🏆")
    print("-----------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a match_history JSON file into a human‐readable progression with emojis."
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        default="match_history/match_20250219_201958.json",
        help="Path to the match_history JSON file"
    )
    args = parser.parse_args()
    main(args.filepath)
