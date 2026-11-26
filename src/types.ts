export type Word = {text: string; start: number; end: number};

export type SceneBase = {narration: string};

export type Scene =
  | (SceneBase & {type: 'hook'; heading: string})
  | (SceneBase & {type: 'text'; heading: string; body?: string})
  | (SceneBase & {type: 'stat'; value: string; label: string})
  | (SceneBase & {type: 'list'; heading: string; items: string[]})
  | (SceneBase & {
      type: 'bars';
      heading: string;
      unit?: string;
      data: {label: string; value: number}[];
    })
  | (SceneBase & {type: 'outro'; heading: string})
  // ---- stickman story scenes ----
  | (SceneBase & StoryFields & {type: 'story'})
  | (SceneBase & StoryFields & {type: 'question'; question: string});

export type StoryFields = {
  setting?: string;
  time?: string;
  pose?: string;
  mood?: string;
  position?: string;
  facing?: 'left' | 'right';
  hold?: string;
  props?: string[];
  overhead?: string;
  crowd?: number;
  label?: string;
  hero?: string;
};

export type Character = {
  outfit?: string;
  hair?: 'messy' | 'spiky' | 'long' | 'none' | 'bun';
  scarf?: string;
};

export type ScriptJson = {
  slug: string;
  title: string;
  description: string;
  tags: string[];
  scenes: Scene[];
  format?: 'facts' | 'stickman';
};

export type Timings = {
  total: number;
  scenes: {start: number; duration: number}[];
  words: Word[];
};

export type VideoProps = {
  script: ScriptJson;
  timings: Timings;
  audioSrc: string | null;
  theme?: {accent?: string; accent2?: string; bg?: string};
  character?: Character;
};
