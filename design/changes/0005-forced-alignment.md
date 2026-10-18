# 0005: Time given lyrics by forced alignment to the vocals

## Status

`accepted` 2026-10-10 by the owner (asked for on 2026-10-10). The details are in
[decisions.md](../decisions.md) D-055 to D-059, accepted by the coordinator 2026-10-10 with these
answers: projects made before keep their timing, the weights get a file name of their own, lyrics are
still aligned on the mix (with a warning), and lines the aligner is unsure of are named.

## Context

Lines are timed from the words a speech model heard (D-003, D-016). Recognition misses lines: every
model missed the last line of the owner's song (*The Long Night*, 43 sung lines), `whisper-1` missed
others from run to run, and the listens again of 0002 exist only to find them. Recognition also puts a
line's start where the model's word starts, not where the singing starts: on the owner's song the
approved timeline (timed by `whisper-1`) starts lines a median 600 ms before the vocals begin, up to
1.9 s (D-049).

When the owner gives the lyrics, the words are known. Forced alignment places a known text on the audio:
it does not have to recognise anything, so it cannot miss a line, and it times every given word.

## Decision

1. **Align the given lyrics** (design §6 step 1c, D-055). In the `transcribe` stage, when the owner gave
   lyrics, the given sung lines (the `[bracketed]` notes left out) are aligned to the song's isolated
   vocals (the mix when they could not be isolated, D-045) with Meta's MMS forced aligner, torchaudio's
   `MMS_FA` bundle, on the CPU. Every given word gets its start and end in milliseconds. It is the
   optional extra `align` (torch, torchaudio, uroman); the weights (1.2 GB) download once to torch's
   cache. It lives in this library behind the `Models` port (`align`), like D-002 and D-041, until
   hone-models has an alignment client.
2. **Romanised text** (D-056). The aligner knows Latin letters only: each word goes through `uroman`;
   Latin transliterations in the lyrics stay as they are. A word with no letter left is not aligned.
3. **Instrumental passages** (D-057). A word is not sung across a pause of the vocals: when a pause of
   at least 300 ms lies between a word's letters, the word keeps the side with more letters. A token
   that absorbs what is not the text sits between words.
4. **Times from the aligner** (D-059). The lines are then timed from the aligned words instead of the
   heard words: the lyrics editor gets the aligned words in place of the heard ones and still only
   splits lines and marks sections and instrumental spans; the code takes every time from the aligned
   words. Times are still measured from the audio, never written by the LLM (D-003's spirit).
5. **Recognition stays** (D-058). The first listen and the listens again (0002) are made as before. Without
   given lyrics, or with the aligner off or not installed, the lines are timed from the heard words as
   before. With given lyrics, recognition is the cross-check: a line whose aligned start is more than
   750 ms from the start of the heard words it was found in is named in a warning, and so is a line
   the aligner placed with a low score (under 0.3). Aligned on the mix (no isolated vocals), the
   report says so.
6. **A setting** `models.align`, default `MMS_FA`; `null` turns alignment off. Projects made before
   keep their timing: stored settings without it mean it off (D-059).

## Consequences

- `words.json` gains `aligned` (the aligner, its time, the aligned words, the lines that disagree with
  recognition) and `not_aligned` (why the given lyrics could not be aligned). Both default to `None`,
  so older files load. The `transcribe` step is version 4, `lyrics` 3, `check_lyrics` 2.
- The `Models` port gains `align` (words with a score, `AlignedWord`). `check_lyrics` gains the
  `not-aligned`, `align-disagrees` and `align-unsure` warnings, and checks a line's times against the
  words it was timed from (aligned or heard).
- On the owner's song (D-055): about 50 s of CPU once the weights are cached, every one of the 43 lines
  placed, line starts within a median 38 ms of the vocals' onset (21 lines with a clear onset, all
  within 456 ms) where the approved timeline was a median 600 ms early.
- Settings stored before keep working and keep their timing: without `models.align` they read as
  alignment off.
