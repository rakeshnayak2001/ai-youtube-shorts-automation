import React from 'react';

const INK = '#1d1d1d';
const S = {stroke: INK, strokeWidth: 3.5, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const};

const Flame: React.FC<{t: number; size?: number}> = ({t, size = 1}) => {
  const f1 = Math.sin(t * 14) * 3;
  const f2 = Math.cos(t * 11) * 3;
  return (
    <g transform={`scale(${size})`}>
      <path d={`M-14 0 Q-18 -22 ${-4 + f1} -46 Q2 -30 8 ${-40 + f2} Q18 -18 14 0 Z`} fill="#F4762C" stroke={INK} strokeWidth={3} />
      <path d={`M-7 0 Q-9 -14 ${-1 + f2} -28 Q4 -16 7 0 Z`} fill="#FFD23F" />
    </g>
  );
};

export const Glow: React.FC<{r: number; color?: string; t: number}> = ({r, color = '#FFB347', t}) => {
  const id = `g${Math.round(r)}${color.replace('#', '')}`;
  return (
    <>
      <defs>
        <radialGradient id={id}>
          <stop offset="0%" stopColor={color} stopOpacity={0.55 + Math.sin(t * 9) * 0.05} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </radialGradient>
      </defs>
      <circle r={r} fill={`url(#${id})`} />
    </>
  );
};

// ---------- things held in the hand (origin = hand) ----------
export const HeldProp: React.FC<{name: string; t: number}> = ({name, t}) => {
  switch (name) {
    case 'torch':
      return (
        <g>
          <g transform="translate(0,-48)"><Glow r={110} t={t} /></g>
          <line x1={0} y1={14} x2={0} y2={-40} stroke="#6B4226" strokeWidth={7} strokeLinecap="round" />
          <g transform="translate(0,-38)"><Flame t={t} size={0.8} /></g>
        </g>
      );
    case 'spear':
    case 'stick':
      return (
        <g>
          <line x1={0} y1={40} x2={0} y2={-80} stroke="#6B4226" strokeWidth={5} strokeLinecap="round" />
          {name === 'spear' ? <path d="M-7 -78 L0 -104 L7 -78 Z" fill="#9AA5B1" {...S} /> : null}
        </g>
      );
    case 'phone':
      return <g><rect x={-9} y={-30} width={18} height={30} rx={4} fill="#222" {...S} /><rect x={-6} y={-26} width={12} height={20} fill="#7DD3FC" /></g>;
    case 'letter':
      return <g><rect x={-16} y={-22} width={32} height={22} fill="#FFF7E6" {...S} /><path d="M-16 -22 L0 -10 L16 -22" fill="none" {...S} /></g>;
    case 'coin':
      return <g><circle cy={-10} r={11} fill="#F6C343" {...S} /><circle cy={-10} r={5} fill="none" stroke="#B98A0E" strokeWidth={2} /></g>;
    case 'map':
      return <g><path d="M-22 -30 L-8 -26 L8 -32 L22 -28 L22 0 L8 -4 L-8 2 L-22 -2 Z" fill="#F3E3B5" {...S} /><path d="M-14 -8 Q0 -26 12 -16" fill="none" stroke="#C0392B" strokeWidth={2.5} strokeDasharray="4 4" /></g>;
    case 'book':
      return <g><path d="M-22 -24 Q-11 -30 0 -24 Q11 -30 22 -24 L22 0 Q11 -6 0 0 Q-11 -6 -22 0 Z" fill="#E8F1FF" {...S} /><line x1={0} y1={-24} x2={0} y2={0} {...S} /></g>;
    case 'scroll':
      return <g><rect x={-10} y={-30} width={20} height={30} fill="#F3E3B5" {...S} /><circle cx={0} cy={-30} r={5} fill="#D4B483" {...S} /><circle cx={0} cy={0} r={5} fill="#D4B483" {...S} /></g>;
    default:
      return null;
  }
};

