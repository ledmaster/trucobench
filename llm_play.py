from engine import TrucoPaulistaEngine

def format_game_state(engine, player_cards, player_num):
    """Format game state for LLM consumption"""
    return {
        'my_cards': player_cards,
        'vira': engine.vira,
        'manilhas': engine.manilhas,
        'my_score': engine.teams[player_num]['score'],
        'opponent_score': engine.teams[1 - player_num]['score'],
        'current_bet': engine.current_bet,
        'bet_history': engine.bet_stack
    }

def playerA(game_state):
    """Simulated LLM Player A decision"""
    # For now, just play first card and never bet
    return {
        'action': 'play',
        'card': game_state['my_cards'][0]
    }

def playerB(game_state):
    """Simulated LLM Player B decision"""
    # For now, just play first card and never bet
    return {
        'action': 'play',
        'card': game_state['my_cards'][0]
    }

def play_match():
    """Play a single match between two LLM players"""
    engine = TrucoPaulistaEngine()
    engine.new_match()
    
    # Split dealt cards between players
    player_a_cards = engine.current_hand[:3]
    player_b_cards = engine.current_hand[3:]
    
    # Play three rounds
    for round_num in range(3):
        print(f"\nRound {round_num + 1}")
        print(f"Vira: {engine.vira}")
        print(f"Manilhas: {engine.manilhas}")
        
        # Get player A's move
        state_a = format_game_state(engine, player_a_cards, 0)
        move_a = playerA(state_a)
        card_a = move_a['card']
        player_a_cards.remove(card_a)
        print(f"Player A plays: {card_a}")
        
        # Get player B's move
        state_b = format_game_state(engine, player_b_cards, 1)
        move_b = playerB(state_b)
        card_b = move_b['card']
        player_b_cards.remove(card_b)
        print(f"Player B plays: {card_b}")
        
        # Resolve round
        winner = engine.resolve_round([card_a, card_b])
        print(f"Round winner: Player {'A' if winner == 0 else 'B'}")
    
    print("\nMatch complete!")
    print(f"Team A score: {engine.teams[0]['score']}")
    print(f"Team B score: {engine.teams[1]['score']}")

if __name__ == '__main__':
    play_match()
