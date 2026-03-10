---
description: Create and render Remotion video projects using AI
---

# Remotion Video Generation Workflow

This workflow guides you through creating and rendering motion graphics videos using Remotion.

## Prerequisites

- Container: `antigravity`
- Tools already installed: Node.js, FFMPEG, @remotion/cli, bun

## Step 1: Create a New Project

```bash
cd /home/node/remotion_projects
bun create video my_video_project
cd my_video_project
```

## Step 2: Install Remotion Skills (AI Agent Support)

```bash
npx skills add remotion-dev/skills
```

This enables AI agents to understand Remotion best practices.

## Step 3: Edit Video Composition

Modify `src/Root.tsx` or create new components in `src/`.

Key Remotion concepts:

- `<Composition>`: Defines a video with width, height, fps, durationInFrames
- `<Sequence>`: Adds timing to child elements
- `useCurrentFrame()`: Hook to animate based on current frame
- `interpolate()`: Smoothly animate values between frames

## Step 4: Preview

```bash
npm run dev
```

Opens preview at <http://localhost:3000>

## Step 5: Render to Video

```bash
npx remotion render src/index.ts MyComposition out/video.mp4
```

## Example: Simple Text Animation

```tsx
import {useCurrentFrame, interpolate, AbsoluteFill} from 'remotion';

export const MyText = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1]);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <h1 style={{opacity, fontSize: 100}}>Hello Remotion!</h1>
    </AbsoluteFill>
  );
};
```

## Tips

- Use `npx remotion preview` for live editing
- Export as MP4, WebM, or GIF
- Remotion docs: <https://www.remotion.dev/docs>