// ---------- things in the scene (origin = bottom centre on the ground) ----------
export const SceneProp: React.FC<{name: string; t: number; night?: boolean}> = ({name, t, night}) => {
  switch (name) {
    case 'fire':
      return (
        <g>
          <g transform="translate(0,-30)"><Glow r={night ? 340 : 170} t={t} /></g>
          <line x1={-34} y1={-4} x2={30} y2={-14} stroke="#6B4226" strokeWidth={10} strokeLinecap="round" />
          <line x1={-30} y1={-14} x2={34} y2={-4} stroke="#7A4B2A" strokeWidth={10} strokeLinecap="round" />
          <g transform="translate(0,-8)"><Flame t={t} size={1.5} /></g>
        </g>
      );
    case 'tree':
      return (
        <g>
          <rect x={-12} y={-150} width={24} height={150} fill="#7A4B2A" {...S} />
          <circle cx={-40} cy={-160} r={48} fill="#4F9D5D" {...S} />
          <circle cx={40} cy={-165} r={46} fill="#4F9D5D" {...S} />
          <circle cx={0} cy={-210} r={58} fill="#5DB06B" {...S} />
        </g>
      );
    case 'rock':
      return <path d="M-50 0 Q-56 -30 -26 -44 Q8 -60 34 -38 Q56 -22 50 0 Z" fill="#9AA0A6" {...S} />;
    case 'hut':
      return (
        <g>
          <rect x={-70} y={-90} width={140} height={90} fill="#C8A27A" {...S} />
          <path d="M-95 -86 L0 -170 L95 -86 Z" fill="#D9B44A" {...S} />
          <path d="M-18 0 L-18 -50 Q0 -64 18 -50 L18 0 Z" fill="#5A3A22" {...S} />
        </g>
      );
    case 'wolf': {
      const tail = Math.sin(t * 6) * 6;
      return (
        <g>
          <ellipse cx={0} cy={-52} rx={52} ry={22} fill="#4A4E57" {...S} />
          <path d={`M-48 -58 Q-80 ${-70 + tail} -88 ${-46 + tail}`} fill="none" stroke="#4A4E57" strokeWidth={12} strokeLinecap="round" />
          {[-36, -18, 18, 36].map((x) => <line key={x} x1={x} y1={-40} x2={x} y2={0} stroke="#4A4E57" strokeWidth={9} strokeLinecap="round" />)}
          <path d="M34 -64 L62 -88 L58 -104 L48 -92 L40 -104 L36 -86 Z" fill="#4A4E57" {...S} />
          <path d="M58 -80 L84 -72 L60 -64 Z" fill="#4A4E57" {...S} />
          <circle cx={54} cy={-84} r={night ? 5 : 3} fill={night ? '#FFE45C' : INK} />
          {night ? <g transform="translate(54,-84)"><Glow r={22} color="#FFE45C" t={t} /></g> : null}
        </g>
      );
    }
    case 'clock': {
      const a = t * 90;
      return (
        <g transform="translate(0,-60)">
          <circle r={50} fill="#FFFBF0" {...S} strokeWidth={5} />
          {[...Array(12)].map((_, i) => {
            const r = (i * 30 * Math.PI) / 180;
            return <line key={i} x1={Math.sin(r) * 40} y1={-Math.cos(r) * 40} x2={Math.sin(r) * 46} y2={-Math.cos(r) * 46} stroke={INK} strokeWidth={3} />;
          })}
          <line x1={0} y1={0} x2={Math.sin((a * Math.PI) / 180) * 34} y2={-Math.cos((a * Math.PI) / 180) * 34} stroke={INK} strokeWidth={4} strokeLinecap="round" />
          <line x1={0} y1={0} x2={Math.sin((a / 12 * Math.PI) / 180) * 22} y2={-Math.cos((a / 12 * Math.PI) / 180) * 22} stroke={INK} strokeWidth={5} strokeLinecap="round" />
        </g>
      );
    }
    case 'coins':
      return (
        <g>
          {[0, 1, 2, 3].map((i) => <ellipse key={i} cx={-20} cy={-8 - i * 9} rx={22} ry={8} fill="#F6C343" {...S} />)}
          {[0, 1].map((i) => <ellipse key={`b${i}`} cx={24} cy={-8 - i * 9} rx={22} ry={8} fill="#F6C343" {...S} />)}
        </g>
      );
    case 'scroll':
    case 'map':
    case 'book':
    case 'letter':
    case 'phone':
      return <g transform="translate(0,-40) scale(1.8)"><rect x={-24} y={-4} width={48} height={26} fill="#8B5E3C" {...S} transform="translate(0,22)" /><HeldProp name={name} t={t} /></g>;
    case 'laptop':
      return (
        <g>
          <rect x={-60} y={-40} width={120} height={40} fill="#8B5E3C" {...S} />
          <path d="M-44 -40 L-36 -104 L36 -104 L44 -40 Z" fill="#2B2F36" {...S} />
          <path d="M-32 -48 L-26 -96 L26 -96 L32 -48 Z" fill="#7DD3FC" />
        </g>
      );
    case 'pot':
      return <path d="M-30 0 Q-46 -30 -26 -56 L-20 -66 L20 -66 L26 -56 Q46 -30 30 0 Z" fill="#C0603A" {...S} />;
    case 'wheel':
      return (
        <g transform={`translate(0,-50) rotate(${t * 40})`}>
          <circle r={48} fill="none" stroke="#7A4B2A" strokeWidth={9} />
          {[0, 45, 90, 135].map((a) => <line key={a} x1={-46 * Math.cos((a * Math.PI) / 180)} y1={-46 * Math.sin((a * Math.PI) / 180)} x2={46 * Math.cos((a * Math.PI) / 180)} y2={46 * Math.sin((a * Math.PI) / 180)} stroke="#7A4B2A" strokeWidth={6} />)}
          <circle r={8} fill="#5A3A22" />
        </g>
      );
    case 'bird': {
      const flap = Math.sin(t * 10) * 10;
      return (
        <g transform={`translate(${(t * 40) % 200 - 100},-320)`}>
          <path d={`M-20 ${-flap} Q-10 -4 0 0 Q10 -4 20 ${-flap}`} fill="none" stroke={INK} strokeWidth={4} strokeLinecap="round" />
          <path d={`M30 ${-20 - flap} Q38 -26 46 -20 Q54 -26 62 ${-20 - flap}`} fill="none" stroke={INK} strokeWidth={4} strokeLinecap="round" />
        </g>
      );
    }
    case 'sundial': {
      return (
        <g>
          <ellipse cx={0} cy={-10} rx={60} ry={14} fill="#B8B2A7" {...S} />
          <rect x={-60} y={-10} width={120} height={10} fill="#A39E94" {...S} />
          <path d={`M0 -12 L${30 + Math.sin(t) * 10} -6`} stroke="#555" strokeWidth={5} strokeLinecap="round" opacity={0.5} />
          <path d="M-4 -12 L0 -50 L18 -12 Z" fill="#7C7C7C" {...S} />
        </g>
      );
    }
    case 'boat':
      return (
        <g transform={`translate(0,${Math.sin(t * 2) * 3})`}>
          <path d="M-80 -30 L80 -30 L56 0 L-56 0 Z" fill="#8B5E3C" {...S} />
          <line x1={0} y1={-30} x2={0} y2={-150} {...S} strokeWidth={5} />
          <path d="M4 -146 L64 -50 L4 -50 Z" fill="#FFF7E6" {...S} />
        </g>
      );
    case 'tower':
      return (
        <g>
          <path d="M-40 0 L-30 -220 L30 -220 L40 0 Z" fill="#B8B2A7" {...S} />
          <rect x={-40} y={-240} width={80} height={22} fill="#A39E94" {...S} />
          <rect x={-10} y={-60} width={20} height={60} fill="#5A3A22" {...S} />
          <g transform="translate(0,-244)"><Glow r={120} t={t} /><Flame t={t} size={1.1} /></g>
        </g>
      );
    case 'door':
      // a heavy closed wooden double door with a lock bar
      return (
        <g>
          <path d="M-85 0 L-85 -200 Q0 -270 85 -200 L85 0 Z" fill="#8A8178" {...S} />
          <path d="M-70 0 L-70 -195 Q0 -250 70 -195 L70 0 Z" fill="#7A4B2A" {...S} />
          <line x1={0} y1={-232} x2={0} y2={0} stroke="#111" strokeWidth={6} />
          {[-48, -24, 24, 48].map((x) => <line key={x} x1={x} y1={-215} x2={x} y2={-6} stroke="#5A3A22" strokeWidth={4} />)}
          <rect x={-60} y={-118} width={120} height={16} rx={4} fill="#4A4A4A" {...S} />
          <rect x={-14} y={-108} width={28} height={30} rx={5} fill="#C9A227" {...S} />
          <circle cx={0} cy={-96} r={4} fill="#111" />
        </g>
      );
    case 'temple':
      // a tall curved temple spire (rekha deula) with a wheel and flag on top
      return (
        <g transform="scale(0.72)">
          <rect x={-95} y={-70} width={190} height={70} fill="#E8D9B5" {...S} />
          <rect x={-22} y={-52} width={44} height={52} fill="#5A3A22" {...S} />
          <path d="M-80 -70 C-80 -200 -50 -300 -26 -340 L26 -340 C50 -300 80 -200 80 -70 Z" fill="#F1E6C8" {...S} />
          {[-120, -170, -220, -270].map((y) => <line key={y} x1={-74 + (y + 70) * -0.12} y1={y} x2={74 - (y + 70) * -0.12} y2={y} stroke="#C2B28A" strokeWidth={4} />)}
          <ellipse cx={0} cy={-348} rx={36} ry={12} fill="#D9C89E" {...S} />
          <line x1={0} y1={-360} x2={0} y2={-440} stroke="#111" strokeWidth={5} />
          <circle cx={0} cy={-378} r={14} fill="#C9A227" {...S} />
          <path d={`M0 -440 L${52 + Math.sin(t * 5) * 6} ${-428 + Math.sin(t * 5) * 3} L0 -414 Z`} fill="#E63946" {...S} />
        </g>
      );
    case 'jagannath':
      return <Deity kind="jagannath" t={t} />;
    case 'trinity':
      // Balabhadra, Subhadra, Jagannath (left to right, as seen in the temple)
      return (
        <g transform="scale(0.56)">
          <g transform="translate(-215,0)"><Deity kind="balabhadra" t={t + 0.7} /></g>
          <g transform="translate(0,0) scale(0.78)"><Deity kind="subhadra" t={t + 1.4} /></g>
          <g transform="translate(215,0)"><Deity kind="jagannath" t={t} /></g>
        </g>
      );
    case 'log': {
      // the sacred floating log (daru), bobbing with a soft glow
      const bob = Math.sin(t * 2.2) * 6;
      return (
        <g transform={`translate(0,${bob - 20}) rotate(${Math.sin(t * 1.6) * 2})`}>
          <g transform="translate(0,-25)"><Glow r={170} color="#FFE7A0" t={t} /></g>
          <rect x={-130} y={-48} width={260} height={52} rx={26} fill="#8B5E3C" {...S} />
          <path d="M-100 -34 Q-40 -26 20 -36 M-60 -14 Q10 -8 80 -18" stroke="#6B4226" strokeWidth={4} fill="none" />
          <ellipse cx={118} cy={-22} rx={14} ry={24} fill="#C89B6D" {...S} />
          <ellipse cx={118} cy={-22} rx={6} ry={12} fill="none" stroke="#8B5E3C" strokeWidth={3} />
          {[-80, 0, 70].map((x, i) => (
            <circle key={x} cx={x} cy={-70 - ((t * 40 + i * 25) % 50)} r={4} fill="#FFF3B0" opacity={1 - ((t * 40 + i * 25) % 50) / 50} />
          ))}
        </g>
      );
    }
    case 'chariot': {
      // a Rath Yatra chariot: big wheels, striped red-yellow canopy, Jagannath riding inside
      const roll = t * 40;
      return (
        <g>
          <path d="M-110 -205 L-70 -330 L70 -330 L110 -205 Z" fill="#D62828" {...S} />
          {[-1, 0, 1].map((k) => (
            <path key={k} d={`M${k * 40 - 14} -205 L${k * 22 - 8} -330 L${k * 22 + 8} -330 L${k * 40 + 14} -205 Z`} fill="#F2C230" />
          ))}
          <path d="M-110 -205 L-70 -330 L70 -330 L110 -205 Z" fill="none" {...S} />
          <path d="M-30 -330 Q0 -370 30 -330 Z" fill="#E9B828" {...S} />
          <line x1={0} y1={-360} x2={0} y2={-410} stroke={INK} strokeWidth={4} />
          <path d={`M0 -410 L${40 + Math.sin(t * 5) * 5} -400 L0 -390 Z`} fill="#E63946" {...S} />
          <rect x={-95} y={-215} width={190} height={12} fill="#8B5E3C" {...S} />
          {[-80, 80].map((x) => <rect key={x} x={x - 6} y={-205} width={12} height={95} fill="#8B5E3C" {...S} />)}
          <g transform="translate(0,-112) scale(0.33)"><Deity kind="jagannath" t={t} /></g>
          <rect x={-135} y={-112} width={270} height={30} fill="#7A4B2A" {...S} />
          {[-90, 0, 90].map((x) => (
            <g key={x} transform={`translate(${x},-42)`}>
              <circle r={42} fill="#B5651D" {...S} strokeWidth={5} />
              <g transform={`rotate(${roll})`}>
                {[0, 30, 60, 90, 120, 150].map((a) => (
                  <line key={a} x1={0} y1={-38} x2={0} y2={38} stroke={INK} strokeWidth={3} transform={`rotate(${a})`} />
                ))}
              </g>
              <circle r={9} fill="#F2C230" {...S} />
            </g>
          ))}
        </g>
      );
    }
    default:
      return null;
  }
};

