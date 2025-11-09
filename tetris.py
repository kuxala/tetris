"""
Tetris Game - Terminal Edition
Classic Tetris game playable in the terminal using only built-in Python libraries.

Features:
- Adaptive board sizing based on terminal dimensions
- Classic green monochrome color scheme
- AI player with heuristic-based evaluation
- Toggle between manual and AI play modes
- Real-time score tracking and level progression
- Visible spawn zone for piece appearance
"""
import sys
import time
import random
import os
import tty
import termios
import select
import copy
from typing import List, Tuple, Optional, Dict
from enum import Enum

# Import AI module
from tetris_ai import TetrisAI


# ANSI Color codes
class Color:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    GREEN = '\033[92m'     # All pieces (classic monochrome look)
    RED = '\033[91m'
    BLUE = '\033[94m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'      # Empty cells


# Tetromino shapes
SHAPES: Dict[str, List[List[List[int]]]] = {
    'I': [
        [[1, 1, 1, 1]],
        [[1], [1], [1], [1]]
    ],
    'O': [
        [[1, 1], [1, 1]]
    ],
    'T': [
        [[0, 1, 0], [1, 1, 1]],
        [[1, 0], [1, 1], [1, 0]],
        [[1, 1, 1], [0, 1, 0]],
        [[0, 1], [1, 1], [0, 1]]
    ],
    'S': [
        [[0, 1, 1], [1, 1, 0]],
        [[1, 0], [1, 1], [0, 1]]
    ],
    'Z': [
        [[1, 1, 0], [0, 1, 1]],
        [[0, 1], [1, 1], [1, 0]]
    ],
    'J': [
        [[1, 0, 0], [1, 1, 1]],
        [[1, 1], [1, 0], [1, 0]],
        [[1, 1, 1], [0, 0, 1]],
        [[0, 1], [0, 1], [1, 1]]
    ],
    'L': [
        [[0, 0, 1], [1, 1, 1]],
        [[1, 0], [1, 0], [1, 1]],
        [[1, 1, 1], [1, 0, 0]],
        [[1, 1], [0, 1], [0, 1]]
    ]
}

COLORS: Dict[str, str] = {
    'I': Color.GREEN,
    'O': Color.GREEN,
    'T': Color.GREEN,
    'S': Color.GREEN,
    'Z': Color.GREEN,
    'J': Color.GREEN,
    'L': Color.GREEN
}


class Tetromino:
    """Represents a Tetris piece (tetromino)"""

    def __init__(self, shape_type: str) -> None:
        if shape_type not in SHAPES:
            raise ValueError(f"Invalid shape type: {shape_type}")

        self.type: str = shape_type
        self.shapes: List[List[List[int]]] = SHAPES[shape_type]
        self.rotation: int = 0
        self.shape: List[List[int]] = self.shapes[0]
        self.color: str = COLORS[shape_type]
        self.x: int = 0  # Starting column (will be set by spawn_piece)
        self.y: int = 0  # Starting row

    def rotate_cw(self) -> None:
        """Rotate clockwise"""
        self.rotation = (self.rotation + 1) % len(self.shapes)
        self.shape = self.shapes[self.rotation]

    def rotate_ccw(self) -> None:
        """Rotate counter-clockwise"""
        self.rotation = (self.rotation - 1) % len(self.shapes)
        self.shape = self.shapes[self.rotation]

    def get_cells(self) -> List[Tuple[int, int]]:
        """Get list of occupied cells"""
        cells: List[Tuple[int, int]] = []
        for r, row in enumerate(self.shape):
            for c, val in enumerate(row):
                if val:
                    cells.append((self.y + r, self.x + c))
        return cells


