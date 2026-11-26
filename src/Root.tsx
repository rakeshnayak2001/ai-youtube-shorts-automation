import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Video} from './Video';
import {StoryVideo} from './story/StoryVideo';
import {FilmVideo} from './film/FilmVideo';
import filmSample from './film/sample-film-props.json';
import storySample from './story/sample-story-props.json';
import {VideoProps} from './types';
import sample from './sample-props.json';

export const FPS = 30;
const TAIL_SECONDS = 0.6;

const calc: CalculateMetadataFunction<VideoProps> = ({props}) => ({
  durationInFrames: Math.max(
    FPS * 3,
    Math.ceil((props.timings.total + TAIL_SECONDS) * FPS),
  ),
});

export const RemotionRoot: React.FC = () => (
  <>
    {/* Shorts / Reels */}
    <Composition
      id="Short"
      component={Video}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={300}
      defaultProps={sample as unknown as VideoProps}
      calculateMetadata={calc}
    />
    {/* Regular YouTube video */}
    <Composition
      id="Wide"
      component={Video}
      width={1920}
      height={1080}
      fps={FPS}
      durationInFrames={300}
      defaultProps={sample as unknown as VideoProps}
      calculateMetadata={calc}
    />
    {/* Cinematic AI film format (Veo / Gemini Omni clips) */}
    <Composition
      id="FilmShort"
      component={FilmVideo}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={300}
      defaultProps={filmSample as unknown as VideoProps}
      calculateMetadata={calc}
    />
    <Composition
      id="FilmWide"
      component={FilmVideo}
      width={1920}
      height={1080}
      fps={FPS}
      durationInFrames={300}
      defaultProps={filmSample as unknown as VideoProps}
      calculateMetadata={calc}
    />
    {/* Stickman story format */}
    <Composition
      id="StoryShort"
      component={StoryVideo}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={300}
      defaultProps={storySample as unknown as VideoProps}
      calculateMetadata={calc}
    />
    <Composition
      id="StoryWide"
      component={StoryVideo}
      width={1920}
      height={1080}
      fps={FPS}
      durationInFrames={300}
      defaultProps={storySample as unknown as VideoProps}
      calculateMetadata={calc}
    />
  </>
);
