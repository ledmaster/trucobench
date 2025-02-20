import random

class TrucoEngine:
    RANKS = ['4', '5', '6', '7', 'Q', 'J', 'K', 'A', '2', '3']
    SUITS = ['P', 'C', 'E', 'O']  # Paus, Copas, Espadas, Ouros
    
    def __init__(self):
        self.scores = [0, 0]  # Team scores by index
        self.teams = [[1], [2]]  # Team players by index
        self.deck = []
        self.vira = None
        self.manilhas = []
        self.player_hands = {0: [], 1: []}  # Cards for each player
        self.bet_stack = []
        self.current_bet = 1
        self.round_winners = []  # Track winners of each round in the hand
        self.game_finished = False
        self.current_betting_player = 0
        self.betting_complete = False
        self.pending_bet_response = None
        self.last_bet_action = None
        self.skip_round = False
        self.bet_accepted = False
        
    def new_hand(self):
        """Initialize a new hand: shuffle the deck, deal three cards to each player, set the single vira, and determine the manilhas"""
        self.round_winners = []  # Reset round winners
        self._create_deck()
        random.shuffle(self.deck)
        
        # Deal 3 cards to each player
        self.player_hands = {
            0: [self.deck.pop() for _ in range(3)],
            1: [self.deck.pop() for _ in range(3)]
        }
            
        # Set vira and determine manilhas
        self.vira = self.deck.pop()
        self._set_manilhas()
        self.current_bet = 1
        self.bet_stack = []
        
    def _create_deck(self):
        """Create a 40-card deck"""
        self.deck = [(rank, suit) for rank in self.RANKS for suit in self.SUITS]
        
    def _set_manilhas(self):
        """Determine manilhas based on vira"""
        vira_idx = self.RANKS.index(self.vira[0])
        manilha_rank = self.RANKS[(vira_idx + 1) % len(self.RANKS)]
        
        # Order by suit strength: Paus > Copas > Espadas > Ouros
        self.manilhas = [
            (manilha_rank, 'P'),
            (manilha_rank, 'C'),
            (manilha_rank, 'E'),
            (manilha_rank, 'O')
        ]
        
    def _compare_cards(self, card1, card2):
        """Compare two cards, returns True if card1 wins"""
        # Check if either card is a manilha
        card1_manilha_idx = -1
        card2_manilha_idx = -1
        
        for idx, manilha in enumerate(self.manilhas):
            if card1 == manilha:
                card1_manilha_idx = idx
            if card2 == manilha:
                card2_manilha_idx = idx
                
        # If both are manilhas, higher manilha wins
        if card1_manilha_idx >= 0 and card2_manilha_idx >= 0:
            return card1_manilha_idx < card2_manilha_idx
            
        # If only one is manilha, it wins
        if card1_manilha_idx >= 0:
            return True
        if card2_manilha_idx >= 0:
            return False
            
        # Neither is manilha, compare by rank; if equal, use suit as a tiebreaker.
        rank1 = self.RANKS.index(card1[0])
        rank2 = self.RANKS.index(card2[0])
        if rank1 == rank2:
            # Compare suits based on defined strength: Paus > Copas > Espadas > Ouros.
            return self.SUITS.index(card1[1]) < self.SUITS.index(card2[1])
        else:
            return rank1 > rank2
        
    def resolve_round(self, played_cards):
        """Resolve a round with played cards, returns winning team index"""
        if len(played_cards) != 2:
            raise ValueError("Need exactly 2 played cards")
            
        winner = 0 if self._compare_cards(played_cards[0], played_cards[1]) else 1
        self.round_winners.append(winner)
        return winner
        
    def handle_bet(self, bet_type, team):
        """Handle betting (truco/six/nine/twelve)"""
        bet_values = {
            'truco': 3,
            'six': 6,
            'nine': 9,
            'twelve': 12
        }
        
        if bet_type not in bet_values:
            raise ValueError("Invalid bet type")
            
        # Validate bet sequence
        if self.bet_stack:
            last_bet = self.bet_stack[-1]['type']
            valid_sequence = {
                'truco': ['six'],
                'six': ['nine'],
                'nine': ['twelve'],
                'twelve': []
            }
            if bet_type not in valid_sequence[last_bet]:
                raise ValueError("Invalid bet sequence")
            
        self.bet_stack.append({
            'type': bet_type,
            'value': bet_values[bet_type],
            'team': team
        })
        self.current_bet = bet_values[bet_type]
        
        return {
            'current_bet': bet_values[bet_type],
            'responding_team': (team + 1) % 2
        }
        
    def run_from_bet(self, running_team):
        """Handle when a team runs from a bet"""
        if not self.bet_stack:
            raise ValueError("No active bet to run from")
            
        # Points go to the team that made the last bet
        last_bet = self.bet_stack[-1]
        scoring_team = last_bet['team']
        
        # Calculate points based on previous bet
        if len(self.bet_stack) == 1:  # Running from truco
            self.scores[scoring_team] += 1
        else:
            prev_bet = self.bet_stack[-2]
            self.scores[scoring_team] += prev_bet['value']
        
        if self.scores[scoring_team] >= 12:
            self.game_finished = True
            
        return True
        
    def check_hand_winner(self):
        """Check if there's a winner for the current hand"""
        if len(self.round_winners) < 2:
            return None
            
        # Count wins for each team
        team_wins = [self.round_winners.count(0), self.round_winners.count(1)]
        
        # Need 2 wins to win the hand
        if team_wins[0] >= 2:
            return 0
        elif team_wins[1] >= 2:
            return 1
        return None
        
    def award_hand_points(self, winning_team):
        """Award points for winning a hand"""
        self.scores[winning_team] += self.current_bet
        
        # Check if game is finished
        if self.scores[winning_team] >= 12:
            self.game_finished = True
            
    def start_betting_phase(self):
        """Initialize betting phase state"""
        self.current_betting_player = 0  # Player index
        self.betting_complete = False
        self.pending_bet_response = None
        self.last_bet_action = None
        self.skip_round = False

    def handle_player_bet_action(self, action, player_idx):
        """Process a player's betting action"""
        if self.betting_complete:
            return

        # Validate it's the player's turn
        if player_idx != self.current_betting_player:
            raise ValueError("Not this player's turn to act")

        if action['action'] == 'bet':
            self.handle_bet(action['bet_type'], player_idx)
            self.last_bet_action = action
            self.current_betting_player = 1 - self.current_betting_player
            self.pending_bet_response = True
        elif action['action'] == 'accept':
            if self.bet_stack:
                self.current_bet = self.bet_stack[-1]['value']
            else:
                self.current_bet = 1  # fallback (should not occur if a bet was made)
            self.betting_complete = True
            self.bet_accepted = True
        elif action['action'] == 'run':
            self.run_from_bet(player_idx)
            self.betting_complete = True
            self.skip_round = True
        elif action['action'] == 'pass':
            if self.pending_bet_response:
                if self.bet_stack:
                    self.current_bet = self.bet_stack[-1]['value']
                else:
                    self.current_bet = 1
                self.betting_complete = True
                self.bet_accepted = True
            else:
                # Both players passing means keep current bet
                self.current_betting_player = 1 - self.current_betting_player
                if self.current_betting_player == 0:  # Both passed
                    self.betting_complete = True

    def run_betting_phase(self, get_bet_action):
        self.start_betting_phase()
        bet_actions = []
        while not self.betting_complete:
            current_player = self.current_betting_player
            action = get_bet_action(current_player)
            try:
                self.handle_player_bet_action(action, current_player)
            except Exception:
                action = {'action': 'pass'}
                self.handle_player_bet_action(action, current_player)
            bet_actions.append((current_player, action))
        return bet_actions

    def play_card(self, player_idx, card):
        """Play a card from a player's hand"""
        if card in self.player_hands[player_idx]:
            self.player_hands[player_idx].remove(card)
        else:
            raise ValueError("Card not in player's hand")
