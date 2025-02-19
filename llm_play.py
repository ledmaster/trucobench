import random
from engine import TrucoPaulistaEngine
from litellm import completion

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

class TrucoPlayer:
    def __init__(self, name, strategy="aggressive"):
        self.name = name
        self.strategy = strategy
        
    def decide_move(self, game_state):
        """Make a decision based on game state and strategy"""
        rules = """Você é um jogador de Truco Paulista. Regras do jogo:

O Truco é disputado em mãos. Cada mão vale inicialmente 1 ponto, e ganha o jogo quem fizer 12 pontos. 
Cada jogador recebe três cartas por mão.

Uma carta é virada (a vira) e a carta seguinte em seus 4 naipes são as Manilhas, na ordem de força:
- Paus (mais forte)
- Copas
- Espadas
- Ouros (mais fraca)

A mão é dividida em 3 rodadas. Em cada rodada, cada jogador joga uma carta.
Quem ganhar 2 rodadas ganha a mão e marca os pontos.

A qualquer momento pode-se pedir Truco para aumentar a aposta:
- Truco: aumenta para 3 pontos
- Seis: aumenta para 6 pontos
- Nove: aumenta para 9 pontos
- Twelve: aumenta para 12 pontos

Ao ser trucado, pode-se:
1. Aceitar (a mão vale o valor proposto)
2. Aumentar para o próximo valor
3. Correr (o adversário ganha os pontos da aposta anterior)"""

        state_info = f"""
Estado atual do jogo:
- Suas cartas: {game_state['my_cards']}
- Vira: {game_state['vira']}
- Manilhas: {game_state['manilhas']}
- Seu placar: {game_state['my_score']}
- Placar adversário: {game_state['opponent_score']}
- Aposta atual: {game_state['current_bet']}
- Histórico de apostas: {game_state['bet_history']}

Qual sua próxima jogada? Você pode:
1. Jogar uma carta ('action': 'play', 'card': [carta])
2. Pedir truco ('action': 'bet', 'bet_type': 'truco/six/nine/twelve')
3. Aceitar aposta ('action': 'accept')
4. Correr ('action': 'run')"""

        messages = [
            {"role": "system", "content": rules},
            {"role": "user", "content": state_info}
        ]
        
        response = completion(model='openai/gpt-4o-mini',
                            messages=messages)
        
        if self.strategy == "aggressive":
            # Bet truco 20% of the time
            if random.random() < 0.2 and game_state['current_bet'] == 1:
                return {
                    'action': 'bet',
                    'bet_type': 'truco'
                }
        elif self.strategy == "conservative":
            # Always accept bets, never initiate
            if game_state['current_bet'] > 1:
                return {
                    'action': 'accept'
                }
                
        # Default action: play first card
        return {
            'action': 'play',
            'card': game_state['my_cards'][0]
        }

def play_match():
    """Play a single match between two LLM players"""
    engine = TrucoPaulistaEngine()
    
    # Create players with different strategies
    player_a = TrucoPlayer("A", strategy="aggressive")
    player_b = TrucoPlayer("B", strategy="conservative")
    
    while not engine.game_finished:
        engine.new_match()
        
        # Get player hands
        player_a_cards = engine.player_hands[0].copy()
        player_b_cards = engine.player_hands[1].copy()
        
        print("\nNew Hand")
        
        # Play up to 3 rounds per hand
        for round_num in range(3):
            print(f"\nRound {round_num + 1}")
            print(f"Vira: {engine.vira}")
            print(f"Manilhas: {engine.manilhas}")
            
            # Betting phase
        while True:
            # Get player A's decision
            state_a = format_game_state(engine, player_a_cards, 0)
            move_a = player_a.decide_move(state_a)
            
            if move_a['action'] == 'bet':
                print(f"Player A bets: {move_a['bet_type']}")
                bet_result = engine.handle_bet(move_a['bet_type'], 0)
                
                # Get player B's response
                state_b = format_game_state(engine, player_b_cards, 1)
                move_b = player_b.decide_move(state_b)
                
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
        move_a = player_a.decide_move(state_a)
        card_a = move_a['card']
        player_a_cards.remove(card_a)
        print(f"Player A plays: {card_a}")
        
        # Player B's turn
        state_b = format_game_state(engine, player_b_cards, 1)
        move_b = player_b.decide_move(state_b)
        card_b = move_b['card']
        player_b_cards.remove(card_b)
        print(f"Player B plays: {card_b}")
        
        # Resolve round
        winner = engine.resolve_round([card_a, card_b])
        print(f"Round winner: Player {'A' if winner == 0 else 'B'}")
        
        # Check for hand winner
        hand_winner = engine.check_hand_winner()
        if hand_winner is not None:
            engine.award_hand_points(hand_winner)
            print(f"\nHand winner: Player {'A' if hand_winner == 0 else 'B'}")
            print(f"Team A score: {engine.scores[0]}")
            print(f"Team B score: {engine.scores[1]}")
            break
    
    print("\nGame complete!")
    print(f"Team A score: {engine.scores[0]}")
    print(f"Team B score: {engine.scores[1]}")
    print(f"Winner: Team {'A' if engine.scores[0] >= 12 else 'B'}")

if __name__ == '__main__':
    play_match()
