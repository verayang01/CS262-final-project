import unittest
import os
import tempfile
import socket
import threading
import time
import tkinter as tk
import io
from unittest.mock import MagicMock, patch

# Import modules
from shared import User, GameHistory, GameState, Message, MessageType, BOARD_SIZE
from server import Database, UserManager, Matchmaking, GameManager, GameServer
from client import GameClient, AuthUI, HomeUI, WaitingUI, GameUI, GameReplayUI, LiveGamesUI, LiveGameViewerUI, HistoryUI, LeaderboardUI, MatchingRoomUI

# -------------------------------------------------------------------
# TestSharedModels 
# -------------------------------------------------------------------
class TestSharedModels(unittest.TestCase):
    """Test cases for shared data models used across client and server."""
    
    def test_user_model(self):
        """
        Test the User model's attributes and serialization.
        
        Verifies:
        - User attributes are correctly set
        - to_dict() method produces expected dictionary output
        """
        user = User(username="test", password="pass", credits=100, wins=5, losses=2)
        self.assertEqual(user.username, "test")
        self.assertEqual(user.password, "pass")
        self.assertEqual(user.credits, 100)
        self.assertEqual(user.wins, 5)
        self.assertEqual(user.losses, 2)
        
        user_dict = user.to_dict()
        self.assertEqual(user_dict["username"], "test")
        self.assertEqual(user_dict["password"], "pass")
        self.assertEqual(user_dict["credits"], 100)

    def test_game_history_model(self):
        """
        Test the GameHistory model's attributes and serialization.
        
        Verifies:
        - Game history attributes are correctly set
        - to_dict() method produces expected dictionary output
        - Move list is properly stored
        """
        history = GameHistory(
            game_id="game1",
            player1="p1",
            player2="p2",
            winner="p1",
            start_time="2023-01-01",
            end_time="2023-01-01",
            moves=[(1,1), (2,2)],
            credits_change={"p1": 10, "p2": -10}
        )
        
        self.assertEqual(history.game_id, "game1")
        self.assertEqual(history.player1, "p1")
        self.assertEqual(history.winner, "p1")
        self.assertEqual(len(history.moves), 2)
        
        history_dict = history.to_dict()
        self.assertEqual(history_dict["game_id"], "game1")
        self.assertEqual(history_dict["credits_change"]["p1"], 10)

    def test_game_state_model(self):
        """
        Test the GameState model's attributes and serialization.
        
        Verifies:
        - Game board initialization
        - Player turn tracking
        - Serialization to dictionary
        """
        board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        state = GameState(
            board=board,
            current_player="black",
            players={"black": "p1", "white": "p2"},
            last_move=(1,1),
            game_over=False,
            winner=None
        )
        
        self.assertEqual(state.current_player, "black")
        self.assertEqual(state.players["white"], "p2")
        self.assertFalse(state.game_over)
        
        state_dict = state.to_dict()
        self.assertEqual(state_dict["current_player"], "black")
        self.assertEqual(len(state_dict["board"]), BOARD_SIZE)

    def test_message_protocol(self):
        """
        Test the Message protocol serialization and deserialization.
        
        Verifies:
        - Message type and data are correctly set
        - JSON serialization/deserialization round trip
        - Message type preservation
        """
        msg = Message(MessageType.LOGIN_REQUEST, {"username": "test", "password": "pass"})
        self.assertEqual(msg.type, MessageType.LOGIN_REQUEST)
        self.assertEqual(msg.data["username"], "test")
        
        json_str = msg.to_json()
        parsed_msg = Message.from_json(json_str)
        self.assertEqual(parsed_msg.type, MessageType.LOGIN_REQUEST)
        self.assertEqual(parsed_msg.data["username"], "test")

