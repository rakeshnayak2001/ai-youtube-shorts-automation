// Single source of truth for what the story scenes can use.
// scripts/generate.py parses this file directly, so new entries are offered to Claude automatically.
export const SETTINGS = [
  'cave', 'forest', 'campfire', 'village', 'city', 'desert', 'river',
  'mountains', 'field', 'ocean', 'room', 'office', 'market', 'space',
] as const;

export const TIMES = ['day', 'dusk', 'night'] as const;

export const POSES = [
  'stand', 'walk', 'run', 'point', 'wave', 'think', 'scared', 'cheer',
  'sit', 'crouch', 'sad', 'hold', 'look_up', 'shrug',
] as const;

export const MOODS = ['neutral', 'happy', 'sad', 'scared', 'surprised', 'thinking', 'angry'] as const;

// things the character can hold in its hand (with pose "hold" or any pose)
export const HELD = ['torch', 'spear', 'phone', 'letter', 'coin', 'map', 'book', 'scroll', 'stick'] as const;

// things placed in the scene (ground) or above the head (overhead)
export const PROPS = [
  'fire', 'tree', 'rock', 'hut', 'wolf', 'clock', 'coins', 'scroll', 'map', 'pot',
  'wheel', 'book', 'laptop', 'phone', 'letter', 'bird', 'sundial', 'boat', 'tower',
  'door', 'temple', 'jagannath', 'trinity', 'log', 'chariot',
] as const;

// props that can fill the frame as a close-up 'hero' shot (scene.hero); the stickman is hidden
export const HEROES = ['jagannath', 'trinity', 'chariot', 'temple', 'door', 'log'] as const;

export const OVERHEAD = ['lightbulb', 'question', 'exclamation', 'heart', 'zzz', 'thought'] as const;

export const POSITIONS = ['left', 'center', 'right'] as const;
