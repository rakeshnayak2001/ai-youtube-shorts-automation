import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Freeze,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Captions} from '../Captions';
import {VideoProps} from '../types';

export type FilmClip = {src: string; seconds: number} | null;
export type FilmProps = VideoProps & {
  film?: {
    clips: FilmClip[];
    clipVolume?: number; // clip audio under narration
    musicSrc?: string | null;
    musicVolume?: number;
    letterbox?: boolean;
  };
};

const SERIF = "'Cinzel', 'Trajan Pro', Georgia, 'Times New Roman', serif";
const XFADE = 8; // frames of cross-fade between shots

const Shot: React.FC<{clip: FilmClip; durationFrames: number; volume: number; index: number}> = ({
  clip,
  durationFrames,
  volume,
  index,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const fadeIn = index === 0 ? 1 : interpolate(frame, [0, XFADE], [0, 1], {extrapolateRight: 'clamp'});
  const zoom = interpolate(frame, [0, durationFrames], [1.0, 1.06]);

  if (!clip) {
    return (
      <AbsoluteFill style={{background: '#111', color: '#888', justifyContent: 'center', alignItems: 'center',
        fontSize: Math.min(width, height) / 18, fontFamily: SERIF, opacity: fadeIn}}>
        SHOT {index + 1} MISSING
      </AbsoluteFill>
    );
  }
  // slow the clip down (to 0.7x) if the narration runs longer, then hold the last frame
  const clipFrames = Math.max(1, Math.floor(clip.seconds * fps) - 1);
  const rate = Math.max(0.7, Math.min(1, clipFrames / durationFrames));
  const playFrames = Math.floor(clipFrames / rate);
  const video = (
    <OffthreadVideo
      src={staticFile(clip.src)}
      playbackRate={rate}
      volume={volume}
      style={{width: '100%', height: '100%', objectFit: 'cover'}}
    />
  );
  return (
    <AbsoluteFill style={{opacity: fadeIn, transform: `scale(${zoom})`}}>
      {frame < playFrames ? video : <Freeze frame={playFrames - 1}>{video}</Freeze>}
    </AbsoluteFill>
  );
};

const TitleCard: React.FC<{title: string; accent: string}> = ({title, accent}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  const vertical = height > width;
  const op = interpolate(frame, [0, 12, fps * 2.4, fps * 3], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const spread = interpolate(frame, [0, fps * 3], [2, 8]);
  return (
    <AbsoluteFill style={{justifyContent: vertical ? 'flex-start' : 'center', alignItems: 'center',
      paddingTop: vertical ? height * 0.14 : 0, opacity: op}}>
      <div style={{fontFamily: SERIF, color: 'white', fontSize: (vertical ? 78 : 84) * u, fontWeight: 700,
        letterSpacing: spread * u, textAlign: 'center', padding: `0 ${70 * u}px`, lineHeight: 1.15,
        textShadow: `0 ${4 * u}px ${30 * u}px rgba(0,0,0,0.95)`, textTransform: 'uppercase'}}>
        {title}
      </div>
      <div style={{width: 160 * u, height: 3 * u, background: accent, marginTop: 26 * u}} />
    </AbsoluteFill>
  );
};

const DialogueLine: React.FC<{text: string}> = ({text}) => {
  const {width, height} = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  const vertical = height > width;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center',
      paddingBottom: vertical ? height * 0.24 : 70 * u}}>
      <div style={{fontFamily: SERIF, fontStyle: 'italic', color: '#FFF4DC', fontSize: 52 * u,
        textAlign: 'center', padding: `0 ${80 * u}px`, textShadow: '0 3px 16px rgba(0,0,0,0.95)'}}>
        “{text}”
      </div>
    </AbsoluteFill>
  );
};

export const FilmVideo: React.FC<FilmProps> = ({script, timings, audioSrc, theme, film}) => {
  const {fps, width, height} = useVideoConfig();
  const vertical = height > width;
  const u = Math.min(width, height) / 1080;
  const accent = theme?.accent ?? '#E9B44C';
  const clips = film?.clips ?? [];
  const clipVol = film?.clipVolume ?? 0.3;

  return (
    <AbsoluteFill style={{background: 'black'}}>
      {script.scenes.map((scene, i) => {
        const tm = timings.scenes[i];
        if (!tm) return null;
        const start = Math.round(tm.start * fps);
        const next = timings.scenes[i + 1];
        const end = next ? Math.round(next.start * fps) : Math.round((timings.total + 0.6) * fps);
        const from = Math.max(0, start - (i === 0 ? 0 : XFADE));
        const dur = end - from + (next ? XFADE : 0);
        const dialogue = (scene as any).dialogue as string | undefined;
        return (
          <Sequence key={i} from={from} durationInFrames={Math.max(1, dur)}>
            <Shot clip={clips[i] ?? null} durationFrames={dur} index={i} volume={dialogue ? 1 : clipVol} />
            {dialogue ? <DialogueLine text={dialogue} /> : null}
          </Sequence>
        );
      })}

      {/* cinematic grade: vignette + optional letterbox */}
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)'}} />
      {film?.letterbox && !vertical ? (
        <>
          <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: height * 0.11, background: 'black'}} />
          <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: height * 0.11, background: 'black'}} />
        </>
      ) : null}

      <Sequence durationInFrames={Math.round(fps * 3)}>
        <TitleCard title={script.title} accent={accent} />
      </Sequence>
      <Captions words={timings.words} accent={accent} top={vertical ? '72%' : undefined}
        bottom={vertical ? undefined : (film?.letterbox ? height * 0.12 : 50 * u)} />

      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}
      {film?.musicSrc ? <Audio src={staticFile(film.musicSrc)} volume={film.musicVolume ?? 0.12} loop /> : null}
    </AbsoluteFill>
  );
};
