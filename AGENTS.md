# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build Commands

```bash
# Run game
python main.py

# Build with Nuitka (use build.py wrapper, not nuitka directly)
python build.py --clean                    # Standard build
python build.py --clean --onefile          # Single file
python build.py --clean --onefile --disable-console  # Windows GUI

# Run tests (pytest not required - tests are standalone)
python test_comprehensive.py
python test_ubuntu_fonts.py
```

## Code Style

- **Indent**: 4 spaces (no tabs)
- **Line length**: 100 characters
- **No comments** unless explaining "why" (not "what")
- **No emojis** in code

### Naming
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: leading underscore `_update_state()`

### Import Order
```python
# 1. Standard library
import json
import math
from typing import Dict, List, Optional

# 2. Third-party
import pygame
import pygame_menu

# 3. Local modules (absolute imports)
from constants import SCREEN_WIDTH, FPS
from player import Player
```

### Type Hints
- Use `Optional[T]` instead of `Union[T, None]`
- Use `List[T]`, `Dict[K, V]` from typing

### Error Handling
- Use specific exceptions (no bare `except:`)
- Handle network errors gracefully (UDP is unreliable)

## Project-Specific Patterns

### Configuration System
All game config is in `settings.json`, loaded via `config.py`:
```python
from config import Settings
settings = Settings()
value = settings.get("game.player_speed", default=300)
```

`constants.py` re-exports all config for backward compatibility:
```python
from constants import PLAYER_SPEED, FPS  # Actually from settings.json
```

### AI System Selection
Backend priority is controlled by `settings.json` → `ai.use_rl_ai` / `ai.use_enhanced_ai`:
```python
# ai_factory.make_ai_player() picks the backend
# 1. ai.use_rl_ai: rl_ai.RLAIPlayer (numpy PPO policy, assets/rl_ai_policy.npz)
# 2. ai.use_enhanced_ai: ai_player_enhanced.EnhancedAIPlayer (behavior tree)
# 3. fallback: ai_player.AIPlayer
```
`ai.rl_fallback` controls whether a missing/broken policy falls back to the behavior tree.
Re-export a trained policy with `python -m rl.export_policy --model <ppo.zip> --out assets/rl_ai_policy.npz`.

### File Organization
- One class per file for major classes (Player, Game, NetworkManager)
- Utilities in `utils.py`
- Constants re-exported from `config.py`
- Avoid circular imports (use lazy imports if needed)

### Key Files
- `main.py`: Game loop, menu system, server scanning (3000+ lines)
- `player.py`: Player movement, shooting, health
- `network.py`: UDP communication, state sync
- `ai_player_enhanced.py`: Behavior tree AI
- `rl_ai.py`: Neural-network AI (numpy inference + 47-dim observation encoder)
- `ai_factory.py`: AI backend selection (RL / behavior tree / basic)
- `rl/`: RL training pipeline (collect / BC / PPO / SAC / evaluate / export)
- `team.py`: Team management system
- `map.py`: Room-based map generation, hinged doors (oriented-box collision)
- `camera.py`: World-to-screen transform with camera rotation
- `game_commands.py`: In-game command system

## In-Game Commands

All commands start with `.` (configured in `settings.json`):

| Command | Description |
|---------|-------------|
| `.kill` | Suicide |
| `.list` | List online players |
| `.addai [difficulty]` | Add AI player (server only) |
| `.team add [name]` | Create team |
| `.team join <id>` | Join team |
| `.help` | Show help |

## Critical Gotchas

1. **Font Issue on Linux**: Install `fonts-noto-cjk` for Chinese text rendering
2. **Port 5555**: Check firewall if multiplayer fails (configurable in `settings.json`)
3. **Build Dependencies**: `pip install --upgrade nuitka ordered-set` if build fails
4. **Settings Priority**: `settings.json` > `config.py` defaults > hardcoded fallbacks
5. **UDP Network**: All network code must handle packet loss gracefully