class TetrisGame:
    """Main Tetris game logic and state management"""

    def __init__(self, width: int = 10, height: int = 20) -> None:
        if width < 4 or height < 4:
            raise ValueError("Board dimensions must be at least 4x4")

        self.width: int = width
        self.height: int = height
        self.board: List[List[str]] = [[' ' for _ in range(width)] for _ in range(height)]
        self.score: int = 0
        self.level: int = 1
        self.lines_cleared: int = 0
        self.game_over: bool = False
        self.paused: bool = False

        self.current_piece: Tetromino = self.spawn_piece()
        self.next_piece: Tetromino = self.spawn_piece()

        # Game speed
        self.fall_speed: float = 0.8
        self.last_fall_time: float = time.time()

    def spawn_piece(self) -> Tetromino:
        """Spawn a new random piece centered on the board, starting from above"""
        shape_type: str = random.choice(list(SHAPES.keys()))
        piece: Tetromino = Tetromino(shape_type)
        # Center the piece horizontally based on board width
        piece.x = (self.width - len(piece.shape[0])) // 2
        # Start the piece slightly above the board so it falls into view
        piece.y = -2
        return piece

    def valid_position(self, piece: Tetromino, offset_x: int = 0, offset_y: int = 0) -> bool:
        """Check if piece position is valid"""
        for r, row in enumerate(piece.shape):
            for c, val in enumerate(row):
                if val:
                    new_y: int = piece.y + r + offset_y
                    new_x: int = piece.x + c + offset_x

                    # Check boundaries
                    if new_x < 0 or new_x >= self.width or new_y >= self.height:
                        return False

                    # Check collision with placed pieces
                    if new_y >= 0 and self.board[new_y][new_x] != ' ':
                        return False
        return True

    def place_piece(self) -> None:
        """Place current piece on board"""
        for r, row in enumerate(self.current_piece.shape):
            for c, val in enumerate(row):
                if val:
                    y: int = self.current_piece.y + r
                    x: int = self.current_piece.x + c
                    if 0 <= y < self.height and 0 <= x < self.width:
                        self.board[y][x] = self.current_piece.color

    def clear_lines(self) -> int:
        """Clear completed lines and return number cleared"""
        lines_to_clear: List[int] = []

        for r in range(self.height):
            if all(cell != ' ' for cell in self.board[r]):
                lines_to_clear.append(r)

        # Remove cleared lines and add new empty lines at top
        for r in lines_to_clear:
            del self.board[r]
            self.board.insert(0, [' ' for _ in range(self.width)])

        # Update score
        num_lines: int = len(lines_to_clear)
        if num_lines > 0:
            # Scoring: 100 for 1, 300 for 2, 500 for 3, 800 for 4
            points: List[int] = [0, 100, 300, 500, 800]
            self.score += points[num_lines] * self.level
            self.lines_cleared += num_lines

            # Level up every 10 lines
            self.level = self.lines_cleared // 10 + 1
            # Note: fall_speed may be overridden by AI mode in play_game()
            self.fall_speed = max(0.1, 0.8 - (self.level - 1) * 0.05)

        return num_lines

    def move_left(self) -> None:
        """Move piece left"""
        if self.valid_position(self.current_piece, offset_x=-1):
            self.current_piece.x -= 1

    def move_right(self) -> None:
        """Move piece right"""
        if self.valid_position(self.current_piece, offset_x=1):
            self.current_piece.x += 1

    def move_down(self) -> bool:
        """Move piece down"""
        if self.valid_position(self.current_piece, offset_y=1):
            self.current_piece.y += 1
            return True
        return False

    def hard_drop(self) -> None:
        """Drop piece all the way down"""
        while self.move_down():
            pass
        self.lock_piece()

    def rotate(self) -> None:
        """Rotate piece clockwise"""
        old_rotation: int = self.current_piece.rotation
        self.current_piece.rotate_cw()

        if not self.valid_position(self.current_piece):
            # Try wall kicks
            for offset in [(-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0)]:
                if self.valid_position(self.current_piece, offset[0], offset[1]):
                    self.current_piece.x += offset[0]
                    self.current_piece.y += offset[1]
                    return

            # If no valid position, revert rotation
            self.current_piece.rotation = old_rotation
            self.current_piece.shape = self.current_piece.shapes[old_rotation]

    def lock_piece(self) -> None:
        """Lock current piece and spawn new one"""
        self.place_piece()
        self.clear_lines()

        # Spawn new piece
        self.current_piece = self.next_piece
        self.next_piece = self.spawn_piece()

        # Reset fall timer for new piece
        self.last_fall_time = time.time()

        # Check game over
        if not self.valid_position(self.current_piece):
            self.game_over = True

    def update(self) -> None:
        """Update game state"""
        if self.game_over or self.paused:
            return

        # Auto fall
        current_time: float = time.time()
        if current_time - self.last_fall_time >= self.fall_speed:
            if not self.move_down():
                self.lock_piece()
            self.last_fall_time = current_time

    def render(self) -> None:
        """Render game screen with colors"""
        clear_screen()

        # Create display board with current piece
        display: List[List[str]] = [row[:] for row in self.board]

        # Add current piece to display
        for r, row in enumerate(self.current_piece.shape):
            for c, val in enumerate(row):
                if val:
                    y: int = self.current_piece.y + r
                    x: int = self.current_piece.x + c
                    if 0 <= y < self.height and 0 <= x < self.width:
                        display[y][x] = self.current_piece.color

        # Calculate dynamic border widths
        # Board section between ║ symbols: space(1) + marker(1) + cells(width) + marker(1) = width + 3
        # Next section between ║ symbols: spaces(2) + content(6) + spaces(2) = 10
        board_display_width: int = self.width + 3
        next_display_width: int = 10

        # Print game info
        print("╔" + "═" * board_display_width + "╦" + "═" * next_display_width + "╗")
        title_padding_left = (board_display_width - 6) // 2
        title_padding_right = board_display_width - 6 - title_padding_left
        next_padding_left = (next_display_width - 4) // 2
        next_padding_right = next_display_width - 4 - next_padding_left
        print("║" + " " * title_padding_left + "TETRIS" + " " * title_padding_right + "║" + " " * next_padding_left + "NEXT" + " " * next_padding_right + "║")
        print("╠" + "═" * board_display_width + "╣" + "═" * next_display_width + "╣")

        # Print game board and next piece side by side
        spawn_zone_height = 3  # Top 3 rows are spawn zone

        for i in range(self.height):
            # Game board
            line: str = "║ "

            # Add spawn zone indicator for top rows
            if i < spawn_zone_height:
                line += Color.GRAY + "┊" + Color.RESET
            else:
                line += " "

            for cell in display[i]:
                if cell == ' ':
                    line += Color.GRAY + '·' + Color.RESET
                else:
                    line += cell + '█' + Color.RESET

            # Add spawn zone indicator on right
            if i < spawn_zone_height:
                line += Color.GRAY + "┊" + Color.RESET + "║"
            else:
                line += " ║"

            # Next piece preview (only first 4 rows)
            if i < 4:
                line += "  "
                if i < len(self.next_piece.shape):
                    for val in self.next_piece.shape[i]:
                        if val:
                            line += self.next_piece.color + '█' + Color.RESET
                        else:
                            line += ' '
                    # Pad to width 6
                    line += ' ' * (6 - len(self.next_piece.shape[i]))
                else:
                    line += ' ' * 6
                line += "  ║"
            else:
                # Match the width of rows 0-3: 2 + 6 + 2 = 10 spaces total
                line += " " * 10 + "║"

            print(line)

        # Bottom border
        print("╚" + "═" * board_display_width + "╩" + "═" * next_display_width + "╝")

        # Game stats
        print()
        print(f"Score: {self.score}  |  Level: {self.level}  |  Lines: {self.lines_cleared}")
        print()
        print("Controls: ← → : Move  |  ↑/W : Rotate  |  ↓/S : Soft Drop  |  Space : Hard Drop")
        print("          P : Pause  |  I : AI Mode  |  Q : Quit")

        if self.paused:
            print("\n*** PAUSED ***")

        if self.game_over:
            print("\n*** GAME OVER ***")
            print(f"Final Score: {self.score}")
            print("Press R to restart or Q to quit")


