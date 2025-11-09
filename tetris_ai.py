"""
Tetris AI Module - SURVIVAL OPTIMIZED
Ultra-robust AI designed to never lose using defensive strategies.

Key Features:
1. SURVIVAL MODE - Automatic panic mode when board > 60% full
2. TWO-piece lookahead - Reliable and battle-tested
3. MASSIVE hole prevention - 14x penalty for holes (was 0.35)
4. Eleven advanced heuristics with survival-optimized weights
5. I-piece well management (ONLY when safe)
6. Adaptive strategy: Normal mode vs Panic mode
7. Line clearing simulation in lookahead

PANIC MODE TRIGGERS (board > 60% full):
- 10x hole penalty (no holes allowed!)
- 5x max height penalty (flatten urgently!)
- 15x pit penalty (avoid death traps!)
- Disables risky I-well strategy
- Prioritizes line clearing and height reduction

NORMAL MODE (board < 60% full):
- Balanced play with I-well management
- Smart I-piece placement for TETRIS
- Optimized for score while maintaining safety

This AI should survive indefinitely on most difficulty levels!
"""
from typing import List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tetris import TetrisGame, Tetromino


class TetrisAI:
    """AI player for Tetris using heuristic evaluation"""

    def __init__(self, game: 'TetrisGame') -> None:
        self.game: 'TetrisGame' = game

    def evaluate_board(self, board: List[List[str]], piece_type: Optional[str] = None) -> float:
        """Evaluate board state using multiple heuristics (higher is better)"""
        height_score = self._aggregate_height(board)
        holes_score = self._count_holes(board)
        bumpiness_score = self._calculate_bumpiness(board)
        lines_score = self._count_complete_lines(board)
        max_height_score = self._get_max_height(board)
        wells_score = self._count_wells(board)
        row_transitions_score = self._count_row_transitions(board)
        col_transitions_score = self._count_column_transitions(board)
        pit_score = self._count_pits(board)

        # NEW: I-piece well management heuristics (only when safe)
        board_height = len(board)
        max_height = self._get_max_height(board)
        is_dangerous = max_height > board_height * 0.6  # Board > 60% full

        # Only use I-well strategy when board is safe
        if not is_dangerous:
            well_quality_score = self._evaluate_well_quality(board)
            tetris_ready_score = self._evaluate_tetris_readiness(board, piece_type)
        else:
            # In danger mode, ignore I-well strategy
            well_quality_score = 0
            tetris_ready_score = 0

        # SURVIVAL MODE: If board is dangerous, heavily prioritize safety
        if is_dangerous:
            # PANIC MODE - extreme penalties for danger
            score = (
                -2.0 * height_score +            # Minimize height aggressively
                1.5 * lines_score +              # Clear lines urgently
                -10.0 * holes_score +            # NO HOLES ALLOWED in panic
                -1.0 * bumpiness_score +         # Keep flat
                -5.0 * max_height_score +        # Absolutely minimize max height
                -2.0 * wells_score +             # No deep wells
                -0.5 * row_transitions_score +
                -0.3 * col_transitions_score +
                -15.0 * pit_score                # Pits are deadly in panic mode
            )
        else:
            # NORMAL MODE - balanced play with I-well strategy
            score = (
                -0.8 * height_score +            # Keep height down (increased from 0.51)
                1.2 * lines_score +              # Reward line clears (increased from 0.76)
                -5.0 * holes_score +             # MASSIVELY penalize holes (was 0.35)
                -0.3 * bumpiness_score +         # Some bumpiness OK
                -1.5 * max_height_score +        # Keep max height low (was 0.5)
                -0.5 * wells_score +             # General wells OK
                -0.15 * row_transitions_score +
                -0.1 * col_transitions_score +
                -8.0 * pit_score +               # Pits very bad (was 0.65)
                0.3 * well_quality_score +       # I-well (reduced from 0.8)
                0.8 * tetris_ready_score         # TETRIS opportunity (reduced from 1.5)
            )

        return score

    def _get_max_height(self, board: List[List[str]]) -> float:
        """Get the maximum column height"""
        heights = self._get_column_heights(board)
        return float(max(heights)) if heights else 0.0

    def _get_column_heights(self, board: List[List[str]]) -> List[int]:
        """Get the height of each column"""
        heights: List[int] = []
        for col in range(len(board[0])):
            height = 0
            for row in range(len(board)):
                if board[row][col] != ' ':
                    height = len(board) - row
                    break
            heights.append(height)
        return heights

    def _aggregate_height(self, board: List[List[str]]) -> float:
        """Sum of all column heights"""
        heights = self._get_column_heights(board)
        return float(sum(heights))

    def _count_holes(self, board: List[List[str]]) -> float:
        """Count empty cells with filled cells above them"""
        holes = 0
        for col in range(len(board[0])):
            found_block = False
            for row in range(len(board)):
                if board[row][col] != ' ':
                    found_block = True
                elif found_block and board[row][col] == ' ':
                    holes += 1
        return float(holes)

    def _calculate_bumpiness(self, board: List[List[str]]) -> float:
        """Sum of absolute height differences between adjacent columns"""
        heights = self._get_column_heights(board)
        bumpiness = 0
        for i in range(len(heights) - 1):
            bumpiness += abs(heights[i] - heights[i + 1])
        return float(bumpiness)

    def _count_complete_lines(self, board: List[List[str]]) -> float:
        """Count number of complete lines"""
        complete_lines = 0
        for row in board:
            if all(cell != ' ' for cell in row):
                complete_lines += 1
        return float(complete_lines)

    def _count_wells(self, board: List[List[str]]) -> float:
        """Count wells (columns significantly lower than neighbors)"""
        heights = self._get_column_heights(board)
        wells = 0

        for i in range(len(heights)):
            left_height = heights[i - 1] if i > 0 else float('inf')
            right_height = heights[i + 1] if i < len(heights) - 1 else float('inf')
            current_height = heights[i]

            # A well is when both neighbors are higher
            if current_height < left_height and current_height < right_height:
                well_depth = min(left_height - current_height, right_height - current_height)
                wells += well_depth * well_depth  # Square to heavily penalize deep wells

        return float(wells)

    def _count_row_transitions(self, board: List[List[str]]) -> float:
        """Count transitions from filled to empty cells in rows"""
        transitions = 0
        for row in board:
            for i in range(len(row) - 1):
                if (row[i] == ' ') != (row[i + 1] == ' '):
                    transitions += 1
        return float(transitions)

    def _count_column_transitions(self, board: List[List[str]]) -> float:
        """Count transitions from filled to empty cells in columns"""
        transitions = 0
        for col in range(len(board[0])):
            for row in range(len(board) - 1):
                if (board[row][col] == ' ') != (board[row + 1][col] == ' '):
                    transitions += 1
        return float(transitions)

    def _count_pits(self, board: List[List[str]]) -> float:
        """Count pits (holes that are very hard to fill)"""
        pits = 0
        heights = self._get_column_heights(board)

        for col in range(len(board[0])):
            # Start from the top of this column
            top_row = len(board) - heights[col] if heights[col] > 0 else len(board)

            for row in range(top_row, len(board)):
                if board[row][col] == ' ':
                    # Check if this hole is surrounded (making it a pit)
                    left_blocked = col == 0 or board[row][col - 1] != ' '
                    right_blocked = col == len(board[0]) - 1 or board[row][col + 1] != ' '

                    # If blocked on both sides and has blocks above, it's a dangerous pit
                    if left_blocked and right_blocked:
                        # Count depth of blocks above this pit
                        blocks_above = 0
                        for r in range(row):
                            if board[r][col] != ' ':
                                blocks_above += 1
                        if blocks_above > 0:
                            pits += 1 + blocks_above  # Worse the deeper it is

        return float(pits)

    def _evaluate_well_quality(self, board: List[List[str]]) -> float:
        """Evaluate quality of I-piece well (higher is better)"""
        heights = self._get_column_heights(board)
        board_width = len(board[0])

        # Check left edge and right edge for potential wells
        best_well_score = 0.0

        # Prefer edge columns for wells (easier to maintain)
        for col in [0, board_width - 1]:
            well_height = heights[col]
            neighbor_col = 1 if col == 0 else board_width - 2
            neighbor_height = heights[neighbor_col]

            # Good well: column is 3-4 blocks lower than neighbor
            height_diff = neighbor_height - well_height

            if height_diff >= 3:
                # Reward wells that are the right depth (3-4 blocks)
                if 3 <= height_diff <= 4:
                    well_score = 10.0  # Perfect well depth
                elif height_diff > 4:
                    well_score = 5.0 - (height_diff - 4) * 0.5  # Too deep, slight penalty
                else:
                    well_score = height_diff * 2.0

                # Bonus if well is clean (no holes in the column)
                is_clean = True
                for row in range(len(board) - well_height, len(board)):
                    if board[row][col] != ' ':
                        is_clean = False
                        break

                if is_clean:
                    well_score *= 1.5

                best_well_score = max(best_well_score, well_score)

        return best_well_score

    def _evaluate_tetris_readiness(self, board: List[List[str]], piece_type: Optional[str]) -> float:
        """Evaluate if board is ready for a TETRIS (4-line clear) with I-piece"""
        if piece_type != 'I':
            return 0.0  # Only relevant when placing I-piece

        heights = self._get_column_heights(board)
        board_width = len(board[0])
        board_height = len(board)

        # Check for TETRIS opportunity
        # Look for 4 consecutive rows that are nearly complete except for one column

        max_tetris_score = 0.0

        for col in range(board_width):
            # Check if placing I-piece here would clear 4 lines
            potential_clears = 0

            # Find how high this column is
            col_height = heights[col]
            start_row = board_height - col_height - 4  # Check 4 rows above column top

            if start_row < 0:
                continue

            # Check if 4 rows would be complete if we fill this column
            for row_offset in range(4):
                row = start_row + row_offset
                if row < 0 or row >= board_height:
                    continue

                # Count filled cells in this row (excluding target column)
                filled = sum(1 for c in range(board_width) if c != col and board[row][c] != ' ')

                # If row would be complete with I-piece, count it
                if filled == board_width - 1 and board[row][col] == ' ':
                    potential_clears += 1

            # Reward based on number of lines that would clear
            if potential_clears == 4:
                max_tetris_score = 50.0  # HUGE reward for TETRIS!
            elif potential_clears == 3:
                max_tetris_score = max(max_tetris_score, 15.0)
            elif potential_clears == 2:
                max_tetris_score = max(max_tetris_score, 5.0)

        return max_tetris_score

    def get_best_move(self, use_lookahead: bool = True) -> Optional[Tuple[int, int]]:
        """Find the best position and rotation with 2-piece lookahead (reliable and fast)"""
        from tetris import Tetromino

        current_piece = self.game.current_piece

        if use_lookahead:
            # Use reliable 2-piece lookahead (simpler and more robust than beam search)
            return self._get_best_move_with_2piece_lookahead()
        else:
            # Simple evaluation without lookahead
            return self._get_best_move_simple(current_piece)

    def _get_best_move_with_2piece_lookahead(self) -> Optional[Tuple[int, int]]:
        """Reliable 2-piece lookahead - evaluates current + next piece"""
        from tetris import Tetromino

        current_piece = self.game.current_piece
        next_piece = self.game.next_piece

        best_overall_score = float('-inf')
        best_overall_move = None

        num_rotations = len(current_piece.shapes)

        # Try all placements of current piece
        for rotation in range(num_rotations):
            test_piece = Tetromino(current_piece.type)
            test_piece.rotation = rotation
            test_piece.shape = test_piece.shapes[rotation]
            test_piece.y = 0

            for x in range(-2, self.game.width + 2):
                test_piece.x = x

                if not self.game.valid_position(test_piece):
                    continue

                # Drop piece
                test_piece.y = 0
                while self.game.valid_position(test_piece, offset_y=1):
                    test_piece.y += 1

                if not self.game.valid_position(test_piece):
                    continue

                # Create test board after current piece
                test_board1 = [row[:] for row in self.game.board]
                for r, row in enumerate(test_piece.shape):
                    for c, val in enumerate(row):
                        if val:
                            y = test_piece.y + r
                            x_pos = test_piece.x + c
                            if 0 <= y < len(test_board1) and 0 <= x_pos < len(test_board1[0]):
                                test_board1[y][x_pos] = test_piece.color

                test_board1 = self._clear_lines_from_board(test_board1)

                # Evaluate current piece placement
                current_score = self.evaluate_board(test_board1, current_piece.type)

                # Now try all placements of next piece on this board
                best_next_score = float('-inf')
                num_rotations2 = len(next_piece.shapes)

                for rotation2 in range(num_rotations2):
                    test_piece2 = Tetromino(next_piece.type)
                    test_piece2.rotation = rotation2
                    test_piece2.shape = test_piece2.shapes[rotation2]
                    test_piece2.y = 0

                    for x2 in range(-2, len(test_board1[0]) + 2):
                        test_piece2.x = x2

                        if not self._is_valid_on_board(test_piece2, test_board1):
                            continue

                        test_piece2.y = 0
                        while self._is_valid_on_board(test_piece2, test_board1, offset_y=1):
                            test_piece2.y += 1

                        if not self._is_valid_on_board(test_piece2, test_board1):
                            continue

                        # Create test board after next piece
                        test_board2 = [row[:] for row in test_board1]
                        for r, row in enumerate(test_piece2.shape):
                            for c, val in enumerate(row):
                                if val:
                                    y = test_piece2.y + r
                                    x_pos = test_piece2.x + c
                                    if 0 <= y < len(test_board2) and 0 <= x_pos < len(test_board2[0]):
                                        test_board2[y][x_pos] = test_piece2.color

                        test_board2 = self._clear_lines_from_board(test_board2)
                        next_score = self.evaluate_board(test_board2, next_piece.type)

                        best_next_score = max(best_next_score, next_score)

                # Combine current and next scores
                if best_next_score == float('-inf'):
                    combined_score = current_score
                else:
                    combined_score = 0.6 * current_score + 0.4 * best_next_score

                if combined_score > best_overall_score:
                    best_overall_score = combined_score
                    best_overall_move = (rotation, x)

        return best_overall_move

    def _get_best_move_simple(self, piece: 'Tetromino') -> Optional[Tuple[int, int]]:
        """Get best move for a single piece without lookahead"""
        from tetris import Tetromino

        best_score: float = float('-inf')
        best_move: Optional[Tuple[int, int]] = None

        num_rotations = len(piece.shapes)

        for rotation in range(num_rotations):
            test_piece = Tetromino(piece.type)
            test_piece.rotation = rotation
            test_piece.shape = test_piece.shapes[rotation]
            test_piece.y = 0

            for x in range(-2, self.game.width + 2):
                test_piece.x = x

                if not self.game.valid_position(test_piece):
                    continue

                # Drop piece
                test_piece.y = 0
                while self.game.valid_position(test_piece, offset_y=1):
                    test_piece.y += 1

                if not self.game.valid_position(test_piece):
                    continue

                # Create test board
                test_board = [row[:] for row in self.game.board]
                for r, row in enumerate(test_piece.shape):
                    for c, val in enumerate(row):
                        if val:
                            y = test_piece.y + r
                            x_pos = test_piece.x + c
                            if 0 <= y < len(test_board) and 0 <= x_pos < len(test_board[0]):
                                test_board[y][x_pos] = test_piece.color

                test_board = self._clear_lines_from_board(test_board)
                score = self.evaluate_board(test_board, piece.type)

                if score > best_score:
                    best_score = score
                    best_move = (rotation, x)

        return best_move

    def _clear_lines_from_board(self, board: List[List[str]]) -> List[List[str]]:
        """Remove complete lines from a board and return new board"""
        new_board = [row[:] for row in board if not all(cell != ' ' for cell in row)]
        # Add empty lines at top for each cleared line
        lines_cleared = len(board) - len(new_board)
        for _ in range(lines_cleared):
            new_board.insert(0, [' ' for _ in range(len(board[0]))])
        return new_board

    def _is_valid_on_board(self, piece: 'Tetromino', board: List[List[str]],
                           offset_x: int = 0, offset_y: int = 0) -> bool:
        """Check if piece position is valid on a given board"""
        for r, row in enumerate(piece.shape):
            for c, val in enumerate(row):
                if val:
                    new_y = piece.y + r + offset_y
                    new_x = piece.x + c + offset_x

                    if new_x < 0 or new_x >= len(board[0]) or new_y >= len(board):
                        return False

                    if new_y >= 0 and board[new_y][new_x] != ' ':
                        return False
        return True

    def execute_move(self, move: Optional[Tuple[int, int]]) -> None:
        """Execute the AI's chosen move - position piece and drop it fast"""
        if move is None:
            return

        rotation, target_x = move
        current_piece = self.game.current_piece

        # Rotate to target rotation
        while current_piece.rotation != rotation:
            self.game.rotate()

        # Move to target x position
        while current_piece.x < target_x and self.game.valid_position(current_piece, offset_x=1):
            current_piece.x += 1

        while current_piece.x > target_x and self.game.valid_position(current_piece, offset_x=-1):
            current_piece.x -= 1

        # Use soft drop speed for fast but visible descent
        # Set fall speed to nearly instant for this piece
        self.game.fall_speed = 0.005  # Super fast drop after positioning
        self.game.last_fall_time = 0  # Make it drop immediately
