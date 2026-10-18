# Timed lyrics (stages 1 to 4)

Every cut of the video lands on the lyrics, so the first stages time every sung line and word in integer
milliseconds, from the audio (design §5.1, §6).

1. **`measure`** reads the song with `ffprobe`: its length (`duration_ms`, the length of the video),
   sample rate and channels. WAV, FLAC, MP3, M4A and OGG work.
2. **`transcribe`** isolates the song's vocals with Demucs on the CPU (the optional `separate` extra;
   about 90 s for a five-minute song, once: they are kept in the project's `vocals/`) and sends them to
   the speech model (ElevenLabs' `scribe_v2` on the OpenAI-compatible gateway by default) with word timestamps. When you give the lyrics,
   their opening is passed as a hint, which helps a lot with sung words. Without the extra, or when the
   separation fails, the mix is sent and the lyrics report says why (and how to install the extra). The
   transcriber can vary from run to run (`whisper-1` does): when more than a third of your lines are
   not heard, the song is sent once more and the better listen kept. A given
   line still not heard (under drums, say) is **listened for again**: its stretch of the song, in
   windows of at most 30 s, goes back to the transcriber with the lines expected there as the hint,
   first the mix, then the vocals when that is not enough. At most 16 such listens per song; a reply
   that echoes the hint or has a word longer than 5 s is not taken as heard. Every listen is kept in
   `words.json` (`listened_again`, `retried`, `vocals`) (D-040, D-045 to D-047).

   **When you give the lyrics, they are then aligned to the vocals** (change 0005): Meta's MMS forced
   aligner (torchaudio's `MMS_FA`, the optional `align` extra) places your sung lines (not the
   `[bracketed]` notes) on the singing, on the CPU, about a minute for a five-minute song. It does not
   have to recognise the words, so it places every line, and its line starts land on the singing (on
   the owner's song a median 38 ms from where the vocals begin; `scribe_v2`'s were 60 ms, `whisper-1`'s 600 ms
   early). Non-Latin scripts are romanised with `uroman` first; Latin transliterations in your
   lyrics stay as they are. A word is not stretched across a pause of the vocals (an instrumental
   break). The lines are then timed from these aligned words (`words.json` `aligned`), and the
   transcriber's words are the cross-check: a line whose aligned start is more than 750 ms from where
   the transcriber heard it is named in the report, to check by ear, and so is a line the aligner is
   unsure of (a low score: on the owner's song the whispered outro line and the held last word). A line
   that is both, far from where it was heard and placed with a low score, is one the aligner lost (an
   outro put inside a guitar solo): it is timed from the transcriber's words instead, and the report
   says so (0032). A confident line more than 3 s from where it was heard is an error: an unattended
   project stops at the lyrics so you can set its times.
   Without isolated vocals the mix is aligned and the report says so. Without the extra, or when the
   aligner fails, the lines are timed from the heard words and the report says why; set
   `models.align` to `null` to turn alignment off. A project made before alignment keeps the timing
   it was made with; a run of it stopped before `check_lyrics` finished continues as a fork after
   upgrading, reusing the steps it finished.
3. **`lyrics`** is one call to the lyrics editor (a strong hosted LLM). It corrects misheard words from
   your lyrics (aligned words are your own words already), splits the lines as the song phrases them,
   groups them into sections and marks the instrumental spans; it never writes a time. The code takes
   every time from the aligned words, or the heard words without them: a line starts at its first word
   and ends at its last (D-016, D-059).
4. **`check_lyrics`** checks the result: times inside the song, lines in order without overlaps, words
   inside their line, each line within 150 ms of the words it was timed from, sections covering the
   lines. Errors block the gate; warnings (words no line uses, given lines not found in the audio,
   listens not made, a line not heard where an instrumental span is marked, lyrics not aligned or
   aligned on the mix, a line aligned and heard more than 750 ms apart, a line aligned with a low
   score: check these by ear) are shown.

**The lyrics gate (`review_lyrics`).** The run stops. In the dashboard's Lyrics view you can play every
line, read each finding under its line, fix a line's times, and **Approve**, or **Reject with note**: the
lyrics editor runs again with your note ("L004 belongs to the chorus"). The note box is always there;
pressing Approve with a note written asks whether you meant to reject (change 0018).

**Fixing the timing (0018).** The editor never moves a time, so a note cannot fix timing. Instead, open a
line's timing (the clock beside it): set its start or end to where the song is playing ("Set start
here", "Set end here"), or nudge either by ±100 ms or ±500 ms, play the line again, and **Save timing**.
The server checks the times (whole milliseconds, start before end, inside the song, no overlap with the
neighbouring lines) and refuses the whole save on any problem, naming each. The line's words move with
it, scaled within it; its section and the instrumental span beside it follow. `check_lyrics` runs again
on the edited timeline and is what the gate goes by; a line you timed is not held to its heard words.
Your times are kept in `current/lyrics/` (the edits, and each timeline they made, never overwritten),
and approving makes the edited timeline the one the cast planner, the shot planner and the assembly use.
If you then run the lyrics again with a note, the editor is asked to change the text only, and your
times are applied again to the lines whose ids remain; those that no longer fit are listed with why.

From the command line:

```text
hone-music-video status projects/my-song             # waiting for review_lyrics
hone-music-video lyrics-timing projects/my-song L012=77300-81200 L013=-   # L013's edit taken back
hone-music-video reject projects/my-song --note "L004 belongs to the chorus"
hone-music-video resume projects/my-song             # the lyrics stage runs again with the note
hone-music-video approve projects/my-song
```

The timeline is `current/timeline.json` once approved (design §4.1). Without given lyrics expect to
correct some lines: Whisper mishears sung words.

**Cost:** a few cents per song (one or two transcriptions, one editor call, and a fraction of a cent
per listen again). The alignment is local: about a minute of CPU.
