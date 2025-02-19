import unittest
from engine import TrucoPaulistaEngine

class TestTrucoPaulistaEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TrucoPaulistaEngine()

    def test_initial_state(self):
        """Test initial game state"""
        self.assertEqual(len(self.engine.teams), 2)
        self.assertEqual(self.engine.scores[0], 0)
        self.assertEqual(self.engine.scores[1], 0)
        self.assertEqual(self.engine.teams[0], [1])
        self.assertEqual(self.engine.teams[1], [2])

    def test_new_match_deck_setup(self):
        """Test deck initialization for a new match"""
        self.engine.new_match()
        # Should have 33 cards (40 initial - 6 dealt - 1 vira)
        self.assertEqual(len(self.engine.deck), 33)
        # Check if vira was set
        self.assertIsNotNone(self.engine.vira)
        # Each player should have 3 cards
        self.assertEqual(len(self.engine.player_hands[0]), 3)
        self.assertEqual(len(self.engine.player_hands[1]), 3)

    def test_manilha_rules(self):
        """Test manilha determination based on vira"""
        # Simulate vira as 4
        self.engine.vira = ('4', 'E')
        self.engine._set_manilhas()
        expected_manilhas = [
            ('5', 'P'),  # Strongest - Zap
            ('5', 'C'),  # Second - Copas
            ('5', 'E'),  # Third - Espadas
            ('5', 'O'),  # Weakest - Ouros
        ]
        self.assertEqual(self.engine.manilhas, expected_manilhas)

    def test_card_strength_comparison(self):
        """Test card comparison rules"""
        # Regular cards (no manilhas)
        self.assertTrue(
            self.engine._compare_cards(('3', 'E'), ('2', 'C'))
        )
        self.assertTrue(
            self.engine._compare_cards(('2', 'E'), ('A', 'C'))
        )
        
        # Manilha comparison
        self.engine.vira = ('4', 'E')
        self.engine._set_manilhas()
        self.assertTrue(
            self.engine._compare_cards(('5', 'P'), ('5', 'C'))  # Paus beats Copas
        )
        self.assertTrue(
            self.engine._compare_cards(('5', 'C'), ('5', 'E'))  # Copas beats Espadas
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

    def test_betting_truco_accept(self):
        # Scenario: Player 0 bets 'truco', then Player 1 accepts.
        self.engine.start_betting_phase()
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'truco'}, 0)
        self.engine.handle_player_bet_action({'action': 'accept'}, 1)
        self.assertTrue(self.engine.betting_complete)
        self.assertEqual(self.engine.current_bet, 3)
        self.assertEqual(len(self.engine.bet_stack), 1)
        self.assertEqual(self.engine.bet_stack[0]['type'], 'truco')

    def test_betting_truco_six_accept(self):
        # Scenario: Player 0 bets 'truco', then Player 1 raises with 'six', and Player 0 accepts.
        self.engine.start_betting_phase()
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'truco'}, 0)
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'six'}, 1)
        self.engine.handle_player_bet_action({'action': 'accept'}, 0)
        self.assertTrue(self.engine.betting_complete)
        self.assertEqual(self.engine.current_bet, 6)
        self.assertEqual(len(self.engine.bet_stack), 2)
        self.assertEqual(self.engine.bet_stack[0]['type'], 'truco')
        self.assertEqual(self.engine.bet_stack[1]['type'], 'six')

    def test_betting_truco_six_nine_accept(self):
        # Scenario: Player 0 bets 'truco', Player 1 raises with 'six', then Player 0 raises with 'nine' and Player 1 accepts.
        self.engine.start_betting_phase()
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'truco'}, 0)
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'six'}, 1)
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'nine'}, 0)
        self.engine.handle_player_bet_action({'action': 'accept'}, 1)
        self.assertTrue(self.engine.betting_complete)
        self.assertEqual(self.engine.current_bet, 9)
        self.assertEqual(len(self.engine.bet_stack), 3)
        self.assertEqual(self.engine.bet_stack[2]['type'], 'nine')

    def test_betting_truco_six_run(self):
        # Scenario: Player 0 bets 'truco', Player 1 raises with 'six', then Player 0 runs.
        self.engine.start_betting_phase()
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'truco'}, 0)
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'six'}, 1)
        initial_scores = self.engine.scores.copy()
        self.engine.handle_player_bet_action({'action': 'run'}, 0)
        self.assertTrue(self.engine.betting_complete)
        self.assertTrue(self.engine.skip_round)
        # With two bets, run awards points equal to the previous bet's value (i.e. 3) to the betting team of the last bet.
        scoring_team = self.engine.bet_stack[-1]['team']
        self.assertEqual(self.engine.scores[scoring_team], initial_scores[scoring_team] + 3)

    def test_both_pass_no_bet(self):
        # Scenario: Both players pass without any bet being initiated.
        self.engine.start_betting_phase()
        self.engine.handle_player_bet_action({'action': 'pass'}, 0)
        self.engine.handle_player_bet_action({'action': 'pass'}, 1)
        self.assertTrue(self.engine.betting_complete)
        self.assertEqual(len(self.engine.bet_stack), 0)
        self.assertEqual(self.engine.current_bet, 1)  # Remains the default bet (1)

    def test_betting_truco_pass(self):
        # Scenario: Player 0 bets 'truco', then Player 1 passes (which the engine treats as accept due to a pending bet).
        self.engine.start_betting_phase()
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'truco'}, 0)
        self.engine.handle_player_bet_action({'action': 'pass'}, 1)
        self.assertTrue(self.engine.betting_complete)
        self.assertEqual(self.engine.current_bet, 3)
        self.assertEqual(len(self.engine.bet_stack), 1)

    def test_betting_truco_six_nine_run(self):
        # Scenario: Player 0 bets 'truco', Player 1 raises with 'six', Player 0 raises with 'nine',
        # then Player 1 runs. With three bets, run should award points equal to the previous bet's value (i.e. 6)
        self.engine.start_betting_phase()
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'truco'}, 0)
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'six'}, 1)
        self.engine.handle_player_bet_action({'action': 'bet', 'bet_type': 'nine'}, 0)
        initial_scores = self.engine.scores.copy()
        self.engine.handle_player_bet_action({'action': 'run'}, 1)
        self.assertTrue(self.engine.betting_complete)
        self.assertTrue(self.engine.skip_round)
        scoring_team = self.engine.bet_stack[-1]['team']
        self.assertEqual(self.engine.scores[scoring_team], initial_scores[scoring_team] + 6)

    def test_run_betting_phase_pass(self):
        engine = TrucoPaulistaEngine()
        actions = [{'action': 'pass'}, {'action': 'pass'}]
        def get_bet_action(player_idx):
            return actions.pop(0)
        result = engine.run_betting_phase(get_bet_action)
        self.assertTrue(engine.betting_complete)
        self.assertEqual(engine.current_bet, 1)  # Default bet remains unchanged
        self.assertEqual(len(engine.bet_stack), 0)
        self.assertEqual(result, [(0, {'action': 'pass'}), (1, {'action': 'pass'})])

    def test_run_betting_phase_truco_accept(self):
        engine = TrucoPaulistaEngine()
        actions = [{'action': 'bet', 'bet_type': 'truco'}, {'action': 'accept'}]
        def get_bet_action(player_idx):
            return actions.pop(0)
        result = engine.run_betting_phase(get_bet_action)
        self.assertTrue(engine.betting_complete)
        self.assertEqual(engine.current_bet, 3)
        self.assertEqual(len(engine.bet_stack), 1)
        self.assertEqual(result, [(0, {'action': 'bet', 'bet_type': 'truco'}), (1, {'action': 'accept'})])

    def test_run_betting_phase_run(self):
        engine = TrucoPaulistaEngine()
        actions = [{'action': 'bet', 'bet_type': 'truco'}, {'action': 'run'}]
        initial_scores = engine.scores.copy()
        def get_bet_action(player_idx):
            return actions.pop(0)
        result = engine.run_betting_phase(get_bet_action)
        self.assertTrue(engine.betting_complete)
        self.assertTrue(engine.skip_round)
        scoring_team = engine.bet_stack[-1]['team']
        self.assertEqual(engine.scores[scoring_team], initial_scores[scoring_team] + 1)

if __name__ == '__main__':
    unittest.main()
