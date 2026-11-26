import React from 'react';
import {Character} from '../types';
import {HeldProp} from './Props';

// Units: feet on the ground at (0,0), up is negative y. Full height ~190 units.
const THIGH = 42;
const SHIN = 40;
const UPPER = 36;
const FORE = 34;
const TORSO = 58;
const NECK = 4;
const HEAD_R = 22;
const INK = '#151515';
const LINE = 5.5;

type Limb = [number, number]; // [angle from straight down (+ = forward), bend relative]
type PoseDef = {
  front: Limb;
  back: Limb;
  frontLeg: Limb;
  backLeg: Limb;
  lean?: number;
  headTilt?: number;
  bob?: number;
  shake?: number;
};

const rad = (d: number) => (d * Math.PI) / 180;
const dir = (deg: number, len: number) => ({x: Math.sin(rad(deg)) * len, y: Math.cos(rad(deg)) * len});

export const poseAt = (pose: string, t: number): PoseDef => {
  switch (pose) {
    case 'walk':
    case 'run': {
      const run = pose === 'run';
      const p = Math.sin(t * Math.PI * 2 * (run ? 2.4 : 1.6));
      const amp = run ? 40 : 24;
      return {
        frontLeg: [amp * p, -Math.max(0, -p) * (run ? 70 : 40)],
        backLeg: [-amp * p, -Math.max(0, p) * (run ? 70 : 40)],
        front: [-amp * 0.9 * p, run ? 80 : 18],
        back: [amp * 0.9 * p, run ? 80 : 18],
        lean: run ? 12 : 3,
        bob: -Math.abs(p) * (run ? 8 : 4),
      };
    }
    case 'point':
      return {front: [92, 0], back: [-8, -12], frontLeg: [8, 0], backLeg: [-8, 0]};
    case 'wave':
      return {front: [150 + Math.sin(t * 12) * 18, 30], back: [-8, -12], frontLeg: [7, 0], backLeg: [-7, 0]};
    case 'think':
      return {front: [28, 135], back: [25, 85], frontLeg: [6, 0], backLeg: [-6, 0], headTilt: 8};
    case 'scared':
      return {
        front: [150, 35], back: [128, 45], frontLeg: [16, 0], backLeg: [-16, 0],
        lean: -8, shake: Math.sin(t * 45) * 1.6,
      };
    case 'cheer':
      return {
        front: [168, 10], back: [192, -10], frontLeg: [10, 0], backLeg: [-10, 0],
        bob: -Math.abs(Math.sin(t * Math.PI * 1.8)) * 14,
      };
    case 'sit':
      return {front: [40, 45], back: [30, 45], frontLeg: [88, -90], backLeg: [78, -88]};
    case 'crouch':
      return {front: [60, 25], back: [40, 35], frontLeg: [70, -130], backLeg: [48, -118], lean: 22};
    case 'sad':
      return {front: [6, 0], back: [-4, 0], frontLeg: [5, 0], backLeg: [-5, 0], lean: 12, headTilt: 22};
    case 'hold':
      return {front: [48, 55], back: [-8, -12], frontLeg: [7, 0], backLeg: [-7, 0]};
    case 'look_up':
      return {front: [10, 8], back: [-10, -8], frontLeg: [7, 0], backLeg: [-7, 0], lean: -5, headTilt: -24};
    case 'shrug':
      return {front: [25, 95], back: [-25, -95], frontLeg: [7, 0], backLeg: [-7, 0], headTilt: 10, bob: -2};
    case 'stand':
    default:
      return {
        front: [10 + Math.sin(t * 1.3) * 2, 8], back: [-10, -10],
        frontLeg: [7, 0], backLeg: [-7, 0],
      };
  }
};

