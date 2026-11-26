import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Scene} from '../types';
import {useLayout} from '../layout';

type P = {scene: Scene; accent: string; accent2: string};

const useEnter = (delay = 0) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - delay, fps, config: {damping: 15, mass: 0.7}});
};

const Area: React.FC<{children: React.ReactNode}> = ({children}) => {
  const {vertical, s} = useLayout();
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const out = interpolate(frame, [durationInFrames - 6, durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 80 * s,
        right: 80 * s,
        top: vertical ? '11%' : '9%',
        height: vertical ? '52%' : '66%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        opacity: out,
      }}
    >
      {children}
    </div>
  );
};

const Heading: React.FC<{text: string; size?: number; accent: string; delay?: number}> = ({
  text,
  size = 96,
  accent,
  delay = 0,
}) => {
  const {s} = useLayout();
  const e = useEnter(delay);
  return (
    <div
      style={{
        fontSize: size * s,
        fontWeight: 900,
        lineHeight: 1.05,
        letterSpacing: -2 * s,
        transform: `translateY(${(1 - e) * 60 * s}px)`,
        opacity: e,
        textShadow: `0 0 ${40 * s}px ${accent}66`,
      }}
    >
      {text}
    </div>
  );
};

const Pill: React.FC<{text: string; accent: string}> = ({text, accent}) => {
  const {s} = useLayout();
  const e = useEnter(0);
  return (
    <div
      style={{
        fontSize: 34 * s,
        fontWeight: 800,
        textTransform: 'uppercase',
        letterSpacing: 4 * s,
        color: accent,
        border: `${3 * s}px solid ${accent}`,
        borderRadius: 999,
        padding: `${10 * s}px ${30 * s}px`,
        marginBottom: 40 * s,
        opacity: e,
      }}
    >
      {text}
    </div>
  );
};

const Hook: React.FC<{heading: string; accent: string}> = ({heading, accent}) => {
  const {s} = useLayout();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const words = heading.split(' ');
  return (
    <Area>
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: `0 ${24 * s}px`}}>
        {words.map((w, i) => {
          const e = spring({frame: frame - i * 4, fps, config: {damping: 11, mass: 0.6}});
          return (
            <span
              key={i}
              style={{
                fontSize: 128 * s,
                fontWeight: 900,
                lineHeight: 1.02,
                letterSpacing: -3 * s,
                display: 'inline-block',
                transform: `scale(${e}) rotate(${(1 - e) * -8}deg)`,
                color: i === words.length - 1 ? accent : 'white',
              }}
            >
              {w}
            </span>
          );
        })}
      </div>
    </Area>
  );
};

const parseNumber = (v: string) => {
  const m = v.match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
  if (!m) return null;
  const num = parseFloat(m[2].replace(/,/g, ''));
  if (Number.isNaN(num)) return null;
  const decimals = (m[2].split('.')[1] ?? '').length;
  return {prefix: m[1], num, suffix: m[3], decimals, commas: m[2].includes(',')};
};