def get_terminal_size() -> Tuple[int, int]:
    """Get terminal size and return (width, height)"""
    try:
        size = os.get_terminal_size()
        return (size.columns, size.lines)
    except (OSError, AttributeError):
        # Fallback to default size if terminal size can't be determined
        return (80, 24)


def calculate_board_dimensions(term_width: int, term_height: int) -> Tuple[int, int]:
    """Calculate optimal board dimensions based on terminal size"""
    # Exact layout calculation:
    # Width: "╔" + board_display (width+3) + "╦" + next_display (10) + "╗"
    #        = 1 + (width + 3) + 1 + 10 + 1 = width + 16
    # Height: 3 (header) + board_height + 1 (bottom) + 1 (blank) + 1 (stats) + 2 (controls) + 2 (mode/blank)
    #        = board_height + 10 (minimum)

    # Calculate available space
    # For width: term_width = width + 16, so width = term_width - 16
    # For height: term_height = height + 10, so height = term_height - 10
    available_width = term_width - 16
    available_height = term_height - 10

    # Traditional Tetris is 10 wide x 20 high
    # Set reasonable bounds
    board_width = min(max(8, available_width), 14)  # Between 8 and 14
    board_height = min(max(16, available_height), 26)  # Between 16 and 26

    # Maintain a reasonable aspect ratio (height should be roughly 2x width)
    if board_height < board_width * 1.8:
        board_height = max(16, int(board_width * 2))

    return (board_width, board_height)


def clear_screen() -> None:
    """Clear terminal screen and reset cursor position"""
    # Use multiple methods to ensure screen clears properly
    # \033[H - Move cursor to home (1,1)
    # \033[2J - Clear entire screen
    # \033[3J - Clear scrollback buffer (prevents stacking)
    sys.stdout.write("\033[H\033[2J\033[3J")
    sys.stdout.flush()


