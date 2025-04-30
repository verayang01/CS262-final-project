import socket
import json
import threading
import configparser
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import time

from shared import Message, MessageType, BOARD_SIZE, TIMEOUT

class AuthUI:
    """
    Handles the authentication UI (login/signup) for the Five in a Row game.
    Manages user authentication forms and interactions with the game client.
    """
    def __init__(self, root, client):
        """
        Initializes the authentication UI.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
        """
        self.root = root
        self.client = client
        self.frame = tk.Frame(root)
        self.show_login_form() # Start with login form

    def show_login_form(self):
        """Displays the login form with username/password fields and buttons."""
        # Clear any existing widgets
        for widget in self.frame.winfo_children():
            widget.destroy()
        # Create and layout login form widgets
        self.title_label = tk.Label(self.frame, text="Five in a Row", font=('Helvetica', 24, 'bold'), fg='#333')
        self.title_label.pack(pady=(40, 20))
        # Username and password
        self.username_label = tk.Label(self.frame, text="Username:", font=('Helvetica', 12), fg='#555')
        self.username_entry = tk.Entry(self.frame, font=('Helvetica', 12), relief=tk.GROOVE, bd=2)
        self.password_label = tk.Label(self.frame, text="Password:", font=('Helvetica', 12), fg='#555')
        self.password_entry = tk.Entry(self.frame, show="*", font=('Helvetica', 12), relief=tk.GROOVE, bd=2)
        # Action buttons
        self.login_button = tk.Button(self.frame, text="Login", command=self.login, width=18, height=2)
        self.signup_button = tk.Button(self.frame, text="Sign Up", command=self.show_signup_form, width=18, height=2)
        # Layout all widgets
        self.username_label.pack()
        self.username_entry.pack(ipady=3)
        self.password_label.pack()
        self.password_entry.pack(ipady=3)
        self.login_button.pack(pady=(30, 10))
        self.signup_button.pack(pady=(0, 20))
        self.frame.pack(padx=20, pady=20)
        self.root.geometry("700x450")

    def show_signup_form(self):
        """Displays the signup form with username/password fields."""
        # Clear any existing widgets
        for widget in self.frame.winfo_children():
            widget.destroy()
        # Create and layout signup form widgets
        self.title_label = tk.Label(self.frame, text="Five in a Row", font=('Helvetica', 24, 'bold'), fg='#333')
        self.title_label.pack(pady=(40, 20))
        # Username and password
        self.username_label = tk.Label(self.frame, text="Username:", font=('Helvetica', 12), fg='#555')
        self.username_entry = tk.Entry(self.frame, font=('Helvetica', 12), relief=tk.GROOVE, bd=2)
        self.password_label = tk.Label(self.frame, text="Password:", font=('Helvetica', 12), fg='#555')
        self.password_entry = tk.Entry(self.frame, show="*", font=('Helvetica', 12), relief=tk.GROOVE, bd=2)
        # Action buttons
        self.signup_button = tk.Button(self.frame, text="Sign Up", command=self.attempt_signup, width=18, height=2)
        self.back_button = tk.Button(self.frame, text="Back to Login", command=self.show_login_form, width=18, height=2)
        # Layout all widgets
        self.username_label.pack()
        self.username_entry.pack(ipady=3)
        self.password_label.pack()
        self.password_entry.pack(ipady=3)
        self.signup_button.pack(pady=(30, 10))
        self.back_button.pack(pady=(0, 20))

    def login(self):
        """
        Handles login form submission.
        Validates inputs and sends login request to server.
        """
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password: # Check if username or password is empty
            messagebox.showerror("Error", "Username and password are required")
            return
        self.client.username = username
        self.client.send_message(Message(
            MessageType.LOGIN_REQUEST,
            {'username': username, 'password': password}
        ))

    def attempt_signup(self):
        """
        Handles signup form submission.
        Validates inputs and sends signup request to server.
        """
        username = self.username_entry.get()
        password = self.password_entry.get()
        # Check if the username and password are valid
        if not username:
            messagebox.showerror("Error", "Username cannot be empty.")
            return
        if ' ' in username or '\n' in username or ' ' in password or '\n' in password:
            messagebox.showerror("Error", "Username and password cannot contain spaces or newlines.")
            return     
        if not password:
            messagebox.showerror("Error", "Password cannot be empty.")
            return
        self.client.send_message(Message(
            MessageType.SIGNUP_REQUEST,
            {'username': username, 'password': password}
        ))

