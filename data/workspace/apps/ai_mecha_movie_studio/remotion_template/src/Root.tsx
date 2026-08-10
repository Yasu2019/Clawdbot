import React from 'react';
import {AbsoluteFill, Composition, Sequence, Video, staticFile} from 'remotion';

type Scene = {file: string; from: number; duration: number};

const scenes: Scene[] = [
  {file: 'scene_001.mp4', from: 0, duration: 150},
];

const Main: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      {scenes.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.duration}>
          <Video src={staticFile(s.file)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <Composition id="Main" component={Main} durationInFrames={1800} fps={30} width={1280} height={720} />
);
