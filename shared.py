from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import json

# Constants
BOARD_SIZE = 19  # Standard board size for Five in a Row (19x19 grid)
TIMEOUT = 30  # Default timeout duration for player moves in seconds

# Models
@dataclass
class User:
    """
    Represents a user account in the Five in a Row game system.
    
    Attributes:
        username (str): Unique identifier for the user.
        password (str): Hashed password for authentication.
        credits (int): In-game currency balance.
        wins (int): Total number of games won.
        losses (int): Total number of games lost.
        draws (int): Total number of games drawn.
    """
    username: str
    password: str 
    credits: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0

    def to_dict(self):
        """
        Converts the User object to a dictionary for serialization.
        
        Returns:
            dict: Dictionary representation of the User object.
        """
        return {
            'username': self.username,
            'password': self.password,
            'credits': self.credits,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws
        }

@dataclass
class GameHistory:
    """
    Represents the historical record of a completed Five in a Row game.
    
    Attributes:
        game_id (str): Unique identifier for the game.
        player1 (str): Username of the first player (Black).
        player2 (str): Username of the second player (White).
        winner (Optional[str]): Username of the winner.
        end_time (str): ISO-formatted timestamp of game end.
        moves (List[List[int, int]]): Sequence of moves as [row, col] lists.
        credits_change (dict): Dictionary mapping usernames to credit changes.
    """
    game_id: str
    player1: str
    player2: str
    winner: Optional[str]
    end_time: str
    moves: List[Tuple[int, int]]
    credits_change: dict  # {username: change}

    def to_dict(self):
        return {
            'game_id': self.game_id,
            'player1': self.player1,
            'player2': self.player2,
            'winner': self.winner,
            'end_time': self.end_time,
            'moves': self.moves,
            'credits_change': self.credits_change
        }

@dataclass
class GameState:
    """
    Represents the current state of an ongoing Five in a Row game.
    
    Attributes:
        board (List[List[Optional[str]]]): 19x19 game board with 'black', 'white', or None.
        current_player (str): Which player's turn it is ('black' or 'white').
        players (dict): Mapping of player roles to usernames.
        last_move (Optional[Tuple[int, int]]): Coordinates of the last move made.
        game_over (bool): Flag indicating if the game has concluded.
        winner (Optional[str]): Username of the winner if game is over.
        time_remaining (int): Seconds remaining for current player's move.
    """
    board: List[List[Optional[str]]]  # 'black', 'white', or None
    current_player: str  # 'black' or 'white'
    players: dict  # {'black': username, 'white': username}
    last_move: Optional[Tuple[int, int]] = None
    game_over: bool = False
    winner: Optional[str] = None  # username of winner
    time_remaining: int = TIMEOUT

    def to_dict(self):
        """
        Converts the GameState object to a dictionary for serialization.
        
        Returns:
            dict: Dictionary representation of the GameState object.
        """
        return {
            'board': self.board,
            'current_player': self.current_player,
            'players': self.players,
            'last_move': self.last_move,
            'game_over': self.game_over,
            'winner': self.winner,
            'time_remaining': self.time_remaining 
        }

# Protocol
class MessageType(Enum):
    """
    Enumeration of all message types used in client-server communication.
    Each value represents a specific type of message in the Five in a Row protocol.
    """
    # Authentication
    LOGIN_REQUEST = "login_request"
    LOGIN_RESPONSE = "login_response"
    LOGOUT = "logout"
    SIGNUP_REQUEST = "signup_request"
    SIGNUP_RESPONSE = "signup_response"
    
    # Matchmaking
    QUEUE_REQUEST = "queue_request"
    QUEUE_RESPONSE = "queue_response"
    MATCH_FOUND = "match_found"
    
    # Gameplay
    GAME_STATE = "game_state"
    MAKE_MOVE = "make_move"
    GAME_OVER = "game_over"
    PLAYER_DISCONNECTED = "player_disconnected"
    GET_GAME_STATE = "get_game_state"
    
    # User data
    GET_HISTORY_REQUEST = "get_history_request"
    GET_HISTORY_RESPONSE = "get_history_response"
    GET_STATS_REQUEST = "get_stats_request"
    GET_STATS_RESPONSE = "get_stats_response"
    GET_LEADERBOARD_REQUEST = "get_leaderboard_request"
    GET_LEADERBOARD_RESPONSE = "get_leaderboard_response"
    GET_LIVE_GAMES_REQUEST = "get_live_games_request"
    GET_LIVE_GAMES_RESPONSE = "get_live_games_response"
    GET_MATCHING_ROOM_USERS = "get_matching_room_users"
    
    # System
    ERROR = "error"
    HEARTBEAT = "heartbeat"

    # Matching Room
    MATCHING_ROOM_JOIN = "matching_room_join"
    MATCHING_ROOM_LEAVE = "matching_room_leave"
    MATCHING_ROOM_USERS = "matching_room_users"
    MATCH_REQUEST = "match_request"
    MATCH_RESPONSE = "match_response"
    MATCH_CANCEL = "match_cancel"
    GET_MATCH_REQUESTS = "get_match_requests"
    MATCH_REQUESTS_RESPONSE = "match_requests_response"
    MATCH_DECLINED = "match_declined"

    # Delete Account
    ACCOUNT_DELETE_REQUEST = "account_delete_request"
    ACCOUNT_DELETE_RESPONSE = "account_delete_response"

class Message:
    """
    Represents a message in the Five in a Row client-server protocol.
    Contains a message type and associated data payload.
    """
    def __init__(self, msg_type: MessageType, data: Optional[Dict[str, Any]] = None):
        """
        Initializes a new Message instance.
        
        Args:
            msg_type (MessageType): The type of message being created.
            data (Optional[Dict[str, Any]]): Additional message data as a dictionary.
        """
        self.type = msg_type
        self.data = data or {}

    def to_json(self):
        """
        Serializes the Message object to a JSON string.
        
        Returns:
            str: JSON string representation of the message.
        """
        return json.dumps({
            'type': self.type.value,
            'data': self.data
        })

    @classmethod
    def from_json(cls, json_str: str):
        """
        Creates a Message object from a JSON string.
        
        Args:
            json_str (str): JSON string to parse into a Message.
            
        Returns:
            Message: New Message instance created from the JSON data.
        """
        data = json.loads(json_str)
        return cls(MessageType(data['type']), data.get('data', {}))
    