class HomeUI:
    """
    The main home screen UI after successful login.
    Provides access to all game features including:
    - Starting new games
    - Joining the matching room
    - Viewing live games
    - Accessing game history
    - Viewing leaderboard
    - Account management (logout/delete)
    
    Also displays real-time player statistics including:
    - Current credits
    - Number of online players
    """
    def __init__(self, root, client):
        """
        Initializes the home screen UI and sets up all interface components.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
        """
        self.root = root
        self.client = client
        self.frame = tk.Frame(root)
        top_frame = tk.Frame(self.frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        # Welcome label
        self.welcome_label = tk.Label(top_frame, text=f"Welcome, {self.client.username}!", font=('Helvetica', 18, 'bold'), fg='#333')
        self.welcome_label.pack(pady=(15, 0))
        # Stats display frame
        stats_frame = tk.Frame(self.frame, bg='#e0e0e0', padx=15, pady=15, relief=tk.GROOVE, bd=2)
        self.credits_label = tk.Label(stats_frame, text="Credits: Loading...", font=('Helvetica', 12), bg='#e0e0e0', fg='#333')
        self.players_online_label = tk.Label(stats_frame, text="Players online: Loading...", font=('Helvetica', 12), bg='#e0e0e0', fg='#333')
        stats_frame.pack(pady=20, padx=20, ipadx=100, ipady=5) 
        self.credits_label.pack(pady=5)
        self.players_online_label.pack()
        # Create a grid frame for the main buttons
        grid_frame = tk.Frame(self.frame)
        grid_frame.pack(pady=0)
        # First row of buttons
        self.start_button = tk.Button(grid_frame, text="Start Game", command=self.start_game, width=14, height=2) # Start Game button (left)
        self.start_button.grid(row=0, column=0, padx=10, pady=10)
        self.matching_room_button = tk.Button(grid_frame, text="Matching Room", command=self.show_matching_room, width=14, height=2) # Matching Room button (middle)
        self.matching_room_button.grid(row=0, column=1, padx=10, pady=10)
        self.live_games_button = tk.Button(grid_frame, text="View Live Games", command=self.show_live_games, width=14, height=2) # View Live Games button (right)
        self.live_games_button.grid(row=0, column=2, padx=10, pady=10)
        # Second row of buttons
        self.history_button = tk.Button(grid_frame, text="Game History", command=self.show_history, width=14, height=2) # Game History button (left)
        self.history_button.grid(row=1, column=0, padx=10, pady=10)
        self.leaderboard_button = tk.Button(grid_frame, text="Leaderboard", command=self.show_leaderboard, width=14, height=2) # Leaderboard button (middle)
        self.leaderboard_button.grid(row=1, column=1, padx=10, pady=10)
        self.delete_button = tk.Button(grid_frame, text="Delete Account", command=self.delete_account, width=14, height=2) # Delete Account button (right)
        self.delete_button.grid(row=1, column=2, padx=10, pady=10)
        # Logout button
        self.logout_button = tk.Button(self.frame, text="Log Out", command=self.logout, width=10, height=2)
        self.logout_button.pack(pady=(20, 0))
        self.frame.pack(padx=20, pady=20)
        self.root.update_idletasks()
        # Request initial stats
        self.client.send_message(Message(MessageType.GET_STATS_REQUEST, {'username': self.client.username}))


    def update_stats_ui(self, data):
        """
        Updates the displayed statistics with latest data from server.
        
        Args:
            data (dict): Contains user stats including:
                - credits (int): Current player credits
                - online_players (int): Number of players online
        """
        self.credits_label.config(text=f"Your credits: {data['credits']}")
        self.players_online_label.config(text=f"Players online: {data.get('online_players', '?')}")

    def start_game(self):
        """Initiates matchmaking by entering the player into the game queue."""
        self.client.show_waiting_ui() # Show waiting page
        self.client.send_message(Message(
            MessageType.QUEUE_REQUEST,
            {'username': self.client.username, 'action': 'join'}
        ))
    
    def show_live_games(self):
        """Opens the live games viewer interface."""
        self.client.show_live_games_ui() # Show game session for live game viewing feature
        self.client.send_message(Message(
            MessageType.GET_LIVE_GAMES_REQUEST,
            {'username': self.client.username}
        ))

    def show_history(self):
        """Opens the game history viewer interface."""
        self.client.show_history_ui() # Show game history page
        self.client.send_message(Message(
            MessageType.GET_HISTORY_REQUEST,
            {'username': self.client.username}
        ))

    def show_leaderboard(self):
        """Opens the leaderboard interface showing player rankings."""
        self.client.show_leaderboard_ui() # Show leaderboard page
        self.client.send_message(Message(
            MessageType.GET_LEADERBOARD_REQUEST, 
            {'username': self.client.username}
        ))

    def show_matching_room(self):
        """Opens the matching room interface for player vs player matches."""
        self.client.show_matching_room_ui() # Show matching room page

    def logout(self):
        """
        Handles user logout by:
        1. Sending logout notification to server
        2. Clearing client state
        3. Returning to authentication screen
        """
        self.client.send_message(Message(
            MessageType.LOGOUT,
            {'username': self.client.username}
        ))
        # Clear client state
        self.client.username = None 
        self.client.current_game_id = None
        self.client.show_auth_ui() # Return to login screen
 
    def delete_account(self):
        """
        Initiates account deletion after confirmation.
        Shows warning dialog before sending delete request to server.
        """
        if not messagebox.askyesno(
            "Delete Account", 
            "Are you sure you want to delete your account?\nThis cannot be undone!",
            icon='warning'
        ):
            return
        self.stop_polling() # Stop stats updates
        self.client.send_message(Message(
            MessageType.ACCOUNT_DELETE_REQUEST,
            {'username': self.client.username}
        ))

    def start_polling(self):
        """
        Prepare to start periodic polling of player stats from server (wait 500ms).
        """
        self.polling_job = self.root.after(500, self.poll_stats)
        
    def stop_polling(self):
        """Stops the stats polling."""
        if hasattr(self, 'polling_job'):
            self.root.after_cancel(self.polling_job)

    def poll_stats(self):
        """
        Polls server for updated player statistics every 400ms.
        Only active when user is logged in (username exists).
        """
        if not self.client.username:
            return  # Don't poll if username isn't set yet
        self.client.send_message(Message(
            MessageType.GET_STATS_REQUEST,
            {'username': self.client.username}
        ))
        self.polling_job = self.root.after(400, self.poll_stats) # Schedule next poll

class WaitingUI:
    """
    The waiting screen UI shown when player is in matchmaking queue.
    Provides visual feedback with animations while waiting for an opponent,
    and allows canceling the queue to return to home screen.
    """
    def __init__(self, root, client):
        """
        Initializes the waiting screen UI components.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
        """
        self.root = root
        self.client = client
        self.frame = tk.Frame(root, padx=30, pady=30)
        # Waiting message with animation dots
        self.waiting_label = tk.Label(self.frame, text="Waiting for another player", font=('Helvetica', 18, 'bold'), fg='#333')
        self.waiting_label.pack(pady=(40, 20))
        self.dots = tk.Label(self.frame, text="...", font=('Helvetica', 18), fg='#666')
        self.dots.pack()
        self.dot_count = 0
        self.animate_dots()
        # Loading spinner animation
        self.spinner = tk.Label(self.frame, text="◐", font=('Helvetica', 24), fg='#DCB35C')
        self.spinner.pack(pady=20)
        self.spin_index = 0
        self.spin_chars = ["◐", "◓", "◑", "◒"]
        self.animate_spinner()
        # Cancel button
        self.cancel_button = tk.Button(self.frame, text="Cancel", command=self.cancel_waiting, width=15, height=2)
        self.cancel_button.pack(pady=30, ipadx=10)
        # Configure window
        self.root.geometry("700x450")
        self.root.configure()
        self.frame.pack(expand=True, fill=tk.BOTH)
        
    def animate_dots(self):
        """Animate the waiting dots."""
        self.dot_count = (self.dot_count + 1) % 4
        self.dots.config(text="." * self.dot_count)
        self.root.after(500, self.animate_dots)

    def animate_spinner(self):
        """Animate the loading spinner."""
        self.spin_index = (self.spin_index + 1) % 4
        self.spinner.config(text=self.spin_chars[self.spin_index])
        self.root.after(300, self.animate_spinner)

    def cancel_waiting(self):
        """
        Handles cancel button press by:
        1. Sending queue leave request to server
        2. Returning to home screen
        """
        self.client.send_message(Message(
            MessageType.QUEUE_REQUEST,
            {'username': self.client.username, 'action': 'leave'}
        ))
        self.client.show_home_ui() # Return to main menu

class GameUI:
    """
    The main game interface for the Five in a Row game.
    Handles all game-related UI components including:
    - Game board display
    - Player turn management
    - Move input handling
    - Game state updates
    - Timer display
    - Game over notifications
    
    Supports both active gameplay and replay modes.
    """
    def __init__(self, root, client, player1, player2, view_mode=False, game_id=None, replay_mode=False, winner=None):
        """
        Initializes the game UI with player information and game settings.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
            player1 (str): Username of the first player (Black).
            player2 (str): Username of the second player (White).
            view_mode (bool): Whether this is a view-only mode (for spectators).
            game_id (str): The ID of the current game.
            replay_mode (bool): Whether this is a replay mode.
            winner (str): The winner's username (for replay mode).
        """
        self.root = root
        self.client = client
        self.player1 = player1
        self.player2 = player2
        self.frame = tk.Frame(root)
        self.offset_x = 24
        self.offset_y = 24
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.is_my_turn = False # Flag indicating if it's the current player's turn
        self.game_over = False # Flag indicating if game has ended
        self.move_numbers = {} # Dictionary tracking move numbers for stones
        self.create_widgets(view_mode, replay_mode, winner)
        self.frame.pack(padx=10, pady=10)
        # Check mode (game, view, or replay)
        if not replay_mode:  # Only start polling in active games
            self.start_polling(game_id)
            if not view_mode:
                self.show_color_assignment() # Show player's color assignment
        self.root.geometry("700x750")
    
    def show_color_assignment(self):
        """
        Displays a popup window indicating the player's assigned color (Black/White).
        Black player moves first.
        """
        popup = tk.Toplevel(self.root)
        popup.title("Your Color Assignment")
        popup.resizable(False, False)
        # Determine player color
        if self.player1 == self.client.username:
            color = "Black"
            message = "You are playing as Black.\nIt's your move first!"
            bg_color = '#f8f8f8' 
            text_color = '#2c3e50'
        else:
            color = "White"
            message = "You are playing as White.\nPlease wait for your turn."
            bg_color = '#f8f8f8' 
            text_color = '#2c3e50'       
        # Set window size and center it
        popup.geometry("400x200")
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        popup.geometry(f"+{x}+{y}")       
        # Make it modal (must close to continue)
        popup.grab_set()
        popup.transient(self.root)
        # Main content
        content_frame = tk.Frame(popup, bg=bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        # Color icon (● for Black, ○ for White)
        icon = "●" if color == "Black" else "○"
        tk.Label(content_frame, text=icon, font=('Helvetica', 48), fg=text_color, bg=bg_color).pack(pady=(20, 0))
        # Message text
        tk.Label(content_frame, text=message, font=('Helvetica', 14), fg=text_color, bg=bg_color, wraplength=350).pack(pady=10)

    def create_widgets(self, view_mode, replay_mode, winner):
        """
        Creates and arranges all UI widgets for the game interface.
        
        Args:
            view_mode (bool): Whether this is a view-only interface.
            replay_mode (bool): Whether this is a replay interface.
            winner (str): The winner's username (for replay mode).
        """
        self.player_frame = tk.Frame(self.frame, bg='#e0e0e0', padx=10, pady=5, relief=tk.GROOVE, bd=2)
        # Player information labels
        self.black_player_label = tk.Label(self.player_frame, text=f"Black: {self.player1}", font=('Helvetica', 12), bg='#e0e0e0')
        self.white_player_label = tk.Label(self.player_frame, text=f"White: {self.player2}", font=('Helvetica', 12), bg='#e0e0e0')
        self.turn_label = tk.Label(self.player_frame, text="", font=('Helvetica', 12, 'bold'), bg='#e0e0e0')
        # Layout player information
        self.black_player_label.pack(side=tk.LEFT, padx=10)
        self.white_player_label.pack(side=tk.LEFT, padx=10)
        if not replay_mode: # Displays timer and set turn_label in non-replay mode (game, view)
            self.turn_label.pack(side=tk.RIGHT, padx=10)
            self.timer_label = tk.Label(self.player_frame, text="Time left: --", font=('Helvetica', 12), bg='#e0e0e0')
            self.timer_label.pack(side=tk.RIGHT, padx=10)
            self.turn_label.pack(side=tk.RIGHT, padx=10)
        elif replay_mode: # Displays winner in replay mode
            self.winner_label = tk.Label(self.player_frame, text=f"Winner: {winner}", font=('Helvetica', 12), bg='#e0e0e0')
            self.winner_label.pack(side=tk.RIGHT, padx=10)
        self.player_frame.pack(fill=tk.X, pady=5)
        self.canvas = tk.Canvas(self.frame, width=600, height=600, bg='#DCB35C')
        self.canvas.pack()
        if not replay_mode and not view_mode: # Create Exit button for game mode
            self.exit_button = tk.Button(self.frame, text="Exit Game", command=self.exit_game, width=15, height=2)
            self.exit_button.pack(pady=13)
        self.draw_board() # Draw the initial empty board
        self.canvas.bind("<Button-1>", self.on_click) # Bind click event for moves

    def draw_board(self):
        """
        Draws the game board grid on the canvas with proper offsets.
        Also redraws any existing stones on the board.
        """
        self.cell_size = 600 // BOARD_SIZE
        # Draw horizontal lines (shifted down by offset_y)
        for i in range(BOARD_SIZE):
            y = self.offset_y + i * self.cell_size
            self.canvas.create_line(
                self.offset_x, y,
                self.offset_x + (BOARD_SIZE - 1) * self.cell_size, y
            )
        # Draw vertical lines (shifted right by offset_x)
        for i in range(BOARD_SIZE):
            x = self.offset_x + i * self.cell_size
            self.canvas.create_line(
                x, self.offset_y,
                x, self.offset_y + (BOARD_SIZE - 1) * self.cell_size
            )
        # Draw existing stones with the same offset
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.board[row][col]:
                    self.draw_stone(row, col, self.board[row][col])

    def draw_stone(self, row, col, color, move_number=None):
        """
        Draws a stone on the board at the specified position.
        
        Args:
            row (int): The row position on the board.
            col (int): The column position on the board.
            color (str): The stone color ('black' or 'white').
            move_number (int, optional): The move number to display on the stone.
        """
        x = self.offset_x + col * self.cell_size
        y = self.offset_y + row * self.cell_size
        r = self.cell_size // 2 - 2  # Stone radius
        if color == 'black':
            fill = '#333333'
            outline = '#666666'
        else:
            fill = '#f8f8f8'
            outline = '#dddddd'
        self.canvas.create_oval(x - r, y - r, x + r, y + r, 
                            fill=fill, outline=outline, width=1.2)
        if move_number is not None:
            text_color = 'white' if color == 'black' else 'black'
            self.canvas.create_text(x+1, y, text=str(move_number), 
                                fill=text_color, font=('Helvetica', 10), tags="stone")
            self.move_numbers[(row, col)] = move_number

    def update_game_state(self, state, view=False, replay=False):
        """
        Updates the game UI based on the latest game state from the server.
        
        Args:
            state (dict): The current game state containing board, players, etc.
            view (bool): Whether this is a view-only update.
            replay (bool): Whether this is a replay update.
        """
        self.board = state['board']
        current = state['current_player']
        players = state['players']
        if view: # Displays current player's username in view mode
            self.turn_label.config(text=f"{current.capitalize()}'s turn ({players[current]})")
        elif not replay: # Set turn in game mode (allows to place stone on board)
            self.is_my_turn = (players[current] == self.client.username)
        self.canvas.delete("all")
        self.draw_board()
        # Draw all stones with move numbers if available
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.board[row][col]:
                    move_num = self.move_numbers.get((row, col))
                    self.draw_stone(row, col, self.board[row][col], move_num)
        if not replay: # Displays current player's information in non-replay mode
            current = state['current_player']
            players = state['players']
            is_my_turn = (players[current] == self.client.username)
            self.remaining_time = int(state.get("time_remaining", TIMEOUT))
            self.timer_label.config(text=f"Time left: {self.remaining_time}s")
            if not view:
                # Determine player color
                if self.player1 == self.client.username:
                    player_color = "Black"
                    opponent_color = "White"
                else:
                    player_color = "White"
                    opponent_color = "Black"
                # Update turn label with color coding
                if is_my_turn:
                    self.start_local_timer()
                    self.turn_label.config(text=f"{player_color}'s turn: It's your move!", fg='#4CAF50')
                else:
                    self.stop_local_timer()
                    self.turn_label.config(text=f"{opponent_color}'s turn: Please wait...", fg='#f44336')

    def start_local_timer(self):
        """Starts the countdown timer for the current player's turn."""
        self.stop_local_timer()  # Prevent duplicates
        self.local_timer = self.root.after(1000, self.tick)

    def tick(self):
        """Callback for timer countdown, updates every second."""
        if not self.is_my_turn or self.game_over:
            return
        self.remaining_time -= 1
        if self.remaining_time < 0:
            self.remaining_time = 0
        self.timer_label.config(text=f"Time left: {self.remaining_time}s")
        self.local_timer = self.root.after(1000, self.tick)

    def stop_local_timer(self):
        """Stops the local timer if it's running."""
        if hasattr(self, 'local_timer'):
            self.root.after_cancel(self.local_timer)
            del self.local_timer

    def on_click(self, event):
        """
        Handles mouse click events on the game board.
        Converts click coordinates to board position and sends move to server.
        
        Args:
            event (tk.Event): The mouse click event containing coordinates.
        """
        if not self.is_my_turn or self.game_over: # Cannot place stone if it's not user's turn or game has ended
            return   
        # Adjust click coordinates for the offset
        adj_x = event.x - self.offset_x
        adj_y = event.y - self.offset_y
        col = round(adj_x / self.cell_size)
        row = round(adj_y / self.cell_size)
        # Validate move and send to server
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE and self.board[row][col] is None:
            self.client.send_message(Message(
                MessageType.MAKE_MOVE,
                {
                    'username': self.client.username,
                    'game_id': self.client.current_game_id,
                    'row': row,
                    'col': col
                }
            ))

    def start_polling(self, game_id=None):
        """
        Starts polling the server for game state updates.
        
        Args:
            game_id (str, optional): Specific game ID to poll. Defaults to current game.
        """
        if game_id:
            self.poll_game_state(game_id)
        else:
            self.poll_game_state()
        
    def stop_polling(self):
        """Stops the polling of game state updates."""
        if hasattr(self, 'polling_job'):
            self.root.after_cancel(self.polling_job)

    def poll_game_state(self, game_id=None):
        """
        Requests the current game state from the server and schedules the next poll.
        
        Args:
            game_id (str, optional): Specific game ID to request. Defaults to current game.
        """
        if self.client.current_game_id: # If there is a current game (game mode)
            self.client.send_message(Message(
                MessageType.GET_GAME_STATE,
                {'username': self.client.username, 'game_id': self.client.current_game_id}
            ))
        elif game_id: # If there is a specific game id (view mode)
            self.client.send_message(Message(
                MessageType.GET_GAME_STATE,
                {'username': self.client.username, 'game_id': game_id}
            ))
        self.polling_job = self.root.after(500, self.poll_game_state) # Schedule next poll in 500ms


    def show_game_over(self, winner, credits_change):
        """
        Displays the game over dialog with the result and credits change.
        
        Args:
            winner (str): The username of the winning player.
            credits_change (dict): Dictionary of credit changes for both players.
        """
        self.stop_polling()
        self.game_over = True
        delta = credits_change.get(self.client.username, 0)
        # Create a custom dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Game Over")
        dialog.geometry("400x250")
        dialog.resizable(False, False)  
        # Set window position (centered relative to main window)
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 125
        dialog.geometry(f"+{x}+{y}") 
        # Configure styles based on win/loss
        dialog.configure(bg='#f0f0f0')
        if winner == self.client.username:
            title_color = '#4CAF50'  # Green for win
            icon_img = "★"  # Star character (you could use an actual image)
        else:
            title_color = '#f44336'  # Red for loss
            icon_img = "✗"  # X character
        # Header frame
        header_frame = tk.Frame(dialog, bg=title_color)
        header_frame.pack(fill=tk.X)
        # Result icon
        icon_label = tk.Label(header_frame, text=icon_img, font=('Helvetica', 48), fg='white', bg=title_color)
        icon_label.pack(pady=10)
        # Result text
        result_text = "You Won!" if winner == self.client.username else "Game Over"
        result_label = tk.Label(header_frame, text=result_text, font=('Helvetica', 18, 'bold'), fg='white', bg=title_color)
        result_label.pack(pady=(0, 10))
        # Credits change
        credits_frame = tk.Frame(dialog, bg='#f0f0f0', padx=20, pady=20)
        credits_frame.pack(fill=tk.BOTH, expand=True)
        change = f"{delta:+}" if delta != 0 else "-0"
        credits_label = tk.Label(credits_frame, text=f"Credits change: "+change, font=('Helvetica', 14), bg='#f0f0f0')
        credits_label.pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def exit_game(self):
        """
        Handles exiting the game before it's over.
        Notifies the server if the game is still active.
        """
        if not self.game_over and self.client.current_game_id:
            self.client.send_message(Message(
                MessageType.PLAYER_DISCONNECTED,
                {'username': self.client.username, 'game_id': self.client.current_game_id}
            ))
        self.stop_polling()
        self.client.show_home_ui() # Return to home screen


class GameReplayUI(GameUI):
    """
    A specialized UI for replaying completed Five in a Row games.
    Inherits from GameUI to reuse board drawing and stone placement logic.
    Provides controls to navigate through game moves step-by-step or replay automatically.
    """
    def __init__(self, root, client, game_data):
        """
        Initializes the game replay interface.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
            game_data (dict): Dictionary containing game history data including:
                - game_id: Unique identifier for the game
                - player1: Username of first player (Black)
                - player2: Username of second player (White)
                - winner: Username of winner (None for draw)
                - moves: List of (row, col) tuples representing moves
        """
        self.game_data = game_data
        self.top = tk.Toplevel(root)
        self.top.title(f"Game Replay - {game_data['game_id']}")
        # Initialize parent class with replay_mode=True
        super().__init__(self.top, client, game_data['player1'], game_data['player2'], replay_mode=True, winner=game_data['winner'])
        # Replay state tracking
        self.current_move = 0 # Current move index
        self.total_moves = len(game_data['moves']) # Total moves in game
        self.moves = game_data['moves'] # List of all moves
        # Add replay controls and initialize display
        self.create_replay_controls()
        self.update_display()
        self.is_replaying = False  # Flag for auto-replay state
        self.replay_job = None  # Initialize replay_job
        self.top.protocol("WM_DELETE_WINDOW", self.safe_close) # Handle window close safely
        self.frame.pack()

    def create_replay_controls(self):
        """
        Creates and arranges the replay control buttons and status display.
        Includes:
        - Move navigation buttons (previous/next)
        - Replay button for automatic playback
        - Reset button to return to start
        - Move counter display
        """
        separator = tk.Frame(self.frame, height=3)
        separator.pack(fill=tk.X)
        control_frame = tk.Frame(self.frame)
        control_frame.pack(fill=tk.X, pady=5)
        # Move counter display
        self.step_var = tk.StringVar()
        step_label = tk.Label(control_frame, textvariable=self.step_var, font=('Helvetica', 12))
        step_label.pack(pady=5)
        # Control buttons
        button_frame = tk.Frame(control_frame)
        button_frame.pack()
        self.reset_btn = tk.Button(button_frame, text="<<", command=self.reset_board)
        self.prev_btn = tk.Button(button_frame, text="<", command=self.previous_move)
        self.next_btn = tk.Button(button_frame, text=">", command=self.next_move)
        self.replay_btn = tk.Button(button_frame, text=">>", command=self.start_replay)
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        self.replay_btn.pack(side=tk.LEFT, padx=5)

    def start_replay(self):
        """Starts the automatic replay of the entire game from the beginning."""
        if not self.is_replaying:
            self.reset_board()
            self.replay_whole_game()

    def replay_whole_game(self):
        """
        Automatically plays through all moves with a 500ms delay between moves.
        Updates the UI after each move and maintains replay state.
        """
        if self.is_replaying:
            return  # Prevent multiple concurrent replays
        self.is_replaying = True
        self.toggle_buttons(False) # Disable buttons during replay
        def replay_step():
            """Recursive function that handles each step of the replay"""
            if not self.is_replaying or self.current_move >= self.total_moves:
                # End of replay reached
                self.is_replaying = False
                self.toggle_buttons(True) # Re-enable buttons
                self.replay_job = None  # Clear the job reference
                return    
            self.next_move() # Advance to next move
            self.replay_job = self.top.after(500, replay_step) # Schedule next step
        replay_step() # Start the replay process

    def reset_board(self):
        """
        Resets the board to its initial empty state and stops any ongoing replay.
        Also resets the move counter to 0.
        """
        if self.is_replaying and self.replay_job:
            self.top.after_cancel(self.replay_job) # Cancel scheduled replay
            self.replay_job = None
        self.is_replaying = False
        self.toggle_buttons(True)
        self.current_move = 0
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.move_numbers = {} # Reset move numbers
        self.update_display() # Refresh UI

    def toggle_buttons(self, enable=True):
        """
        Enables or disables the navigation buttons during replay.
        
        Args:
            enable (bool): Whether to enable the buttons (True) or disable them (False)
        """
        state = tk.NORMAL if enable else tk.DISABLED
        self.prev_btn.config(state=state)
        self.next_btn.config(state=state)
        self.replay_btn.config(state=state)
        self.reset_btn.config(state=tk.NORMAL)  # Reset button is always enabled

    def safe_close(self):
        """Safely handles window closing by stopping any ongoing replay first."""
        if self.is_replaying and self.replay_job:
            self.top.after_cancel(self.replay_job)
        self.top.destroy()

    def previous_move(self):
        """Steps backward one move in the replay sequence."""
        if self.current_move > 0:
            self.current_move -= 1
            # Rebuild board state up to current move
            self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
            self.move_numbers = {}
            for step in range(self.current_move):
                row, col = self.moves[step]
                color = 'black' if (step+1) % 2 == 1 else 'white'
                self.board[row][col] = color
                self.move_numbers[(row, col)] = step+1
            self.update_display()

    def next_move(self):
        """Steps forward one move in the replay sequence."""
        if self.current_move < self.total_moves:
            row, col = self.moves[self.current_move]
            color = 'black' if (self.current_move+1) % 2 == 1 else 'white'
            self.board[row][col] = color
            self.move_numbers[(row, col)] = self.current_move+1
            self.current_move += 1
            self.update_display()

    def update_display(self):
        """
        Updates the board display and move counter text.
        Calls parent class's update_game_state with reconstructed game state.
        """
        self.step_var.set(f"Move {self.current_move}/{self.total_moves}")
        self.update_game_state({
            'board': self.board,
            'current_player': 'black' if self.current_move % 2 == 0 else 'white',
            'players': {'black': self.player1, 'white': self.player2}
        }, replay=True)

class HistoryUI:
    """
    UI component for displaying and navigating a player's game history.
    Shows a list of past games with opponent, result, credits change, and date.
    Allows viewing replays of selected games.
    """
    def __init__(self, root, client):
        """
        Initializes the history UI.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
        """
        self.root = root
        self.client = client
        self.frame = tk.Frame(root)
        self.title_label = tk.Label(self.frame, text="Your Game History", font=('Helvetica', 16))
        self.title_label.pack(pady=10)
        # Treeview for displaying game history
        self.history_tree = ttk.Treeview(self.frame, columns=('opponent', 'result', 'credits_change', 'date'), show='headings', height=11)
        for col in self.history_tree['columns']:
            self.history_tree.heading(col, text=col.replace('_', ' ').title())
            self.history_tree.column(col, width=150)
        # Layout and styling
        self.history_tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.history_tree.tag_configure('oddrow', background='#f8f9fa')
        self.history_tree.tag_configure('evenrow', background='#e9ecef')
        self.history_tree.bind("<Button-1>", self.on_row_click)
        self.selected_game = None # Currently selected game
        # Action buttons
        self.replay_button = tk.Button(self.frame, text="View Replay", command=self.show_replay, state=tk.DISABLED, width=15, height=2)
        self.replay_button.pack(pady=10)
        self.back_button = tk.Button(self.frame, text="Back to Home", command=self.client.show_home_ui, width=15, height=2)
        self.back_button.pack()
        # Window configuration
        self.root.geometry("700x450")
        self.frame.pack(padx=20, pady=20)
        
    def load_history_from_server(self, histories):
        """
        Populates the history treeview with game data from the server.
        
        Args:
            histories (list): List of game history dictionaries from server.
        """
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        # Add games in reverse chronological order (newest first)
        for i, history in enumerate(histories[::-1]):
            if history['player1'] == self.client.username: # Determine opponent username
                opponent = history['player2']
            else:
                opponent = history['player1']
            # Retrieve information
            result = "Win" if history['winner'] == self.client.username else "Loss"
            change = history['credits_change'].get(self.client.username, 0)
            change_str = f"{change:+}" if change != 0 else "-0"
            parsed_time = datetime.fromisoformat(history['end_time'])
            formatted_time = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            # Insert into treeview
            self.history_tree.insert('', tk.END, values=(opponent, result, change_str, formatted_time, history['game_id']),tags=(tag,))
    
    def on_row_click(self, event):
        """
        Handles selection of a game from the history list.
        Enables the replay button when a valid game is selected.
        """
        item = self.history_tree.identify_row(event.y)
        if not item:
            return
        values = self.history_tree.item(item, 'values')
        game_id = values[4]  # Get game_id from hidden column
        self.selected_game = next((h for h in self.client.histories if h['game_id'] == game_id), None) # Find matching game in client's history
        self.replay_button.config(state=tk.NORMAL if self.selected_game else tk.DISABLED) # Enable replay button if game found
                
    def show_replay(self):
        """Launches a GameReplayUI for the currently selected game."""
        if self.selected_game:
            GameReplayUI(self.root, self.client, self.selected_game)

class LiveGameViewerUI:
    """
    A UI component for viewing live Five in a Row games in progress.
    Provides real-time updates of the game state and handles game completion scenarios.
    """
    def __init__(self, root, client, game_id, initial_data, parent_ui):
        """
        Initializes the live game viewer interface.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
            game_id (str): The ID of the game being viewed.
            initial_data (dict): Initial game data containing player information.
            parent_ui (LiveGamesUI): The parent UI that created this viewer.
        """
        self.frame = tk.Frame(root)
        self.game_id = game_id
        self.client = client
        self.top = tk.Toplevel(root)
        self.top.title(f"Live View - Game {game_id}")
        self.game_over = False
        self.last_update_time = time.time()  # Track last update time
        self.parent_ui = parent_ui # Reference to parent UI
        # Clean up any existing polling
        if hasattr(self, 'polling_job'):
            self.top.after_cancel(self.polling_job)
        self.initial_data = initial_data # Store initial data for later use
        self.last_state = None  # Track the last received state
        self.final_state_received = False
        # Create the game UI in view mode
        self.game_ui = GameUI(self.top, self.client, initial_data['player1'], initial_data['player2'], view_mode=True, game_id = game_id)
        self.game_ui.frame.pack(padx=10, pady=10)
        # Close button
        self.close_btn = tk.Button(self.top, text="Close Viewer", command=self.close_viewer, width=15, height=2)
        self.close_btn.pack(pady=7)
        # Start polling for game state updates
        self.poll_game_state()

    def poll_game_state(self):
        """
        Periodically requests game state updates from the server.
        Handles disconnection if no updates are received for too long.
        """
        if hasattr(self, 'polling_job'):
            self.top.after_cancel(self.polling_job)
        if not self.game_over: # Request current game state
            self.client.send_message(Message(
                MessageType.GET_GAME_STATE,
                {
                    'username': self.client.username, 
                    'game_id': self.game_id
                }
            ))
            if time.time() - self.last_update_time > 2: # Check for disconnection (no updates for 2 seconds)
                self.handle_disconnect()
                return
            self.polling_job = self.top.after(250, self.poll_game_state) # Schedule next poll in 250ms
    
    def update_game_state(self, state):
        """
        Updates the game display with new state from server.
        
        Args:
            state (dict): The current game state containing board, players, etc.
        """
        if hasattr(self, 'game_ui') and self.game_ui:
            self.last_state = state
            # Check if game is over
            if state.get('game_over', False):
                if not self.game_over:  # Only handle if we haven't already
                    self._handle_final_state(state)
                return
            self.last_update_time = time.time()
            # Prepare full state data for display
            full_state = {
                'board': state.get('board', [[None]*BOARD_SIZE for _ in range(BOARD_SIZE)]),
                'current_player': state.get('current_player', self.initial_data.get('current_player', 'black')),
                'players': {
                    'black': self.initial_data['player1'],
                    'white': self.initial_data['player2']
                },
                'time_remaining': state.get('time_remaining', TIMEOUT),
                'game_over': False,
                'winner': None
            }
            self.game_ui.update_game_state(full_state, view=True)
    
    def _handle_final_state(self, state):
        """
        Processes the final game state when game ends.
        
        Args:
            state (dict): The final game state containing winner information.
        """
        self.game_over = True
        winner = state.get('winner')
        # Update UI with final state first
        final_state = {
            'board': state.get('board', self.last_state.get('board') if self.last_state else [[None]*BOARD_SIZE for _ in range(BOARD_SIZE)]),
            'current_player': state.get('current_player'),
            'players': {
                'black': self.initial_data['player1'],
                'white': self.initial_data['player2']
            },
            'time_remaining': 0,
            'game_over': True,
            'winner': winner
        }
        self.game_ui.update_game_state(final_state, view=True)
        # Force UI update before showing popup
        self.top.update_idletasks()
        self.top.after(100, lambda: self._show_game_over_popup(winner))

    def handle_disconnect(self):
        """Handles player disconnection scenario with appropriate UI feedback."""
        self.game_over = True
        if hasattr(self, 'polling_job'):
            self.top.after_cancel(self.polling_job)
        # Create disconnect notification popup
        popup = tk.Toplevel(self.top)
        popup.title("Game Ended")
        popup.geometry("350x180")
        popup.resizable(False, False)
        # Center the popup
        x = self.top.winfo_x() + (self.top.winfo_width() - 350) // 2
        y = self.top.winfo_y() + (self.top.winfo_height() - 200) // 2
        popup.geometry(f"+{x}+{y}")        
        # Make it modal
        popup.grab_set()
        popup.transient(self.top)        
        # Popup content
        tk.Label(popup, text="Game Ended", font=('Helvetica', 16, 'bold'),fg='#f44336').pack(pady=8)
        tk.Label(popup, text="A player has disconnected.", font=('Helvetica', 12)).pack(pady=3)
        tk.Label(popup, text="The game has ended prematurely.", font=('Helvetica', 12)).pack(pady=3)       
        ok_button = tk.Button(popup, text="OK", command=popup.destroy, width=6, height=2)
        ok_button.pack(pady=10)
    
    def _show_game_over_popup(self, winner):
        """
        Shows the game over popup with winner information.
        
        Args:
            winner (str): The username of the winning player.
        """
        time.sleep(1)
        self.game_over = True  
        # Stop polling
        if hasattr(self, 'polling_job'):
            self.top.after_cancel(self.polling_job)
        # Create game over popup
        popup = tk.Toplevel(self.top)
        popup.title("Game Over")
        popup.geometry("300x200")
        popup.resizable(False, False)  
        # Center the popup over the viewer window
        x = self.top.winfo_x() + (self.top.winfo_width() - 300) // 2
        y = self.top.winfo_y() + (self.top.winfo_height() - 200) // 2
        popup.geometry(f"+{x}+{y}")     
        # Make it modal
        popup.grab_set()
        popup.transient(self.top)
        # Game over content
        tk.Label(popup, text="GAME OVER", font=('Helvetica', 16, 'bold'), fg='#4a4a4a').pack(pady=10)
        result_text = f"{winner} wins!"
        tk.Label(popup, text=result_text, font=('Helvetica', 14), fg='#2c3e50').pack(pady=5)       
        icon = "🏆" if winner else "🤝"
        tk.Label(popup, text=icon, font=('Helvetica', 48)).pack(pady=10)

    def close_viewer(self):
        """
        Cleans up when closing the viewer.
        Stops polling and notifies parent UI.
        """
        self.game_over = True
        if hasattr(self, 'polling_job'):
            self.top.after_cancel(self.polling_job)
        if self.top.winfo_exists():
            self.top.destroy()
        if self.parent_ui:
            self.parent_ui.live_game_viewer_ui = None

class LiveGamesUI:
    """
    UI component for displaying and managing currently active games.
    Shows a list of live games with player information and stone counts.
    Allows users to view ongoing games.
    """
    def __init__(self, root, client):
        """
        Initializes the live games interface.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
        """
        self.root = root
        self.client = client
        self.frame = tk.Frame(root)
        self.selected_game_id = None # Currently selected game ID
        self.selected_game_data = None # Selected game data
        self.live_game_viewer_ui = None # Reference to active viewer
        self.live_games = None # List of live games from server
        self.title_label = tk.Label(self.frame, text="Live Games", font=('Helvetica', 16))
        self.title_label.pack(pady=10)
        # Treeview for displaying live games
        self.games_tree = ttk.Treeview(self.frame, columns=('player1', 'player2', 'black_stones', 'white_stones', 'current_turn'), show='headings', height=11)
        self.games_tree.heading('player1', text='Black Player')
        self.games_tree.column('player1', width=150)
        self.games_tree.heading('player2', text='White Player')
        self.games_tree.column('player2', width=150)
        self.games_tree.heading('black_stones', text='Black Stones')
        self.games_tree.column('black_stones', width=100, anchor='center')
        self.games_tree.heading('white_stones', text='White Stones')
        self.games_tree.column('white_stones', width=100, anchor='center')
        self.games_tree.heading('current_turn', text='Current Turn')
        self.games_tree.column('current_turn', width=100, anchor='center')
        # Style and layout
        self.games_tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.games_tree.tag_configure('oddrow', background='#f8f9fa')
        self.games_tree.tag_configure('evenrow', background='#e9ecef')
        self.games_tree.tag_configure('selected', background='#0078d7', foreground='white')
        self.games_tree.bind("<Button-1>", self.on_row_click)
        # Action buttons
        self.view_button = tk.Button(self.frame, text="View Game", command=self.view_game, state=tk.DISABLED, width=15, height=2)
        self.view_button.pack(pady=10)
        self.back_button = tk.Button(self.frame, text="Back to Home", command=self.return_to_home, width=15, height=2)
        self.back_button.pack()
        # Window configuration
        self.root.geometry("700x450")
        self.frame.pack(padx=20, pady=20)
        # Start polling for live games
        self.poll_live_games()

    def poll_live_games(self):
        """
        Periodically requests updates of live games from server.
        Manages game selection state and polling interval.
        """
        self.client.send_message(Message(
            MessageType.GET_LIVE_GAMES_REQUEST,
            {'username': self.client.username}
        ))
        if self.selected_game_id: # Validate current selection
            # Check if the game still exists in the Treeview before trying to modify selection
            if self.selected_game_id in self.games_tree.get_children():
                if self.is_game_ended(self.selected_game_id):
                    self.view_button.config(state=tk.DISABLED)
                    self.games_tree.selection_remove(self.selected_game_id)
                    self.selected_game_id = None
            else:
                # Game ID not found in Treeview - clear selection
                self.view_button.config(state=tk.DISABLED)
                self.selected_game_id = None
        self.polling_job = self.root.after(1000, self.poll_live_games)  # Refresh every 1 second

    def stop_polling(self):
        """Stops the live games polling timer."""
        if hasattr(self, 'polling_job'):
            self.root.after_cancel(self.polling_job)
    
    def return_to_home(self):
        """
        Handles returning to home screen.
        Ensures any active viewer is closed first.
        """
        if self.live_game_viewer_ui is not None and self.live_game_viewer_ui.top.winfo_exists():
            messagebox.showwarning(
                "Close Viewer First",
                "You must close the live game viewer before returning to the home screen."
            )
            return
        self.stop_polling()
        self.client.show_home_ui()

    def load_live_games(self, games):
        """
        Updates the UI with the latest list of live games.
        
        Args:
            games (list): List of game dictionaries from server.
        """
        # Store games and current selection
        self.live_games = games
        selected = self.games_tree.selection()
        # Clear existing items
        for item in self.games_tree.get_children():
            self.games_tree.delete(item)
        # Add new items
        for i, game in enumerate(games):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.games_tree.insert('', tk.END, 
                values=(game['player1'], game['player2'], game['black_stones'], game['white_stones'], game['current_player'].capitalize()), 
                tags=(tag,), 
                iid=game['game_id']
            )
        # Restore selection if it still exists
        if selected and selected[0] in self.games_tree.get_children():
            self.games_tree.selection_set(selected[0])
            self.games_tree.focus(selected[0])

    def on_row_click(self, event):
        """
        Handles selection of a game from the list.
        Validates selection and enables/disables view button accordingly.
        """
        item = self.games_tree.identify_row(event.y)
        if not item:
            return
        if self.is_game_ended(item): # Check if selected game has ended
            self.view_button.config(state=tk.DISABLED)
            self.games_tree.selection_remove(item)  # Remove selection if game is over
            return
        # Set new selection
        self.games_tree.selection_set(item)
        values = self.games_tree.item(item, 'values')
        if not values or len(values) < 5:  # Ensure we have all expected columns
            self.view_button.config(state=tk.DISABLED)
            return
        # Store the game_id and basic game data
        self.selected_game_id = item
        self.selected_game_data = {
            'game_id': item,
            'player1': values[0],  # Black player
            'player2': values[1],  # White player
            'current_player': values[4].lower(),  # Current turn
        }
        # Enable view button if game is active
        game_ended = self.is_game_ended(item)
        self.view_button.config(state=tk.NORMAL if not game_ended else tk.DISABLED)
        
    def is_game_ended(self, game_id):
        """
        Checks if a game has ended.
        
        Args:
            game_id (str): The game ID to check.
            
        Returns:
            bool: True if game has ended, False otherwise.
        """
        for game in self.live_games:
            if game['game_id'] == game_id:
                return game.get('game_over', False) or not game.get('current_player')
        return True

    def view_game(self):
        """
        Opens a live viewer for the selected game.
        Ensures only one viewer is open at a time.
        """
        if self.live_game_viewer_ui is not None and self.live_game_viewer_ui.top.winfo_exists():
            messagebox.showwarning("Viewer Limit", "You already have a game viewer open.\nPlease close it before opening another.")
            return
        if self.selected_game_data:
            self.live_game_viewer_ui = LiveGameViewerUI(
                root=self.root,
                client=self.client,
                game_id=self.selected_game_id,
                initial_data={
                    'player1': self.selected_game_data['player1'],
                    'player2': self.selected_game_data['player2']
                },
                parent_ui=self
            )
            self.live_game_viewer_ui.frame.pack()


class LeaderboardUI:
    """
    A UI component for displaying the game leaderboard, showing player rankings based on credits and wins.
    Displays player statistics including:
    - Rank (position in leaderboard)
    - Username
    - Credits (in-game currency)
    - Wins (number of games won)
    - Losses (number of games lost)
    """
    def __init__(self, root, client):
        """
        Initializes the Leaderboard UI with all necessary components.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
        """
        self.root = root
        self.client = client
        self.frame = tk.Frame(root)
        self.title_label = tk.Label(self.frame, text="Leaderboard", font=('Helvetica', 16))
        self.title_label.pack(pady=10)
        # Treeview widget to display leaderboard data in tabular format
        self.leaderboard_tree = ttk.Treeview(self.frame, columns=('rank', 'username', 'credits', 'wins', 'losses'), show='headings', height=11)
        self.leaderboard_tree.heading('rank', text='Rank')
        self.leaderboard_tree.column('rank', width=100, anchor='center')
        self.leaderboard_tree.heading('username', text='Username')
        self.leaderboard_tree.column('username', width=150, anchor='w')
        self.leaderboard_tree.heading('credits', text='Credits')
        self.leaderboard_tree.column('credits', width=150, anchor='center')
        self.leaderboard_tree.heading('wins', text='Wins')
        self.leaderboard_tree.column('wins', width=100, anchor='center')
        self.leaderboard_tree.heading('losses', text='Losses')
        self.leaderboard_tree.column('losses', width=100, anchor='center')
        # Layout and styling
        self.leaderboard_tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.leaderboard_tree.tag_configure('oddrow', background='#f8f9fa')
        self.leaderboard_tree.tag_configure('evenrow', background='#e9ecef')
        # Action button
        self.refresh_button = tk.Button(self.frame, text="Refresh", command=self.refresh, width=15, height=2)
        self.refresh_button.pack(pady=10)
        self.back_button = tk.Button(self.frame, text="Back to Home", command=self.client.show_home_ui, width=15, height=2)
        self.back_button.pack()
        self.root.geometry("700x450")
        self.frame.pack(padx=20, pady=20)

    def load_leaderboard(self, leaderboard_data):
        """
        Loads and displays leaderboard data in the Treeview widget.
        
        Args:
            leaderboard_data (list): List of dictionaries containing player statistics.
        """
        # Clear existing data
        for item in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(item)
        # Add new data with alternating colors
        for i, player in enumerate(leaderboard_data, 1):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.leaderboard_tree.insert('', tk.END, values=(
                i,
                player['username'],
                player['credits'],
                player['wins'],
                player['losses']
            ), tags=(tag,))
    
    def refresh(self):
        """
        Refresh with the latest leaderboard data.
        """
        self.client.send_message(Message(
            MessageType.GET_LEADERBOARD_REQUEST,
            {'username': self.client.username}
        ))

class MatchingRoomUI:
    """
    A UI component for the game's matching room, where players can:
    - View available opponents
    - Send and receive game invitations
    - Search and filter players by username and credits
    - Manage pending invitations
    
    The interface consists of two main panels:
    1. Left panel: Shows available players with search/filter functionality
    2. Right panel: Displays pending invitations with accept/decline options
    
    Features:
    - Real-time updates of available players
    - Timed invitations with countdown display
    - Visual indicators for expiring invitations
    - Search by username and credit range
    """
    def __init__(self, root, client):
        """
        Initializes the Matching Room UI with all interface components.
        
        Args:
            root (tk.Tk): The root Tkinter window.
            client (GameClient): The game client instance for server communication.
        """
        self.root = root
        self.client = client
        self.frame = tk.Frame(root)
        self.selected_user = None  # Currently selected player for invitation
        self.polling_job = None  # Reference to the polling job
        self.request_polling_job = None  # Reference to request polling job
        self.current_search_filter = None  # Current search criteria
        self.is_waiting_for_response = False  # Flag for pending invitation
        self.pending_invitations = {}  # Track pending invitations with timers
        self.invitation_timer_job = None  # Timer for invitation countdowns
        self.matching_room_users = []  # List of available players
        self.root.geometry("700x450") 
        # Title
        self.title_label = tk.Label(self.frame, text="Matching Room", font=('Helvetica', 16))
        self.title_label.pack(pady=5) #10
        # Panels container
        panels_frame = tk.Frame(self.frame)
        panels_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        panels_frame.columnconfigure(0, weight=1, uniform='panels')
        panels_frame.columnconfigure(1, weight=1, uniform='panels')

        # Left panel - User list
        left_panel = tk.Frame(panels_frame, bd=1, relief=tk.GROOVE)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5)
        tk.Label(left_panel, text="Available Players", font=('Helvetica', 12)).pack(pady=3) #5
        # Search frame
        search_frame = tk.Frame(left_panel)
        search_frame.pack(fill=tk.X, padx=3, pady=3)
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, width=28)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, padx=3)
        # Credits range search
        credits_frame = tk.Frame(left_panel)
        credits_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(credits_frame, text="Credits:").pack(side=tk.LEFT)
        self.min_credits = tk.Entry(credits_frame, width=5)
        self.min_credits.pack(side=tk.LEFT)
        tk.Label(credits_frame, text="-").pack(side=tk.LEFT)
        self.max_credits = tk.Entry(credits_frame, width=5)
        self.max_credits.pack(side=tk.LEFT)
        # Search and reset buttons
        self.search_button = tk.Button(credits_frame, text="Search", command=self.search_users, width=4)
        self.reset_button = tk.Button(credits_frame, text="Reset", command=self.reset_search, width=4)
        self.search_button.pack(side=tk.LEFT, padx=3)
        self.reset_button.pack(side=tk.LEFT, padx=0)
        # Player list (Treeview)
        self.user_tree = ttk.Treeview(left_panel, columns=('username', 'credits'), show='headings', height=11)
        self.user_tree.heading('username', text='Username')
        self.user_tree.heading('credits', text='Credits')
        self.user_tree.column('username', width=150, anchor='w')
        self.user_tree.column('credits', width=80, anchor='center')
        vsb = ttk.Scrollbar(left_panel, orient="vertical", command=self.user_tree.yview)
        hsb = ttk.Scrollbar(left_panel, orient="horizontal", command=self.user_tree.xview)
        self.user_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.user_tree.bind('<<TreeviewSelect>>', self.on_user_select)
        
        # Right panel - Invitations
        right_panel = tk.Frame(panels_frame, bd=1, relief=tk.GROOVE)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5)
        tk.Label(right_panel, text="Pending Invitations", font=('Helvetica', 12)).pack(pady=5)  
        # Invitations Treeview
        self.invitations_tree = ttk.Treeview(right_panel, columns=('from', 'credits', 'time_left'), show='headings', height=11)
        self.invitations_tree.heading('from', text='From')
        self.invitations_tree.heading('credits', text='Credits')
        self.invitations_tree.heading('time_left', text='Time Left')
        self.invitations_tree.column('from', width=120, anchor='w')
        self.invitations_tree.column('credits', width=80, anchor='center')
        self.invitations_tree.column('time_left', width=80, anchor='center')
        inv_vsb = ttk.Scrollbar(right_panel, orient="vertical", command=self.invitations_tree.yview)
        inv_hsb = ttk.Scrollbar(right_panel, orient="horizontal", command=self.invitations_tree.xview)
        self.invitations_tree.configure(yscrollcommand=inv_vsb.set, xscrollcommand=inv_hsb.set)
        self.invitations_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.invitations_tree.bind('<<TreeviewSelect>>', self.on_invitation_select)

        self.user_tree.tag_configure('oddrow', background='#f8f9fa')
        self.user_tree.tag_configure('evenrow', background='#e9ecef')
        self.invitations_tree.tag_configure('oddrow', background='#f8f9fa')
        self.invitations_tree.tag_configure('evenrow', background='#e9ecef')
        self.invitations_tree.tag_configure('expiring', background='#ffcccc')

        # Action buttons
        button_frame = tk.Frame(self.frame)
        button_frame.pack(fill=tk.X, pady=(10, 20))
        self.back_button = tk.Button(button_frame, text="Back to Home", command=self.return_to_home, width=10, height=2)
        self.back_button.pack(side=tk.LEFT, padx=30)
        self.match_button = tk.Button(button_frame, text="Send Invite", command=self.send_match_request, width=10, height=2, state=tk.DISABLED)
        self.match_button.pack(side=tk.LEFT, padx=10)
        self.decline_button = tk.Button(button_frame, text="Decline", command=self._decline_invitation, width=10, height=2, state=tk.DISABLED)
        self.decline_button.pack(side=tk.RIGHT, padx=30)
        self.accept_button = tk.Button(button_frame, text="Accept", command=self._accept_invitation, width=10, height=2, state=tk.DISABLED)
        self.accept_button.pack(side=tk.RIGHT, padx=10)
        # Start background processes
        self.start_polling() # Start polling
        self.update_invitation_timers() # Start invitation timer updates
        self.frame.pack(fill=tk.BOTH, expand=True)

    def update_invitation_timers(self):
        """
        Updates the countdown timers for all pending invitations.
        Highlights invitations that are about to expire and removes expired ones.
        Runs every 500ms to keep timers accurate.
        """
        current_time = time.time()
        expired = []
        for req_id, invitation in list(self.pending_invitations.items()).copy():
            time_left = max(0, invitation['expiry'] - current_time)
            # Find the item in the treeview
            for item in self.invitations_tree.get_children():
                if self.invitations_tree.item(item, 'values')[0] == invitation['from']:
                    mins, secs = divmod(int(time_left), 60)
                    time_str = f"{mins:02d}:{secs:02d}"                    
                    # Update the time left display
                    values = list(self.invitations_tree.item(item, 'values'))
                    values[2] = time_str
                    self.invitations_tree.item(item, values=values)
                    # Highlight if less than 5 seconds left
                    if time_left <= 6:
                        self.invitations_tree.item(item, tags=('expiring',))
                    else:
                        self.invitations_tree.item(item, tags=())
                    if time_left <= 0:
                        expired.append(req_id)
                    break
        # Remove expired invitations
        for req_id in expired:
            self._remove_invitation(req_id)
        # Schedule next update
        self.invitation_timer_job = self.root.after(500, self.update_invitation_timers)

    def start_polling(self):
        """
        Starts periodic polling of server for matching room updates.
        Requests updated player list every 500ms while in matching room.
        """
        if not self.client.username:
            return 
        self.client.send_message(Message(
            MessageType.GET_MATCHING_ROOM_USERS,
            {'username': self.client.username}
        ))
        self.polling_job = self.root.after(500, self.start_polling)

    def stop_polling(self):
        """
        Stops all background polling processes when leaving matching room.
        Cancels both player list updates and invitation timer updates.
        """
        if hasattr(self, 'polling_job'):
            self.root.after_cancel(self.polling_job)
        if hasattr(self, 'invitation_timer_job') and self.invitation_timer_job:
            self.root.after_cancel(self.invitation_timer_job)

    def search_users(self):
        """
        Filters the player list based on search criteria from UI inputs.
        Supports filtering by:
        - Username substring match (case-insensitive)
        - Credit range (minimum and maximum values)
        """
        search_term = self.search_entry.get().lower()
        min_credits = self.min_credits.get()
        max_credits = self.max_credits.get()
        try:
            min_c = int(min_credits) if min_credits else 0
            max_c = int(max_credits) if max_credits else float('inf')  
            # Store the current search criteria
            self.current_search_filter = (search_term, min_c, max_c)
            # Apply the filter to current data
            if hasattr(self.client, 'matching_room_users'):
                self.update_users_list(self.client.matching_room_users)
        except ValueError:
            messagebox.showerror("Error", "Credits must be numbers")
    
    def reset_search(self):
        """
        Resets all search filters and displays the full player list.
        Clears search fields and removes any active filtering.
        """
        self.search_entry.delete(0, tk.END)
        self.min_credits.delete(0, tk.END)
        self.max_credits.delete(0, tk.END)
        self.current_search_filter = None
        if hasattr(self.client, 'matching_room_users'):
            self.update_users_list(self.client.matching_room_users)

    def update_users_list(self, users):
        """
        Updates the player list display with current data.
        Preserves selection state and applies active filters.
        
        Args:
            users (list): List of player dictionaries containing username and credits
        """
        self.matching_room_users = users
        current_selection = self.user_tree.selection()
        selected_username = None
        if current_selection:
            selected_username = self.user_tree.item(current_selection[0])['values'][0]
        # Clear current items
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        # Add filtered items
        filtered_users = []
        for user in users:
            username = user['username'] if isinstance(user, dict) else str(user)
            credits = user['credits'] if isinstance(user, dict) else 0
            # Apply search filter if it exists
            if self.current_search_filter:
                search_term, min_c, max_c = self.current_search_filter
                if (search_term in username.lower() and 
                    min_c <= credits <= max_c):
                    filtered_users.append(user)
            else:
                filtered_users.append(user)
        # Add to treeview
        for i, user in enumerate(filtered_users):
            username = user['username'] if isinstance(user, dict) else str(user)
            credits = user['credits'] if isinstance(user, dict) else 0
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            item_id = self.user_tree.insert('', 'end', values=(username, credits), tags=(tag,))
            # Restore selection if this was the previously selected user
            if username == selected_username:
                self.user_tree.selection_set(item_id)
                self.user_tree.focus(item_id)
        # If no selection was restored, disable match button
        if not self.user_tree.selection():
            self.match_button.config(state=tk.DISABLED)
            self.selected_user = None

    def update_requests_list(self, requests):
        """
        Updates the invitations list with new match requests.
        Adds new requests and removes expired ones.
        
        Args:
            requests (list): List of invitation dictionaries from server
        """
        current_time = time.time()
        # Add new requests
        req = requests[0]
        req_id = req['id']
        if req_id not in self.pending_invitations:
            self.pending_invitations[req_id] = {
                'from': req['from'],
                'credits': req.get('credits', 0),
                'expiry': req['expiry'],
                'id': req_id
            }
            # Add to treeview
            time_str = "00:15"  # Initial time
            tag = 'oddrow' if len(self.invitations_tree.get_children()) % 2 == 0 else 'evenrow'
            self.invitations_tree.insert('', 'end', 
                values=(req['from'], req.get('credits', 0), time_str),
                tags=(tag,)
            )
        # Remove expired requests
        to_remove = []
        for req_id, inv in list(self.pending_invitations.items()).copy():
            if current_time > inv['expiry']:
                to_remove.append(req_id)
        for req_id in to_remove:
            self._remove_invitation(req_id)
    
    def _remove_invitation(self, req_id):
        """
        Removes a specific invitation from display and tracking.
        
        Args:
            req_id (str): The unique ID of the invitation to remove
        """
        if req_id in self.pending_invitations:
            from_user = self.pending_invitations[req_id]['from']
            for item in self.invitations_tree.get_children():
                if self.invitations_tree.item(item, 'values')[0] == from_user:
                    self.invitations_tree.delete(item)
                    break
            del self.pending_invitations[req_id]
        # Disable buttons if no selection
        if not self.invitations_tree.selection():
            self.accept_button.config(state=tk.DISABLED)
            self.decline_button.config(state=tk.DISABLED)

    def on_user_select(self, event):
        """
        Handles selection of a player from the available players list.
        Enables/disables the invitation button based on selection state.
        """
        selected_items = self.user_tree.selection()
        if selected_items and not self.is_waiting_for_response:
            self.selected_user = self.user_tree.item(selected_items[0])['values'][0]
            self.match_button.config(state=tk.NORMAL)
        else:
            self.selected_user = None
            self.match_button.config(state=tk.DISABLED)

    def on_invitation_select(self, event):
        """
        Handles selection of an invitation from the pending invitations list.
        Enables/disables the accept/decline buttons based on selection state.
        """
        selected_items = self.invitations_tree.selection()
        if selected_items:
            self.accept_button.config(state=tk.NORMAL)
            self.decline_button.config(state=tk.NORMAL)
        else:
            self.accept_button.config(state=tk.DISABLED)
            self.decline_button.config(state=tk.DISABLED)
    
    def _accept_invitation(self):
        """
        Handles accepting a received game invitation.
        Sends acceptance to server and removes the invitation from display.
        """
        selected = self.invitations_tree.selection()
        if not selected:
            return           
        invitation = self.invitations_tree.item(selected[0], 'values')
        from_user = invitation[0]       
        # Find the request ID
        req_id = None
        for rid, req in list(self.pending_invitations.items()).copy():
            if req['from'] == from_user:
                req_id = rid
                break
        if req_id:
            self.client.send_message(Message(
                MessageType.MATCH_RESPONSE,
                {
                    'request_id': req_id,
                    'accepted': True,
                    'username': self.client.username
                }
            ))
            self._remove_invitation(req_id)
            # Clear selection after accepting
            for item in selected:
                if item in self.invitations_tree.get_children():
                    self.invitations_tree.selection_remove(item)

    def _decline_invitation(self):
        """
        Handles declining a received game invitation.
        Sends decline to server and removes the invitation from display.
        """
        selected = self.invitations_tree.selection()
        if not selected:
            return
        invitation = self.invitations_tree.item(selected[0], 'values')
        from_user = invitation[0]
        # Find the request ID
        req_id = None
        for rid, req in list(self.pending_invitations.items()).copy():
            if req['from'] == from_user:
                req_id = rid
                break        
        if req_id:
            self.client.send_message(Message(
                MessageType.MATCH_RESPONSE,
                {
                    'request_id': req_id,
                    'accepted': False,
                    'username': self.client.username
                }
            ))
            self._remove_invitation(req_id)
    
    def handle_match_response(self, accepted: bool, responder: str):
        """
        Handles response to a sent invitation from another player.
        
        Args:
            accepted (bool): Whether the invitation was accepted
            responder (str): Username of the player who responded
        """
        if hasattr(self, 'waiting_dialog') and self.waiting_dialog.winfo_exists():
            self.waiting_dialog.destroy()
        self.is_waiting_for_response = False
        self.match_button.config(state=tk.NORMAL)        
        if accepted:
            pass # Match found handling is done by client's message handler
        else:
            messagebox.showinfo("Info", f"Match request was declined by {responder}")

    def send_match_request(self):
        """
        Sends a game invitation to the selected player.
        Shows a waiting dialog with countdown timer.
        Handles cases where the target player leaves the matching room.
        """
        if not self.selected_user:
            return
        self.is_waiting_for_response = True
        self.match_button.config(state=tk.DISABLED)
        # Create waiting dialog
        self.waiting_dialog = tk.Toplevel(self.root)
        self.waiting_dialog.title("Waiting for Response")
        self.waiting_dialog.resizable(False, False)
        self.waiting_dialog.overrideredirect(True)
        self.waiting_dialog.geometry("400x300")
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
        self.waiting_dialog.geometry(f"+{x}+{y}")
        self.waiting_dialog.grab_set()
        self.waiting_dialog.transient(self.root)
        # Main content frame
        content_frame = tk.Frame(self.waiting_dialog, padx=30, pady=30)
        content_frame.pack()
        self.waiting_label = tk.Label(content_frame, text=f"Waiting for {self.selected_user} to respond", font=('Helvetica', 14, 'bold'), fg='#333')
        self.waiting_label.pack(pady=(0, 10))
        self.time_left_label = tk.Label(content_frame, text="15 seconds remaining", font=('Helvetica', 12))
        self.time_left_label.pack()
        # Animated dots
        self.dots = tk.Label(content_frame, text="...", font=('Helvetica', 14), fg='#666')
        self.dots.pack()
        self.dot_count = 0
        self.animate_dots()
        # Loading spinner
        self.spinner = tk.Label(content_frame, text="◐", font=('Helvetica', 24), fg='#DCB35C')
        self.spinner.pack(pady=10)
        self.spin_index = 0
        self.spin_chars = ["◐", "◓", "◑", "◒"]
        self.animate_spinner()
        # Cancel button
        user = self.selected_user
        cancel_button = tk.Button(content_frame, text="Cancel", command=lambda: self._cancel_waiting(user=user, notify=True), width=15, height=2)
        cancel_button.pack(pady=20)
        # Start countdown
        self.waiting_end_time = time.time() + 15
        self.update_waiting_timer(self.selected_user)
        # Send the match request
        self.client.send_message(Message(
            MessageType.MATCH_REQUEST,
            {
                'from': self.client.username,
                'to': self.selected_user,
                'username': self.client.username,
                'expiry': self.waiting_end_time
            }
        ))

    def update_waiting_timer(self, to_user):
        """
        Updates the countdown timer in the waiting dialog.
        Handles cases where the invited player leaves the matching room.
        
        Args:
            to_user (str): Username of the invited player
        """
        if not hasattr(self, 'waiting_dialog') or not self.waiting_dialog.winfo_exists():
            return
        usernames = [entry['username'] for entry in self.matching_room_users.copy()]
        if to_user not in usernames: # If the invited user has left matching room
            self._cancel_waiting()
            messagebox.showinfo("Info", f"{to_user} has left the matching room", parent=self.root)
            return
        time_left = max(0, self.waiting_end_time - time.time())
        if hasattr(self, 'time_left_label'):
            self.time_left_label.config(text=f"{int(time_left)} seconds remaining")
        if time_left <= 0: # Expire
            self._cancel_waiting()
            messagebox.showinfo("Timeout", "The invitation has expired", parent=self.root)
        else:
            self.root.after(500, lambda: self.update_waiting_timer(to_user))
    

    def animate_dots(self):
        """Animates the waiting dots."""
        if hasattr(self, 'waiting_dialog') and self.waiting_dialog.winfo_exists():
            self.dot_count = (self.dot_count + 1) % 4
            self.dots.config(text="." * self.dot_count)
            self.waiting_dialog.after(500, self.animate_dots)

    def animate_spinner(self):
        """Animates the loading spinner."""
        if hasattr(self, 'waiting_dialog') and self.waiting_dialog.winfo_exists():
            self.spin_index = (self.spin_index + 1) % 4
            self.spinner.config(text=self.spin_chars[self.spin_index])
            self.waiting_dialog.after(300, self.animate_spinner)

    def _cancel_waiting(self, user=None, notify=False):
        """
        Cancels a pending invitation request.
        
        Args:
            user (str, optional): Username of player to notify about cancellation
            notify (bool): Whether to notify the other player about cancellation
        """
        if hasattr(self, 'waiting_dialog') and self.waiting_dialog.winfo_exists():
            self.waiting_dialog.destroy()
        self.is_waiting_for_response = False
        self.match_button.config(state=tk.NORMAL)       
        # Cancel the match request
        if user:
            self.client.send_message(Message(
                MessageType.MATCH_CANCEL,
                {
                    'from': self.client.username,
                    'to': user,
                    'username': self.client.username,
                    'notify': notify
                }
            ))

    def return_to_home(self):
        """
        Handles returning to the home screen.
        Stops all background processes and notifies server about leaving matching room.
        """
        self.stop_polling()
        self.client.send_message(Message(
            MessageType.MATCHING_ROOM_LEAVE,
            {'username': self.client.username}
        ))
        self.client.show_home_ui()