# -------------------------------------------------------------------
# TestDatabase 
# -------------------------------------------------------------------
class TestDatabase(unittest.TestCase):
    """Test cases for the Database class handling persistent storage."""

    def setUp(self):
        """Create temporary directory and initialize test database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.users_file = os.path.join(self.temp_dir.name, "users.json")
        self.games_file = os.path.join(self.temp_dir.name, "games.json")
        self.live_games_file = os.path.join(self.temp_dir.name, "live_games.json")
        
        self.db = Database(self.users_file, self.games_file, self.live_games_file)

    def tearDown(self):
        """Clean up temporary directory after tests."""
        self.temp_dir.cleanup()

    def test_user_operations(self):
        """
        Test basic user operations.
        
        Verifies:
        - User can be saved and retrieved
        - Non-existent user returns None
        """
        user = User(username="test", password="hash")
        
        # Test save and get
        self.db.save_user(user)
        retrieved = self.db.get_user("test")
        self.assertEqual(retrieved.username, "test")
        self.assertEqual(retrieved.password, "hash")
        
        # Test non-existent user
        self.assertIsNone(self.db.get_user("nonexistent"))

    def test_game_history_operations(self):
        """
        Test game history storage and retrieval.
        
        Verifies:
        - Game history can be saved
        - User-specific history filtering
        """
        history = GameHistory(
            game_id="game1",
            player1="p1",
            player2="p2",
            winner="p1",
            start_time="2023-01-01",
            end_time="2023-01-01",
            moves=[(1,1)],
            credits_change={"p1": 10}
        )
        
        self.db.save_game_history(history)
        histories = self.db.get_user_history("p1")
        self.assertEqual(len(histories), 1)
        self.assertEqual(histories[0].game_id, "game1")
        
        # Test filtering by user
        histories = self.db.get_user_history("p3")
        self.assertEqual(len(histories), 0)

    def test_live_game_operations(self):
        """
        Test live game state storage operations.
        
        Verifies:
        - Game state can be saved and loaded
        - Game state can be deleted
        """
        board = [[None for _ in range(19)] for _ in range(19)]
        state = GameState(
            board=board,
            current_player="black",
            players={"black": "p1", "white": "p2"},
            game_over=False
        )
        
        # Test save and load
        self.db.save_live_game("game1", state)
        loaded = self.db.load_live_game("game1")
        self.assertEqual(loaded.current_player, "black")
        self.assertEqual(loaded.players["white"], "p2")
        
        # Test delete
        self.db.delete_live_game("game1")
        self.assertIsNone(self.db.load_live_game("game1"))

    def test_get_live_games(self):
        """
        Test retrieval of all live games.
        
        Verifies:
        - Correct number of live games returned
        """
        board = [[None for _ in range(19)] for _ in range(19)]
        state = GameState(
            board=board,
            current_player="black",
            players={"black": "p1", "white": "p2"},
            game_over=False
        )
        
        # Test correct live game information
        self.db.save_live_game("game1", state)
        live_games = self.db.get_live_games()
        self.assertEqual(len(live_games), 1)
        self.assertEqual(live_games[0]["player1"], "p1")
        self.assertEqual(live_games[0]["current_player"], "black")

# -------------------------------------------------------------------
# TestUserManager 
# -------------------------------------------------------------------
class TestUserManager(unittest.TestCase):
    """Test cases for the UserManager handling authentication and user operations."""

    def setUp(self):
        """Initialize test database and user manager."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(
            os.path.join(self.temp_dir.name, "users.json"),
            os.path.join(self.temp_dir.name, "games.json"),
            os.path.join(self.temp_dir.name, "live_games.json")
        )
        self.manager = UserManager(self.db)

    def tearDown(self):
        """Clean up temporary directory after tests."""
        self.temp_dir.cleanup()

    def test_signup_and_login(self):
        """
        Test user signup and login workflow.
        
        Verifies:
        - Successful user registration
        - Duplicate username prevention
        - Successful login with valid password
        - Failed login with invalid password
        - Proper logout functionality
        """
        # Test successful signup
        signup_msg = Message(MessageType.SIGNUP_REQUEST, {
            "username": "newuser", 
            "password": "pass"
        })
        response = self.manager.handle_message(signup_msg)
        self.assertEqual(response.type, MessageType.SIGNUP_RESPONSE)
        self.assertTrue(response.data["success"])
        
        # Test duplicate signup
        response = self.manager.handle_message(signup_msg)
        self.assertEqual(response.type, MessageType.ERROR)
        
        # Test successful login
        login_msg = Message(MessageType.LOGIN_REQUEST, {
            "username": "newuser", 
            "password": "pass"
        })
        response = self.manager.handle_message(login_msg)
        self.assertEqual(response.type, MessageType.LOGIN_RESPONSE)
        self.assertEqual(response.data["username"], "newuser")
        self.assertIn("newuser", self.manager.logged_in_users)
        
        # Test invalid password
        login_msg = Message(MessageType.LOGIN_REQUEST, {
            "username": "newuser", 
            "password": "wrong"
        })
        response = self.manager.handle_message(login_msg)
        self.assertEqual(response.type, MessageType.ERROR)
        
        # Test logout
        logout_msg = Message(MessageType.LOGOUT, {"username": "newuser"})
        response = self.manager.handle_message(logout_msg)
        self.assertEqual(response.type, MessageType.LOGOUT)
        self.assertNotIn("newuser", self.manager.logged_in_users)

    def test_get_stats(self):
        """
        Test user statistics retrieval.
        
        Verifies:
        - Correct stats are returned for existing user
        - Correct response message format
        """
        # Create a test user
        user = User(username="statsuser", password="pass", credits=100, wins=5, losses=2)
        self.db.save_user(user)
        
        # Test get stats
        stats_msg = Message(MessageType.GET_STATS_REQUEST, {"username": "statsuser"})
        response = self.manager.handle_message(stats_msg)
        self.assertEqual(response.type, MessageType.GET_STATS_RESPONSE)
        self.assertEqual(response.data["credits"], 100)

    def test_account_deletion(self):
        """
        Test user account deletion.
        
        Verifies:
        - Successful account removal
        - Cleanup of logged in users
        """
        # Create and login a test user
        user = User(username="todelete", password="pass")
        self.db.save_user(user)
        self.manager.logged_in_users.add("todelete")
        
        # Test account deletion
        delete_msg = Message(MessageType.ACCOUNT_DELETE_REQUEST, {"username": "todelete"})
        response = self.manager.handle_message(delete_msg)
        self.assertEqual(response.type, MessageType.ACCOUNT_DELETE_RESPONSE)
        self.assertTrue(response.data["success"])
        self.assertNotIn("todelete", self.manager.logged_in_users)
        self.assertIsNone(self.db.get_user("todelete"))

    def test_leaderboard(self):
        """
        Test leaderboard generation and ordering.
        
        Verifies:
        - Correct ordering by credits
        - Complete data returned
        """
        # Create test users with different stats
        users = [
            User(username="user1", password="p", credits=200, wins=10, losses=5),
            User(username="user2", password="p", credits=150, wins=8, losses=3),
            User(username="user3", password="p", credits=300, wins=15, losses=1)
        ]
        for user in users:
            self.db.save_user(user)
        
        # Test leaderboard ordering
        leaderboard = self.manager.get_leaderboard()
        self.assertEqual(len(leaderboard), 3)
        self.assertEqual(leaderboard[0]["username"], "user3")
        self.assertEqual(leaderboard[1]["username"], "user1")
        self.assertEqual(leaderboard[2]["username"], "user2")

