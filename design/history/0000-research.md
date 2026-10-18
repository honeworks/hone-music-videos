# 0000: The research behind the first design (October 2026)

Before hone-music-video existed, its pipeline was tried end to end in a private playground on one real
song: a story from an epic poem (a queen, an aging hero, his young son, a war horse), photoreal
live-action look, 27 planned shots. Every number below was measured on the reference machine: an
NVIDIA RTX 4060 Laptop GPU with **8 GB** of video memory and 30 GB of RAM. The owner judged every
side-by-side comparison; their verdicts are the decisions.

## Character sheets

- Four image models drew the same four character turnarounds, two takes each: Z-Image Turbo, FLUX.2 klein
  4B, Qwen-Image-Edit 2511 and RealVisXL (SDXL). **Z-Image Turbo** was the most photographic and framed
  full bodies best. Qwen-Image-Edit followed unusual details best but looked glossy. RealVisXL could not
  follow long prompts (its text encoder reads 77 tokens).
- The owner chose **one model for every character**: Z-Image Turbo, four takes, the owner picks one.
- Z-Image draws **three to five figures** whatever count is asked, and rarely a true three-quarter view.
  A cutter finds the figures by their heads and necks (they stand apart even when coats and weapons
  touch) and names them front, side and back.
- Some props cannot be drawn from words: an "ox-headed mace" came out as an axe in every take.
- Faces on a four-figure sheet are about 80 pixels tall, too small to carry identity. A **face portrait**
  drawn by a reference-taking model from the front and side views fixed that.

## Start frames

- **Qwen-Image-Edit 2511** with up to three reference pictures kept faces, costumes and props across
  scenes. A prompt that names each character by its images ("the woman from images 1 and 2") and says
  what changes in this shot (age, clothes, hair) keeps the reference from overruling the scene.
- Its look is glossy; a light **Z-Image image-to-image pass** (denoise 0.3) made it photographic. In the
  final video the difference is small, but it costs about 40 s a shot, so it stays.
- The **4-step** distilled LoRA was as good as the 8-step one at about half the time, and drawing at
  **1024x576** instead of 1664x928 made no visible difference in the video (the video model works at
  480p).
- A full 40-step render without the distilled LoRA took 26 minutes a picture and was not better.

## Clips

- **Wan 2.2 I2V 14B** (fp8, Apache-2.0) was the best image-to-video model that runs here. Of three
  setups (the 4-step distilled LoRA on both experts; the first steps without it for more natural motion;
  8 seconds instead of 5), the owner chose the **4-step "fast" setup**, and **8-second single clips**
  stayed smooth on calm and action shots alike, so long shots need no chaining.
- Faces are the weak point: in a wide shot at 480p a face is about 40 pixels and the eyes come and go
  frame to frame. **960x544** is clearly better; **1280x720 does not fit** in 8 GB (out of memory even
  with SageAttention and less reserved memory). In medium shots faces held well at 480p.
- **SageAttention** made Wan 22% faster with no visible difference; ComfyUI's fp8 matrix-multiply
  option gave nothing (Wan here is limited by moving weights, not by arithmetic).
- Clips come out at 16 fps and look choppy; **RIFE x2 to 32 fps** "looks great".
- Upscaling: SeedVR2 was sharper on paper but no better to the eye, sometimes worse, and took 14 minutes
  per 5-second clip; **Real-ESRGAN x2** (BSD-3) plus a resize does the job in about a minute.

## Time

For a 5-minute song (about 43 shots, one still each) the final stack takes about **8 hours** on the
reference machine: packs 0.5 h, stills 1.1 h, clips 5 h, finishing 1.1 h. Wan is about 60% of it; the
model load itself is only about 6 seconds per session, so loading models once saves time mostly in the
image steps. A 24 GB GPU would be roughly 5 to 15 times faster and would allow real 720p.

## Timing lyrics (literature)

Whisper's word error rate on sung vocals is much higher than on speech (one study: 0.56 sung against
0.14 spoken for the same lyrics), and its word times are approximate (tens to hundreds of milliseconds).
Known lyrics, given as the transcription prompt and aligned to the heard words, are the usual remedy.
Hence the design: measured word times, an LLM that only corrects text and structure, and a validator.

## Model limitations (literature and practice)

- Image-to-video prompts should describe **motion and camera, not the picture**; one action and **one
  camera move** per clip; name a static camera explicitly or the model invents a drift; combined moves
  (dolly plus tilt) fail; complex multi-subject interaction, rapid motion and ambiguous start frames
  degrade the result.
- Qwen-Image-Edit 2511 is reliable with **one to three** references; more degrade identity; results
  depend on the references themselves.

These limits are written into the planner's prompt (design §8).