class GameClient:
    """
    The main client class for the Five in a Row game that handles:
    - Server communication and message processing
    - UI management and navigation between screens
    - Game state tracking and synchronization
    
    Manages all aspects of the client-side application including:
    - Authentication (login/signup)
    - Game views (board, waiting, history, etc.)
    - Matchmaking and live game viewing
    - Leaderboard and statistics
    
    The client maintains a persistent connection to the server and
    handles all message passing in a separate thread.
    """
    def __init__(self, root):
        """
        Initializes the game client and establishes server connection.
        
        Args:
            root (tk.Tk): The root Tkinter window.
        """
        self.root = root
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        # Load configuration from config.ini
        config = configparser.ConfigParser()
        config.read("config.ini")
        self.server_host = config.get("server", "host")
        self.server_port = config.getint("server", "port")
        # Client state variables
        self.username = None  # Current logged in user
        self.current_game_id = None  # Active game identifier
        self.current_ui = None  # Currently displayed UI component
        self.histories = []  # Stores game history data
        self.live_games = []  # Stores live games data
        self.matching_room_users = []  # Users in matching room
        self.connect() # Establish server connection
        # Start thread for receiving server messages
        self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.receive_thread.start()
        # Initialize UI components
        self.auth_ui = None
        self.home_ui = None
        self.waiting_ui = None
        self.game_ui = None
        self.live_games_ui = None
        self.history_ui = None
        self.leaderboard_ui = None
        self.show_auth_ui() # Start with authentication UI

    def connect(self):
        """
        Establishes connection to the game server using configured host/port.
        Displays error message and exits if connection fails.
        """
        try:
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
        except ConnectionRefusedError:
            messagebox.showerror("Error", "Could not connect to server")
            self.root.destroy()

    def send_message(self, message: Message):
        """
        Sends a message to the game server.
        Handles connection errors by showing message and closing app.
        
        Args:
            message (Message): The message object to send to the server.
        """
        try:
            self.socket.send((message.to_json() + '\n').encode("utf-8")) # delimiter
        except (ConnectionError, OSError):
            messagebox.showerror("Error", "Lost connection to server")
            self.root.destroy()

    def receive_messages(self):
        """
        Runs in background thread to continuously receive messages from server.
        Handles message buffering and parsing, dispatches to message handler.
        Uses newline delimiter to separate messages in the stream.
        """
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data: # Connection closed
                    break
                buffer += data.decode("utf-8")
                # Process complete messages (delimited by newline)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1) # delimiter
                    if line.strip():
                        message = Message.from_json(line)
                        self.root.after(0, self.handle_server_message, message)
            except (ConnectionError, OSError, json.JSONDecodeError) as e:
                print(f"[ERROR] Client recv: {e}")
                break

    def handle_server_message(self, message):
        """
        Processes incoming server messages and updates UI/state accordingly.
        Dispatches different message types to appropriate handlers.
        
        Args:
            message (Message): The received message from server.
        """
        if message.type == MessageType.LOGIN_RESPONSE: # Successful login - store username and show home screen
            self.username = message.data.get("username")
            self.show_home_ui()
        elif message.type == MessageType.SIGNUP_RESPONSE: # Successful signup - return to auth screen
            messagebox.showinfo("Success", "Sign up successful! Please log in.")
            self.show_auth_ui()
        elif message.type == MessageType.GET_STATS_RESPONSE: # Update displayed player statistics
            if self.home_ui:
                self.home_ui.update_stats_ui(message.data)
        elif message.type == MessageType.ACCOUNT_DELETE_RESPONSE: # Account deletion confirmation
            if message.data.get('success'):
                self.show_auth_ui()
                messagebox.showinfo("Success", "Your account has been deleted")
                self.username = None
                self.current_game_id = None
        elif message.type == MessageType.MATCH_FOUND: # Start new game with assigned players
            self.start_game(
                message.data["black"], message.data["white"], message.data.get("game_id")
            )
            if hasattr(self, 'matching_room_ui') and self.matching_room_ui:
                self.matching_room_ui.handle_match_response(True, "")
        elif message.type == MessageType.GAME_STATE: # Update game board display
            if self.game_ui:
                self.game_ui.update_game_state(message.data["state"])
            if self.live_games_ui and self.live_games_ui.live_game_viewer_ui:
                self.live_games_ui.live_game_viewer_ui.update_game_state(message.data["state"])
        elif message.type == MessageType.GAME_OVER: # Show game result with delay for board update
            if self.game_ui:
                self.root.after(400, lambda: self.game_ui.show_game_over(
                    message.data["winner"], message.data["credits_change"]
                ))
        elif message.type == MessageType.GET_LIVE_GAMES_RESPONSE: # Update live games list
            self.live_games = message.data['live_games']
            if self.live_games_ui:
                self.live_games_ui.load_live_games(self.live_games)
        elif message.type == MessageType.GET_HISTORY_RESPONSE: # Update game history display
            self.histories = message.data["histories"]
            if self.history_ui:
                self.history_ui.load_history_from_server(message.data["histories"])
        elif message.type == MessageType.GET_LEADERBOARD_RESPONSE: # Update leaderboard display
            self.leaderboard = message.data['leaderboard']
            if self.leaderboard_ui:
                self.leaderboard_ui.load_leaderboard(self.leaderboard)
        elif message.type == MessageType.ERROR: # Show error messages (filter certain expected errors)
            if message.data.get("message") not in ["Game not found", "Invalid move"]:
                messagebox.showerror("Error", message.data.get("message", "Unknown error"))
        elif message.type == MessageType.MATCHING_ROOM_USERS: # Update matching room player list
            self.matching_room_users = message.data.get('users', [])
            if hasattr(self, 'matching_room_ui') and self.matching_room_ui:
                self.matching_room_ui.update_users_list(self.matching_room_users)
        elif message.type == MessageType.MATCH_REQUESTS_RESPONSE: # Update match requests list
            if hasattr(self, 'matching_room_ui') and self.matching_room_ui:
                self.matching_room_ui.update_requests_list(message.data.get('requests', []))
            return
        elif message.type == MessageType.MATCH_CANCEL: # Cancel match invitation
            if hasattr(self, 'matching_room_ui') and self.matching_room_ui:
                self.matching_room_ui._remove_invitation(message.data.get('request_id'))
            return
        elif message.type == MessageType.MATCH_DECLINED: # Match invitation is declined
            if hasattr(self, 'matching_room_ui') and self.matching_room_ui:
                self.matching_room_ui.handle_match_response(False, message.data['to'])
        
    def show_auth_ui(self):
        """Displays the authentication (login/signup) screen."""
        self._clear_current_ui()
        self.auth_ui = AuthUI(self.root, self)
        self.auth_ui.frame.pack()
        self.current_ui = self.auth_ui

    def show_home_ui(self):
        """Displays the main home screen with game options."""
        self._clear_current_ui()
        self.home_ui = HomeUI(self.root, self)
        self.home_ui.frame.pack()
        self.current_ui = self.home_ui
        self.root.geometry("700x450")
        if self.username:
            self.home_ui.start_polling()  # Start polling only after login

    def show_waiting_ui(self):
        """Displays the matchmaking waiting screen."""
        self._clear_current_ui()
        if not self.waiting_ui:
            self.waiting_ui = WaitingUI(self.root, self)
        self.waiting_ui.frame.pack()
        self.current_ui = self.waiting_ui
    
    def show_live_games_ui(self):
        """Displays the live games viewer screen."""
        self._clear_current_ui()
        self.live_games_ui = LiveGamesUI(self.root, self)
        self.live_games_ui.frame.pack()
        self.current_ui = self.live_games_ui

    def show_history_ui(self):
        """Displays the game history screen."""
        self._clear_current_ui()
        self.history_ui = HistoryUI(self.root, self)
        self.history_ui.frame.pack()
        self.current_ui = self.history_ui
    
    def show_leaderboard_ui(self):
        """Displays the leaderboard screen."""
        self._clear_current_ui()
        self.leaderboard_ui = LeaderboardUI(self.root, self)
        self.leaderboard_ui.frame.pack()
        self.current_ui = self.leaderboard_ui

    def show_matching_room_ui(self):
        """Displays the matching room screen and notifies server."""
        self._clear_current_ui()
        self.matching_room_ui = MatchingRoomUI(self.root, self)
        self.matching_room_ui.frame.pack()
        self.current_ui = self.matching_room_ui
        self.send_message(Message(
            MessageType.MATCHING_ROOM_JOIN,
            {'username': self.username}
        ))

    def start_game(self, black_player, white_player, game_id):
        """
        Starts a new game with the specified players and game ID.
        
        Args:
            black_player (str): Username of black stone player
            white_player (str): Username of white stone player
            game_id (str): Unique identifier for the game
        """
        self._clear_current_ui()
        self.current_game_id = game_id
        self.game_ui = GameUI(self.root, self, black_player, white_player)
        self.game_ui.frame.pack()
        self.current_ui = self.game_ui

    def _clear_current_ui(self):
        """Cleans up the currently displayed UI screen."""
        if self.current_ui:
            if isinstance(self.current_ui, HomeUI):
                self.current_ui.stop_polling()  # Stop polling if leaving home
            self.current_ui.frame.pack_forget()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Five in a Row")
    client = GameClient(root)
    root.mainloop()