// ---------- Jagannath, Balabhadra and Subhadra in their traditional temple form ----------
// big round eyes, broad smile, stump arms, crown and garland. Origin = ground, ~280 units tall.
const DEITY = {
  jagannath: {face: '#1B1B1F', rim: '#D62828', drape: '#F2C230', band: '#D62828', arms: true, oval: false},
  balabhadra: {face: '#F5F0E4', rim: '#D62828', drape: '#2A7F9E', band: '#F2C230', arms: true, oval: true},
  subhadra: {face: '#F2C230', rim: '#B5651D', drape: '#D62828', band: '#2A7F9E', arms: false, oval: false},
} as const;

export const Deity: React.FC<{kind: keyof typeof DEITY; t: number}> = ({kind, t}) => {
  const d = DEITY[kind];
  const dark = kind === 'jagannath';
  const line = dark ? '#000' : INK;
  const blink = (t % 4.2) > 4.05 ? 0.15 : 1; // a rare, gentle blink
  const sway = Math.sin(t * 1.4) * 1.5;
  return (
    <g transform={`rotate(${sway * 0.3}, 0, 0)`}>
      {/* pedestal */}
      <rect x={-80} y={-22} width={160} height={22} rx={4} fill="#7A4B2A" stroke={INK} strokeWidth={3.5} />
      <rect x={-70} y={-34} width={140} height={14} rx={3} fill="#C9A227" stroke={INK} strokeWidth={3} />
      {/* draped body */}
      <path d="M-62 -34 L-50 -110 L50 -110 L62 -34 Z" fill={d.drape} stroke={INK} strokeWidth={3.5} />
      <path d="M-57 -62 L57 -62 L59 -48 L-59 -48 Z" fill={d.band} />
      {/* stump arms reaching forward */}
      {d.arms ? (
        <>
          <rect x={-128} y={-138} width={66} height={26} rx={13} fill={d.face} stroke={line} strokeWidth={3.5} />
          <rect x={62} y={-138} width={66} height={26} rx={13} fill={d.face} stroke={line} strokeWidth={3.5} />
        </>
      ) : null}
      {/* garland */}
      {[...Array(9)].map((_, i) => {
        const a = Math.PI * (0.1 + 0.8 * (i / 8));
        return <circle key={i} cx={Math.cos(a) * -60} cy={-104 + Math.sin(a) * 22} r={8}
          fill={['#F77F00', '#FCBF49', '#E63946'][i % 3]} stroke={INK} strokeWidth={2} />;
      })}
      {/* head */}
      <rect x={-82} y={-252} width={164} height={142} rx={46} fill={d.face} stroke={line} strokeWidth={4} />
      {/* eyes */}
      {[-38, 38].map((x) => (
        <g key={x} transform={`translate(${x},-192) scale(1,${blink})`}>
          {d.oval
            ? <ellipse rx={24} ry={30} fill="white" stroke={d.rim} strokeWidth={7} />
            : <circle r={28} fill="white" stroke={d.rim} strokeWidth={7} />}
          <circle r={11} fill="#111" />
          <circle cx={-4} cy={-4} r={3.5} fill="white" />
        </g>
      ))}
      {/* tilak */}
      <path d="M-12 -250 Q0 -212 12 -250" fill="none" stroke={dark ? '#FFFFFF' : '#D62828'} strokeWidth={5} strokeLinecap="round" />
      <circle cx={0} cy={-228} r={5} fill="#D62828" />
      {/* nose and smile */}
      <path d="M-6 -168 Q0 -158 6 -168" fill="none" stroke={dark ? '#555' : '#9A7B4F'} strokeWidth={4} strokeLinecap="round" />
      <path d="M-56 -146 Q0 -112 56 -146 Q0 -128 -56 -146 Z" fill="#D62828" stroke={line} strokeWidth={2.5} />
      {/* crown */}
      <path d="M-76 -248 L-62 -296 L-34 -270 L0 -312 L34 -270 L62 -296 L76 -248 Z" fill="#E9B828" stroke={INK} strokeWidth={3.5} />
      {[-48, 0, 48].map((x, i) => <circle key={x} cx={x} cy={i === 1 ? -276 : -262} r={7} fill={i === 1 ? '#2A9D8F' : '#D62828'} stroke={INK} strokeWidth={2} />)}
    </g>
  );
};

