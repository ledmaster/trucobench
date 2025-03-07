import os
from pathlib import Path
import json
import math
import random
from engine import TrucoEngine
from human_readable_match import format_match_events
from litellm import completion, completion_cost
import requests
from datetime import datetime, timezone
import uuid
from match_events import MatchEventLogger
import re
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_exponential
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

os.environ["OR_APP_NAME"] = "TrucoArena"
os.environ["OR_SITE_URL"] = "https://mariofilho.com"

def generate_match_id():
    """Generate a unique match identifier with timestamp and UUID"""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    match_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{match_id}"

class MatchTraceLogger:
    def __init__(self, model_a, model_b, match_id):
        self.model_a = model_a
        self.model_b = model_b
        self.trace_dir = Path("match_traces")
        self.trace_dir.mkdir(exist_ok=True)
        
        self.trace_file = self.trace_dir / f"match_trace_{match_id}.jsonl"
        
    def log_completion(self, model, messages, response, player, action_type):
        trace = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'model': model,
            'player': player,
            'action_type': action_type,
            'messages': messages,
            'response': response.model_dump() if hasattr(response, 'model_dump') else response,
        }
        
        with open(self.trace_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trace, ensure_ascii=False) + '\n')

class LLMResponseError(Exception):
    def __init__(self, message, player_name=None, model=None, game_state=None, raw_response=None):
        self.player_name = player_name
        self.model = model
        self.game_state = game_state
        self.raw_response = raw_response
        
        error_details = [
            f"Player: {player_name}" if player_name else None,
            f"Model: {model}" if model else None,
            f"Game state: {game_state}" if game_state else None,
            f"Raw response: {raw_response}" if raw_response else None
        ]
        
        detailed_message = "\n".join(filter(None, [message] + error_details))
        super().__init__(detailed_message)

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
        'pending_bet': pending_bet,
        'betting_round': len(engine.bet_stack) + 1
    }

class TrucoPlayer:
    def __init__(self, name, model='openai/gpt-4o-mini', trace_logger=None):
        self.name = name
        self.model = model
        self.total_cost = 0.0
        self.trace_logger = trace_logger
        
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), retry=retry_if_exception_type(LLMResponseError))
    def decide_bet(self, game_state):
        """Decide whether to make/respond to a bet"""
        rules = """Você é um jogador de Truco tomando uma decisão sobre apostas.

IMPORTANTE: Se houver uma aposta pendente, você DEVE responder com uma das ações:
- 'accept' para aceitar a aposta (apenas se houver uma aposta pendente)
- 'run' para correr (apenas se houver uma aposta pendente)
- 'bet' com o próximo valor para aumentar

Se não houver aposta pendente, você DEVE:
- Retornar 'pass' para não fazer aposta, ou
- Fazer uma aposta com 'bet' e o tipo de aposta

Nota: 'accept' só é válido quando há uma aposta pendente!

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
- Rodada de apostas: {game_state['betting_round']}
- Histórico de apostas: {game_state['bet_history']}
- Aposta pendente: {game_state['pending_bet'] if game_state['pending_bet'] else 'Nenhuma'}

Qual sua decisão sobre apostas? Retorne um dicionário Python, num bloco de código Python (três crases ``` antes e depois), com uma das seguintes estruturas:

1. Para não fazer aposta:
```python
{{'action': 'pass'}}
```

2. Para pedir truco/aumentar aposta:
   {{"action": "bet", "bet_type": "truco/six/nine/twelve"}}
   Exemplo:
```python
{{"action": "bet", "bet_type": "truco"}}
```

3. Para aceitar uma aposta pendente:
```python
{{'action': 'accept'}}
```

4. Para correr de uma aposta pendente:
```python
   {{'action': 'run'}}
```
"""

        messages = [
            {"role": "system", "content": rules},
            {"role": "user", "content": state_info}
        ]
        
        try:
            if 'openrouter' in self.model:
                response = completion(model=self.model,
                                    messages=messages,
                                    timeout=300,
                                    extra_body={
                                        "include_reasoning": True,
                                        "provider": {
                                            "sort":"throughput"
                                        }
                                    })
            else:
                response = completion(model=self.model,
                                    messages=messages,
                                    timeout=300)
                
            if self.trace_logger:
                self.trace_logger.log_completion(
                    model=self.model,
                    messages=messages,
                    response=response,
                    player=self.name,
                    action_type='bet'
                )
            
            # Only track cost for non-openrouter models
            try:
                cost = completion_cost(completion_response=response)
                formatted_cost = f"${float(cost):.10f}"
                #print(formatted_cost)
                self.total_cost += float(cost)
            except:
                pass
            
            content = response.choices[0].message.content
            #print(content)
                
            # Look for content between ```python and ``` or just {...}
            match = re.search(r'```python\s*(\{[^}]*\})\s*```|(\{[^}]*\})', content, re.DOTALL)
            if not match:
                print("Invalid LLM response format in decide_bet. Full response:")
                print(content)
                raise LLMResponseError(
                    "Invalid LLM response format in decide_bet",
                    player_name=self.name,
                    model=self.model,
                    game_state=game_state,
                    raw_response=content
                )
                
            # Use the first group that matched (either inside ``` or standalone)
            dict_str = match.group(1) or match.group(2)
            action = eval(dict_str)
            
            # Validate the action has required fields
            if 'action' not in action:
                return None
                
            if action['action'] == 'bet' and 'bet_type' not in action:
                print("LLM response missing 'bet_type' in decide_bet. Full response:")
                print(content)
                raise LLMResponseError(
                    "Invalid bet action in decide_bet - missing bet_type",
                    player_name=self.name,
                    model=self.model,
                    game_state=game_state,
                    raw_response=content
                )
                
            return action
            
        except Exception as e:
            print(f"LLM parsing error in decide_bet for model: {self.model}. Raw response:")
            if 'content' in locals():
                print(content)
            raise LLMResponseError(
                f"Error parsing LLM response in decide_bet: {str(e)}",
                player_name=self.name,
                model=self.model,
                game_state=game_state,
                raw_response=content if 'content' in locals() else None
            )
            
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), retry=retry_if_exception_type(LLMResponseError))
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
- Rodada de apostas: {game_state['betting_round']}
- Aposta atual: {game_state['current_bet']}

