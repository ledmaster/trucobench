import random

class TrucoPaulistaEngine:
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
        
    def new_match(self):
        """Initialize a new match with shuffled deck and dealt cards"""
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
            
        # Neither is manilha, compare by rank
        return self.RANKS.index(card1[0]) > self.RANKS.index(card2[0])
        
    def resolve_round(self, played_cards):
        """Resolve a round with played cards, returns winning team index"""
        if len(played_cards) != 2:
            raise ValueError("Need exactly 2 played cards")
            
        return 0 if self._compare_cards(played_cards[0], played_cards[1]) else 1
        
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
            
        self.bet_stack.append({
            'type': bet_type,
            'value': bet_values[bet_type],
            'team': team
        })
        
        return {
            'current_bet': bet_values[bet_type],
            'responding_team': (team + 1) % 2
        }
