"""Runtime budgets: update here when engine limits change."""
UNITS = 6.5
MAX_PARTS = 128
MAX_CHUNKS = 4096
MAX_LINES = 64   # engine SCRIPT_MESH_LINES is 64 since the mission engine packet
MAX_INDICES = 65535
MAX_VERTICES = 65535
MAX_NAME = 48
ASSET_MEMORY_BUDGET = 64 * 1024 * 1024
ASSET_MEMORY_WARNING = 0.8
ENEMY_KINDS = frozenset(('goomba', 'koopa', 'redead', 'like_like', 'octorok', 'polar_bear', 'topi'))
MAX_ENEMIES = 64
MAX_WAVE_ENEMIES = 32
MAX_WAVES = 8
MAX_CHECKPOINTS = 16
MAX_TRIGGERS = 16
MAX_ZONE = 2000
WORLD_LIMIT = 50000
