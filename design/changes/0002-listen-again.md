# 0002: Listen again for given lyrics lines Whisper did not hear

## Status

`accepted` 2026-10-10 by the owner: the owner chose the second listen and the in-library third listen.
Amended 2026-10-10 (robust listening, below; D-045 to D-047 accepted by the coordinator with the review's changes).
The details and the review's changes are in [decisions.md](../decisions.md) D-040 and D-041.

## Context

On the owner's song (*The Long Night*, 5:13), the gateway's `whisper-1` heard no words between
67 280 and 90 820 ms, the drum drop before Verse 1, so the given line "چُو Noh ماه بُگذَشتْ، زادی چُو
شیرْ!" was never heard. Times come only from heard words (D-003, D-016), so the line was dropped, the
editor marked the whole gap as an instrumental `break`, and `check_lyrics` only warned
`lyrics-not-found`.

## Decision

1. **Second listen** (design §6 step 1b, D-040). In the `transcribe` stage, the given sung lines are
   matched in order against the heard words, robust to Whisper's mishearings and to transliterations.
   Each run of lines not found is a gap between the found lines around it. The gap's slice of the
   song, 500 ms wider on each side, goes to the same transcriber with the missing lines as the prompt.
   The words it hears inside the gap, shifted to song time, replace the first listen's words there.
   At most 5 gaps per song, none longer than 30 s.
2. **Third listen** (design §6 step 1c, D-041). When the second listen still misses a line of the gap,
   the slice's vocals are isolated with Demucs `htdemucs` on the CPU and sent again with the same
   prompt. It is the optional extra `separate`. It lives in this library behind the `Models` port
   (`separate_vocals`), like D-002, until hone-models has a separation client. Without the extra, the
   listen is skipped and the lyrics report warns.
3. **Not heard.** A reply is not taken as heard when it has a word longer than 5 s (an invented time),
   or when it echoes the prompt (the given lines' own transliterations). The next listen is then tried.
4. **Still not heard.** The editor's instrumental spans are kept. `check_lyrics` warns
   `line-in-instrumental` where a missing line's gap is marked instrumental, so the owner checks it by
   ear at the gate.

Times stay measured: every line and word time is still a heard word's (D-003).

## Consequences

- `words.json` gains `listened_again` (each listen with its call, its rejection and its separation) and
  `not_listened`. Both default to empty, so older files load. The `transcribe` and `lyrics` steps are
  version 2.
- The settings gain `models.vocals` (default `htdemucs`). The `Models` port gains `separate_vocals`.
  `check_lyrics` gains the `not-listened` and `line-in-instrumental` warnings.
- A transcription costs a few tenths of a cent more per gap. A third listen adds about 35 s of CPU for a
  25 s slice.

## Amendment 2026-10-10: robust listening

Status: decided by the owner on 2026-10-10; the details (D-045 to D-047) accepted by the coordinator on 2026-10-10.

Hosted `whisper-1` is not deterministic on the owner's song. Across runs it once missed a line after the
drum drop (1:07-1:30), once heard only "موسیقی" ("music") from 1:07 to 3:11 (16 of 43 lines missing, and
the second listen skipped the gap because of the 30 s cap), and otherwise heard 42 or 43 lines. Three
changes make listening robust:

1. **First listen on the isolated vocals** (D-045). The whole song's vocals are isolated once with
   Demucs `htdemucs` on the CPU (the `separate` extra, `models.vocals`) and transcribed. They are kept in
   the project's `vocals/`, named after the model and the song's sha256 with their record, so a run made
   again does not separate again; `words.json` records the separation (`vocals`: model, time,
   sha256s). Without the extra, or when the separation fails, the first listen hears the mix and the
   lyrics report warns `not-listened` ("first listen on the mix, not the isolated vocals: …").
2. **Long gaps in windows** (D-046). A gap longer than 30 s is no longer skipped: it is listened to in
   consecutive windows of at most 30 s (with the 500 ms margin), each with the missing lines expected
   in it as the prompt (the gap's lines spread over its windows in order). Each window: the second
   listen is its slice of the mix, the third the same slice of the vocals (measured: mix first found
   one line more in one call fewer). The per-slice separation of decision 2 above is replaced by
   slices of the song's vocals. At most 16 listens again per song; windows and vocals listens past the
   cap are named. The echo and invented-time guard (decision 3) applies to every listen. After lines
   missed in a row, the matcher looks further for the next one, so a long run of hallucinated words
   does not hide every later line (review).
3. **A poor first listen made again** (D-047). When more than a third of the given sung lines are not
   found after the first listen, it is made once more; a listen that passes the guard of decision 3 is
   preferred, then the one that found more lines; both calls are recorded (`retried`).

Consequences: the `transcribe` step is version 3. `words.json` gains `vocals` and `retried` (both
default to `None`, so older files load). The project folder gains `vocals/`. A five-minute song costs
about 90 s of CPU once, and the first listen can cost twice; a bad run's windows cost a few cents more.