// a slowly turning ring of soft light behind a deity (used by hero shots)
export const DivineRays: React.FC<{r: number; t: number}> = ({r, t}) => (
  <g transform={`rotate(${t * 8})`} opacity={0.5}>
    {[...Array(14)].map((_, i) => (
      <path key={i} d={`M0 0 L${r * 0.12} ${-r} L${-r * 0.12} ${-r} Z`} fill="#FFE7A0" transform={`rotate(${(i * 360) / 14})`} />
    ))}
  </g>
);

// ---------- above the head (origin = centre) ----------
export const OverheadProp: React.FC<{name: string; t: number}> = ({name, t}) => {
  const b = Math.sin(t * 4) * 5;
  const pop = Math.min(1, t * 4);
  const wrap = (child: React.ReactNode) => <g transform={`translate(0,${b}) scale(${pop})`}>{child}</g>;
  switch (name) {
    case 'lightbulb':
      return wrap(
        <g>
          <Glow r={70} color="#FFE45C" t={t} />
          <circle cy={-6} r={22} fill="#FFE45C" {...S} />
          <rect x={-10} y={14} width={20} height={12} fill="#9AA0A6" {...S} />
        </g>,
      );
    case 'question':
    case 'exclamation':
      return wrap(
        <text textAnchor="middle" y={22} fontSize={70} fontWeight={900} fill={name === 'question' ? '#7C5CFF' : '#E63946'}
          stroke={INK} strokeWidth={3} fontFamily="Arial Black, Arial, sans-serif">
          {name === 'question' ? '?' : '!'}
        </text>,
      );
    case 'heart':
      return wrap(<path d="M0 18 L-24 -6 Q-34 -24 -16 -30 Q-4 -32 0 -18 Q4 -32 16 -30 Q34 -24 24 -6 Z" fill="#E63946" {...S} />);
    case 'zzz':
      return wrap(<text textAnchor="middle" fontSize={40} fontWeight={900} fill={INK} fontFamily="Arial, sans-serif">z Z z</text>);
    case 'thought':
      return wrap(
        <g>
          <circle cx={-30} cy={40} r={6} fill="white" {...S} />
          <circle cx={-16} cy={24} r={10} fill="white" {...S} />
          <ellipse cx={20} cy={-10} rx={56} ry={34} fill="white" {...S} />
          <text x={20} y={6} textAnchor="middle" fontSize={40} fontWeight={900} fill="#7C5CFF" fontFamily="Arial, sans-serif">...</text>
        </g>,
      );
    default:
      return null;
  }
};

export const BIG_PROPS = new Set(['tree', 'hut', 'tower', 'boat']);
