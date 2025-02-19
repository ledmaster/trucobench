from datetime import datetime
import random
from engine import TrucoPaulistaEngine
from litellm import completion
import logging
logging.getLogger('litellm').setLevel(logging.ERROR)
import re
from match_logger import setup_logger, save_match_history

# Setup logger
logger = setup_logger()

def format_game_state(engine, player_cards, player_num):
    """Format game state for LLM consumption"""
    # Calculate if there's a pending bet to respond to
    pending_bet = None
    if engine.bet_stack and engine.bet_stack[-1]['team'] != player_num:
        pending_bet = engine.bet_stack[-1]['type']

    return {
        'my_cards': player_cards,
        'vira': engine.vira,
        'manilhas': engine.manilhas,
        'my_score': engine.scores[player_num],
        'opponent_score': engine.scores[1 - player_num],
        'current_bet': engine.current_bet,
        'bet_history': engine.bet_stack,
        'pending_bet': pending_bet
    }

class TrucoPlayer:
    def __init__(self, name):
        self.name = name
        
    def decide_move(self, game_state):
        rules = """Você é um jogador de Truco Paulista. 

IMPORTANTE: Se houver uma aposta pendente (pending_bet não é None), você DEVE responder com uma das ações:
- 'accept' para aceitar
- 'run' para correr
- 'bet' com o próximo valor para aumentar

Regras do jogo:

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

Força das cartas (da mais fraca para mais forte):
4 < 5 < 6 < 7 < Q < J < K < A < 2 < 3 < Manilhas

Manilhas (da mais forte para mais fraca):
- Manilha de Paus (mais forte) - P
- Manilha de Copas - C
- Manilha de Espadas - E
- Manilha de Ouros (mais fraca) - O

Qual sua próxima jogada? Você deve retornar um dicionário Python com uma das seguintes estruturas:

1. Para jogar uma carta:
   {{"action": "play", "card": ["rank", "suit"]}}
   Exemplo: {{"action": "play", "card": ["K", "P"]}}

2. Para pedir truco/aumentar aposta:
   {{"action": "bet", "bet_type": "truco/six/nine/twelve"}}
   Exemplo: {{"action": "bet", "bet_type": "truco"}}

3. Para aceitar uma aposta:
   {{'action': 'accept'}}

4. Para correr de uma aposta:
   {{'action': 'run'}}"""

        messages = [
            {"role": "system", "content": rules},
            {"role": "user", "content": state_info}
        ]
        
        try:
            response = completion(model='openai/gpt-4o-mini',
                                messages=messages)
            
            # Parse the response using regex to find the dictionary
            
            content = response.choices[0].message.content
            print(content)
            
            # Look for content between ```python and ``` or just {...}
            match = re.search(r'```python\s*({.*?})\s*```|({.*?})', content, re.DOTALL)
            if not match:
                raise ValueError("No valid dictionary found in response")
                
            # Use the first group that matched (either inside ``` or standalone)
            dict_str = match.group(1) or match.group(2)
            action = eval(dict_str)
            
            
            # Validate the action has required fields
            if 'action' not in action:
                raise ValueError("Missing 'action' in response")
                
            if action['action'] == 'play' and 'card' not in action:
                raise ValueError("Missing 'card' for play action")
                
            if action['action'] == 'bet' and 'bet_type' not in action:
                raise ValueError("Missing 'bet_type' for bet action")
                
            return action
            
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            # Fallback to playing first card if there's an error
            return {
                'action': 'play',
                'card': game_state['my_cards'][0]
            }

