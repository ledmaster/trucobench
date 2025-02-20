from datetime import datetime
import random
from engine import TrucoEngine
from litellm import completion, completion_cost
from match_logger import save_match_history
import re
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

class LLMResponseError(Exception):
    pass

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
    def __init__(self, name, model='openai/gpt-4o-mini'):
        self.name = name
        self.model = model
        self.total_cost = 0.0
        
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5), retry=retry_if_exception_type(LLMResponseError))
    def decide_bet(self, game_state):
        """Decide whether to make/respond to a bet"""
        rules = """Você é um jogador de Truco tomando uma decisão sobre apostas.

IMPORTANTE: Se houver uma aposta pendente (pending_bet não é None), você DEVE responder com uma das ações:
- 'accept' para aceitar
- 'run' para correr
- 'bet' com o próximo valor para aumentar

Se não houver aposta pendente, você pode:
- Retornar 'pass' para não fazer aposta
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
            response = completion(model=self.model,
                                  messages=messages)
            
            cost = completion_cost(completion_response=response)
            formatted_cost = f"${float(cost):.10f}"
            print(formatted_cost)
            self.total_cost += float(cost)
            self.total_cost += float(cost)
            
            content = response.choices[0].message.content
            print(content)
                
            # Look for content between ```python and ``` or just {...}
            match = re.search(r'```python\s*({.*?})\s*```|({.*?})', content, re.DOTALL)
            if not match:
                print("Invalid LLM response format in decide_bet. Full response:")
                print(content)
                raise LLMResponseError(f"Invalid LLM response format in decide_bet for player {self.name}")
                
            # Use the first group that matched (either inside ``` or standalone)
            dict_str = match.group(1) or match.group(2)
            action = eval(dict_str)
            
            # Validate the action has required fields
            if 'action' not in action:
                return None
                
            if action['action'] == 'bet' and 'bet_type' not in action:
                print("LLM response missing 'bet_type' in decide_bet. Full response:")
                print(content)
                raise LLMResponseError(f"Invalid bet action in decide_bet for player {self.name}")
                
            return action
            
        except Exception as e:
            print("LLM parsing error in decide_bet. Raw response:")
            if 'content' in locals():
                print(content)
            raise LLMResponseError(f"Error parsing LLM response in decide_bet for player {self.name}: {e}")
            
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5), retry=retry_if_exception_type(LLMResponseError))
    def decide_play(self, game_state):
        """Decide which card to play"""
        rules = """Você é um jogador de Truco decidindo qual carta jogar.

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
        
        #print(state_info)
        try:
            response = completion(model=self.model,
                                  messages=messages)
            
            cost = completion_cost(completion_response=response)
            formatted_cost = f"${float(cost):.10f}"
            print(formatted_cost)
            
            content = response.choices[0].message.content
            #print(content)
            
            # Look for content between ```python and ``` or just {...}
            match = re.search(r'```python\s*({.*?})\s*```|({.*?})', content, re.DOTALL)
            if not match:
                print("Invalid LLM response format in decide_play. Full response:")
                print(content)
                raise LLMResponseError(f"No valid dictionary found in LLM response in decide_play for player {self.name}")
                
            # Use the first group that matched (either inside ``` or standalone)
            dict_str = match.group(1) or match.group(2)
            action = eval(dict_str)
            
            # Validate the action has required fields
            if action['action'] != 'play' or 'card' not in action:
                print("Invalid play action format in decide_play. Full response:")
                print(content)
                raise LLMResponseError(f"Invalid play action in decide_play for player {self.name}")
                
            return action
            
        except Exception as e:
            print("LLM parsing error in decide_play. Raw response:")
            if 'content' in locals():
                print(content)
            raise LLMResponseError(f"Error parsing LLM response in decide_play for player {self.name}: {e}")