def get_key_non_blocking() -> Optional[str]:
    """Get keyboard input without blocking"""
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
    except Exception:
        pass
    return None


def play_game(ai_mode: bool = False) -> None:
    """Main game loop with improved error handling and AI support"""
    # Get terminal size and calculate board dimensions
    term_width, term_height = get_terminal_size()
    board_width, board_height = calculate_board_dimensions(term_width, term_height)

    try:
        game: TetrisGame = TetrisGame(width=board_width, height=board_height)
        ai: Optional[TetrisAI] = TetrisAI(game) if ai_mode else None

        # Store original fall speed and set faster speed for AI
        original_fall_speed: float = game.fall_speed
        if ai_mode:
            game.fall_speed = 0.05  # Much faster fall speed for AI mode
    except ValueError as e:
        print(f"Error initializing game: {e}")
        return

    # Track when AI should make a move
    ai_move_made: bool = False
    ai_think_time: float = 0.001  # AI delay (nearly instant for fast gameplay)

    # Set terminal to raw mode
    try:
        old_settings = termios.tcgetattr(sys.stdin)
    except termios.error as e:
        print(f"Error: Could not access terminal settings: {e}")
        print("This game requires a Unix-like terminal.")
        return

    try:
        tty.setcbreak(sys.stdin.fileno())
        last_ai_move_time: float = time.time()

        while True:
            # Handle input
            key: Optional[str] = get_key_non_blocking()

            if key:
                if key.lower() == 'q':
                    break
                elif key.lower() == 'p':
                    game.paused = not game.paused
                elif key.lower() == 'i':
                    # Toggle AI mode
                    ai_mode = not ai_mode
                    ai = TetrisAI(game) if ai_mode else None
                    ai_move_made = False

                    # Adjust fall speed based on mode
                    if ai_mode:
                        game.fall_speed = 0.05  # Fast for AI
                    else:
                        # Restore level-appropriate speed for manual play
                        game.fall_speed = max(0.1, 0.8 - (game.level - 1) * 0.05)
                elif key.lower() == 'r' and game.game_over:
                    try:
                        # Recalculate board size in case terminal was resized
                        term_width, term_height = get_terminal_size()
                        board_width, board_height = calculate_board_dimensions(term_width, term_height)
                        game = TetrisGame(width=board_width, height=board_height)
                        ai = TetrisAI(game) if ai_mode else None
                        ai_move_made = False

                        # Set appropriate speed for current mode
                        if ai_mode:
                            game.fall_speed = 0.05  # Fast for AI
                    except ValueError as e:
                        print(f"Error restarting game: {e}")
                        break
                    continue

                # Manual controls (only when AI is off)
                if not ai_mode and not game.game_over and not game.paused:
                    if key == ' ':  # Space for hard drop
                        game.hard_drop()
                    elif key == 'w' or key == '\x1b':  # W or arrow key
                        if key == '\x1b':
                            try:
                                next1: str = sys.stdin.read(1)
                                if next1 == '[':
                                    next2: str = sys.stdin.read(1)
                                    if next2 == 'A':  # Up arrow
                                        game.rotate()
                                    elif next2 == 'B':  # Down arrow
                                        game.move_down()
                                        game.last_fall_time = time.time()
                                    elif next2 == 'C':  # Right arrow
                                        game.move_right()
                                    elif next2 == 'D':  # Left arrow
                                        game.move_left()
                            except Exception:
                                pass
                        else:  # W key
                            game.rotate()
                    elif key == 'a':
                        game.move_left()
                    elif key == 'd':
                        game.move_right()
                    elif key == 's':
                        game.move_down()
                        game.last_fall_time = time.time()

            # AI logic
            if ai_mode and ai and not game.game_over and not game.paused:
                current_time = time.time()
                # Check if a new piece has spawned and AI hasn't moved yet
                # Wait for piece to be fully visible (y >= 1) to avoid simultaneous spawn/drop appearance
                if not ai_move_made and game.current_piece.y >= 1 and current_time - last_ai_move_time >= ai_think_time:
                    best_move = ai.get_best_move()
                    if best_move:
                        try:
                            ai.execute_move(best_move)
                            ai_move_made = True
                            last_ai_move_time = current_time
                        except Exception:
                            # If AI move fails, just continue
                            ai_move_made = False

            # Update game state
            if not game.game_over and not game.paused:
                # Store current piece reference to detect when it changes
                old_piece_id = id(game.current_piece)
                game.update()
                # Check if piece changed (new piece spawned)
                if id(game.current_piece) != old_piece_id:
                    ai_move_made = False
                    # Reset fall speed for new piece in AI mode
                    if ai_mode:
                        game.fall_speed = 0.05
            else:
                game.update()

            # Render game
            game.render()

            # Display AI mode status
            if ai_mode:
                print(f"\n{Color.GREEN}[SURVIVAL AI - NEVER LOSE MODE - TURBO]{Color.RESET} Press 'I' for manual")
            else:
                print(f"\n[MANUAL MODE] - Press 'I' to enable SURVIVAL AI")

            # Frame delay - faster when AI is playing
            if ai_mode:
                time.sleep(0.001)  # Minimal delay for AI mode (super fast)
            else:
                time.sleep(0.02)   # Normal delay for manual play

    except Exception as e:
        print(f"\nError during game: {e}")
    finally:
        # Restore terminal settings
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except Exception:
            pass