Força das cartas (da mais fraca para mais forte):
4 < 5 < 6 < 7 < Q < J < K < A < 2 < 3 < Manilhas

Manilhas (da mais forte para mais fraca):
- Manilha de Paus (mais forte) - P
- Manilha de Copas - C
- Manilha de Espadas - E
- Manilha de Ouros (mais fraca) - O

Qual carta você quer jogar? Retorne um dicionário Python, num bloco de código Python (três crases ``` antes e depois), com a estrutura: {{"action": "play", "card": ["rank", "suit"]}}
Exemplo: 
```python
{{"action": "play", "card": ["K", "P"]}}
```"""

        messages = [
            {"role": "system", "content": rules},
            {"role": "user", "content": state_info}
        ]
        
        #print(state_info)
        try:
            if 'openrouter' in self.model:
                response = completion(model=self.model,
                                    messages=messages,
                                    timeout=300,
                                    extra_body={
                                        "include_reasoning": True,
                                        "provider": {
                                            "sort":"throughput"
                                        }
                                    })
            else:
                response = completion(model=self.model,
                                    messages=messages,
                                    timeout=300)
                
            if self.trace_logger:
                self.trace_logger.log_completion(
                    model=self.model,
                    messages=messages,
                    response=response,
                    player=self.name,
                    action_type='play'
                )
            
            try:
                cost = completion_cost(completion_response=response)
                formatted_cost = f"${float(cost):.10f}"
                #print(formatted_cost)
                self.total_cost += float(cost)
            except:
                pass
            
            content = response.choices[0].message.content
            #print(content)
            
            # Look for content between ```python and ``` or just {...}
            match = re.search(r'```python\s*({.*?})\s*```|({.*?})', content, re.DOTALL)
            if not match:
                print("Invalid LLM response format in decide_play. Full response:")
                print(content)
                raise LLMResponseError(
                    "No valid dictionary found in LLM response in decide_play",
                    player_name=self.name,
                    model=self.model,
                    game_state=game_state,
                    raw_response=content
                )
                
            # Use the first group that matched (either inside ``` or standalone)
            dict_str = match.group(1) or match.group(2)
            action = eval(dict_str)
            
            # Validate the action has required fields
            if action['action'] != 'play' or 'card' not in action:
                print("Invalid play action format in decide_play. Full response:")
                print(content)
                raise LLMResponseError(
                    "Invalid play action in decide_play - missing required fields",
                    player_name=self.name,
                    model=self.model,
                    game_state=game_state,
                    raw_response=content
                )
                
            if action['action'] == 'play':
                # Validate that the chosen card is indeed in the provided game state.
                if tuple(action['card']) not in game_state['my_cards']:
                    print("Decided card is not among the available cards in game_state.")
                    raise LLMResponseError(
                        "Invalid card: not in player's hand",
                        player_name=self.name,
                        model=self.model,
                        game_state=game_state,
                        raw_response=content
                    )
                    
            return action
            
        except Exception as e:
            print(f"LLM parsing error in decide_play for model: {self.model}. Raw response:")
            if 'content' in locals():
                print(content)
            raise LLMResponseError(
                f"Error parsing LLM response in decide_play: {str(e)}",
                player_name=self.name,
                model=self.model,
                game_state=game_state,
                raw_response=content if 'content' in locals() else None
            )

