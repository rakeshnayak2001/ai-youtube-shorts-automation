import React from 'react';

const INK = '#2a2a2a';
const S = {stroke: INK, strokeWidth: 3, strokeLinejoin: 'round' as const};

const SKY: Record<string, [string, string]> = {
  day: ['#86C5EE', '#E3F3FB'],
  dusk: ['#4B3B78', '#F4A06B'],
  night: ['#0A1230', '#28335C'],
};

const rand = (seed: number) => {
  let x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
};

const shade = (hex: string, f: number) => {
  const n = parseInt(hex.slice(1), 16);
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v * f)));
  return `rgb(${c((n >> 16) & 255)},${c((n >> 8) & 255)},${c(n & 255)})`;
};

type P = {setting: string; time: string; w: number; h: number; groundY: number; t: number};

const Sky: React.FC<P> = ({time, w, h, t}) => {
  const [a, b] = SKY[time] ?? SKY.day;
  const u = Math.min(w, h) / 1080;
  return (
    <g>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={a} />
          <stop offset="100%" stopColor={b} />
        </linearGradient>
      </defs>
      <rect width={w} height={h} fill="url(#sky)" />
      {time === 'night'
        ? [...Array(70)].map((_, i) => (
            <circle key={i} cx={rand(i) * w} cy={rand(i + 99) * h * 0.55} r={(1 + rand(i + 7) * 2.2) * u}
              fill="white" opacity={0.5 + 0.5 * Math.sin(t * 2 + i)} />
          ))
        : null}
      {time === 'night' ? (
        <g transform={`translate(${w * 0.78},${h * 0.13})`}>
          <circle r={60 * u} fill="#FFF6D5" />
          <circle cx={22 * u} cy={-12 * u} r={52 * u} fill={a} />
        </g>
      ) : time === 'dusk' ? (
        <circle cx={w * 0.25} cy={h * 0.42} r={110 * u} fill="#FFB36B" opacity={0.9} />
      ) : (
        <circle cx={w * 0.8} cy={h * 0.12} r={70 * u} fill="#FFE07A" stroke="#F4B93A" strokeWidth={4} />
      )}
      {time !== 'night'
        ? [0, 1, 2].map((i) => {
            const x = ((rand(i + 3) * w + t * 12 * u * (i + 1)) % (w + 400 * u)) - 200 * u;
            const y = h * (0.08 + i * 0.09);
            return (
              <g key={i} transform={`translate(${x},${y}) scale(${u})`} opacity={0.9}>
                <ellipse rx={90} ry={30} fill="white" />
                <ellipse cx={-40} cy={8} rx={60} ry={24} fill="white" />
                <ellipse cx={50} cy={6} rx={60} ry={22} fill="white" />
              </g>
            );
          })
        : null}
    </g>
  );
};

const Ground: React.FC<{y: number; w: number; h: number; color: string}> = ({y, w, h, color}) => (
  <g>
    <rect x={0} y={y} width={w} height={h - y} fill={color} />
    <path d={`M0 ${y} Q${w * 0.25} ${y - 10} ${w * 0.5} ${y} T${w} ${y}`} fill="none" stroke={INK} strokeWidth={3} />
  </g>
);

const Tree: React.FC<{x: number; y: number; s: number; c?: string}> = ({x, y, s, c = '#4F9D5D'}) => (
  <g transform={`translate(${x},${y}) scale(${s})`}>
    <rect x={-10} y={-120} width={20} height={120} fill="#7A4B2A" {...S} />
    <circle cx={-32} cy={-130} r={40} fill={c} {...S} />
    <circle cx={32} cy={-134} r={38} fill={c} {...S} />
    <circle cx={0} cy={-170} r={48} fill={c} {...S} />
  </g>
);