def play_match():
    """Play a single match between two LLM players"""
    engine = TrucoPaulistaEngine()
    
    # Initialize match history
    match_history = {
        'rounds': [],
        'final_scores': {'A': 0, 'B': 0},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Create players with different strategies
    player_a = TrucoPlayer("A")
    player_b = TrucoPlayer("B")
    
    while not engine.game_finished:
        engine.new_match()
        
        # Get player hands
        player_a_cards = engine.player_hands[0].copy()
        player_b_cards = engine.player_hands[1].copy()
        
        logger.info("\n=== New Hand ===")
        hand_data = {
            'vira': engine.vira,
            'manilhas': engine.manilhas,
            'initial_hands': {
                'A': player_a_cards.copy(),
                'B': player_b_cards.copy()
            },
            'rounds': []
        }
        
        # Play up to 3 rounds per hand
        for round_num in range(3):
            logger.info(f"\n--- Round {round_num + 1} ---")
            logger.info(f"Vira: {engine.vira}")
            logger.info(f"Manilhas: {engine.manilhas}")
            
            round_data = {
                'round_num': round_num + 1,
                'betting': [],
                'plays': []
            }
            
            # Betting phase
            betting_complete = False
            while not betting_complete:
                # Get player A's decision
                state_a = format_game_state(engine, player_a_cards, 0)
                logger.info(f"Player A cards: {player_a_cards}")
                logger.info(f"Player B cards: {player_b_cards}")
                logger.info(f"Game state A: {state_a}")
                move_a = player_a.decide_move(state_a)
                
                if move_a['action'] == 'bet':
                    logger.info(f"Player A bets: {move_a['bet_type']}")
                    round_data['betting'].append({
                        'player': 'A',
                        'bet': move_a['bet_type']
                    })
                    bet_result = engine.handle_bet(move_a['bet_type'], 0)
                    
                    # Get player B's response to the bet
                    state_b = format_game_state(engine, player_b_cards, 1)
                    move_b = player_b.decide_move(state_b)
                    
                    if move_b['action'] == 'bet':
                        logger.info(f"Player B raises to: {move_b['bet_type']}")
                        round_data['betting'].append({
                            'player': 'B',
                            'bet': move_b['bet_type']
                        })
                        bet_result = engine.handle_bet(move_b['bet_type'], 1)
                        
                        # Get player A's response to the raise
                        state_a = format_game_state(engine, player_a_cards, 0)
                        move_a = player_a.decide_move(state_a)
                        
                        if move_a['action'] == 'accept':
                            logger.info("Player A accepts the raise")
                            round_data['betting'].append({
                                'player': 'A',
                                'action': 'accept'
                            })
                            break
                        elif move_a['action'] == 'run':
                            logger.info("Player A runs - Player B wins the hand")
                            engine.run_from_bet(0)
                            round_data['betting'].append({
                                'player': 'A',
                                'action': 'run'
                            })
                            return
                    elif move_b['action'] == 'accept':
                        logger.info("Player B accepts the bet")
                        round_data['betting'].append({
                            'player': 'B',
                            'action': 'accept'
                        })
                        betting_complete = True
                    else:  # Player B runs
                        logger.info("Player B runs - Player A wins the hand")
                        round_data['betting'].append({
                            'player': 'B',
                            'action': 'run'
                        })
                        engine.run_from_bet(1)
                        return
                else:
                    betting_complete = True  # No bet, proceed to card play
                
            # Card playing phase
            # Player A's turn
            state_a = format_game_state(engine, player_a_cards, 0)
            logger.info(f"Player A cards before play: {player_a_cards}")
            logger.info(f"Player B cards before play: {player_b_cards}")
            move_a = player_a.decide_move(state_a)
            card_a = tuple(move_a['card'])  # Convert list to tuple
            player_a_cards.remove(card_a)
            logger.info(f"Player A plays: {card_a}")
            round_data['plays'].append({
                'player': 'A',
                'card': card_a
            })
            
            # Player B's turn
            state_b = format_game_state(engine, player_b_cards, 1)
            logger.info(f"Player A cards before B's play: {player_a_cards}")
            logger.info(f"Player B cards before B's play: {player_b_cards}")
            move_b = player_b.decide_move(state_b)
            card_b = tuple(move_b['card'])  # Convert list to tuple
            player_b_cards.remove(card_b)
            logger.info(f"Player B plays: {card_b}")
            round_data['plays'].append({
                'player': 'B',
                'card': card_b
            })
            
            # Log remaining cards after plays
            logger.info(f"Player A remaining cards: {player_a_cards}")
            logger.info(f"Player B remaining cards: {player_b_cards}")
            
            # Save intermediate state
            hand_data['current_cards'] = {
                'A': player_a_cards.copy(),
                'B': player_b_cards.copy()
            }
            save_match_history(match_history)
            
            # Resolve round
            winner = engine.resolve_round([card_a, card_b])
            logger.info(f"Round winner: Player {'A' if winner == 0 else 'B'}")
            round_data['winner'] = 'A' if winner == 0 else 'B'
            hand_data['rounds'].append(round_data)
            
            # Check for hand winner
            hand_winner = engine.check_hand_winner()
            if hand_winner is not None:
                engine.award_hand_points(hand_winner)
                logger.info(f"\nHand winner: Player {'A' if hand_winner == 0 else 'B'}")
                logger.info(f"Team A score: {engine.scores[0]}")
                logger.info(f"Team B score: {engine.scores[1]}")
                
                hand_data['winner'] = 'A' if hand_winner == 0 else 'B'
                hand_data['final_scores'] = {
                    'A': engine.scores[0],
                    'B': engine.scores[1]
                }
                match_history['rounds'].append(hand_data)
                break
    
    logger.info("\n=== Game Complete! ===")
    logger.info(f"Team A score: {engine.scores[0]}")
    logger.info(f"Team B score: {engine.scores[1]}")
    logger.info(f"Winner: Team {'A' if engine.scores[0] >= 12 else 'B'}")
    
    # Save final scores and winner
    match_history['final_scores'] = {
        'A': engine.scores[0],
        'B': engine.scores[1]
    }
    match_history['winner'] = 'A' if engine.scores[0] >= 12 else 'B'
    
    # Save match history
    save_match_history(match_history)

if __name__ == '__main__':
    play_match()
