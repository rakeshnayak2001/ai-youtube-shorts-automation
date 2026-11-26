import {useVideoConfig} from 'remotion';

export const FONT =
  "Inter, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', 'Noto Sans Oriya', 'Noto Sans Devanagari', Arial, sans-serif";

export const useLayout = () => {
  const {width, height} = useVideoConfig();
  const vertical = height > width;
  const s = (Math.min(width, height) / 1080) * (vertical ? 1.15 : 1); // scale unit
  return {width, height, vertical, s};
};