def play_match(model_A='openai/gpt-4o-mini', model_B='openai/gpt-4o-mini'):
    """Play a single match between two LLM players"""
    engine = TrucoEngine()
    
    # Generate unique match ID
    match_id = generate_match_id()
    
    # Initialize loggers
    trace_logger = MatchTraceLogger(model_A, model_B, match_id)
    
    # Create players with different strategies
    player_a = TrucoPlayer("A", model=model_A, trace_logger=trace_logger)
    player_b = TrucoPlayer("B", model=model_B, trace_logger=trace_logger)

    # Initialize event logger
    event_logger = MatchEventLogger(player_a.model, player_b.model, match_id)

    print(f"\n=== Game Started! ===\nTeam {player_a.model} vs Team {player_b.model}")
    
    while not engine.game_finished:
        engine.new_hand()
        
        #print("\n=== New Hand ===")
        # Log hand start
        event_logger.log_hand_start(
            engine.vira,
            engine.manilhas,
            {
                'A': engine.player_hands[0].copy(),
                'B': engine.player_hands[1].copy()
            }
        )
        
        # Play up to 3 rounds per hand
        for round_num in range(3):
            #print(f"\n--- Round {round_num + 1} ---")
            #print(f"Vira: {engine.vira}")
            #print(f"Manilhas: {engine.manilhas}")
            if engine.game_finished:
                break
            
            
            def get_bet_action(player_idx):
                player = player_a if player_idx == 0 else player_b
                state = format_game_state(engine, engine.player_hands[player_idx], player_idx)
                return player.decide_bet(state)
    
            try:
                bet_results = engine.run_betting_phase(get_bet_action)
                for (p_idx, action) in bet_results:
                    player_name = 'A' if p_idx == 0 else 'B'
                    event_logger.log_betting_action(
                        player_name,
                        action.get('action', 'error')
                    )
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
                # A mão foi encerrada por um "run": a aposta não foi aceita,
                # e os pontos devem ser os da aposta anterior (ou 1, se for o caso).
                hand_winner = engine.bet_stack[-1]['team']  # O time que fez a última aposta
                winner = 'A' if hand_winner == 0 else 'B'
                event_logger.log_hand_end(
                    winner=winner,
                    scores={'A': engine.scores[0], 'B': engine.scores[1]},
                    ended_by_run=True
                )
                break  # Encerra imediatamente a mão sem rodadas adicionais
            if engine.game_finished:
                break
            # Card playing phase
            # Player A's turn
            if len(engine.player_hands[0]) == 1:
                card_a = tuple(engine.player_hands[0][0])
                #print(f"Last round: automatically playing the only remaining card for Player A: {card_a}")
            else:
                try:
                    state_a = format_game_state(engine, engine.player_hands[0], 0)
                    play_a = player_a.decide_play(state_a)
                    card_a = tuple(play_a['card'])
                except LLMResponseError as e:
                    print(f"Error from Player A after 3 attempts: {e}. Awarding win to Player B.")
                    engine.scores[1] = 12
                    engine.game_finished = True
                    return
                #print(f"Player A plays: {card_a}")
                engine.play_card(0, card_a)
            event_logger.log_card_play('A', card_a)
            
            # Player B's turn
            if len(engine.player_hands[1]) == 1:
                card_b = tuple(engine.player_hands[1][0])
                #print(f"Last round: automatically playing the only remaining card for Player B: {card_b}")
            else:
                try:
                    state_b = format_game_state(engine, engine.player_hands[1], 1)
                    play_b = player_b.decide_play(state_b)
                    card_b = tuple(play_b['card'])
                except LLMResponseError as e:
                    print(f"Error from Player B after 3 attempts: {e}. Awarding win to Player A.")
                    engine.scores[0] = 12
                    engine.game_finished = True
                    return
                #print(f"Player B plays: {card_b}")
                engine.play_card(1, card_b)
            event_logger.log_card_play('B', card_b)
            
            # Log remaining cards after plays
            #print(f"Player A remaining cards: {engine.player_hands[0]}")
            #print(f"Player B remaining cards: {engine.player_hands[1]}")
            
            
            # Resolve round
            winner = engine.resolve_round([card_a, card_b])
            #print(f"Round winner: Player {'A' if winner == 0 else 'B'}")
            event_logger.log_round_end(round_num + 1, 'A' if winner == 0 else 'B')
            
            # Check for hand winner
            hand_winner = engine.check_hand_winner()
            if hand_winner is not None:
                engine.award_hand_points(hand_winner)
                #print(f"\nHand winner: Player {'A' if hand_winner == 0 else 'B'}")
                #print(f"Team A score: {engine.scores[0]}")
                #print(f"Team B score: {engine.scores[1]}")
                
                event_logger.log_hand_end(
                    winner='A' if hand_winner == 0 else 'B',
                    scores={'A': engine.scores[0], 'B': engine.scores[1]}
                )
                if engine.game_finished:
                    break
                break
    
    print(f"\n=== Game Complete! ===\nTeam {player_a.model} score: {engine.scores[0]} - Team {player_b.model} score: {engine.scores[1]}\nWinner: Team {'A' if engine.scores[0] >= 12 else 'B'}")
    
    # Log match end
    event_logger.log_match_end(
        final_scores={'A': engine.scores[0], 'B': engine.scores[1]},
        winner='A' if engine.scores[0] >= 12 else 'B',
        costs={'A': player_a.total_cost, 'B': player_b.total_cost}
    )
    
    # Save human readable match output
    match_history_dir = Path("match_history")
    match_history_dir.mkdir(exist_ok=True)
    
    readable_output = format_match_events(event_logger.events)
    readable_file = match_history_dir / f"match_{event_logger.match_id}.txt"
    with open(readable_file, "w", encoding="utf-8") as f:
        f.write(readable_output)