const solve = (p: PoseDef) => {
  const hip = {x: 0, y: 0};
  const leg = ([h, k]: Limb) => {
    const knee = {x: hip.x + dir(h, THIGH).x, y: hip.y + dir(h, THIGH).y};
    const f = dir(h + k, SHIN);
    return {knee, foot: {x: knee.x + f.x, y: knee.y + f.y}};
  };
  const fl = leg(p.frontLeg);
  const bl = leg(p.backLeg);
  // move everything so the lowest foot touches the ground
  const drop = Math.max(fl.foot.y, bl.foot.y);
  const off = (pt: {x: number; y: number}) => ({x: pt.x, y: pt.y - drop + (p.bob ?? 0)});
  const lean = p.lean ?? 0;
  // vector pointing "up the body", tilted forward by the lean angle
  const up = (len: number, ang = lean) => ({x: Math.sin(rad(ang)) * len, y: -Math.cos(rad(ang)) * len});
  const H = off(hip);
  const sv = up(TORSO - 6);
  const nv = up(TORSO);
  const shoulder = {x: H.x + sv.x, y: H.y + sv.y};
  const neck = {x: H.x + nv.x, y: H.y + nv.y};
  const hv = up(NECK + HEAD_R, lean + (p.headTilt ?? 0));
  const head = {x: neck.x + hv.x, y: neck.y + hv.y};
  const arm = ([a, b]: Limb) => {
    const e = dir(a + lean, UPPER);
    const elbow = {x: shoulder.x + e.x, y: shoulder.y + e.y};
    const h = dir(a + b + lean, FORE);
    return {elbow, hand: {x: elbow.x + h.x, y: elbow.y + h.y}, angle: a + b + lean};
  };
  return {
    hip: H,
    shoulder,
    neck,
    head,
    lean,
    headAngle: lean + (p.headTilt ?? 0),
    frontLeg: {knee: off(fl.knee), foot: off(fl.foot)},
    backLeg: {knee: off(bl.knee), foot: off(bl.foot)},
    front: arm(p.front),
    back: arm(p.back),
  };
};

const Face: React.FC<{mood: string; blink: boolean}> = ({mood, blink}) => {
  const eyeRy = blink ? 0.6 : mood === 'scared' || mood === 'surprised' ? 3.6 : 3;
  const eyes = (
    <>
      <ellipse cx={4} cy={-3} rx={2.8} ry={eyeRy} fill={INK} />
      <ellipse cx={14} cy={-3} rx={2.8} ry={eyeRy} fill={INK} />
    </>
  );
  const brow = (x: number, tiltIn: number, y = -11) => (
    <line x1={x - 4} y1={y + (x < 9 ? tiltIn : -tiltIn)} x2={x + 4} y2={y + (x < 9 ? -tiltIn : tiltIn)}
      stroke={INK} strokeWidth={2.4} strokeLinecap="round" />
  );
  let brows = <>{brow(4, 0)}{brow(14, 0)}</>;
  let mouth = <line x1={6} y1={10} x2={14} y2={10} stroke={INK} strokeWidth={2.4} strokeLinecap="round" />;
  switch (mood) {
    case 'happy':
      mouth = <path d="M4 7 Q10 15 16 7" fill="none" stroke={INK} strokeWidth={2.6} strokeLinecap="round" />;
      brows = <>{brow(4, 0, -12)}{brow(14, 0, -12)}</>;
      break;
    case 'sad':
      mouth = <path d="M5 13 Q10 7 15 13" fill="none" stroke={INK} strokeWidth={2.6} strokeLinecap="round" />;
      brows = <>{brow(4, -2.5)}{brow(14, -2.5)}</>;
      break;
    case 'scared':
      mouth = <ellipse cx={10} cy={11} rx={3.5} ry={4.5} fill={INK} />;
      brows = <>{brow(4, -3, -13)}{brow(14, -3, -13)}</>;
      break;
    case 'surprised':
      mouth = <ellipse cx={10} cy={11} rx={4} ry={5} fill="none" stroke={INK} strokeWidth={2.4} />;
      brows = <>{brow(4, 0, -15)}{brow(14, 0, -15)}</>;
      break;
    case 'thinking':
      mouth = <line x1={8} y1={11} x2={15} y2={9} stroke={INK} strokeWidth={2.4} strokeLinecap="round" />;
      brows = <>{brow(4, 0, -11)}{brow(14, 1.5, -15)}</>;
      break;
    case 'angry':
      mouth = <line x1={5} y1={11} x2={15} y2={11} stroke={INK} strokeWidth={2.6} strokeLinecap="round" />;
      brows = <>{brow(4, 3)}{brow(14, 3)}</>;
      break;
  }
  return <>{eyes}{brows}{mouth}</>;
};

