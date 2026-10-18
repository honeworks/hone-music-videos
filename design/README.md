# Why hone-music-video exists

> Give it a song. Get back a music video whose shots follow the story of the lyrics, whose characters
> stay the same person from the first shot to the last, and whose cuts land exactly on the lines, made
> with open models on a single consumer GPU.

## The problem

Making a story-driven music video with generative models is still a pile of manual steps:

- **Timing is done by hand.** Somebody scrubs through the song to find where each line starts. Speech
  tools mishear sung words, and a planner that guesses times produces cuts that drift off the lyrics.
- **Characters drift.** A text-to-image model draws a different face in every shot. Consistency needs
  reference sheets and a model that takes them, and somebody has to decide who needs a sheet.
- **Shot lists ignore what the models can do.** A planner asks for a sword fight in a crowd, a tiny face
  in a wide shot, or a 20-second take, and the local video model returns melting hands, vanishing eyes or
  a loop. The limits are known; they just never reach the planner.
- **Planning one shot at a time loses the story.** Calling a model per shot is slow, expensive and
  forgets what happened two shots earlier.
- **Long local runs are opaque.** Hours of generation with no way to see a frame early, redo one shot or
  resume after a crash.

## The core ideas

1. **Measured timing, not guessed timing.** Word timestamps come from a speech model; a strong LLM only
   fixes words, lines and sections; a validator checks every time against the audio. Every time is an
   integer number of milliseconds.
2. **Whole-song planning with the limits in the prompt.** One call plans the cast; one call plans every
   shot. The prompt carries the timed lyrics, the story, the characters, the style and a written
   description of what the local models can and cannot do, in words a planner can act on.
3. **References with a purpose.** Characters get turnaround sheets, cut into views, plus a face
   portrait; every shot names its cast and gets exactly their pictures. Sheets the user already has are
   reused, not redrawn.
4. **Local generation, chosen by evidence.** Every default model and setting was picked in side-by-side
   tests on an 8 GB GPU ([history/0000-research.md](history/0000-research.md)), and every one is a setting.
5. **Every stage is a resumable run with human gates.** The owner approves the timed lyrics, the cast,
   the sheets and the shot list before hours of GPU time are spent, and can redo any single shot.

## Non-goals

Writing or generating the music, lip-sync, dialogue scenes, live editing on a timeline, training models,
several users, hosted rendering. The output is a finished video file and every clip; finer editing
belongs in an editor.
