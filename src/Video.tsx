import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {VideoProps} from './types';
import {Captions} from './Captions';
import {SceneView} from './scenes/SceneView';
import {FONT, useLayout} from './layout';

const Background: React.FC<{accent: string; accent2: string; bg: string}> = ({
  accent,
  accent2,
  bg,
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const t = frame / 30;
  const x1 = 30 + Math.sin(t * 0.35) * 18;
  const y1 = 25 + Math.cos(t * 0.27) * 12;
  const x2 = 70 + Math.cos(t * 0.31) * 18;
  const y2 = 78 + Math.sin(t * 0.22) * 10;
  const grid = Math.round(Math.min(width, height) / 12);
  return (
    <AbsoluteFill style={{backgroundColor: bg}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${x1}% ${y1}%, ${accent}55 0%, transparent 45%),
                       radial-gradient(circle at ${x2}% ${y2}%, ${accent2}44 0%, transparent 50%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px)',
          backgroundSize: `${grid}px ${grid}px`,
          backgroundPosition: `0 ${(frame * 0.6) % grid}px`,
          maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 80%)',
          WebkitMaskImage:
            'radial-gradient(ellipse at center, black 30%, transparent 80%)',
        }}
      />
    </AbsoluteFill>
  );
};

const ProgressBar: React.FC<{accent: string}> = ({accent}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const {s} = useLayout();
  const p = interpolate(frame, [0, durationInFrames - 1], [0, 100], {
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: 10 * s,
        width: `${p}%`,
        background: accent,
        boxShadow: `0 0 ${20 * s}px ${accent}`,
      }}
    />
  );
};

export const Video: React.FC<VideoProps> = ({script, timings, audioSrc, theme}) => {
  const {fps} = useVideoConfig();
  const accent = theme?.accent ?? '#7C5CFF';
  const accent2 = theme?.accent2 ?? '#00D1B2';
  const bg = theme?.bg ?? '#0B0B14';

  return (
    <AbsoluteFill style={{fontFamily: FONT, color: 'white'}}>
      <Background accent={accent} accent2={accent2} bg={bg} />
      {script.scenes.map((scene, i) => {
        const t = timings.scenes[i];
        if (!t) return null;
        const from = Math.round(t.start * fps);
        const next = timings.scenes[i + 1];
        const end = next ? Math.round(next.start * fps) : Math.round((timings.total + 0.6) * fps);
        return (
          <Sequence key={i} from={from} durationInFrames={Math.max(1, end - from)}>
            <SceneView scene={scene} accent={accent} accent2={accent2} />
          </Sequence>
        );
      })}
      <Captions words={timings.words} accent={accent} />
      <ProgressBar accent={accent} />
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}
    </AbsoluteFill>
  );
};
