---
description: Add a new setting, pose, prop or icon to the stickman library
argument-hint: <what to add, e.g. "a pyramid setting" or "a horse prop">
---
Add this to the stickman drawing library: $ARGUMENTS

1. Add the name to the right list in src/story/catalog.ts (SETTINGS, POSES, PROPS, HELD or OVERHEAD).
2. Draw it in code in the matching file: src/story/Backgrounds.tsx (settings), src/story/Stickman.tsx (poses),
   src/story/Props.tsx (props, held items, overhead icons). Match the existing style: flat soft colours,
   dark #1d1d1d outlines ~3.5 units, simple shapes, and animate gently with `t` if it makes sense.
3. Add a scene using it to src/story/sample-story-props.json temporarily, render a still with
   `npx remotion still src/index.ts StoryShort out/preview.png --frame=<frame>` and look at the image.
   Iterate until it looks good in both StoryShort and StoryWide, then revert the sample change.
4. Run `npx tsc --noEmit` to make sure everything compiles.
The generator reads catalog.ts automatically, so Claude will start using the new asset in scripts.