const Stat: React.FC<{value: string; label: string; accent: string; accent2: string}> = ({
  value,
  label,
  accent,
  accent2,
}) => {
  const {s} = useLayout();
  const frame = useCurrentFrame();
  const parsed = parseNumber(value);
  const p = interpolate(frame, [0, 28], [0, 1], {
    extrapolateRight: 'clamp',
    easing: (x) => 1 - Math.pow(1 - x, 3),
  });
  let shown = value;
  if (parsed) {
    const n = parsed.num * p;
    const str = parsed.commas
      ? n.toLocaleString('en-US', {maximumFractionDigits: parsed.decimals, minimumFractionDigits: parsed.decimals})
      : n.toFixed(parsed.decimals);
    shown = `${parsed.prefix}${str}${parsed.suffix}`;
  }
  const e = useEnter(0);
  return (
    <Area>
      <div
        style={{
          fontSize: (value.length > 8 ? 170 : 240) * s,
          fontWeight: 900,
          letterSpacing: -6 * s,
          lineHeight: 1,
          backgroundImage: `linear-gradient(135deg, ${accent}, ${accent2})`,
          WebkitBackgroundClip: 'text',
          backgroundClip: 'text',
          color: 'transparent',
          transform: `scale(${0.7 + 0.3 * e})`,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {shown}
      </div>
      <div style={{marginTop: 30 * s}}>
        <Heading text={label} size={58} accent={accent} delay={8} />
      </div>
    </Area>
  );
};

const List: React.FC<{heading: string; items: string[]; accent: string}> = ({heading, items, accent}) => {
  const {s} = useLayout();
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const step = Math.max(8, Math.floor((durationInFrames * 0.7) / Math.max(1, items.length)));
  return (
    <Area>
      <Heading text={heading} size={80} accent={accent} />
      <div style={{marginTop: 50 * s, display: 'flex', flexDirection: 'column', gap: 26 * s, width: '100%'}}>
        {items.map((item, i) => {
          const e = spring({frame: frame - 10 - i * step, fps, config: {damping: 14}});
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 28 * s,
                background: 'rgba(255,255,255,0.07)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: 26 * s,
                padding: `${22 * s}px ${32 * s}px`,
                opacity: e,
                transform: `translateX(${(1 - e) * 120 * s}px)`,
                textAlign: 'left',
              }}
            >
              <div
                style={{
                  minWidth: 70 * s,
                  height: 70 * s,
                  borderRadius: 999,
                  background: accent,
                  color: '#0B0B14',
                  fontWeight: 900,
                  fontSize: 38 * s,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {i + 1}
              </div>
              <div style={{fontSize: 52 * s, fontWeight: 800}}>{item}</div>
            </div>
          );
        })}
      </div>
    </Area>
  );
};

const Bars: React.FC<{
  heading: string;
  unit?: string;
  data: {label: string; value: number}[];
  accent: string;
  accent2: string;
}> = ({heading, unit, data, accent, accent2}) => {
  const {s} = useLayout();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <Area>
      <Heading text={heading} size={72} accent={accent} />
      <div style={{marginTop: 50 * s, width: '100%', display: 'flex', flexDirection: 'column', gap: 30 * s}}>
        {data.map((d, i) => {
          const e = spring({frame: frame - 8 - i * 6, fps, config: {damping: 20, mass: 1}});
          const pct = (d.value / max) * 100 * e;
          const shown = d.value * e;
          const decimals = Number.isInteger(d.value) ? 0 : 1;
          return (
            <div key={i} style={{textAlign: 'left'}}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 44 * s,
                  fontWeight: 800,
                  marginBottom: 10 * s,
                }}
              >
                <span>{d.label}</span>
                <span style={{color: i === 0 ? accent : accent2, fontVariantNumeric: 'tabular-nums'}}>
                  {shown.toLocaleString('en-US', {maximumFractionDigits: decimals, minimumFractionDigits: decimals})}
                  {unit ?? ''}
                </span>
              </div>
              <div style={{height: 46 * s, background: 'rgba(255,255,255,0.08)', borderRadius: 999}}>
                <div
                  style={{
                    height: '100%',
                    width: `${pct}%`,
                    borderRadius: 999,
                    backgroundImage: `linear-gradient(90deg, ${accent}, ${accent2})`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Area>
  );
};

const TextScene: React.FC<{heading: string; body?: string; accent: string}> = ({heading, body, accent}) => {
  const {s} = useLayout();
  const e = useEnter(10);
  return (
    <Area>
      <Heading text={heading} size={100} accent={accent} />
      {body ? (
        <div
          style={{
            marginTop: 40 * s,
            fontSize: 50 * s,
            fontWeight: 600,
            lineHeight: 1.3,
            color: 'rgba(255,255,255,0.85)',
            opacity: e,
            transform: `translateY(${(1 - e) * 30 * s}px)`,
          }}
        >
          {body}
        </div>
      ) : null}
    </Area>
  );
};

export const SceneView: React.FC<P> = ({scene, accent, accent2}) => {
  switch (scene.type) {
    case 'hook':
      return <Hook heading={scene.heading} accent={accent} />;
    case 'stat':
      return <Stat value={scene.value} label={scene.label} accent={accent} accent2={accent2} />;
    case 'list':
      return <List heading={scene.heading} items={scene.items} accent={accent} />;
    case 'bars':
      return <Bars heading={scene.heading} unit={scene.unit} data={scene.data} accent={accent} accent2={accent2} />;
    case 'outro':
      return (
        <Area>
          <Pill text="Follow" accent={accent} />
          <Heading text={scene.heading} size={96} accent={accent} />
        </Area>
      );
    case 'text':
    default:
      return <TextScene heading={(scene as any).heading} body={(scene as any).body} accent={accent} />;
  }
};