# -------------------------------------------------------------------
# TestMatchmaking 
# -------------------------------------------------------------------
class TestMatchmaking(unittest.TestCase):
    """Test cases for the Matchmaking system."""

    def setUp(self):
        """Initialize matchmaking system."""
        self.matchmaking = Matchmaking()

    def test_queue_operations(self):
        """
        Test queue join/leave operations.
        
        Verifies:
        - Players can join and leave queue
        - Queue size tracking
        - Proper response messages
        """
        # Test joining queue
        join_msg = Message(MessageType.QUEUE_REQUEST, {
            "username": "player1", 
            "action": "join"
        })
        response = self.matchmaking.handle_message(join_msg)
        self.assertEqual(response.type, MessageType.QUEUE_RESPONSE)
        self.assertEqual(response.data["queue_size"], 1)
        
        # Test leaving queue
        leave_msg = Message(MessageType.QUEUE_REQUEST, {
            "username": "player1", 
            "action": "leave"
        })
        response = self.matchmaking.handle_message(leave_msg)
        self.assertEqual(response.type, MessageType.QUEUE_RESPONSE)
        self.assertEqual(response.data["status"], "left_queue")
        self.assertEqual(len(self.matchmaking.queue), 0)

    def test_match_found(self):
        """
        Test matchmaking when two players join.
        
        Verifies:
        - Match found notification sent
        - Queue cleared after match
        - Single player remains if odd number
        """
        # Add two players to queue
        response1 = self.matchmaking.handle_message(Message(MessageType.QUEUE_REQUEST, {
            "username": "player1", 
            "action": "join"
        }))
        self.assertEqual(response1.type, MessageType.QUEUE_RESPONSE)
        response2 = self.matchmaking.handle_message(Message(MessageType.QUEUE_REQUEST, {
            "username": "player2", 
            "action": "join"
        }))
        self.assertEqual(response2.type, MessageType.MATCH_FOUND)
        # Should return a match found message
        response3 = self.matchmaking.handle_message(Message(MessageType.QUEUE_REQUEST, {
            "username": "player3", 
            "action": "join"
        }))
        self.assertEqual(response3.type, MessageType.QUEUE_RESPONSE)
        self.assertEqual(len(self.matchmaking.queue), 1)  # player3 remains

