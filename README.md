# Terminal Tetris

Classic Tetris game playable in your terminal with an advanced AI player that can play indefinitely without losing.

## Features

### Game
- **Pure Python** - Uses only standard library, no dependencies required
- **Monochrome Green** - Authentic retro GameBoy aesthetic
- **Adaptive Board** - Automatically sizes to fit your terminal
- **Spawn Zone** - Visible markers showing where pieces appear
- **Scoring System** - 100/300/500/800 points for 1/2/3/4 lines
- **Progressive Levels** - Game speeds up every 10 lines cleared

### AI Mode
- **Survival Algorithm** - Designed to play indefinitely without losing
- **Two-Piece Lookahead** - Plans ahead for current and next piece
- **Heuristic Evaluation** - Uses 11 different metrics to evaluate board states
- **Dual-Mode Strategy**:
  - **Normal Mode** - Balanced play with I-well management for 4-line clears
  - **Panic Mode** - Activates when board > 60% full, extreme defensive play
- **Smart Penalties** - 14x stronger hole prevention, massive pit avoidance
- **Turbo Speed** - Runs 16x faster than manual play
- **Real-time Toggle** - Press **I** anytime to switch between manual/AI

## Installation & Usage

```bash
# Clone or download the repository
git clone https://github.com/yourusername/tetris.git
cd tetris

# Run the game
python tetris.py

# Start with AI enabled from menu, or press 'I' during gameplay
```

**Requirements:**
- Python 3.6 or higher
- Unix-like terminal (Linux, macOS, or WSL on Windows)
- Terminal with ANSI color support

## Controls

| Key | Action |
|-----|--------|
| `←` `→` or `A` `D` | Move left/right |
| `↑` or `W` | Rotate piece |
| `↓` or `S` | Soft drop |
| `Space` | Hard drop (instant) |
| `I` | Toggle AI mode |
| `P` | Pause/Resume |
| `Q` | Quit |
| `R` | Restart after game over |

## Technical Details

### Architecture
```
tetris.py       - Main game engine, rendering, input handling
tetris_ai.py    - AI player with heuristic evaluation system
```

### AI Algorithm

The AI evaluates board positions using these heuristics:
- Aggregate height (sum of all column heights)
- Hole count (empty cells with blocks above)
- Surface bumpiness (height differences between adjacent columns)
- Complete lines (rewards clearing lines)
- Maximum height (keeps stack low)
- Wells (columns lower than neighbors)
- Row/column transitions
- Pits (dangerous hard-to-fill holes)
- I-piece well quality (maintains edge column for 4-line clears)
- TETRIS readiness (detects 4-line clear opportunities)

**Weight Adjustments:**
- Normal: -5.0 hole penalty, -1.5 max height
- Panic: -10.0 hole penalty, -5.0 max height, -15.0 pit penalty

### Implementation
- **Rendering**: ANSI escape codes for colors and screen control
- **Input**: Raw terminal mode using `tty` and `termios` modules
- **Type Safety**: Full type annotations throughout codebase
- **Board Simulation**: Deep copy for lookahead without affecting game state

## How It Works

1. Piece spawns at top (y=-2, invisible)
2. Falls naturally into view
3. AI waits until piece is visible (y≥1)
4. AI calculates best position using two-piece lookahead
5. Positions and rotates piece horizontally
6. Piece drops rapidly (0.005s per row)
7. Locks at bottom, clears lines, spawns next piece
8. Cycle repeats indefinitely

## License

MIT License - Free to use, modify, and distribute.