const Hair: React.FC<{hair: string}> = ({hair}) => {
  const r = HEAD_R;
  switch (hair) {
    case 'none':
      return null;
    case 'spiky':
      return <path d={`M${-r + 2} -8 L-14 -30 L-6 -20 L0 -34 L6 -21 L14 -31 L${r - 3} -8 Q0 -${r + 4} ${-r + 2} -8Z`} fill={INK} />;
    case 'long':
      return <path d={`M${-r - 1} 4 Q${-r - 6} -${r + 8} 2 -${r + 2} Q${r + 2} -${r} ${r} -6 Q4 -14 -8 -10 Q-14 0 -${r - 6} 22 Z`} fill={INK} />;
    case 'bun':
      return (
        <>
          <circle cx={-12} cy={-22} r={9} fill={INK} />
          <path d={`M${-r} -2 Q-18 -${r + 6} 4 -${r + 1} Q${r} -${r - 4} ${r} -8 Q2 -16 -10 -12 Z`} fill={INK} />
        </>
      );
    case 'messy':
    default:
      return (
        <path
          d={`M${-r} -2 Q-24 -16 -18 -22 L-22 -28 L-12 -26 L-10 -34 L-2 -27 L4 -35 L8 -26 L18 -30 L15 -21 Q${r + 2} -14 ${r - 1} -6 Q6 -16 -6 -14 Q-14 -10 ${-r} -2 Z`}
          fill={INK}
        />
      );
  }
};

export const Stickman: React.FC<{
  pose: string;
  mood?: string;
  t: number; // seconds since scene start
  facing?: 'left' | 'right';
  character?: Character;
  hold?: string;
  color?: string; // ink override for crowd figures
  frameSeed?: number;
}> = ({pose, mood = 'neutral', t, facing = 'right', character, hold, color, frameSeed = 0}) => {
  const p = poseAt(pose, t);
  const j = solve(p);
  const ink = color ?? INK;
  const outfit = color ? undefined : character?.outfit ?? '#8B5A2B';
  const blink = ((t + frameSeed) % 3.4) < 0.12;
  const line = (a: {x: number; y: number}, b: {x: number; y: number}, w = LINE) => (
    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={ink} strokeWidth={w} strokeLinecap="round" />
  );
  const limb = (a: {x: number; y: number}, b: {x: number; y: number}, c: {x: number; y: number}) => (
    <polyline points={`${a.x},${a.y} ${b.x},${b.y} ${c.x},${c.y}`} fill="none" stroke={ink}
      strokeWidth={LINE} strokeLinecap="round" strokeLinejoin="round" />
  );
  // tunic: from shoulders to below hips, ragged hem
  const tunic = (() => {
    if (!outfit) return null;
    const s = j.shoulder;
    const h = j.hip;
    const dx = Math.sin(rad(j.lean));
    const w1 = 9;
    const w2 = 15;
    const hemY = h.y + 12;
    const hemX = h.x - dx * 12;
    return (
      <path
        d={`M${s.x - w1} ${s.y - 2} L${s.x + w1} ${s.y - 2} L${hemX + w2} ${hemY}
            L${hemX + 9} ${hemY - 5} L${hemX + 4} ${hemY + 1} L${hemX - 2} ${hemY - 5}
            L${hemX - 8} ${hemY + 1} L${hemX - w2} ${hemY - 3} Z`}
        fill={outfit}
        stroke={ink}
        strokeWidth={3}
        strokeLinejoin="round"
      />
    );
  })();

  return (
    <g transform={`translate(${p.shake ?? 0},0) scale(${facing === 'left' ? -1 : 1},1)`}>
      {/* back limbs */}
      {limb(j.hip, j.backLeg.knee, j.backLeg.foot)}
      {limb(j.shoulder, j.back.elbow, j.back.hand)}
      {/* body */}
      {limb(j.hip, j.frontLeg.knee, j.frontLeg.foot)}
      {line(j.hip, j.neck)}
      {tunic}
      {character?.scarf && !color ? line({x: j.neck.x - 9, y: j.neck.y + 3}, {x: j.neck.x + 9, y: j.neck.y + 3}, 7) : null}
      {/* head */}
      <g transform={`translate(${j.head.x},${j.head.y}) rotate(${j.headAngle})`}>
        <circle r={HEAD_R} fill="white" stroke={ink} strokeWidth={4} />
        {color ? (
          <>
            <circle cx={5} cy={-3} r={2.4} fill={ink} />
            <circle cx={14} cy={-3} r={2.4} fill={ink} />
          </>
        ) : (
          <>
            <Hair hair={character?.hair ?? 'messy'} />
            <Face mood={mood} blink={blink} />
          </>
        )}
      </g>
      {/* front arm + held prop */}
      {limb(j.shoulder, j.front.elbow, j.front.hand)}
      {hold ? (
        <g transform={`translate(${j.front.hand.x},${j.front.hand.y})`}>
          <HeldProp name={hold} t={t} />
        </g>
      ) : null}
      <circle cx={j.front.hand.x} cy={j.front.hand.y} r={3.5} fill={ink} />
    </g>
  );
};

export const headTop = (pose: string) => {
  const j = solve(poseAt(pose, 0));
  return {x: j.head.x, y: j.head.y - HEAD_R};
};