# -------------------------------------------------------------------
# TestGameManager 
# -------------------------------------------------------------------
class TestGameManager(unittest.TestCase):
    """Test cases for the GameManager handling game logic and state."""

    def setUp(self):
        """Initialize test environment with database and test users."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(
            os.path.join(self.temp_dir.name, "users.json"),
            os.path.join(self.temp_dir.name, "games.json"),
            os.path.join(self.temp_dir.name, "live_games.json")
        )
        self.user_manager = UserManager(self.db)
        self.manager = GameManager(self.user_manager)
        
        # Create test users
        self.user1 = User(username="player1", password="p")
        self.user2 = User(username="player2", password="p")
        self.db.save_user(self.user1)
        self.db.save_user(self.user2)

    def tearDown(self):
        """Clean up temporary directory after tests."""
        self.temp_dir.cleanup()

    def test_game_creation(self):
        """
        Test game instance creation.
        
        Verifies:
        - Game is properly created in manager
        - Players assigned to black/white
        - Initial game state
        """
        game_id = self.manager.create_game("player1", "player2")
        self.assertIn(game_id, self.manager.games)
        
        game = self.manager.games[game_id]
        self.assertIn("player1", [game.players["black"], game.players["white"]])
        self.assertIn("player2", [game.players["black"], game.players["white"]])
        self.assertEqual(game.current_player, "black")
        self.assertFalse(game.game_over)

    def test_valid_move(self):
        """
        Test valid game move processing.
        
        Verifies:
        - Move is applied to board
        - Player turn switches
        - Correct response message
        """
        game_id = self.manager.create_game("player1", "player2")
        game = self.manager.games[game_id]

        move_msg = Message(MessageType.MAKE_MOVE, {
            "username": game.players["black"],
            "game_id": game_id,
            "row": 1,
            "col": 1
        })
        
        response = self.manager.handle_message(move_msg)
        self.assertEqual(response.type, MessageType.GAME_STATE)
        self.assertEqual(response.data["state"]["board"][1][1], "black")
        self.assertEqual(response.data["state"]["current_player"], "white")

    def test_invalid_move(self):
        """
        Test invalid move handling.
        
        Verifies:
        - Wrong player move is rejected
        - Out of bounds move is rejected
        - Error message returned
        """
        game_id = self.manager.create_game("player1", "player2")
        game = self.manager.games[game_id]
        
        # Test wrong player
        move_msg = Message(MessageType.MAKE_MOVE, {
            "username": game.players["white"],
            "game_id": game_id,
            "row": 1,
            "col": 1
        })
        response = self.manager.handle_message(move_msg)
        self.assertEqual(response.type, MessageType.ERROR)
        
        # Test out of bounds on board
        move_msg = Message(MessageType.MAKE_MOVE, {
            "username": "player1",
            "game_id": game_id,
            "row": 100,
            "col": 100
        })
        response = self.manager.handle_message(move_msg)
        self.assertEqual(response.type, MessageType.ERROR)

    def test_win_condition(self):
        """
        Test win condition detection.
        
        Verifies:
        - Five in a row is detected
        - Game over state set
        - Winner properly identified
        - Correct messages sent
        """
        game_id = self.manager.create_game("player1", "player2")
        game = self.manager.games[game_id]

        # Create a winning sequence for black
        for i in range(4):  # Place first 4 stones
            row = col = i
            game.board[row][col] = "black"
            game.last_move = (row, col)

        # Final winning move
        move_msg = Message(MessageType.MAKE_MOVE, {
            "username": game.players["black"],
            "game_id": game_id,
            "row": 4,
            "col": 4
        })

        response = self.manager.handle_message(move_msg)

        # Test if the response is a tuple of two messages (implying game ends)
        self.assertIsInstance(response, tuple)
        self.assertEqual(len(response), 2)

        game_state_msg, game_over_msg = response

        self.assertEqual(game_state_msg.type, MessageType.GAME_STATE)
        self.assertTrue(game_state_msg.data["state"]["game_over"])

        self.assertEqual(game_over_msg.type, MessageType.GAME_OVER)
        self.assertEqual(game_over_msg.data["winner"], game.players["black"])

        # Check server state
        self.assertTrue(self.manager.games[game_id].game_over)

    def test_disconnect_handling(self):
        """
        Test player disconnect handling.
        
        Verifies:
        - Game ends when player disconnects
        - Opponent is declared winner
        - Game state marked as over
        """
        game_id = self.manager.create_game("player1", "player2")
        disconnect_msg = Message(MessageType.PLAYER_DISCONNECTED, {
            "username": "player1",
            "game_id": game_id
        })
        
        response = self.manager.handle_message(disconnect_msg)
        self.assertEqual(response.type, MessageType.GAME_OVER)
        self.assertEqual(response.data["winner"], "player2")
        self.assertTrue(self.manager.games[game_id].game_over)

    def test_history_retrieval(self):
        """
        Test game history retrieval.
        
        Verifies:
        - User-specific history returned
        - Complete history data
        - Proper message format
        """
        # Create a test game history
        history = GameHistory(
            game_id="test_game",
            player1="player1",
            player2="player2",
            winner="player1",
            start_time="2023-01-01",
            end_time="2023-01-01",
            moves=[(1,1), (2,2)],
            credits_change={"player1": 10, "player2": -10}
        )
        self.db.save_game_history(history)
        
        # Test history retrieval
        history_msg = Message(MessageType.GET_HISTORY_REQUEST, {"username": "player1"})
        response = self.manager.handle_message(history_msg)
        self.assertEqual(response.type, MessageType.GET_HISTORY_RESPONSE)
        self.assertEqual(len(response.data["histories"]), 1)
        self.assertEqual(response.data["histories"][0]["player1"], "player1")

# -------------------------------------------------------------------
# TestGameServer
# -------------------------------------------------------------------
class TestGameServer(unittest.TestCase):
    """Integration tests for the GameServer class."""

    def setUp(self):
        """Set up test server with temporary config and data files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "config.ini")
        self.users_file = os.path.join(self.temp_dir.name, "users.json")
        self.games_file = os.path.join(self.temp_dir.name, "games.json")
        self.live_games_file = os.path.join(self.temp_dir.name, "live_games.json")

        with open(self.config_path, "w") as f:
            f.write(f"""
                    [server]
                    host = 127.0.0.1
                    port = 5555
                    max_players = 100
                    max_games = 50

                    [database]
                    users_file = {self.users_file}
                    games_file = {self.games_file}
                    live_games_file = {self.live_games_file}

                    [game]
                    board_size = 19
                    timeout = 30
                    """)

        # Start the server
        self.server = GameServer(self.config_path)
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()
        self.stderr_patch = patch('sys.stderr', new=io.StringIO())
        self.stderr_patch.start()
        self.addCleanup(self.stderr_patch.stop)
        time.sleep(0.1)  # Give server time to start

    def tearDown(self):
        """Stop server and clean up resources."""
        try:
            self.server.stop()
            self.server_thread.join()
            time.sleep(0.1)  # Allow time for file release
        finally:
            # Retry logic to clean up even if file is locked momentarily
            for _ in range(5):
                try:
                    self.temp_dir.cleanup()
                    break
                except PermissionError:
                    time.sleep(0.2)

    def test_connect_to_server(self):
        """
        Test basic server connectivity.
        
        Verifies:
        - Server accepts connections
        - Socket communication possible
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 5555))
        sock.close()

    def test_signup_and_login(self):
        """
        Test end-to-end signup and login workflow.
        
        Verifies:
        - Successful user registration
        - Successful login
        - Matchmaking queue join
        - Match found when two players join
        """
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock1.connect(("127.0.0.1", 5555))
        sock2.connect(("127.0.0.1", 5555))
        file1 = sock1.makefile("r")
        file2 = sock2.makefile("r")

        # Helper function to send and receive message
        def send_and_recv(sock, file, msg_obj):
            sock.sendall((msg_obj.to_json() + "\n").encode("utf-8"))
            return Message.from_json(file.readline())

        # Signup
        send_and_recv(sock1, file1, Message(MessageType.SIGNUP_REQUEST, {
            "username": "match1", "password": "pass"
        }))
        send_and_recv(sock2, file2, Message(MessageType.SIGNUP_REQUEST, {
            "username": "match2", "password": "pass"
        }))

        # Login
        send_and_recv(sock1, file1, Message(MessageType.LOGIN_REQUEST, {
            "username": "match1", "password": "pass"
        }))
        send_and_recv(sock2, file2, Message(MessageType.LOGIN_REQUEST, {
            "username": "match2", "password": "pass"
        }))

        # Join matchmaking queue
        send_and_recv(sock1, file1, Message(MessageType.QUEUE_REQUEST, {
            "username": "match1", "action": "join"
        }))
        # Test if match found when the second player join
        response_msg = send_and_recv(sock2, file2, Message(MessageType.QUEUE_REQUEST, {
            "username": "match2", "action": "join"
        }))

        # Check result
        self.assertEqual(response_msg.type, MessageType.MATCH_FOUND)
        self.assertIn(response_msg.data["black"], ["match1", "match2"])
        self.assertIn(response_msg.data["white"], ["match1", "match2"])

        # Cleanup
        sock1.close()
        sock2.close()

    def test_matchmaking(self):
        """
        Test matchmaking system integration.
        
        Verifies:
        - Players can join queue
        - Match found when two players available
        - Proper player assignment (black/white)
        """
        # Create two client connections
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock1.connect(("127.0.0.1", 5555))
        
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2.connect(("127.0.0.1", 5555))
        
        # Login both users
        sock1.sendall((Message(MessageType.SIGNUP_REQUEST, {
            "username": "match1", 
            "password": "pass"
        }).to_json() + "\n").encode("utf-8"))
        sock1.recv(1024)
        
        sock2.sendall((Message(MessageType.SIGNUP_REQUEST, {
            "username": "match2", 
            "password": "pass"
        }).to_json() + "\n").encode("utf-8"))
        sock2.recv(1024)

        sock1.sendall((Message(MessageType.LOGIN_REQUEST, {
            "username": "match1",
            "password": "pass"
        }).to_json() + "\n").encode())
        sock1.recv(1024)

        sock2.sendall((Message(MessageType.LOGIN_REQUEST, {
            "username": "match2",
            "password": "pass"
        }).to_json() + "\n").encode())
        sock2.recv(1024)
        
        # Join queue with both
        sock1.sendall((Message(MessageType.QUEUE_REQUEST, {
            "username": "match1", 
            "action": "join"
        }).to_json() + "\n").encode("utf-8"))
        sock1.recv(1024)
        
        sock2.sendall((Message(MessageType.QUEUE_REQUEST, {
            "username": "match2", 
            "action": "join"
        }).to_json() + "\n").encode("utf-8"))
        
        # Test if the second player get match found
        response = sock2.recv(1024).decode("utf-8")
        response_msg = Message.from_json(response.strip())
        self.assertEqual(response_msg.type, MessageType.MATCH_FOUND)
        self.assertIn(response_msg.data["black"], ["match1", "match2"])
        self.assertIn(response_msg.data["white"], ["match1", "match2"])
        
        sock1.close()
        sock2.close()

# -------------------------------------------------------------------
# TestClientUI 
# -------------------------------------------------------------------
class TestClientUI(unittest.TestCase):
    """Test cases for client UI components."""

    def setUp(self):
        """Initialize hidden Tk root window for UI tests."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window for tests

    def tearDown(self):
        """Clean up Tkinter resources."""
        self.root.destroy()

    @patch('client.messagebox.showerror')
    def test_auth_ui(self, mock_showerror):
        """
        Test authentication UI functionality.
        
        Verifies:
        - Empty field validation
        - Proper message sending
        - Error handling
        """
        mock_client = MagicMock()
        auth_ui = AuthUI(self.root, mock_client)
        
        # Test login with empty fields
        auth_ui.username_entry.insert(0, "")
        auth_ui.password_entry.insert(0, "")
        auth_ui.login()
        mock_showerror.assert_called_once()
        
        # Should show error and not send message
        self.assertEqual(mock_client.send_message.call_count, 0)
        
        # Test valid login
        auth_ui.username_entry.delete(0, tk.END)
        auth_ui.password_entry.delete(0, tk.END)
        auth_ui.username_entry.insert(0, "testuser")
        auth_ui.password_entry.insert(0, "testpass")
        auth_ui.login()
        
        # Should send login message
        self.assertEqual(mock_client.send_message.call_count, 1)
        msg = mock_client.send_message.call_args[0][0]
        self.assertEqual(msg.type.value, "login_request")
        self.assertEqual(msg.data["username"], "testuser")

    def test_home_ui(self):
        """
        Test home screen UI functionality.
        
        Verifies:
        - Game start button triggers queue request
        - Stats polling sends correct message
        """
        mock_client = MagicMock()
        mock_client.username = "testuser"
        home_ui = HomeUI(self.root, mock_client)
        
        # Test start game button
        home_ui.start_button.invoke()
        msg = mock_client.send_message.call_args[0][0]
        self.assertEqual(msg.type.value, "queue_request")
        self.assertEqual(msg.data["username"], "testuser")
        
        # Test stats polling
        home_ui.poll_stats()
        msg = mock_client.send_message.call_args[0][0]
        self.assertEqual(msg.type.value, "get_stats_request")

    @patch('client.messagebox')
    def test_waiting_ui(self, mock_messagebox):
        """
        Test waiting room UI functionality.
        
        Verifies:
        - Cancel button sends leave queue message
        """
        mock_client = MagicMock()
        mock_client.username = "testuser"
        waiting_ui = WaitingUI(self.root, mock_client)
        
        # Test cancel waiting
        waiting_ui.cancel_button.invoke()
        self.assertEqual(mock_client.send_message.call_count, 1)
        msg = mock_client.send_message.call_args[0][0]
        self.assertEqual(msg.type.value, "queue_request")
        self.assertEqual(msg.data["action"], "leave")

    def test_game_ui(self):
        """
        Test game board UI functionality.
        
        Verifies:
        - Valid moves are sent to server
        - Turn validation works
        - Click handling
        """
        mock_client = MagicMock()
        mock_client.username = "player1"
        mock_client.current_game_id = "test_game"
        
        game_ui = GameUI(
            self.root, mock_client,
            player1="player1", player2="player2"
        )
        
        # Test valid move
        game_ui.is_my_turn = True
        game_ui.on_click(MagicMock(x=50, y=50))  # Simulate click at (2,2)
        
        msg = mock_client.send_message.call_args[0][0]
        self.assertEqual(msg.type.value, "make_move")
        self.assertEqual(msg.data["game_id"], "test_game")
        
        # Test invalid move (not your turn)
        game_ui.is_my_turn = False
        mock_client.send_message.reset_mock()
        game_ui.on_click(MagicMock(x=50, y=50))
        self.assertEqual(mock_client.send_message.call_count, 0)
    
    def test_history_ui(self):
        """
        Test game history UI functionality.
        
        Verifies:
        - History data loading
        """
        mock_client = MagicMock()
        history_ui = HistoryUI(self.root, mock_client)
        test_history = [{
            'game_id': 'game1',
            'player1': 'player1',
            'player2': 'player2',
            'winner': 'player1',
            'start_time': '2023-01-01',
            'end_time': '2023-01-01',
            'moves': [(1,1), (2,2)],
            'credits_change': {'player1': 10}
        }]
        history_ui.load_history_from_server(test_history)
        self.assertEqual(len(history_ui.history_tree.get_children()), 1)

    def test_game_replay_ui(self):
        """
        Test game replay UI functionality.
        
        Verifies:
        - Move navigation
        - Replay controls
        - Board updates
        """
        mock_client = MagicMock()
        moves = [(0,0), (1,1), (2,2)]
        game_data = {
            "game_id": "game123",
            "player1": "p1",
            "player2": "p2",
            "winner": "p1",
            "moves": moves
        }
        replay_ui = GameReplayUI(self.root, mock_client, game_data)
        replay_ui.next_move()
        replay_ui.previous_move()
        replay_ui.start_replay()
        replay_ui.reset_board()
        self.assertTrue(replay_ui.step_var.get().startswith("Move"))

    def test_live_games_ui(self):
        """
        Test live games UI functionality.
        
        Verifies:
        - Live games data loading
        """
        mock_client = MagicMock()
        live_games_ui = LiveGamesUI(self.root, mock_client)
        test_games = [{
            'game_id': 'live1',
            'player1': 'playerA',
            'player2': 'playerB',
            'black_stones': 10,
            'white_stones': 9,
            'current_player': 'black'
        }]
        live_games_ui.load_live_games(test_games)
        self.assertEqual(len(live_games_ui.games_tree.get_children()), 1)

    def test_live_game_viewer_ui(self):
        """
        Test live game viewer UI initialization.
        
        Verifies:
        - UI creation with game state
        - No errors during setup
        """
        mock_client = MagicMock()
        mock_client.username = "viewer"
        game_state = {
            "player1": "p1",
            "player2": "p2",
            "board": [[None]*19 for _ in range(19)],
            "current_player": "black"
        }
        viewer_ui = LiveGameViewerUI(self.root, mock_client, "g1", game_state, parent_ui=MagicMock())
        self.assertIsNotNone(viewer_ui)

    def test_leaderboard_ui(self):
        """
        Test leaderboard UI functionality.
        
        Verifies:
        - Leaderboard data loading
        """
        mock_client = MagicMock()
        mock_client.username = "leaderboard_viewer"
        test_leaderboard = [
            {'username': 'player1', 'credits': 100, 'wins': 10, 'losses': 2},
            {'username': 'player2', 'credits': 90, 'wins': 8, 'losses': 3}
        ]
        
        leaderboard_ui = LeaderboardUI(self.root, mock_client)
        leaderboard_ui.load_leaderboard(test_leaderboard)
        
        # Verify leaderboard loaded
        self.assertEqual(len(leaderboard_ui.leaderboard_tree.get_children()), 2)

    def test_matching_room_ui(self):
        """
        Test matching room UI functionality.
        
        Verifies:
        - User list update
        - Appropriate invitation handling
        """
        mock_client = MagicMock()
        mock_client.username = "me"
        matching_ui = MatchingRoomUI(self.root, mock_client)

        # Test user list update
        test_users = [
            {'username': 'player2', 'credits': 100},
            {'username': 'player3', 'credits': 90}
        ]
        matching_ui.update_users_list(test_users)
        self.assertEqual(len(matching_ui.user_tree.get_children()), 2)

        # Test invitation handling
        test_requests = [{
            'id': 'req1',
            'from': 'player2',
            'credits': 100,
            'expiry': time.time() + 15
        }]
        matching_ui.update_requests_list(test_requests)
        self.assertEqual(len(matching_ui.invitations_tree.get_children()), 1)

