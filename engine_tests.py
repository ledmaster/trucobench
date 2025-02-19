import unittest
from engine import TrucoPaulistaEngine

class TestTrucoPaulistaEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TrucoPaulistaEngine()

    def test_initial_state(self):
        """Test initial game state"""
        self.assertEqual(len(self.engine.teams), 2)
        self.assertEqual(self.engine.teams[0]['score'], 0)
        self.assertEqual(self.engine.teams[1]['score'], 0)
        self.assertEqual(self.engine.teams[0]['players'], [1])
        self.assertEqual(self.engine.teams[1]['players'], [2])

    def test_new_match_deck_setup(self):
        """Test deck initialization for a new match"""
        self.engine.new_match()
        # Should have 40 cards (no 8,9,10,jokers)
        self.assertEqual(len(self.engine.deck), 40)
        # Check if vira was set
        self.assertIsNotNone(self.engine.vira)
        # Each player should have 3 cards
        self.assertEqual(len(self.engine.current_hand), 6)  # 2 players * 3 cards

    def test_manilha_rules(self):
        """Test manilha determination based on vira"""
        # Simulate vira as 4
        self.engine.vira = ('4', '♠')
        self.engine._set_manilhas()
        expected_manilhas = [
            ('5', '♣'),  # Strongest - Zap
            ('5', '♥'),  # Second - Copas
            ('5', '♠'),  # Third - Espadas
            ('5', '♦'),  # Weakest - Ouros
        ]
        self.assertEqual(self.engine.manilhas, expected_manilhas)

    def test_card_strength_comparison(self):
        """Test card comparison rules"""
        # Regular cards (no manilhas)
        self.assertTrue(
            self.engine._compare_cards(('3', '♠'), ('2', '♥'))
        )
        self.assertTrue(
            self.engine._compare_cards(('2', '♠'), ('A', '♥'))
        )
        
        # Manilha comparison
        self.engine.vira = ('4', '♠')
        self.engine._set_manilhas()
        self.assertTrue(
            self.engine._compare_cards(('5', '♣'), ('5', '♥'))  # Paus beats Copas
        )
        self.assertTrue(
            self.engine._compare_cards(('5', '♥'), ('5', '♠'))  # Copas beats Espadas
        )

    def test_bet_handling(self):
        """Test bet management"""
        # Initial truco bet
        result = self.engine.handle_bet('truco', 0)
        self.assertEqual(result['current_bet'], 3)
        self.assertEqual(result['responding_team'], 1)
        
        # Six bet response
        result = self.engine.handle_bet('six', 1)
        self.assertEqual(result['current_bet'], 6)
        self.assertEqual(result['responding_team'], 0)

if __name__ == '__main__':
    unittest.main()
