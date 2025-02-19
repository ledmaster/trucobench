import random
from engine import TrucoPaulistaEngine

def format_game_state(engine, player_cards, player_num):
    """Format game state for LLM consumption"""
    return {
        'my_cards': player_cards,
        'vira': engine.vira,
        'manilhas': engine.manilhas,
        'my_score': engine.scores[player_num],
        'opponent_score': engine.scores[1 - player_num],
        'current_bet': engine.current_bet,
        'bet_history': engine.bet_stack
    }

def playerA(game_state):
    """Simulated LLM Player A decision"""
    # For now, simple strategy: bet truco 20% of the time
    if random.random() < 0.2 and game_state['current_bet'] == 1:
        return {
            'action': 'bet',
            'bet_type': 'truco'
        }
    return {
        'action': 'play',
        'card': game_state['my_cards'][0]
    }

def playerB(game_state):
    """Simulated LLM Player B decision"""
    # For now, simple strategy: always accept bets, never initiate
    if game_state['current_bet'] > 1:
        return {
            'action': 'accept'
        }
    return {
        'action': 'play',
        'card': game_state['my_cards'][0]
    }

def play_match():
    """Play a single match between two LLM players"""
    engine = TrucoPaulistaEngine()
    engine.new_match()
    
    # Get player hands
    player_a_cards = engine.player_hands[0]
    player_b_cards = engine.player_hands[1]
    
    # Play three rounds
    for round_num in range(3):
        print(f"\nRound {round_num + 1}")
        print(f"Vira: {engine.vira}")
        print(f"Manilhas: {engine.manilhas}")
        
        # Betting phase
        while True:
            # Get player A's decision
            state_a = format_game_state(engine, player_a_cards, 0)
            move_a = playerA(state_a)
            
            if move_a['action'] == 'bet':
                print(f"Player A bets: {move_a['bet_type']}")
                bet_result = engine.handle_bet(move_a['bet_type'], 0)
                
                # Get player B's response
                state_b = format_game_state(engine, player_b_cards, 1)
                move_b = playerB(state_b)
                
                if move_b['action'] == 'accept':
                    print("Player B accepts the bet")
                    break
                else:
                    print("Player B runs - Player A wins the hand")
                    continue
            else:
                break  # No bet, proceed to card play
                
        # Card playing phase
        # Player A's turn
        state_a = format_game_state(engine, player_a_cards, 0)
        move_a = playerA(state_a)
        card_a = move_a['card']
        player_a_cards.remove(card_a)
        print(f"Player A plays: {card_a}")
        
        # Player B's turn
        state_b = format_game_state(engine, player_b_cards, 1)
        move_b = playerB(state_b)
        card_b = move_b['card']
        player_b_cards.remove(card_b)
        print(f"Player B plays: {card_b}")
        
        # Resolve round
        winner = engine.resolve_round([card_a, card_b])
        print(f"Round winner: Player {'A' if winner == 0 else 'B'}")
    
    print("\nMatch complete!")
    print(f"Team A score: {engine.scores[0]}")
    print(f"Team B score: {engine.scores[1]}")

if __name__ == '__main__':
    play_match()
