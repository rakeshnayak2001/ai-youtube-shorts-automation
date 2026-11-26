import React, {useMemo} from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Word} from './types';
import {useLayout} from './layout';

const MAX_WORDS = 4;
const MAX_GAP = 0.6; // seconds — a pause starts a new caption page

type Page = {start: number; end: number; words: Word[]};

const toPages = (words: Word[]): Page[] => {
  const pages: Page[] = [];
  let cur: Word[] = [];
  for (const w of words) {
    const prev = cur[cur.length - 1];
    const endsSentence = prev && /[.!?]$/.test(prev.text);
    if (
      cur.length >= MAX_WORDS ||
      (prev && w.start - prev.end > MAX_GAP) ||
      endsSentence
    ) {
      pages.push({start: cur[0].start, end: cur[cur.length - 1].end, words: cur});
      cur = [];
    }
    cur.push(w);
  }
  if (cur.length) pages.push({start: cur[0].start, end: cur[cur.length - 1].end, words: cur});
  // extend each page until the next one starts (avoids flicker)
  for (let i = 0; i < pages.length - 1; i++) {
    pages[i].end = Math.min(pages[i + 1].start, pages[i].end + 0.5);
  }
  return pages;
};

export const Captions: React.FC<{words: Word[]; accent: string; top?: string; bottom?: number}> = ({
  words,
  accent,
  top,
  bottom,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {vertical, s} = useLayout();
  const pages = useMemo(() => toPages(words), [words]);
  const t = frame / fps;
  const page = pages.find((p) => t >= p.start && t < p.end + 0.05);
  if (!page) return null;

  const pop = spring({frame: frame - Math.round(page.start * fps), fps, config: {damping: 14, mass: 0.6}});

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: top ?? (vertical ? '66%' : undefined),
        bottom: top ? undefined : bottom ?? (vertical ? undefined : 70 * s),
        display: 'flex',
        justifyContent: 'center',
        padding: `0 ${70 * s}px`,
        transform: `scale(${0.85 + 0.15 * pop})`,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: `${6 * s}px ${18 * s}px`,
          fontSize: (vertical ? 76 : 60) * s,
          fontWeight: 900,
          lineHeight: 1.15,
          textAlign: 'center',
          textTransform: 'uppercase',
          letterSpacing: -1 * s,
        }}
      >
        {page.words.map((w, i) => {
          const active = t >= w.start && t < w.end + 0.08;
          return (
            <span
              key={i}
              style={{
                color: active ? '#0B0B14' : 'white',
                background: active ? accent : 'transparent',
                borderRadius: 14 * s,
                padding: `${2 * s}px ${12 * s}px`,
                textShadow: active ? 'none' : `0 ${4 * s}px ${18 * s}px rgba(0,0,0,0.9)`,
                WebkitTextStroke: active ? undefined : `${2 * s}px rgba(0,0,0,0.6)`,
              }}
            >
              {w.text.replace(/[.,!?;:]+$/, '')}
            </span>
          );
        })}
      </div>
    </div>
  );
};
