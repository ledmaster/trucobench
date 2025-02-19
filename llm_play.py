from datetime import datetime
import random
from engine import TrucoPaulistaEngine
from litellm import completion
import logging
logging.getLogger('litellm').setLevel(logging.ERROR)
logging.getLogger('litellm').propagate = False
import re
from match_logger import setup_logger, save_match_history

# Setup logger
logger = setup_logger()
logger.propagate = False

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
        
    def decide_bet(self, game_state):
        """Decide whether to make/respond to a bet"""
        rules = """Você é um jogador de Truco Paulista tomando uma decisão sobre apostas.

IMPORTANTE: Se houver uma aposta pendente (pending_bet não é None), você DEVE responder com uma das ações:
- 'accept' para aceitar
- 'run' para correr
- 'bet' com o próximo valor para aumentar

Se não houver aposta pendente, você pode:
- Retornar None para não fazer aposta
- Fazer uma aposta com 'bet' e o tipo de aposta

Regras de apostas:

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
- Aposta pendente: {game_state['pending_bet']}

Qual sua decisão sobre apostas? Retorne um dicionário Python com uma das seguintes estruturas:

1. Para não fazer aposta:
   {{'action': 'pass'}}

2. Para pedir truco/aumentar aposta:
   {{"action": "bet", "bet_type": "truco/six/nine/twelve"}}
   Exemplo: {{"action": "bet", "bet_type": "truco"}}

3. Para aceitar uma aposta pendente:
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
            
            content = response.choices[0].message.content
            print(content)
                
            # Look for content between ```python and ``` or just {...}
            match = re.search(r'```python\s*({.*?})\s*```|({.*?})', content, re.DOTALL)
            if not match:
                return None
                
            # Use the first group that matched (either inside ``` or standalone)
            dict_str = match.group(1) or match.group(2)
            action = eval(dict_str)
            
            # Validate the action has required fields
            if 'action' not in action:
                return None
                
            if action['action'] == 'bet' and 'bet_type' not in action:
                return None
                
            return action
            
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return None
            
    def decide_play(self, game_state):
        """Decide which card to play"""
        rules = """Você é um jogador de Truco Paulista decidindo qual carta jogar.

Regras do jogo:
O Truco é disputado em mãos. Cada mão vale inicialmente 1 ponto, e ganha o jogo quem fizer 12 pontos. 
Cada jogador recebe três cartas por mão.

Uma carta é virada (a vira) e a carta seguinte em seus 4 naipes são as Manilhas, na ordem de força:
- Paus (mais forte)
- Copas
- Espadas
- Ouros (mais fraca)"""

        state_info = f"""
Estado atual do jogo:
- Suas cartas: {game_state['my_cards']}
- Vira: {game_state['vira']}
- Manilhas: {game_state['manilhas']}
- Seu placar: {game_state['my_score']}
- Placar adversário: {game_state['opponent_score']}
- Aposta atual: {game_state['current_bet']}

Força das cartas (da mais fraca para mais forte):
4 < 5 < 6 < 7 < Q < J < K < A < 2 < 3 < Manilhas

Manilhas (da mais forte para mais fraca):
- Manilha de Paus (mais forte) - P
- Manilha de Copas - C
- Manilha de Espadas - E
- Manilha de Ouros (mais fraca) - O

Qual carta você quer jogar? Retorne um dicionário Python com a estrutura:
{{"action": "play", "card": ["rank", "suit"]}}
Exemplo: {{"action": "play", "card": ["K", "P"]}}"""

        messages = [
            {"role": "system", "content": rules},
            {"role": "user", "content": state_info}
        ]
        
        try:
            response = completion(model='openai/gpt-4o-mini',
                                messages=messages)
            
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
            if action['action'] != 'play' or 'card' not in action:
                raise ValueError("Invalid play action")
                
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
        
        logger.info("\n=== New Hand ===")
        hand_data = {
            'vira': engine.vira,
            'manilhas': engine.manilhas,
            'initial_hands': {
                'A': engine.player_hands[0].copy(),
                'B': engine.player_hands[1].copy()
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
            current_player = 0  # Start with player A
            betting_complete = False
            skip_round = False

            while not betting_complete:
                # Get current player's state and decision
                state = format_game_state(engine, 
                                        engine.player_hands[current_player],
                                        current_player)
                bet = (player_a if current_player == 0 else player_b).decide_bet(state)
                player_name = 'A' if current_player == 0 else 'B'
                
                # If player doesn't bet
                if bet['action'] == 'pass':
                    # Track that this player passed
                    round_data['betting'].append({
                        'player': player_name,
                        'action': 'pass'
                    })
                    # Switch to other player
                    current_player = 1 - current_player
                    # Only end betting if both players have passed
                    passed_count = sum(1 for b in round_data['betting'] if b['action'] == 'pass')
                    if passed_count == 2:
                        betting_complete = True
                elif bet['action'] == 'bet':
                    logger.info(f"Player {player_name} bets: {bet['bet_type']}")
                    round_data['betting'].append({
                        'player': player_name,
                        'bet': bet['bet_type']
                    })
                    engine.handle_bet(bet['bet_type'], current_player)
                    current_player = 1 - current_player  # Switch to other player
                
                elif bet['action'] == 'accept':
                    logger.info(f"Player {player_name} accepts the bet")
                    round_data['betting'].append({
                        'player': player_name,
                        'action': 'accept'
                    })
                    betting_complete = True
                
                elif bet['action'] == 'run':
                    logger.info(f"Player {player_name} runs - Player {1-current_player} wins the hand")
                    round_data['betting'].append({
                        'player': player_name,
                        'action': 'run'
                    })
                    engine.run_from_bet(current_player)
                    hand_data['rounds'].append(round_data)
                    match_history['rounds'].append(hand_data)
                    save_match_history(match_history)
                    skip_round = True
                    break  # Exit betting loop and hand processing
            
            if skip_round:
                continue
            # Card playing phase
            # Player A's turn
            state_a = format_game_state(engine, engine.player_hands[0], 0)
            logger.info(f"Player A cards before play: {engine.player_hands[0]}")
            logger.info(f"Player B cards before play: {engine.player_hands[1]}")
            play_a = player_a.decide_play(state_a)
            card_a = tuple(play_a['card'])  # Convert list to tuple
            engine.play_card(0, card_a)
            logger.info(f"Player A plays: {card_a}")
            round_data['plays'].append({
                'player': 'A',
                'card': card_a
            })
            
            # Player B's turn
            state_b = format_game_state(engine, engine.player_hands[1], 1)
            logger.info(f"Player A cards before B's play: {engine.player_hands[0]}")
            logger.info(f"Player B cards before B's play: {engine.player_hands[1]}")
            play_b = player_b.decide_play(state_b)
            card_b = tuple(play_b['card'])  # Convert list to tuple
            engine.play_card(1, card_b)
            logger.info(f"Player B plays: {card_b}")
            round_data['plays'].append({
                'player': 'B',
                'card': card_b
            })
            
            # Log remaining cards after plays
            logger.info(f"Player A remaining cards: {engine.player_hands[0]}")
            logger.info(f"Player B remaining cards: {engine.player_hands[1]}")
            
            # Save intermediate state
            hand_data['current_cards'] = {
                'A': engine.player_hands[0].copy(),
                'B': engine.player_hands[1].copy()
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