def play_match():
    """Play a single match between two LLM players"""
    engine = TrucoEngine()
    

    
    # Create players with different strategies
    player_a = TrucoPlayer("A")
    player_b = TrucoPlayer("B")

    # Initialize match history
    match_history = {
        'model_A': player_a.model,
        'model_B': player_b.model,
        'rounds': [],
        'final_scores': {'A': 0, 'B': 0},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    while not engine.game_finished:
        engine.new_match()
        
        print("\n=== New Hand ===")
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
            print(f"\n--- Round {round_num + 1} ---")
            print(f"Vira: {engine.vira}")
            print(f"Manilhas: {engine.manilhas}")
            
            round_data = {
                'round_num': round_num + 1,
                'betting': [],
                'plays': []
            }
            
            def get_bet_action(player_idx):
                player = player_a if player_idx == 0 else player_b
                state = format_game_state(engine, engine.player_hands[player_idx], player_idx)
                return player.decide_bet(state)
    
            try:
                bet_results = engine.run_betting_phase(get_bet_action)
                for (p_idx, action) in bet_results:
                    player_name = 'A' if p_idx == 0 else 'B'
                    round_data['betting'].append({
                        'player': player_name,
                        'action': action.get('action', 'error')
                    })
            except LLMResponseError as e:
                print(e)
                if "A" in str(e):
                    print("LLM parsing error from Player A. Awarding win to Player B.")
                    engine.scores[1] = 12
                else:
                    print("LLM parsing error from Player B. Awarding win to Player A.")
                    engine.scores[0] = 12
                engine.game_finished = True
                return
    
            if engine.skip_round:
                continue
            # Card playing phase
            # Player A's turn
            if len(engine.player_hands[0]) == 1:
                card_a = tuple(engine.player_hands[0][0])
                print(f"Last round: automatically playing the only remaining card for Player A: {card_a}")
            else:
                state_a = format_game_state(engine, engine.player_hands[0], 0)
                print(f"Player A cards before play: {engine.player_hands[0]}")
                print(f"Player B cards before play: {engine.player_hands[1]}")
                try:
                    play_a = player_a.decide_play(state_a)
                except LLMResponseError as e:
                    print(e)
                    print("LLM parsing error from Player A during card play. Awarding win to Player B.")
                    engine.scores[1] = 12
                    engine.game_finished = True
                    return
                card_a = tuple(play_a['card'])
            engine.play_card(0, card_a)
            print(f"Player A plays: {card_a}")
            round_data['plays'].append({
                'player': 'A',
                'card': card_a
            })
            
            # Player B's turn
            if len(engine.player_hands[1]) == 1:
                card_b = tuple(engine.player_hands[1][0])
                print(f"Last round: automatically playing the only remaining card for Player B: {card_b}")
            else:
                state_b = format_game_state(engine, engine.player_hands[1], 1)
                print(f"Player A cards before B's play: {engine.player_hands[0]}")
                print(f"Player B cards before B's play: {engine.player_hands[1]}")
                try:
                    play_b = player_b.decide_play(state_b)
                except LLMResponseError as e:
                    print(e)
                    print("LLM parsing error from Player B during card play. Awarding win to Player A.")
                    engine.scores[0] = 12
                    engine.game_finished = True
                    return
                card_b = tuple(play_b['card'])
            engine.play_card(1, card_b)
            print(f"Player B plays: {card_b}")
            round_data['plays'].append({
                'player': 'B',
                'card': card_b
            })
            
            # Log remaining cards after plays
            print(f"Player A remaining cards: {engine.player_hands[0]}")
            print(f"Player B remaining cards: {engine.player_hands[1]}")
            
            # Save intermediate state
            hand_data['current_cards'] = {
                'A': engine.player_hands[0].copy(),
                'B': engine.player_hands[1].copy()
            }
            #save_match_history(match_history)
            
            # Resolve round
            winner = engine.resolve_round([card_a, card_b])
            print(f"Round winner: Player {'A' if winner == 0 else 'B'}")
            round_data['winner'] = 'A' if winner == 0 else 'B'
            hand_data['rounds'].append(round_data)
            
            # Check for hand winner
            hand_winner = engine.check_hand_winner()
            if hand_winner is not None:
                engine.award_hand_points(hand_winner)
                print(f"\nHand winner: Player {'A' if hand_winner == 0 else 'B'}")
                print(f"Team A score: {engine.scores[0]}")
                print(f"Team B score: {engine.scores[1]}")
                
                hand_data['winner'] = 'A' if hand_winner == 0 else 'B'
                hand_data['final_scores'] = {
                    'A': engine.scores[0],
                    'B': engine.scores[1]
                }
                match_history['rounds'].append(hand_data)
                break
    
    print("\n=== Game Complete! ===")
    print(f"Team A score: {engine.scores[0]}")
    print(f"Team B score: {engine.scores[1]}")
    print(f"Winner: Team {'A' if engine.scores[0] >= 12 else 'B'}")
    
    # Save final scores and winner
    match_history['final_scores'] = {
        'A': engine.scores[0],
        'B': engine.scores[1]
    }
    match_history['winner'] = 'A' if engine.scores[0] >= 12 else 'B'
    
    match_history['llm_costs'] = {'A': player_a.total_cost, 'B': player_b.total_cost}
    # Save match history
    save_match_history(match_history)

if __name__ == '__main__':
    play_match()
