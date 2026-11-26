import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Character, Scene, StoryFields, VideoProps} from '../types';
import {Captions} from '../Captions';
import {FONT} from '../layout';
import {Background} from './Backgrounds';
import {Stickman, headTop} from './Stickman';
import {BIG_PROPS, DivineRays, OverheadProp, SceneProp} from './Props';

// close-up 'hero' shots: scale and where the light rays centre (in prop units above the ground)
const HERO: Record<string, {scale: number; glowY: number}> = {
  jagannath: {scale: 2.75, glowY: 190},
  trinity: {scale: 2.7, glowY: 120},
  chariot: {scale: 2.2, glowY: 230},
  temple: {scale: 2.6, glowY: 200},
  door: {scale: 2.7, glowY: 130},
  log: {scale: 3.0, glowY: 40},
};

const POS: Record<string, number> = {left: 0.3, center: 0.5, right: 0.7};

const StoryScene: React.FC<{
  scene: Scene & StoryFields;
  character?: Character;
  accent: string;
  index: number;
}> = ({scene, character, accent, index}) => {
  const frame = useCurrentFrame();
  const {fps, width: w, height: h, durationInFrames} = useVideoConfig();
  const t = frame / fps;
  const vertical = h > w;
  const u = Math.min(w, h) / 1080;
  const groundY = vertical ? h * 0.62 : h * 0.84;
  const k = (vertical ? 3.3 : 2.7) * u; // character scale
  const isQuestion = scene.type === 'question';

  const setting = scene.setting ?? 'field';
  const time = scene.time ?? 'day';
  const pose = scene.pose ?? (isQuestion ? 'think' : 'stand');
  const mood = scene.mood ?? (isQuestion ? 'thinking' : 'neutral');
  const facing = scene.facing ?? 'right';
  const progress = frame / Math.max(1, durationInFrames);

  let cx = (POS[scene.position ?? (isQuestion ? 'center' : 'left')] ?? 0.3) * w;
  if (pose === 'walk' || pose === 'run') {
    const span = (pose === 'run' ? 0.3 : 0.18) * w;
    cx += (facing === 'left' ? -1 : 1) * (progress - 0.5) * span;
  }

  const hero = scene.hero && HERO[scene.hero] ? scene.hero : undefined;
  if (hero) cx = w * 0.5;
  const props = hero ? [] : [...(scene.props ?? [])];
  if (setting === 'campfire' && !props.includes('fire')) props.unshift('fire');
  const side = cx < w / 2 ? 1 : -1;
  const night = time === 'night';

  const head = headTop(pose);
  const overhead = scene.overhead ?? (isQuestion ? 'question' : undefined);

  // camera: alternate push-in, pull-out and a gentle drift so consecutive scenes feel different
  const move = index % 3;
  const zoom = hero ? 1.12 - 0.1 * progress : move === 1 ? 1.1 - 0.08 * progress : 1 + 0.08 * progress;
  const drift = !hero && move === 2 ? (progress - 0.5) * 40 * u : 0;
  const fadeIn = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});
  const enter = spring({frame, fps, config: {damping: 16}});

  return (
    <AbsoluteFill style={{opacity: fadeIn}}>
      <AbsoluteFill style={{transform: `translateX(${drift}px) scale(${zoom})`, transformOrigin: `${cx}px ${groundY - 120 * k}px`}}>
        <Background setting={setting} time={time} w={w} h={h} groundY={groundY} t={t} />
        <svg width={w} height={h} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
          {/* scene props, on the side opposite the character */}
          {props.map((name, i) => {
            const big = BIG_PROPS.has(name);
            const x = cx + side * (0.24 * w + i * 0.17 * w);
            const px = Math.min(w * 0.94, Math.max(w * 0.06, x));
            const y = big ? groundY - 6 * u : groundY;
            return (
              <g key={i} transform={`translate(${px},${y}) scale(${k * (big ? 0.85 : 0.75)})`}>
                <SceneProp name={name} t={t} night={night} />
              </g>
            );
          })}
          {/* hero close-up: the prop fills the frame, with slow rays of light behind it */}
          {hero ? (
            <g>
              <g transform={`translate(${w / 2},${groundY - HERO[hero].glowY * HERO[hero].scale * u})`}>
                <DivineRays r={1100 * u} t={t} />
              </g>
              <g transform={`translate(${w / 2},${groundY}) scale(${HERO[hero].scale * u * (0.94 + 0.06 * enter)})`}>
                <SceneProp name={hero} t={t} night={night} />
              </g>
            </g>
          ) : null}
          {/* background crowd (on both sides in a hero shot) */}
          {[...Array(Math.min(4, scene.crowd ?? 0))].map((_, i) => {
            const x = hero
              ? w * (i % 2 ? 0.88 - Math.floor(i / 2) * 0.1 : 0.12 + Math.floor(i / 2) * 0.1)
              : Math.min(w * 0.95, Math.max(w * 0.05, cx + side * (0.2 * w + i * 0.13 * w)));
            return (
              <g key={`c${i}`} transform={`translate(${x},${groundY - 4 * u}) scale(${k * 0.8})`} opacity={0.85}>
                <Stickman pose={hero ? ['cheer', 'look_up', 'wave', 'cheer'][i % 4] : ['stand', 'point', 'look_up', 'wave'][i % 4]} t={t + i}
                  facing={hero ? (x < w / 2 ? 'right' : 'left') : side > 0 ? 'left' : 'right'}
                  color="#5B6270" frameSeed={i} />
              </g>
            );
          })}
          {/* main character */}
          {hero ? null : <g transform={`translate(${cx},${groundY}) scale(${k * (0.8 + 0.2 * enter)})`}>
            <ellipse cx={0} cy={2} rx={36} ry={6} fill="black" opacity={0.18} />
            {pose === 'sit' ? (
              <g transform={`scale(${facing === 'left' ? -1 : 1},1)`}>
                <rect x={-34} y={-44} width={52} height={44} rx={10} fill="#7A4B2A" stroke="#1d1d1d" strokeWidth={3.5} />
                <ellipse cx={-8} cy={-44} rx={26} ry={7} fill="#B08968" stroke="#1d1d1d" strokeWidth={3} />
              </g>
            ) : null}
            <Stickman pose={pose} mood={mood} t={t} facing={facing} character={character} hold={scene.hold} frameSeed={index} />
          </g>}
          {overhead && !hero ? (
            <g transform={`translate(${cx + (facing === 'left' ? -head.x : head.x) * k},${groundY + (head.y - 55) * k}) scale(${k * 0.9})`}>
              <OverheadProp name={overhead} t={t} />
            </g>
          ) : null}
        </svg>
      </AbsoluteFill>

      {/* on-screen text */}
      {isQuestion ? (
        <div
          style={{
            position: 'absolute',
            left: 70 * u,
            right: 70 * u,
            top: vertical ? h * 0.1 : h * 0.07,
            display: 'flex',
            justifyContent: 'center',
            transform: `translateY(${(1 - enter) * -40 * u}px)`,
            opacity: enter,
          }}
        >
          <div
            style={{
              background: 'rgba(255,255,255,0.95)',
              border: `${6 * u}px solid #151515`,
              borderRadius: 34 * u,
              padding: `${28 * u}px ${44 * u}px`,
              fontSize: (vertical ? 76 : 64) * u,
              fontWeight: 900,
              lineHeight: 1.1,
              color: '#151515',
              textAlign: 'center',
              boxShadow: `${10 * u}px ${10 * u}px 0 ${accent}`,
            }}
          >
            {(scene as any).question}
          </div>
        </div>
      ) : scene.label ? (
        <div
          style={{
            position: 'absolute',
            top: vertical ? h * 0.09 : h * 0.07,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            opacity: enter,
          }}
        >
          <div
            style={{
              background: '#151515',
              color: 'white',
              fontSize: 44 * u,
              fontWeight: 800,
              letterSpacing: 2 * u,
              textTransform: 'uppercase',
              borderRadius: 999,
              padding: `${12 * u}px ${34 * u}px`,
              border: `${4 * u}px solid ${accent}`,
            }}
          >
            {scene.label}
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const StoryVideo: React.FC<VideoProps> = ({script, timings, audioSrc, theme, character}) => {
  const {fps, width, height} = useVideoConfig();
  const accent = theme?.accent ?? '#7C5CFF';
  const vertical = height > width;
  const u = Math.min(width, height) / 1080;
  return (
    <AbsoluteFill style={{fontFamily: FONT, backgroundColor: '#000'}}>
      {script.scenes.map((scene, i) => {
        const tm = timings.scenes[i];
        if (!tm) return null;
        const from = Math.round(tm.start * fps);
        const next = timings.scenes[i + 1];
        const end = next ? Math.round(next.start * fps) : Math.round((timings.total + 0.6) * fps);
        return (
          <Sequence key={i} from={from} durationInFrames={Math.max(1, end - from)}>
            <StoryScene scene={scene as Scene & StoryFields} character={character} accent={accent} index={i} />
          </Sequence>
        );
      })}
      <Captions words={timings.words} accent={accent} top={vertical ? '70%' : undefined} bottom={vertical ? undefined : 40 * u} />
      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}
    </AbsoluteFill>
  );
};
