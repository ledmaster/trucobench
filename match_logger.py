import logging
import json
from datetime import datetime
import os

def setup_logger():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Setup file handler for match logs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'logs/match_{timestamp}.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('truco')

def save_match_history(match_data):
    """Save match history to JSON file"""
    if not os.path.exists('match_history'):
        os.makedirs('match_history')
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'match_history/match_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(match_data, f, indent=2)