def get_model_pair(available_models, weights):
    """Select two different models using weighted random sampling"""
    first = random.choices(available_models, weights=weights, k=1)[0]
    remaining_models = [m for m in available_models if m != first]
    remaining_weights = [w for m, w in zip(available_models, weights) if m != first]
    second = random.choices(remaining_models, weights=remaining_weights, k=1)[0]
    return (first, second)


def get_openrouter_credits():
    # curl https://openrouter.ai/api/v1/credits \-H "Authorization: Bearer <token>"
    response = requests.get(
        "https://openrouter.ai/api/v1/credits",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"
        }
    )
    data = response.json()
    return round(data['data']['total_credits'] - data['data']['total_usage'])

if __name__ == '__main__':
    #print(get_openrouter_credits())
    #import time
    #time.sleep(1000)
    NUM_MATCHES = 16  # Set the number of matches to run in parallel
    # Load previous match counts
    try:
        with open('model_matches.json', 'r') as f:
            model_matches = json.load(f)
    except FileNotFoundError:
        model_matches = {}

    # Lista de modelos disponíveis (deve ter pelo menos 2)
    available_models = [
        'gemini/gemini-2.0-flash-lite-preview-02-05',
        'gemini/gemini-2.0-flash',
        'gemini/gemini-1.5-pro',
        'openrouter/openai/gpt-4o-mini',
        'openrouter/openai/gpt-4o',
        'openrouter/openai/o3-mini',
        'openrouter/deepseek/deepseek-chat',
        'openrouter/deepseek/deepseek-r1',
        'openrouter/anthropic/claude-3.5-sonnet',
        'openrouter/anthropic/claude-3.5-haiku',
        'openrouter/qwen/qwen-max',
        'openrouter/qwen/qwen-turbo',
        'openrouter/qwen/qwen-plus'
    ]

    # Calculate total matches across all models
    total_matches = sum(model_matches.get(model.split('/')[-1], 0) for model in available_models)
    
    # Calculate UCB weights for each model
    active_models = []
    weights = []
    for model in available_models:
        matches = model_matches.get(model.split('/')[-1], 0)
        if matches < 30:  # Still keep the max matches limit
            active_models.append(model)
            # UCB formula: sqrt(ln(total_matches)/(matches + 1))
            # Add 1 to matches to handle 0 matches case
            weight = math.sqrt(math.log(total_matches + 1)/(matches + 1))
            weights.append(weight)
    
    if len(active_models) < 2:
        print("Not enough active models to play matches (need at least 2)")
        sys.exit(1)
        
    print('Active models and weights:', {model: weight for model, weight in zip(active_models, weights)})
    executor = ThreadPoolExecutor(max_workers=min(get_openrouter_credits(), 8))
    try:
        futures = [
            executor.submit(
                play_match,
                model_A=models[0],
                model_B=models[1],
            )
            for _ in range(NUM_MATCHES)
            for models in [get_model_pair(active_models, weights)]
        ]
        for future in as_completed(futures):
            future.result()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received: canceling pending matches and shutting down...")
        for future in futures:
            future.cancel()
        sys.exit(0)
    finally:
        executor.shutdown(wait=False)