# -------------------------------------------------------------------
# TestGameClient
# -------------------------------------------------------------------
class TestGameClient(unittest.TestCase):
    """Test cases for the GameClient class handling client-side functionality and server communication."""

    def setUp(self):
        """
        Initializes the test environment for GameClient tests.
        
        Sets up:
        - Hidden Tkinter root window
        - Mock server socket
        - Mock server thread
        - Patched configuration
        - GameClient instance
        """
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window for tests
        
        # Create a mock server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('127.0.0.1', 0))
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(1)
        
        # Start the mock server in a thread
        self.server_thread = threading.Thread(target=self._mock_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.stderr_patch = patch('sys.stderr', new=io.StringIO())
        self.stderr_patch.start()
        self.addCleanup(self.stderr_patch.stop)
        
        # Patch config to use our mock server
        self.patcher = patch('client.configparser.ConfigParser')
        self.mock_config = self.patcher.start()
        mock_config_instance = self.mock_config.return_value
        mock_config_instance.get.return_value = '127.0.0.1'
        mock_config_instance.getint.return_value = self.port
        
        # Create client instance
        self.client = GameClient(self.root)
        
        # Wait for client to connect
        time.sleep(0.1)

    def tearDown(self):
        """Cleans up test resources."""
        self.client.socket.close()
        self.server_socket.close()
        self.server_thread.join()
        self.root.update_idletasks()
        self.root.destroy()
        self.patcher.stop()
        time.sleep(0.1)

    def _mock_server(self):
        """
        Runs a simple mock server that responds to basic client messages.
        
        Handles:
        - LOGIN_REQUEST with successful response
        - GET_STATS_REQUEST with sample stats
        - QUEUE_REQUEST with waiting status
        - Closes connection on timeout or error
        """
        try:
            conn, addr = self.server_socket.accept()
            conn.settimeout(2) 
            try:
                while True:
                    try:
                        data = conn.recv(1024)
                        if not data:
                            break

                        try:
                            message = Message.from_json(data.decode('utf-8').strip())
                        except Exception as e:
                            continue

                        # Respond to known message types
                        if message.type == MessageType.LOGIN_REQUEST:
                            response = Message(MessageType.LOGIN_RESPONSE, {
                                'username': message.data['username'],
                                'credits': 100,
                                'wins': 0,
                                'losses': 0
                            })
                            conn.sendall((response.to_json() + '\n').encode('utf-8'))

                        elif message.type == MessageType.GET_STATS_REQUEST:
                            response = Message(MessageType.GET_STATS_RESPONSE, {
                                'username': message.data['username'],
                                'credits': 100,
                                'wins': 5,
                                'losses': 2,
                                'online_players': 10
                            })
                            conn.sendall((response.to_json() + '\n').encode('utf-8'))

                        elif message.type == MessageType.QUEUE_REQUEST:
                            if message.data['action'] == 'join':
                                response = Message(MessageType.QUEUE_RESPONSE, {
                                    'status': 'waiting',
                                    'queue_size': 1
                                })
                                conn.sendall((response.to_json() + '\n').encode('utf-8'))

                    except (ConnectionResetError, ConnectionAbortedError) as e:
                        break
                    except socket.timeout:
                        break
            finally:
                conn.close()
        except Exception as e:
            print(f"[Mock Server] Accept failed: {e}")

    def test_client_connection(self):
        """
        Tests that the client connects to the server properly.
        
        Verifies:
        - Client's connected status is True after initialization
        """
        self.assertTrue(self.client.connected)
        
    def test_send_message(self):
        """
        Tests message sending functionality.
        
        Verifies:
        - Messages are properly sent through the socket
        - Correct message format is used
        """
        with patch('socket.socket.send') as mock_send:
            test_msg = Message(MessageType.LOGIN_REQUEST, {'username': 'test', 'password': 'pass'})
            self.client.send_message(test_msg)
            mock_send.assert_called_once()
            
    def test_handle_server_message(self):
        """
        Tests handling of various server messages.
        
        Verifies:
        - LOGIN_RESPONSE sets client username
        - GET_STATS_RESPONSE updates stats and shows home UI
        - MATCH_FOUND sets game ID and shows game UI
        """
        # Test login response
        login_response = Message(MessageType.LOGIN_RESPONSE, {
            'username': 'testuser',
            'credits': 100,
            'wins': 5,
            'losses': 2
        })
        self.client.handle_server_message(login_response)
        self.assertEqual(self.client.username, 'testuser')
        
        # Test stats response
        stats_response = Message(MessageType.GET_STATS_RESPONSE, {
            'username': 'testuser',
            'credits': 100,
            'wins': 5,
            'losses': 2,
            'online_players': 10
        })
        self.client.handle_server_message(stats_response)
        self.assertIsNotNone(self.client.home_ui)
        
        # Test match found
        match_response = Message(MessageType.MATCH_FOUND, {
            'black': 'testuser',
            'white': 'opponent',
            'game_id': 'game123'
        })
        self.client.handle_server_message(match_response)
        self.assertEqual(self.client.current_game_id, 'game123')
        self.assertIsNotNone(self.client.game_ui)
        
    def test_ui_transitions(self):
        """
        Tests transitions between different UI states.
        
        Verifies:
        - Initial UI is AuthUI
        - Successful login transitions to HomeUI
        - All UI transitions work as expected:
            - WaitingUI
            - HistoryUI  
            - LeaderboardUI
            - MatchingRoomUI
        """
        # Start with auth UI
        self.assertIsInstance(self.client.current_ui, AuthUI)
        
        # Simulate successful login
        login_response = Message(MessageType.LOGIN_RESPONSE, {
            'username': 'testuser',
            'credits': 100,
            'wins': 5,
            'losses': 2
        })
        self.client.handle_server_message(login_response)
        self.assertIsInstance(self.client.current_ui, HomeUI)
        
        # Test transition to waiting UI
        self.client.show_waiting_ui()
        self.assertIsInstance(self.client.current_ui, WaitingUI)
        
        # Test transition back to home
        self.client.show_home_ui()
        self.assertIsInstance(self.client.current_ui, HomeUI)
        
        # Test transition to history UI
        self.client.show_history_ui()
        self.assertIsInstance(self.client.current_ui, HistoryUI)
        
        # Test transition to leaderboard UI
        self.client.show_leaderboard_ui()
        self.assertIsInstance(self.client.current_ui, LeaderboardUI)
        
        # Test transition to matching room UI
        self.client.show_matching_room_ui()
        self.assertIsInstance(self.client.current_ui, MatchingRoomUI)


if __name__ == '__main__':
    unittest.main(verbosity=0)