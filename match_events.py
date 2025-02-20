from datetime import datetime
import json
from pathlib import Path

class MatchEventLogger:
    def __init__(self, model_a, model_b, unique_timestamp=True):
        self.events = []
        # Create match_events directory if it doesn't exist
        self.match_dir = Path("match_events")
        self.match_dir.mkdir(exist_ok=True)
        
        base_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if unique_timestamp:
            # Add microseconds to ensure uniqueness in parallel matches
            self.timestamp = f"{base_timestamp}_{datetime.now().microsecond}"
        else:
            self.timestamp = base_timestamp
        self.log_file = self.match_dir / f"match_events_{self.timestamp}.jsonl"
        
        # Log match start
        self.log_event("match_start", {
            "model_a": model_a,
            "model_b": model_b,
            "timestamp": datetime.now().isoformat()
        })

    def log_event(self, event_type, data):
        """Log a single event with timestamp"""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.events.append(event)
        
        # Immediately write to file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')

    def log_hand_start(self, vira, manilhas, initial_hands):
        self.log_event("hand_start", {
            "vira": vira,
            "manilhas": manilhas,
            "initial_hands": initial_hands
        })

    def log_betting_action(self, player, action):
        self.log_event("betting_action", {
            "player": player,
            "action": action
        })

    def log_card_play(self, player, card):
        self.log_event("card_play", {
            "player": player,
            "card": card
        })

    def log_round_end(self, round_num, winner):
        self.log_event("round_end", {
            "round_num": round_num,
            "winner": winner
        })

    def log_hand_end(self, winner, scores, ended_by_run=False):
        self.log_event("hand_end", {
            "winner": winner,
            "scores": scores,
            "ended_by_run": ended_by_run
        })

    def log_match_end(self, final_scores, winner, costs):
        self.log_event("match_end", {
            "final_scores": final_scores,
            "winner": winner,
            "llm_costs": costs
        })