export const Background: React.FC<P> = (p) => {
  const {setting, time, w, h, groundY, t} = p;
  const u = Math.min(w, h) / 1080;
  const horizon = groundY - (h > w ? h * 0.1 : h * 0.16);
  const green = '#8CC06B';
  let body: React.ReactNode = null;

  switch (setting) {
    case 'cave': {
      const ax = w / 2;
      const aw = Math.min(w * 0.5, 900 * u);
      const top = horizon - h * 0.3;
      body = (
        <g>
          <Ground y={horizon} w={w} h={h} color="#8A6E55" />
          <path
            fillRule="evenodd"
            d={`M0 0 H${w} V${h} H0 Z M${ax - aw / 2} ${groundY + 20} Q${ax - aw / 2} ${top} ${ax} ${top} Q${ax + aw / 2} ${top} ${ax + aw / 2} ${groundY + 20} Z`}
            fill="#4A372B"
            {...S}
          />
          {[...Array(9)].map((_, i) => {
            const x = (i + 0.5) * (w / 9);
            const len = (40 + rand(i) * 70) * u;
            return <path key={i} d={`M${x - 22 * u} 0 L${x} ${len} L${x + 22 * u} 0 Z`} fill="#3A2B22" {...S} />;
          })}
          <rect x={0} y={groundY + 20} width={w} height={h} fill="#5B4535" />
          {[...Array(6)].map((_, i) => (
            <path key={i} d={`M${rand(i + 40) * w} ${groundY + 60 * u + rand(i) * 200 * u} q20 -14 40 0`} stroke="#3A2B22" strokeWidth={4} fill="none" />
          ))}
        </g>
      );
      break;
    }
    case 'forest':
    case 'campfire':
      body = (
        <g>
          {[...Array(10)].map((_, i) => (
            <Tree key={`b${i}`} x={(i + 0.3) * (w / 9)} y={horizon + 10 * u} s={0.9 * u} c="#3E7F4C" />
          ))}
          <Ground y={horizon} w={w} h={h} color={setting === 'campfire' ? '#6F9A55' : green} />
          <Tree x={w * 0.06} y={groundY + 30 * u} s={1.5 * u} />
          <Tree x={w * 0.95} y={groundY + 40 * u} s={1.6 * u} />
        </g>
      );
      break;
    case 'village':
      body = (
        <g>
          <path d={`M0 ${horizon} Q${w * 0.3} ${horizon - 80 * u} ${w * 0.6} ${horizon} T${w} ${horizon - 20 * u} V${h} H0Z`} fill="#77AD5C" {...S} />
          {[0.18, 0.5, 0.82].map((x, i) => (
            <g key={i} transform={`translate(${w * x},${horizon + 8 * u}) scale(${0.55 * u})`}>
              <rect x={-70} y={-90} width={140} height={90} fill="#C8A27A" {...S} />
              <path d="M-95 -86 L0 -170 L95 -86 Z" fill="#D9B44A" {...S} />
              <rect x={-16} y={-50} width={32} height={50} fill="#5A3A22" {...S} />
            </g>
          ))}
          <Ground y={horizon + 6 * u} w={w} h={h} color={green} />
          <path d={`M0 ${groundY + 40 * u} Q${w / 2} ${groundY + 10 * u} ${w} ${groundY + 50 * u}`} stroke="#C9A66B" strokeWidth={50 * u} fill="none" opacity={0.6} />
        </g>
      );
      break;
    case 'city':
      body = (
        <g>
          {[...Array(12)].map((_, i) => {
            const bw = w / 10;
            const bh = (180 + rand(i) * 360) * u;
            const x = i * bw * 0.9 - bw * 0.3;
            return (
              <g key={i}>
                <rect x={x} y={horizon - bh} width={bw * 0.85} height={bh + 4} fill={i % 2 ? '#8B95A7' : '#A3ACBC'} {...S} />
                {[...Array(Math.floor(bh / (50 * u)))].map((_, r) =>
                  [0, 1, 2].map((c) => (
                    <rect key={`${r}${c}`} x={x + bw * (0.12 + c * 0.24)} y={horizon - bh + 20 * u + r * 50 * u}
                      width={bw * 0.14} height={24 * u}
                      fill={time === 'night' ? (rand(i * 31 + r * 7 + c) > 0.4 ? '#FFE07A' : '#2B3350') : '#D6E6F5'} />
                  )),
                )}
              </g>
            );
          })}
          <Ground y={horizon} w={w} h={h} color="#6C7380" />
          <rect x={0} y={groundY - 6 * u} width={w} height={14 * u} fill="#B8BEC8" />
          {[...Array(8)].map((_, i) => (
            <rect key={i} x={i * (w / 7)} y={groundY + 80 * u} width={w / 14} height={10 * u} fill="#E8E8E8" />
          ))}
        </g>
      );
      break;
    case 'desert':
      body = (
        <g>
          <path d={`M${w * 0.55} ${horizon} L${w * 0.68} ${horizon - 150 * u} L${w * 0.81} ${horizon} Z`} fill="#D9B262" {...S} />
          <path d={`M${w * 0.75} ${horizon} L${w * 0.84} ${horizon - 100 * u} L${w * 0.93} ${horizon} Z`} fill="#CFA555" {...S} />
          <path d={`M0 ${horizon} Q${w * 0.25} ${horizon - 60 * u} ${w * 0.5} ${horizon} T${w} ${horizon} V${h} H0Z`} fill="#EDCB7A" {...S} />
          <path d={`M0 ${groundY - 20 * u} Q${w * 0.4} ${groundY - 70 * u} ${w} ${groundY - 10 * u} V${h} H0Z`} fill="#F2D58E" />
        </g>
      );
      break;
    case 'river':
    case 'ocean': {
      const waterTop = horizon + (setting === 'ocean' ? 0 : 40 * u);
      const waterBot = setting === 'ocean' ? groundY - 70 * u : waterTop + 120 * u;
      body = (
        <g>
          {setting === 'ocean' ? null : <Ground y={horizon} w={w} h={h} color={green} />}
          <rect x={0} y={waterTop} width={w} height={waterBot - waterTop} fill={time === 'night' ? '#244A7A' : '#4FA3D9'} {...S} />
          {[...Array(10)].map((_, i) => {
            const y = waterTop + ((i % 3) + 0.5) * ((waterBot - waterTop) / 3);
            const x = ((rand(i) * w + t * 30 * u) % w);
            return <path key={i} d={`M${x} ${y} q15 -8 30 0 t30 0`} stroke="white" strokeWidth={3} fill="none" opacity={0.7} />;
          })}
          {setting === 'ocean' ? (
            <>
              <rect x={0} y={waterBot} width={w} height={h - waterBot} fill="#F2D58E" />
              <path d={`M0 ${waterBot} Q${w / 4} ${waterBot + 14 * u} ${w / 2} ${waterBot} T${w} ${waterBot}`} stroke={INK} strokeWidth={3} fill="none" />
            </>
          ) : (
            <rect x={0} y={waterBot} width={w} height={h - waterBot} fill={green} />
          )}
        </g>
      );
      break;
    }
    case 'mountains':
      body = (
        <g>
          {[[0.2, 420], [0.5, 560], [0.82, 460]].map(([x, mh], i) => (
            <g key={i}>
              <path d={`M${w * x - mh * u * 0.9} ${horizon} L${w * x} ${horizon - mh * u} L${w * x + mh * u * 0.9} ${horizon} Z`} fill="#8C93A8" {...S} />
              <path d={`M${w * x - mh * u * 0.22} ${horizon - mh * u * 0.75} L${w * x} ${horizon - mh * u} L${w * x + mh * u * 0.22} ${horizon - mh * u * 0.75} L${w * x + 10 * u} ${horizon - mh * u * 0.68} Z`} fill="white" {...S} />
            </g>
          ))}
          <Ground y={horizon} w={w} h={h} color={green} />
        </g>
      );
      break;
    case 'field':
    case 'market':
      body = (
        <g>
          <path d={`M0 ${horizon} Q${w * 0.3} ${horizon - 70 * u} ${w * 0.6} ${horizon - 10 * u} T${w} ${horizon} V${h} H0Z`} fill="#77AD5C" {...S} />
          <Ground y={horizon + 10 * u} w={w} h={h} color={setting === 'market' ? '#D9B38C' : green} />
          {setting === 'field'
            ? [...Array(30)].map((_, i) => (
                <circle key={i} cx={rand(i) * w} cy={horizon + 40 * u + rand(i + 5) * (h - horizon)} r={5 * u}
                  fill={['#F7D154', '#F08CA0', '#FFFFFF'][i % 3]} />
              ))
            : [0.12, 0.88].map((x, i) => (
                <g key={i} transform={`translate(${w * x},${groundY - 10 * u}) scale(${u})`}>
                  <rect x={-110} y={-120} width={220} height={120} fill="#C8A27A" {...S} />
                  {[...Array(6)].map((_, k) => (
                    <path key={k} d={`M${-130 + k * 44} -170 h44 l-6 50 h-32 Z`} fill={k % 2 ? '#E63946' : '#FFFFFF'} {...S} />
                  ))}
                  {[...Array(4)].map((_, k) => <circle key={k} cx={-75 + k * 50} cy={-135} r={14} fill={['#F4A261', '#E9C46A', '#8AB17D', '#E76F51'][k]} {...S} />)}
                </g>
              ))}
        </g>
      );
      break;
    case 'room':
    case 'office': {
      const wallBottom = groundY - 40 * u;
      body = (
        <g>
          <rect width={w} height={wallBottom} fill={setting === 'office' ? '#DDE3EA' : '#EADBC8'} />
          <rect x={w * 0.62} y={wallBottom - 460 * u} width={300 * u} height={260 * u} fill={`url(#sky)`} {...S} strokeWidth={6} />
          <line x1={w * 0.62 + 150 * u} y1={wallBottom - 460 * u} x2={w * 0.62 + 150 * u} y2={wallBottom - 200 * u} stroke={INK} strokeWidth={5} />
          <rect x={w * 0.12} y={wallBottom - 420 * u} width={170 * u} height={130 * u} fill="#F7D154" {...S} strokeWidth={5} />
          <rect x={0} y={wallBottom} width={w} height={h - wallBottom} fill={setting === 'office' ? '#9AA5B1' : '#B08968'} />
          <line x1={0} y1={wallBottom} x2={w} y2={wallBottom} stroke={INK} strokeWidth={4} />
          {setting === 'office' ? (
            <g transform={`translate(${w * 0.82},${groundY}) scale(${u})`}>
              <rect x={-120} y={-110} width={240} height={18} fill="#8B5E3C" {...S} />
              <line x1={-100} y1={-92} x2={-100} y2={0} stroke={INK} strokeWidth={8} />
              <line x1={100} y1={-92} x2={100} y2={0} stroke={INK} strokeWidth={8} />
              <path d="M-50 -112 L-42 -176 L42 -176 L50 -112 Z" fill="#2B2F36" {...S} />
              <path d="M-38 -120 L-32 -168 L32 -168 L38 -120 Z" fill="#7DD3FC" />
            </g>
          ) : null}
        </g>
      );
      break;
    }
    case 'space':
      body = (
        <g>
          <rect width={w} height={h} fill="#05060F" />
          {[...Array(120)].map((_, i) => (
            <circle key={i} cx={rand(i) * w} cy={rand(i + 300) * h} r={(0.8 + rand(i + 5) * 2) * u} fill="white" opacity={0.4 + 0.6 * rand(i + 9)} />
          ))}
          <circle cx={w * 0.78} cy={h * 0.18} r={120 * u} fill="#4FA3D9" {...S} />
          <path d={`M${w * 0.78 - 90 * u} ${h * 0.16} q60 -40 120 10 q-30 50 -110 20z`} fill="#77AD5C" />
          <Ground y={horizon} w={w} h={h} color="#9A9A9A" />
          {[...Array(8)].map((_, i) => (
            <ellipse key={i} cx={rand(i + 60) * w} cy={horizon + 40 * u + rand(i + 61) * (h - horizon - 60 * u)} rx={50 * u} ry={14 * u} fill="#7E7E7E" {...S} />
          ))}
        </g>
      );
      break;
    default:
      body = <Ground y={horizon} w={w} h={h} color={green} />;
  }

  const indoor = setting === 'room' || setting === 'office' || setting === 'space';
  return (
    <svg width={w} height={h} style={{position: 'absolute', inset: 0}}>
      {setting !== 'space' ? <Sky {...p} /> : null}
      {setting === 'room' || setting === 'office' ? null : null}
      {body}
      {!indoor && time === 'night' ? <rect width={w} height={h} fill="#0A1030" opacity={0.38} /> : null}
      {!indoor && time === 'dusk' ? <rect width={w} height={h} fill="#7A3B5A" opacity={0.12} /> : null}
      {setting === 'room' && time === 'night' ? <rect width={w} height={h} fill="#0A1030" opacity={0.25} /> : null}
    </svg>
  );
};

export {shade};
