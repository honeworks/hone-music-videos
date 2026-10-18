# 0001: Speech models on the OpenAI-compatible gateway, compared (2026-10-10)

The owner asked for the speech models the gateway lists to be compared on the owner's song (*The Long
Night*, 5:13, 43 sung lines), so the best one becomes the default `models.speech`. Decisions:
D-048 (how they are called), D-049 (the default).

## The probe (a 10 s slice, 1:26.5-1:36.5)

Every model took the request `whisper-1` takes (`POST /v1/audio/transcriptions`, `model`,
`response_format=verbose_json`, `timestamp_granularities[]=word`, `language`, `prompt`) and answered
`words` with `word`, `start`, `end` in seconds. So none was dropped and no other adapter was needed.

| Model | Reply |
|---|---|
| `whisper-1` | words, `duration`, the gateway's `estimated_cost` (0.001 USD for 10 s) |
| `scribe_v1`, `scribe_v2` (ElevenLabs) | words (with `speaker_id`), language `fas`, `estimated_cost` (0.000611 USD for 10 s), no `duration` |
| `groq.whisper-large-v3`, `groq.whisper-large-v3-turbo` | words, `duration`, no cost estimate |

`groq.whisper-large-v3-turbo` answered `403 permission_denied` ("Access denied. Please check your network
settings") once, then 200 on the next try; `groq.whisper-large-v3` failed once on a whole-song run and
worked on its retry.

## The whole song (the same prompt as the stage, no language)

Lines found: given sung lines matched in the heard words (`lyrics_match`, D-040). Δ: line starts
against the owner's approved timeline (`current/timeline.json` of the owner's project, read only),
median and maximum of |Δ| over the lines found. On the vocals: the song's vocals by `htdemucs` (D-045).
Onsets: of the lines found, how many start where the vocals get louder (the RMS of the 250 ms after
the start at least twice that of the 250 ms before): an independent check of the starts.

| Model | Audio | Run | Lines | Words | Time | Cost USD | Median Δ | Max Δ | Onsets |
|---|---|---|---|---|---|---|---|---|---|
| whisper-1 | mix | 1 | 40/43 | 297 | 29.5 s | 0.0313 | 40 ms | 3260 ms | 6/40 |
| whisper-1 | mix | 2 | 42/43 | 318 | 28.0 s | 0.0313 | 90 ms | 2260 ms | 9/42 |
| whisper-1 | mix | 3 | 41/43 | 299 | 27.2 s | 0.0313 | 100 ms | 2540 ms | 7/41 |
| whisper-1 | vocals | 1 | 42/43 | 312 | 24.7 s | 0.0313 | 190 ms | 28540 ms | 7/42 |
| whisper-1 | vocals | 2 | 40/43 | 309 | 27.6 s | 0.0313 | 190 ms | 28580 ms | 10/40 |
| whisper-1 | vocals | 3 | 42/43 | 316 | 25.5 s | 0.0313 | 195 ms | 28540 ms | 10/42 |
| scribe_v1 | mix | 1, 2 | 42/43 | 312 | 21.0, 24.2 s | 0.0191 | 470 ms | 3160 ms | 26/42 |
| scribe_v1 | vocals | 1, 2 | 42/43 | 311, 310 | 24.4, 23.2 s | 0.0191 | 490 ms | 3179 ms | 24/42 |
| scribe_v2 | mix | 1, 2, 3 | 42/43 | 312 | 16.8-22.7 s | 0.0191 | 470 ms | 3160 ms | 26/42 |
| scribe_v2 | vocals | 1, 2 | 42/43 | 312, 310 | 25.8, 20.3 s | 0.0191 | 490 ms | 3179 ms | 24/42 |
| scribe_v2 | vocals | 3 | 42/43 | 314 | 23.0 s | 0.0191 | 490 ms | 4460 ms | 22/42 |
| groq.whisper-large-v3 | mix | 1 | 39/43 | 438 | 16.9 s | - | 380 ms | 4180 ms | 9/39 |
| groq.whisper-large-v3 | mix | 2 | 41/43 | 467 | 13.9 s | - | 340 ms | 2320 ms | 10/41 |
| groq.whisper-large-v3 | vocals | 1 | 38/43 | 418 | 11.4 s | - | 420 ms | 5880 ms | 12/38 |
| groq.whisper-large-v3 | vocals | 2 | 28/43 | 383 | 12.4 s | - | 320 ms | 53688 ms | 10/28 |
| groq.whisper-large-v3-turbo | mix | 1 | 40/43 | 452 | 15.7 s | - | 490 ms | 2320 ms | 11/40 |
| groq.whisper-large-v3-turbo | mix | 2 | 39/43 | 435 | 15.9 s | - | 560 ms | 23900 ms | 8/39 |
| groq.whisper-large-v3-turbo | vocals | 1 | 41/43 | 362 | 9.3 s | - | 334 ms | 4788 ms | 15/41 |
| groq.whisper-large-v3-turbo | vocals | 2 | 40/43 | 398 | 13.2 s | - | 383 ms | 8098 ms | 12/40 |

The approved timeline's own starts are on an onset for 10 of its 43 lines.

## What it shows

- **Scribe is steady.** Every Scribe run found 42 of 43 lines (the last, "آخ… Lo-ren-am…", is
  missed by every model), on the mix and on the vocals; its replies were the same run to run (v1 and v2
  gave the same words: the gateway may serve one model under both names). `whisper-1` found 40 to 42, the
  Groq models 28 to 41.
- **Scribe's line starts are on the singing.** Its starts are about 470 ms later than the approved
  timeline's, whose times are `whisper-1`'s: Whisper's words follow each other with no pause (a line
  starts where the line before ended), so its line starts fall in the silence before the singing (6 to
  10 of 40-42 on an onset); Scribe leaves the pauses out (22 to 26 of 42 on an onset). The Δ columns
  measure agreement with Whisper, not truth.
- **Mishearings.** Scribe wrote the spoken intro whole and right ("من سلینا هستم. و این، قصه خونین من
  است…", Celina as سلینا), and no Latin letters. `whisper-1` began with "Moment Of Silence" and wrote
  سلیمه. The Groq models copied the prompt's Latin transliterations into the reply (Dah, Shamshir,
  Darvin, Kaa-ra-van: the echo D-040 rejects) and made up words ("PYM", "JBZ").
- **Price:** Scribe 0.0191 USD for the song (the gateway's estimate), `whisper-1` 0.0313. The Groq replies
  have no price.

## The listens again with each (the bad run rebuilt)

The first listen on the vocals with "موسیقی" every 2 s from 1:07 to 3:11 in place of what it heard there
(the owner's bad run; 62 such words are more than the matcher's `SEARCH = 40`, so every later line is
missing too), then the real windows (D-046): with `whisper-1` 5/43 became 26/43 in 16 listens
(4.7 cents; the last window over the cap), with `scribe_v2` 6/43 became 42/43 in 16 listens (2.8 cents).
With `whisper-1`'s first listen with nothing at all from 1:07 to 3:11: 22/43 became 38/43 in 11 listens.

## Spend

The comparison: about 0.46 USD (the Groq runs priced at Groq's list price, about 0.01 USD each).
