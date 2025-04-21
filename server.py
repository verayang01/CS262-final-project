import socket
import threading
import json
import configparser
import os
import random
import time
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
import math
import hashlib

from shared import User, GameHistory, GameState, Message, MessageType, BOARD_SIZE, TIMEOUT

# ------------------ Database ------------------

class Database:
    """
    Handles all data persistence for the Five in a Row game server.
    Manages storage and retrieval of user accounts, game histories, and live game states.
    Uses JSON files for persistent storage of all game data.
    """
    def __init__(self, users_file: str, games_file: str, live_games_file: str):
        """
        Initializes the database with file paths for different data types.
        Creates the necessary files and directories if they don't exist.
        
        Args:
            users_file (str): Path to JSON file storing user account data
            games_file (str): Path to JSON file storing completed game histories
            live_games_file (str): Path to JSON file storing active game states
        """
        self.users_file = users_file
        self.games_file = games_file
        self.live_games_file = live_games_file
        self._prev_live_info = None  # Initialize as None
        self._prev_live_info_lock = threading.Lock()  # Add thread safety
        self._ensure_files_exist() # Create files if they don't exist

    def _ensure_files_exist(self):
        """
        Ensures all required database files exist with proper directory structure.
        Creates empty files with appropriate initial content if they don't exist.
        Handles both the parent directory and individual data files.
        """
        Path(self.users_file).parent.mkdir(parents=True, exist_ok=True)
        for file in [self.users_file, self.games_file, self.live_games_file]:
            if not os.path.exists(file):
                with open(file, 'w') as f: # Initialize with empty dict for user/live files, empty list for games
                    json.dump({} if "users" in file or "live" in file else [], f)

    def save_user(self, user: User):
        """
        Saves a user object to the database.
        Updates the existing user record or creates a new one if it doesn't exist.
        
        Args:
            user (User): The User object containing all user data to be saved
        """
        users = self._load_users()
        users[user.username] = user.to_dict()
        self._save_users(users)

    def get_user(self, username: str) -> Optional[User]:
        """
        Retrieves a user from the database by username.
        
        Args:
            username (str): The username to look up in the database
            
        Returns:
            Optional[User]: User object if found, None if user doesn't exist
        """
        users = self._load_users()
        user_data = users.get(username)
        return User(**user_data) if user_data else None

    def save_game_history(self, history: GameHistory):
        """
        Saves a completed game's history to the database.
        Appends the new history to the existing list of game histories.
        
        Args:
            history (GameHistory): The game history object to be saved
        """
        histories = self._load_game_histories()
        histories.append(history.to_dict())
        self._save_game_histories(histories)

    def get_user_history(self, username: str) -> List[GameHistory]:
        """
        Retrieves all game histories for a specific user.
        
        Args:
            username (str): The username to filter game histories by
            
        Returns:
            List[GameHistory]: List of GameHistory objects where the user participated
        """
        histories = self._load_game_histories()
        return [GameHistory(**h) for h in histories if h['player1'] == username or h['player2'] == username]

    def get_live_games(self) -> List[Dict]:
        """
        Retrieves summary information about all currently active games.
        
        Returns:
            List[Dict]: List of dictionaries containing active games information
        """
        live_games = []
        all_live_info = self._load_live_games()
        for game_id, game in all_live_info.items():
            black_stones = sum(1 for row in game['board'] for cell in row if cell == 'black')
            white_stones = sum(1 for row in game['board'] for cell in row if cell == 'white')
            live_games.append({
                'game_id': game_id,
                'player1': game['players']['black'],
                'player2': game['players']['white'],
                'black_stones': black_stones,
                'white_stones': white_stones,
                'current_player': game['current_player']
            })
        return live_games
    
    def _load_users(self) -> Dict:
        """
        Internal method to load all user data from the users file.

        Returns:
            Dict: Dictionary mapping usernames to user data dictionaries
        """
        retries = 5
        for attempt in range(retries):
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                if attempt < retries - 1:
                    continue  # Try again
                else:
                    raise

    def _save_users(self, users: Dict):
        """
        Internal method to save all user data to the users file.
        
        Args:
            users (Dict): Complete dictionary of user data to be saved
        """
        with open(self.users_file, 'w') as f:
            json.dump(users, f)

    def _load_game_histories(self) -> List:
        """
        Internal method to load all game histories from the game file.

        Returns:
            List: List of all game history dictionaries
        """
        retries = 5
        for attempt in range(retries):
            try:
                with open(self.games_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                if attempt < retries - 1:
                    continue  # Try again
                else:
                    raise


    def _save_game_histories(self, histories: List):
        """
        Internal method to save all game histories to the histories file.
        
        Args:
            histories (List): Complete list of game history dictionaries to save
        """
        with open(self.games_file, 'w') as f:
            json.dump(histories, f)

    def save_live_game(self, game_id: str, game_state: GameState):
        """
        Saves the current state of an active game to the database.
        
        Args:
            game_id (str): Unique identifier for the game
            game_state (GameState): Current state object of the game
        """
        games = self._load_live_games()
        games[game_id] = game_state.to_dict()
        with open(self.live_games_file, 'w') as f:
          json.dump(games, f)

    def load_live_game(self, game_id: str) -> Optional[GameState]:
        """
        Loads the current state of an active game from the database.
        
        Args:
            game_id (str): Unique identifier for the game to load
            
        Returns:
            Optional[GameState]: GameState object if found, None otherwise
        """
        games = self._load_live_games()
        state = games.get(game_id)
        return GameState(**state) if state else None

    def _load_live_games(self) -> Dict:
        """
        Internal method to load all active game states from the live games file.
        Returns last known good state if current read fails.
        """
        try:
            with open(self.live_games_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    return self._get_prev_live_info()        
                current_info = json.loads(content)
                with self._prev_live_info_lock:
                    self._prev_live_info = current_info  # Update last known good
                return current_info
        except json.JSONDecodeError as e:
            return self._get_prev_live_info()

    def _get_prev_live_info(self) -> Dict:
        """Thread-safe access to previous live info"""
        with self._prev_live_info_lock:
            return self._prev_live_info.copy() if self._prev_live_info else {}
        
    def delete_live_game(self, game_id: str):
        """
        Removes a completed game from the active games database.
        Uses atomic file operations with retry logic for Windows file locking issues.
        
        Args:
            game_id (str): Unique identifier of the game to remove
        """
        try:
            games = self._load_live_games()
            if game_id in games:
                del games[game_id]
            tmp_path = self.live_games_file + ".tmp"
            with open(tmp_path, 'w') as f:
                json.dump(games, f)
            # Retry logic for Windows file lock issue
            for attempt in range(5):
                try:
                    os.replace(tmp_path, self.live_games_file)
                    print(f"[DELETE] Game {game_id} removed from live_games.json")
                    break
                except PermissionError as e:
                    print(f"[WARN] Rename attempt {attempt+1} failed: {e}")
                    time.sleep(0.2)
            else:
                print(f"[ERROR] Failed to delete game {game_id} after retries.")

        except Exception as e:
            print(f"[ERROR] Failed to delete game {game_id}: {e}")

# ------------------ UserManager ------------------

class UserManager:
    """
    Manages all user-related operations for the Five in a Row game server.
    Handles authentication, account management, and user statistics.
    Maintains state of logged-in users and interfaces with the database.
    """
    def __init__(self, database: Database):
        """
        Initializes the UserManager with a database connection.
        
        Args:
            database (Database): The database instance for persistent storage
        """
        self.db = database
        self.logged_in_users = set() # Tracks currently logged in users

    def _hash_password(self, password: str) -> str:
        """
        Securely hashes a password using SHA-256 algorithm.
        
        Args:
            password (str): The plaintext password to hash
            
        Returns:
            str: The hexadecimal digest of the hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def handle_message(self, message: Message) -> Optional[Message]:
        """
        Routes incoming messages to appropriate handler methods.
        
        Args:
            message (Message): The incoming message to process
            
        Returns:
            Optional[Message]: Response message if handled, None otherwise
        """
        if message.type == MessageType.SIGNUP_REQUEST:
            return self._handle_signup(message)
        if message.type == MessageType.LOGIN_REQUEST:
            return self._handle_login(message)
        elif message.type == MessageType.LOGOUT:
            return self._handle_logout(message)
        elif message.type == MessageType.GET_STATS_REQUEST:
            return self._handle_get_stats(message)
        elif message.type == MessageType.ACCOUNT_DELETE_REQUEST:
            return self._handle_delete_account(message)
        return None

    def _handle_login(self, message: Message) -> Message:
        """
        Handles user login requests with authentication.
        
        Args:
            message (Message): Login request containing username and password
            
        Returns:
            Message: Response with user data if successful, error otherwise
        """
        username = message.data.get('username')
        password = message.data.get('password')
        if username in self.logged_in_users:
            return Message(MessageType.ERROR, {'message': 'User already logged in'})
        user = self.db.get_user(username)
        if not user:
            return Message(MessageType.ERROR, {'message': 'Username does not exist. Please sign up!'})
        if user.password != self._hash_password(password):
            return Message(MessageType.ERROR, {'message': 'Incorrect password'})
        self.logged_in_users.add(username)
        return Message(MessageType.LOGIN_RESPONSE, {
            'username': user.username,
            'credits': user.credits,
            'wins': user.wins,
            'losses': user.losses
        })
    
    def _handle_signup(self, message: Message) -> Message:
        """
        Handles new user account creation.
        
        Args:
            message (Message): Signup request containing username and password
            
        Returns:
            Message: Success response or error if username exists
        """
        username = message.data.get('username')
        password = message.data.get('password')
        if self.db.get_user(username):
            return Message(MessageType.ERROR, {'message': 'Username already exists'})
        hashed_password = self._hash_password(password)
        user = User(username=username, password=hashed_password)
        self.db.save_user(user)
        return Message(MessageType.SIGNUP_RESPONSE, {'success': True, 'username': username})

    def _handle_logout(self, message: Message) -> Message:  
        """
        Handles user logout requests.
        
        Args:
            message (Message): Logout request containing username
            
        Returns:
            Message: Success response or error if not logged in
        """  
        username = message.data.get('username')
        if username in self.logged_in_users:
            self.logged_in_users.discard(username)
            return Message(MessageType.LOGOUT, {'success': True})
        return Message(MessageType.ERROR, {'message': 'Not logged in'})
    
    def _handle_delete_account(self, message: Message) -> Message:
        """
        Handles account deletion requests with data cleanup.
        
        Args:
            message (Message): Delete request containing username
            
        Returns:
            Message: Success response or error if user not found
        """
        username = message.data.get('username')
        if not username or username not in self.db._load_users():
            return Message(MessageType.ERROR, {'message': 'User not found'})
        # Mark games where this user appears as "account deleted"
        histories = self.db._load_game_histories()
        for history in histories:
            if history['player1'] == username:
                history['player1'] = "account deleted"
            if history['player2'] == username:
                history['player2'] = "account deleted"
            if history['winner'] == username:
                history['winner'] = "account deleted"
        self.db._save_game_histories(histories) 
        # Remove user account
        users = self.db._load_users()
        users.pop(username, None)
        self.db._save_users(users)
        # Log them out
        self.logged_in_users.discard(username)
        return Message(MessageType.ACCOUNT_DELETE_RESPONSE, {'success': True})

    def _handle_get_stats(self, message: Message) -> Message:
        """
        Retrieves and returns user statistics.
        
        Args:
            message (Message): Stats request containing username
            
        Returns:
            Message: Response with user stats or error if not found
        """
        username = message.data.get('username')
        if not username:
            return Message(MessageType.ERROR, {'message': 'Username required'})
        user = self.db.get_user(username)
        if not user:
            return Message(MessageType.ERROR, {'message': 'User not found'})
        return Message(MessageType.GET_STATS_RESPONSE, {
            'username': user.username,
            'credits': user.credits,
            'online_players': len(self.logged_in_users)  
        })

    def update_user_stats(self, username: str, won: bool, credits_change: int):
        """
        Updates user statistics after a completed game.
        
        Args:
            username (str): The user to update
            won (bool): Whether the user won the game
            credits_change (int): Amount to adjust user's credits
        """
        user = self.db.get_user(username)
        if not user:
            return
        user.credits += credits_change
        if won:
            user.wins += 1
        else:
            user.losses += 1
        self.db.save_user(user)
    
    def get_leaderboard(self, limit=100) -> List[Dict]:
        """
        Generates a ranked leaderboard of players.
        
        Args:
            limit (int): Maximum number of players to include (default: 100)
            
        Returns:
            List[Dict]: Sorted list of player dictionaries containing:
                - username: Player name
                - credits: Current credit balance
                - wins: Total wins
                - losses: Total losses
        """
        users = self.db._load_users()
        sorted_users = sorted(
            users.values(),
            key=lambda u: (-u['credits'], -u['wins'], u['losses'])
        )
        return [{
            'username': u['username'],
            'credits': u['credits'],
            'wins': u['wins'],
            'losses': u['losses']
        } for u in sorted_users[:limit]]


# ------------------ Matchmaking ------------------

class Matchmaking:
    """
    Manages the matchmaking queue for pairing players in games.
    Implements a simple FIFO queue system for fair matching.
    """
    def __init__(self):
        """Initializes an empty matchmaking queue."""
        self.queue: List[str] = [] # List of usernames waiting for matches

    def handle_message(self, message: Message) -> Optional[Message]:
        """
        Processes matchmaking-related messages.
        
        Args:
            message (Message): The incoming message to process
            
        Returns:
            Optional[Message]: Response message if handled, None otherwise
        """
        if message.type == MessageType.QUEUE_REQUEST:
            return self._handle_queue_request(message)
        return None

    def _handle_queue_request(self, message: Message) -> Message:
        """
        Handles queue join/leave requests from players.
        
        Args:
            message (Message): Queue request containing:
                - username: Player name
                - action: 'join' or 'leave'
                
        Returns:
            Message: Response with queue status or error
        """
        username = message.data.get('username')
        action = message.data.get('action')
        if not username:
            return Message(MessageType.ERROR, {'message': 'Username required'})
        if action == 'join':
            if username not in self.queue:
                self.queue.append(username)
                if len(self.queue) >= 2:
                    p1 = self.queue.pop(0)
                    p2 = self.queue.pop(0)
                    return Message(MessageType.MATCH_FOUND, {'player1': p1, 'player2': p2})
                return Message(MessageType.QUEUE_RESPONSE, {'status': 'waiting', 'queue_size': len(self.queue)})
        elif action == 'leave':
            if username in self.queue:
                self.queue.remove(username)
            return Message(MessageType.QUEUE_RESPONSE, {'status': 'left_queue'})
        return Message(MessageType.ERROR, {'message': 'Invalid action'})

    def get_queue_size(self) -> int:
        """
        Gets the current number of players in the matchmaking queue.
        
        Returns:
            int: Number of players waiting for matches
        """
        return len(self.queue)

# ------------------ GameManager ------------------

class GameManager:
    """
    Manages all game-related operations for the Five in a Row server.
    Handles game creation, move validation, win detection, and game state persistence.
    Coordinates with UserManager for player statistics and credit calculations.
    """
    def __init__(self, user_manager: UserManager):
        """
        Initializes the GameManager with a UserManager instance.
        
        Args:
            user_manager (UserManager): The UserManager instance for player stats updates
        """
        self.games: Dict[str, GameState] = {}  # Active games dictionary (game_id -> GameState)
        self.user_manager = user_manager  # Reference to user management system
        self.move_deadlines = {}  # Tracks move timeouts (game_id -> deadline timestamp)
        self.move_history = {}  # Records all moves for each game (game_id -> list)

    def create_game(self, player1: str, player2: str) -> str:
        """
        Creates a new game between two players with random color assignment.
        
        Args:
            player1 (str): Username of first player
            player2 (str): Username of second player
            
        Returns:
            str: Unique game ID for the newly created game
        """
        game_id = f"game_{int(time.time())}_{random.randint(1000, 9999)}"
        black, white = (player1, player2) if random.random() < 0.5 else (player2, player1) # Randomly assign colors
        board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)] # Initialize empty board
        self.games[game_id] = GameState(
            board=board,
            current_player='black',
            players={'black': black, 'white': white},
            last_move=None,
            game_over=False,
            winner=None,
            time_remaining=TIMEOUT
        )
        self.user_manager.db.save_live_game(game_id, self.games[game_id])
        self.move_deadlines[game_id] = time.time() + TIMEOUT
        return game_id

    def handle_message(self, message: Message) -> Optional[Message]:
        """
        Routes incoming game-related messages to appropriate handlers.
        
        Args:
            message (Message): The incoming game message to process
            
        Returns:
            Optional[Message]: Response message if handled, None otherwise
        """
        if message.type == MessageType.MAKE_MOVE:
            return self._handle_make_move(message)
        elif message.type == MessageType.GET_HISTORY_REQUEST:
            return self._handle_get_history(message)
        elif message.type == MessageType.GET_LIVE_GAMES_REQUEST:
            return self._handle_get_live()
        elif message.type == MessageType.GET_GAME_STATE:
            game_id = message.data.get('game_id')
            game = self.user_manager.db.load_live_game(game_id)
            if game:
                return Message(MessageType.GAME_STATE, {
                    'game_id': game_id,
                    'state': game.to_dict()
                })
            return Message(MessageType.ERROR, {'message': 'Game not found'})
        elif message.type == MessageType.PLAYER_DISCONNECTED:
            return self._handle_player_disconnected(message)
        return None

    def _handle_make_move(self, message: Message) -> Union[Message, Tuple[Message, Message]]:
        """
        Processes a player's move attempt and updates game state.
        
        Args:
            message (Message): Move request containing:
                - game_id: The game identifier
                - username: Player making the move
                - row: Board row index (0-18)
                - col: Board column index (0-18)
                
        Returns:
            Union[Message, Tuple[Message, Message]]: 
                - Single state update message for normal moves
                - Tuple of (final state, game over) messages when game ends
        """
        data = message.data
        game_id, username, row, col = data.get('game_id'), data.get('username'), data.get('row'), data.get('col')
        if game_id not in self.games:
            return Message(MessageType.ERROR, {'message': 'Invalid game ID'})
        game = self.games[game_id]
        if game.game_over or not self._is_valid_move(game, username, row, col):
            return Message(MessageType.ERROR, {'message': 'Invalid move'})
        if game_id not in self.move_history:
            self.move_history[game_id] = [[row, col]]
        else:
            self.move_history[game_id].append([row, col])
        color = 'black' if game.players['black'] == username else 'white'
        game.board[row][col] = color
        game.last_move = (row, col)
        self.user_manager.db.save_live_game(game_id, game)
        winner = self._check_winner(game, row, col) # Check for win condition
        if not winner and all(cell is not None for row in game.board for cell in row):
            # No empty cells and no winner -> white wins by default
            winner = 'white'
        if winner:
            # Save and update game statistics
            game.game_over = True
            game.winner = game.players[winner]
            self.user_manager.db.save_live_game(game_id, game)  # Save latest board state
            moves_count = sum(1 for r in game.board for c in r if c)
            black_user = self.user_manager.db.get_user(game.players['black'])
            white_user = self.user_manager.db.get_user(game.players['white'])
            if winner == 'black':
                black_change, white_change = self.calculate_credit_change(black_user.credits, white_user.credits, moves_count)
            else:
                white_change, black_change = self.calculate_credit_change(white_user.credits, black_user.credits, moves_count)
            black_change = max(-black_user.credits, black_change)
            white_change = max(-white_user.credits, white_change)
            self.user_manager.update_user_stats(game.players['black'], winner == 'black', black_change)
            self.user_manager.update_user_stats(game.players['white'], winner == 'white', white_change)
            history = GameHistory(
                game_id=game_id,
                player1=game.players['black'],
                player2=game.players['white'],
                winner=game.winner,
                end_time=datetime.now().isoformat(),
                moves=self.move_history[game_id], 
                credits_change={
                    game.players['black']: black_change,
                    game.players['white']: white_change
                }
            )
            self.user_manager.db.save_game_history(history)
            self.user_manager.db.delete_live_game(game_id)
            del self.move_history[game_id]
            final_state_msg = Message(MessageType.GAME_STATE, {
                'game_id': game_id,
                'state': {
                    'board': game.board,
                    'current_player': game.current_player,
                    'players': game.players,
                    'game_over': True,
                    'winner': game.winner,
                    'time_remaining': 0
                }
            })
            # Send game over message
            game_over_msg = Message(MessageType.GAME_OVER, {
                'game_id': game_id,
                'winner': game.winner,
                'credits_change': {
                    game.players['black']: black_change,
                    game.players['white']: white_change
                }
            })
            return (final_state_msg, game_over_msg)
        # Switch turns and update timer
        game.current_player = 'white' if game.current_player == 'black' else 'black'
        game.time_remaining = TIMEOUT
        self.move_deadlines[game_id] = time.time() + TIMEOUT
        self.user_manager.db.save_live_game(game_id, game)
        return Message(MessageType.GAME_STATE, {
            'game_id': game_id,
            'state': {
                'board': game.board,
                'current_player': game.current_player,
                'players': game.players,
                'last_move': game.last_move,
                'game_over': game.game_over,
                'winner': game.winner,
                'time_remaining': game.time_remaining 
            }
        })

    def _is_valid_move(self, game, username, row, col):
        """
        Validates whether a move is legal.
        
        Args:
            game (GameState): Current game state
            username (str): Player attempting the move
            row (int): Board row coordinate
            col (int): Board column coordinate
            
        Returns:
            bool: True if move is valid, False otherwise
        """
        return (game.players[game.current_player] == username and
                0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE and
                game.board[row][col] is None)

    def _check_winner(self, game, row, col):
        """
        Checks if the last move resulted in a win.
        
        Args:
            game (GameState): Current game state
            row (int): Row of last move
            col (int): Column of last move
            
        Returns:
            Optional[str]: 'black' or 'white' if winner found, None otherwise
        """
        color = game.board[row][col]
        for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]: # Check all four possible winning directions
            count = 1
            for dir in [1, -1]:
                r, c = row + dir * dr, col + dir * dc
                while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and game.board[r][c] == color:
                    count += 1
                    r += dir * dr
                    c += dir * dc
            if count >= 5: # Five in a row found
                return color
        return None

    def _handle_get_history(self, message: Message) -> Message:
        """
        Retrieves game history for a specific player.
        
        Args:
            message (Message): History request containing username
            
        Returns:
            Message: Response with player's game histories
        """
        return Message(MessageType.GET_HISTORY_RESPONSE, {
            'histories': [h.to_dict() for h in self.user_manager.db.get_user_history(message.data.get('username'))]
        })
    
    def _handle_get_live(self) -> Message:
        """
        Retrieves information about currently active games.
        
        Returns:
            Message: Response with list of live games
        """
        return Message(MessageType.GET_LIVE_GAMES_RESPONSE, {
            'live_games': [l for l in self.user_manager.db.get_live_games()]
        })
    
    def _handle_player_disconnected(self, message: Message) -> Message:
        """
        Handles player disconnection by ending game and awarding win.
        
        Args:
            message (Message): Disconnect notification containing:
                - game_id: The affected game
                - username: Disconnected player
                
        Returns:
            Message: Game over notification to remaining player
        """
        game_id = message.data.get('game_id')
        username = message.data.get('username')
        if not game_id or not username or game_id not in self.games:
            return Message(MessageType.ERROR, {'message': 'Invalid disconnect request'})
        game = self.games[game_id]
        if game.game_over:
            return None
        # Identify winner as the remaining player
        winner = next(player for role, player in game.players.items() if player != username)
        game.game_over = True
        game.winner = winner
        # Save and update statisitcs
        moves_count = sum(1 for row in game.board for cell in row if cell)
        black_user = self.user_manager.db.get_user(game.players['black'])
        white_user = self.user_manager.db.get_user(game.players['white'])
        if game.players['black'] == winner:
            black_change, white_change = self.calculate_credit_change(black_user.credits, white_user.credits, moves_count)
        else:
            white_change, black_change = self.calculate_credit_change(white_user.credits, black_user.credits, moves_count)
        black_change = max(-black_user.credits, black_change)
        white_change = max(-white_user.credits, white_change)
        self.user_manager.update_user_stats(game.players['black'], winner == game.players['black'], black_change)
        self.user_manager.update_user_stats(game.players['white'], winner == game.players['white'], white_change)
        if game_id not in self.move_history:
            self.move_history[game_id] = []
        history = GameHistory(
            game_id=game_id,
            player1=game.players['black'],
            player2=game.players['white'],
            winner=winner,
            end_time=datetime.now().isoformat(),
            moves = self.move_history[game_id],
            credits_change={
                game.players['black']: black_change,
                game.players['white']: white_change
            }
        )
        self.user_manager.db.save_game_history(history)
        self.user_manager.db.delete_live_game(game_id)
        del self.move_history[game_id]
        # Notify both players
        response = Message(MessageType.GAME_OVER, {
            'game_id': game_id,
            'winner': winner,
            'disconnected': username,
            'credits_change': {
                game.players['black']: black_change,
                game.players['white']: white_change
            }
        })
        return response
    
    def calculate_credit_change(self, C_w, C_l, S, base_reward=50):
        """
        Calculates credit changes for winner and loser based on game factors.
        
        Args:
            C_w (int): Winner's current credits
            C_l (int): Loser's current credits
            S (int): Total stones placed in game
            base_reward (int): Base credit reward amount (default: 50)
            
        Returns:
            Tuple[int, int]: (winner_change, loser_change) credit adjustments
        """
        credit_diff = (C_w - C_l) / 2
        total_stones = max(S, 9)  # avoid division by 0
        avg_credit = (C_w + C_l) / 2
        credit_scale = math.log(avg_credit*2+10)/5 # Scale base_reward with average credit
        stone_efficiency = 1 / math.sqrt(total_stones) # Scaled reward based on stone efficiency
        if C_w >= C_l:
            skill_factor = 1 / (1 + abs(credit_diff) / 100)
        else:
            skill_factor = 1 + abs(credit_diff) / 100
        reward = base_reward * stone_efficiency * skill_factor * credit_scale
        reward = max(round(reward), 1)  # ensure at least 1 credit change
        return reward, -reward

# ------------------ GameServer ------------------

class GameServer:
    """
    The main game server that orchestrates all game operations.
    Handles client connections, message routing, and coordination between subsystems:
    - User authentication and management
    - Matchmaking and game creation  
    - Game state management
    - Real-time communication with clients
    
    The server maintains persistent connections with clients and manages
    the complete lifecycle of games from matchmaking to completion.
    """
    def __init__(self, config_file='config.ini'):
        """
        Initializes the game server with configuration from specified file.
        
        Args:
            config_file (str): Path to configuration file. Defaults to 'config.ini'.
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        # Initialize database and managers
        self.db = Database(
            self.config['database']['users_file'],
            self.config['database']['games_file'],
            self.config['database']['live_games_file']
        )
        self.user_manager = UserManager(self.db)
        self.matchmaking = Matchmaking()
        self.game_manager = GameManager(self.user_manager)
        # Server state variables
        self.clients: Dict[str, socket.socket] = {} # username -> socket mapping
        self.running = False # Server running flag
        self.matching_room_users = set()  # Track users in matching room
        self.match_requests = {}  # Active match requests: {request_id: {'from': username, 'to': username, 'time': timestamp}}

    def start(self):
        """
        Starts the game server and begins accepting connections.
        Binds to configured host/port and launches management threads:
        - Connection acceptor
        - Matchmaking loop  
        - Game timer checker
        """
        host = self.config['server']['host']
        port = int(self.config['server']['port'])
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(int(self.config['server']['max_players']))
        self.running = True
        print(f"Server started on {host}:{port}")
        # Start server components in separate threads
        threading.Thread(target=self._accept_connections).start()
        threading.Thread(target=self._matchmaking_loop).start()
        threading.Thread(target=self._check_timers, daemon=True).start()

    def stop(self):
        """
        Gracefully shuts down the server:
        - Stops accepting new connections
        - Closes existing connections
        - Terminates management threads
        """
        self.running = False
        self.server_socket.close()
        print("Server stopped")

    def _accept_connections(self):
        """
        Continuously accepts new client connections.
        Runs in dedicated thread while server is active.
        Spawns new thread per client for message handling.
        """
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"Connection from {address}")
                threading.Thread(target=self._handle_client, args=(client_socket,)).start()
            except OSError: # Server socket closed
                break

    def _handle_client(self, client_socket: socket.socket):
        """
        Manages communication with an individual client.
        
        Args:
            client_socket (socket.socket): The client's connection socket
        """
        try:
            file = client_socket.makefile('r')  # Read messages line by line
            while self.running:
                try:
                    line = file.readline()
                    if not line: # Connection closed
                        break
                    line = line.strip()
                    if not line: # Empty line
                        continue
                    message = Message.from_json(line)
                    response = self._process_message(message, client_socket)
                    if response:
                        client_socket.sendall((response.to_json() + '\n').encode('utf-8'))
                except Exception as e:
                    print(f"[WARN] Failed to process message from client: {e}")
                    break
        finally:
            # Clean up when client disconnects
            username = next((u for u, s in self.clients.items() if s == client_socket), None)
            if username:
                self.clients.pop(username, None)
                self.user_manager.handle_message(Message(MessageType.LOGOUT, {'username': username}))
                self.matchmaking.handle_message(Message(MessageType.QUEUE_REQUEST, {'username': username, 'action': 'leave'}))
                self.matching_room_users.discard(username)
                # Cancel any pending match requests
                for req_id, req in list(self.match_requests.items()).copy():
                    if req['from'] == username:
                        self._cancel_match_request(req_id, req['from'], req['to'], notify=True)
                print(f"Client {username} disconnected")
                # Check if user was in a game and handle disconnect as game loss
                for game_id, game in list(self.game_manager.games.items()).copy():
                    if username in game.players.values() and not game.game_over:
                        disconnect_msg = Message(MessageType.PLAYER_DISCONNECTED, {
                            'username': username,
                            'game_id': game_id
                        })
                        response = self.game_manager.handle_message(disconnect_msg)
                        if response and response.type == MessageType.GAME_OVER:
                            for player in game.players.values():
                                sock = self.clients.get(player)
                                if sock:
                                    try:
                                        sock.send((response.to_json() + '\n').encode('utf-8'))
                                    except:
                                        pass
            client_socket.close()

    def _process_message(self, message: Message, client_socket: socket.socket) -> Optional[Message]:
        """
        Processes incoming messages from clients and routes them to appropriate handlers.
        
        Args:
            message (Message): The incoming message from client.
            client_socket (socket.socket): The client's socket connection.
            
        Returns:
            Optional[Message]: Response message to send back, or None if no response needed.
        """
        # Authentication messages
        if message.type == MessageType.SIGNUP_REQUEST:
            return self.user_manager.handle_message(message)
        if message.type == MessageType.LOGIN_REQUEST:
            response = self.user_manager.handle_message(message)
            if response.type == MessageType.LOGIN_RESPONSE and 'username' in response.data:
                self.clients[response.data['username']] = client_socket
            return response
        username = message.data.get('username')
        if not username or username not in self.clients: # Authentication check
            print("Received type: " + message.type.value)
            return Message(MessageType.ERROR, {'message': 'Not authenticated'})
        # Route message to appropriate handler based on type
        if message.type in [MessageType.LOGOUT, MessageType.GET_STATS_REQUEST]:
            return self.user_manager.handle_message(message)
        elif message.type == MessageType.ACCOUNT_DELETE_REQUEST:
            return self.user_manager.handle_message(message)
        elif message.type == MessageType.QUEUE_REQUEST:
            queue_response = self.matchmaking.handle_message(message)
            if queue_response and queue_response.type == MessageType.MATCH_FOUND:
                p1, p2 = queue_response.data['player1'], queue_response.data['player2']
                game_id = self.game_manager.create_game(p1, p2)
                game = self.game_manager.games[game_id]
                msg = Message(MessageType.MATCH_FOUND, {
                    'black': game.players['black'],
                    'white': game.players['white'],
                    'game_id': game_id
                })
                for player in [p1, p2]:
                    sock = self.clients.get(player)
                    if sock:
                        sock.send((msg.to_json() + '\n').encode('utf-8'))
                return None
            return queue_response
        elif message.type == MessageType.MAKE_MOVE:
            response = self.game_manager.handle_message(message)
            game_id = message.data.get("game_id")
            game = self.game_manager.games.get(game_id)
            if isinstance(response, tuple):
                game_state_msg, game_over_msg = response
                for player in game.players.values():
                    sock = self.clients.get(player)
                    if sock:
                        try:
                            sock.send((game_state_msg.to_json() + '\n').encode("utf-8"))
                            sock.send((game_over_msg.to_json() + '\n').encode("utf-8"))
                        except:
                            pass
                return None
            elif isinstance(response, Message) and response.type == MessageType.GAME_STATE:
                if game:
                    for player in game.players.values():
                        sock = self.clients.get(player)
                        if sock:
                            try:
                                sock.send((response.to_json() + '\n').encode("utf-8"))
                            except:
                                pass
                return None
            elif isinstance(response, Message):
                return response
        elif message.type == MessageType.GET_HISTORY_REQUEST:
            return self.game_manager.handle_message(message)
        elif message.type == MessageType.GET_LEADERBOARD_REQUEST:
            leaderboard = self.user_manager.get_leaderboard()
            return Message(MessageType.GET_LEADERBOARD_RESPONSE, {
                'leaderboard': leaderboard
            })
        elif message.type == MessageType.GET_GAME_STATE:
            return self.game_manager.handle_message(message)
        elif message.type == MessageType.PLAYER_DISCONNECTED:
            response = self.game_manager.handle_message(message)
            if response and response.type == MessageType.GAME_OVER:
                game_id = message.data.get('game_id')
                game = self.game_manager.games.get(game_id)
                if game:
                    for player in game.players.values():
                        sock = self.clients.get(player)
                        if sock:
                            sock.send((response.to_json() + '\n').encode("utf-8"))
                return None
            return response
        elif message.type == MessageType.GET_LIVE_GAMES_REQUEST:
            return self.game_manager.handle_message(message)
        elif message.type == MessageType.MATCHING_ROOM_JOIN:
            username = message.data.get('username')
            if username and username in self.clients:
                self.matching_room_users.add(username)
                return Message(MessageType.MATCHING_ROOM_USERS, {
                    'users': [u for u in self.matching_room_users.copy() if u != username]
                })
        elif message.type == MessageType.MATCHING_ROOM_LEAVE:
            username = message.data.get('username')
            if username in self.matching_room_users:
                self.matching_room_users.discard(username)
                # Cancel any pending requests
                for req_id, req in list(self.match_requests.items()).copy():
                    if req['from'] == username or req['to'] == username:
                        self._cancel_match_request(req_id)
        elif message.type == MessageType.MATCH_REQUEST:
            from_user = message.data.get('from')
            to_user = message.data.get('to')
            expiry = message.data.get('expiry')
            if from_user in self.matching_room_users and to_user in self.matching_room_users:
                req_id = f"req_{int(time.time())}_{random.randint(1000, 9999)}"
                self.match_requests[req_id] = {
                    'from': from_user,
                    'to': to_user,
                    'time': time.time(),
                    'expiry': expiry  # 15 seconds to respond
                }
                # Notify the recipient
                to_socket = self.clients.get(to_user)
                if to_socket:
                    to_socket.send((Message(MessageType.MATCH_REQUESTS_RESPONSE, {
                        'requests': [{
                            'id': req_id, 
                            'from': from_user,
                            'credits': self.user_manager.db.get_user(from_user).credits,
                            'expiry': expiry
                        }]
                    }).to_json() + '\n').encode('utf-8'))
        elif message.type == MessageType.MATCH_RESPONSE:
            req_id = message.data.get('request_id')
            accepted = message.data.get('accepted')
            if req_id in self.match_requests:
                req = self.match_requests[req_id]
                if accepted:
                    # Create a game between these players
                    game_id = self.game_manager.create_game(req['from'], req['to'])
                    game = self.game_manager.games[game_id]
                    msg = Message(MessageType.MATCH_FOUND, {
                        'black': game.players['black'],
                        'white': game.players['white'],
                        'game_id': game_id
                    })
                    for player in [req['from'], req['to']]:
                        sock = self.clients.get(player)
                        if sock:
                            sock.send((msg.to_json() + '\n').encode('utf-8'))
                        self.matching_room_users.discard(player)
                else:
                    self._cancel_match_request(req_id)
                    sock = self.clients.get(req['from'])
                    if sock:
                        sock.send((Message(MessageType.MATCH_DECLINED, {'to': req['to']}).to_json() + '\n').encode('utf-8'))
        elif message.type == MessageType.MATCH_CANCEL:
            from_user = message.data.get('from')
            to_user = message.data.get('to')
            notify = message.data.get('notify')
            self._cancel_match_request(None, from_user, to_user, notify)
        elif message.type == MessageType.GET_MATCHING_ROOM_USERS:
            username = message.data.get('username')
            if username in self.matching_room_users:
                users_in_room = []
                for user in self.matching_room_users.copy():
                    if user != username:
                        user_data = self.user_manager.db.get_user(user)
                        if user_data:
                            users_in_room.append({
                                'username': user_data.username,
                                'credits': user_data.credits
                            })
                return Message(MessageType.MATCHING_ROOM_USERS, {
                    'users': users_in_room
                })
        return None

    def _cancel_match_request(self, req_id, from_user=None, to_user=None, notify=False):
        """
        Cancels a pending match request.
        
        Args:
            req_id (str): Request ID to cancel
            from_user (str, optional): Sender username
            to_user (str, optional): Recipient username
            notify (bool): Whether to notify recipient
        """
        if req_id in self.match_requests:
            del self.match_requests[req_id]
        elif from_user and to_user:
            try:
                req_id = [req_id for req_id, req in list(self.match_requests.items()).copy() if req['from'] == from_user and req['to'] == to_user][0]
                del self.match_requests[req_id]
            except:
                pass
        if to_user and notify:
            sock = self.clients.get(to_user)
            if sock:
                sock.send((Message(MessageType.MATCH_CANCEL, {
                    'request_id': req_id
                }).to_json() + '\n').encode('utf-8'))
    
    def _clean_expired_requests(self):
        """Periodically removes expired match requests."""
        current_time = time.time()
        expired_ids = [req_id for req_id, req in list(self.match_requests.items()).copy() 
                    if current_time > req['expiry']]
        for req_id in expired_ids:
            del self.match_requests[req_id]
    
    def _check_timers(self):
        """Checks game timers and processes timeouts."""
        while self.running:
            now = time.time()
            for game_id, game in list(self.game_manager.games.items()).copy():
                if game.game_over:
                    continue
                deadline = self.game_manager.move_deadlines.get(game_id)
                if deadline is None:
                    continue
                remaining = int(deadline - now)
                game.time_remaining = max(0, remaining)  # Ensure non-negative
                if remaining < 0:
                    self._make_random_move(game_id)
                else:
                    # Update and persist the remaining time
                    self.db.save_live_game(game_id, game)

            self._clean_expired_requests()
            time.sleep(1)

    def _make_random_move(self, game_id):
        """
        Makes a random move when player times out.
        
        Args:
            game_id (str): The game ID needing a move
        """
        game = self.game_manager.games[game_id]
        color = game.current_player
        username = game.players[color]
        empty_cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if game.board[r][c] is None]
        if not empty_cells:
            return
        row, col = random.choice(empty_cells)
        auto_move = Message(MessageType.MAKE_MOVE, {
            'username': username,
            'game_id': game_id,
            'row': row,
            'col': col
        })
        self._process_message(auto_move, self.clients[username])

    def _matchmaking_loop(self):
        """Maintains matchmaking queue processing."""
        while self.running:
            threading.Event().wait(1)

# ------------------ Main Entry ------------------

if __name__ == '__main__':
    server = GameServer()
    server.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.stop()