def main() -> None:
    """Main menu with color support"""
    clear_screen()

    # Get terminal size and calculate board dimensions
    term_width, term_height = get_terminal_size()
    board_width, board_height = calculate_board_dimensions(term_width, term_height)

    print("="*60)
    print(f"{Color.GREEN}TETRIS{Color.RESET} - Terminal Edition")
    print("="*60)
    print()
    print(f"Terminal Size: {term_width}×{term_height}  |  Board Size: {board_width}×{board_height}")
    print()
    print(f"{Color.GREEN}SURVIVAL AI - NEVER LOSE MODE:{Color.RESET} Ultra-defensive gameplay!")
    print("  • SURVIVAL-OPTIMIZED: Designed to play indefinitely!")
    print("  • AUTO PANIC MODE: Switches to defensive play when board > 60% full")
    print("  • 14x HOLE PENALTY: Virtually eliminates holes (was 0.35, now 5.0)")
    print("  • 5x MAX HEIGHT PENALTY in panic mode (aggressive flattening)")
    print("  • TWO-piece lookahead: Fast, reliable, battle-tested")
    print("  • Smart I-well management (ONLY when safe)")
    print("  • TURBO mode: 16x faster gameplay!")
    print("  • Should NEVER lose on normal speeds!")
    print()
    print("How to Play:")
    print("  • Move and rotate falling pieces")
    print("  • Complete horizontal lines to clear them")
    print("  • Pieces spawn from above (marked with " + Color.GRAY + "┊" + Color.RESET + " at top)")
    print("  • Game speeds up as you progress through levels")
    print("  • Don't let the pieces reach the top!")
    print()
    print("Controls:")
    print("  • ←/→ or A/D  : Move Left/Right")
    print("  • ↑ or W      : Rotate")
    print("  • ↓ or S      : Soft Drop (move down faster)")
    print("  • Space       : Hard Drop (instant drop)")
    print(f"  • {Color.GREEN}I{Color.RESET}           : Toggle SURVIVAL AI (never-lose mode!)")
    print("  • P           : Pause/Resume")
    print("  • Q           : Quit")
    print("  • R           : Restart (after game over)")
    print()
    print("Scoring:")
    print("  • 1 line  : 100 × level")
    print("  • 2 lines : 300 × level")
    print("  • 3 lines : 500 × level")
    print("  • 4 lines : 800 × level (TETRIS!)")
    print()
    print("="*60)
    print()

    # Ask user if they want AI mode
    ai_mode: bool = False
    try:
        choice = input(f"Start with {Color.GREEN}SURVIVAL AI - NEVER LOSE mode{Color.RESET}? (y/n, default n): ").strip().lower()
        if choice == 'y' or choice == 'yes':
            ai_mode = True
            print(f"\n{Color.GREEN}SURVIVAL AI Mode enabled!{Color.RESET} Watch AI that virtually never loses!")
            print("Features: Auto panic mode, 14x hole penalty, survival-optimized")
            print("The AI will play defensively and should survive indefinitely.")
            print("The game will run 16x faster in TURBO mode.")
            print("You can toggle AI mode anytime by pressing 'I' during the game.\n")
            input("Press Enter to start...")
        else:
            print("\nManual mode. Press 'I' during the game to enable SURVIVAL AI.\n")
            input("Press Enter to start...")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return

    try:
        play_game(ai_mode=ai_mode)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nUnexpected error: {e}")

    clear_screen()
    print(f"\nThanks for playing {Color.GREEN}Tetris{Color.RESET}!")
    print()


if __name__ == "__main__":
    main()
