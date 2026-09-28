# 8. Sound and music data

The sound program is a sequencer. It has no notion of "the round theme" or "the jump sound": it has fifty-three
numbered commands, each of which names one or more channel records to fill from data in its ROM, and a byte code
that the channels interpret every timer tick. This chapter follows a command from the main CPU's queue to the
chip registers, decodes the data formats, and lists the commands.

## From the main CPU to the sound CPU

The main program does not write the sound latch directly from game code. Routines that want a sound push a byte
into a sixteen-entry queue at `$E381` (`sound_queue_push`, `$1387`), and the frame handler's per-frame list sends
the first queued byte to the latch `$FA00` once per VBLANK (`sound_queue_pump`, `$136C`), shifting the rest down.
So at most one command reaches the sound CPU per frame, in the order requested, and a routine that fires many
sounds in one frame simply fills the queue.

On the sound CPU the latch raises the NMI. The handler at `$0066` disables further NMIs, reads the byte and
appends it to its own sixteen-byte ring at `$8F82` (write index `$8F80`, read index `$8F81`; a full ring drops the
oldest entry), re-enables the NMI and returns. The main loop, running with interrupts disabled, drains the ring
(`$02A3`):

| Byte | Meaning |
| --- | --- |
| `$00-$34` | Play sound number n: look the command up in the table at `$329C` |
| `$35-$DF` | Ignored |
| `$EE` | All sound off: `$8FAA = 0`, and every later request is refused until |
| `$EF` | All sound on |
| `$F0` | Toggle echo mode: instead of playing, the sound CPU replies each command byte on the latch (a test hook) |
| `$F2 $F4 $F6 $F8` | Play an entry of a second table at `$3306` (unused by the game) |
| `$FF` | Ignored |

The queue and the ring exist because a command must not be lost while the sound CPU is busy in its interrupt
handler, which can run for most of a frame.

## Requests, headers and slots

Entry n of the table at `$329C` is a pointer. It points either at a **sound header** or, when the first byte is
below `$1B`, at a list: a count followed by that many header pointers, all requested together. The round theme,
command `$07`, is a list of nine headers, one per channel of the YM3526; the jump, command `$2C`, is a single
header.

A header is four bytes:

| Byte | Meaning |
| --- | --- |
| 0 | Kind: which channel record the sound occupies. `(kind & $FE) - $84` indexes a table of record addresses at `$0378` |
| 1 | High nibble: priority. Low nibble: loop count (0 = 16) |
| 2 | Number of steps |
| 3 | Follow-up: a command byte queued for the main loop when the sound ends (`$FF` = none) |

The kinds map onto the sound CPU's RAM like this:

| Kind | Record | Channel |
| --- | --- | --- |
| `$84`, `$86` | `$8000`, `$8070` | SSG channels A and B (112 bytes each) |
| `$8C`, `$8E` | `$80E0`, `$8170` | YM2203 FM channel 0, primary and alternate voice (288 bytes each) |
| `$90`, `$92` | `$8200`, `$8290` | YM2203 FM channel 1 |
| `$94`, `$96` | `$8320`, `$83B0` | YM2203 FM channel 2 |
| `$98`, `$9A` | `$8440`, `$8490` | YM3526 channel 0, first and second voice (80 bytes each) |
| `$9C`, `$9E` | `$84E0`, `$8530` | YM3526 channel 1 |
| ... | ... | ... |
| `$B8`, `$BA` | `$8940`, `$8990` | YM3526 channel 8 |

`request_sound` (`$0332`) claims the record for the header: if the record is idle it is taken; if it is playing,
the new sound wins only when its priority is not below the byte at `[5]` of the playing one (the priority of the
step it is in). The record gets flags = 1 (requested), the header pointer and the command number, and the next
timer tick starts it. This is the whole arbitration scheme, and it is where the two voices per channel matter:
the theme occupies the *second* voices of the nine YM3526 channels; an effect on a first voice takes the channel
for its duration (the second voice's writes are skipped while the first is playing) and the melody resumes
where it would have been, because the second voice keeps counting.

After the header come the **steps**, three bytes each: a priority nibble and a repeat nibble, then a pointer to
a **pattern**. A channel plays its steps in order, repeating each `repeat` times, and the whole sequence `loops`
times; then the sound ends and the follow-up byte is queued.

![Command, list, header, steps, pattern: the round theme's first channel.](../img/ch08-structure.svg)

## The pattern byte code

A pattern is a stream of bytes read by the channel's interpreter each time its note duration runs out. There
are three interpreters — for the YM3526 channels (`$077D`), the YM2203 FM channels (`$1557`) and the SSG
(`$243C`) — with the same shape and different command sets. For the FM channels:

| Byte | Meaning |
| --- | --- |
| `$00-$7F` | A duration: key the current note on for this many ticks, then continue with the next byte |
| `$8n-$Fn`, n < 12 | A note: n is the semitone (C to B, tables at `$0840` for the YM3526 and `$1619` for the YM2203), bits 4-6 the octave |
| `$8n-$Fn`, n >= 12 | A command: `(n - 12) + 4 x octave bits` selects one of 32 handlers; most take the next byte as an argument, a few take more |
| `$00` as a pattern's first byte | End of pattern: advance to the next step |

The commands set everything a note does not: the instrument (an index into the instrument table), the operator
levels, key scaling, the software envelope, vibrato, frequency sweeps, the tempo (timer A's period), a tie, a
volume scale, or a note with a detune byte. A second note in the same step, before any duration, marks a tie so
that the key is not retriggered.

Here is the first pattern of the theme's first channel (header `$3718`, YM3526 channel 0, second voice), as the
ROM has it and as the interpreter reads it:

```
7A68  24              rest for 36 ticks
7A69  CC B0 D4        extended command $B0: tempo, timer A period $D4
7A6C  CF 05           instrument 5
7A6E  D3              note D#, octave 5
7A6F  DC 18 00 00     vibrato: depth $18, rate 0, waveform 0
7A73  DD 04 0E        envelope: mask $04, one parameter $0E
7A76  18              ... play D#5 for 24 ticks
7A77  D3 0C           D#5 for 12
7A79  D2 18           D5 for 24
7A7B  D0 0C           C5 for 12
7A7D  D2 18           D5 for 24
7A7F  D3 0C           D#5 for 12
7A81  D5 30           F5 for 48
7A83  CA 24           A#4 for 36
7A85  D0 18           C5 for 24
7A87  C7 0C           G4 for 12
7A89  C7 18           G4 for 24
7A8B  D2 20           D5 for 32
7A8D  CF 00           instrument 0
7A8F  D3 ...
```

The other eight channels of the theme run the same tick clock with their own patterns — the second channel
doubles the melody through "note + detune" commands (`$8F xx`, the same notes slightly off pitch, a chorus)
with a volume command after every note, the third holds long bass notes — and because every channel's pattern is independent, a nine-voice
arrangement costs nine byte streams and no score.

## Instruments

Command 19 loads an instrument. For the YM3526 the table at `$28D7` holds pointers to variable-length records of about eighteen bytes: the
feedback and algorithm bits, the key-scale bits, then for each of the two operators an inverted level and six
envelope bytes (multiplier, key scale, attack/decay, sustain/release, waveform), followed by optional vibrato,
envelope and sweep parameters that the loader hands to the same routines the pattern commands use. The YM2203's
table at `$2A8A` has the four-operator version. Instrument 5, the theme's lead:

```
70 00 18 01 E0 44 02 01 F1 03 00 00 00 01 00 08 01 F5
```

The loader does not copy these bytes to the chip. It copies them into the channel record — bytes `[$18]` to
`[$4D]` for the YM3526 voice — and marks the record's dirty bits. The writer that runs at the end of the tick
(`$0CED` for a full rewrite after an instrument change, `$0D6B` for whatever changed since) turns the record into
register writes. Everything the chip ever receives goes through one of two routines: `$1DD6` writes a YM2203
register after waiting for the chip's busy flag, `$0ECB` writes a YM3526 register and pads the required delay
with NOPs.

## The tick

Both chips' timers are set up at boot (chapter 3). Timer A of the YM2203 paces the YM3526 channels, timer B the
YM2203's FM and SSG channels; the interrupt handler at `$0195` reads the status register, acknowledges whichever
timer expired, and runs the corresponding pass:

* **Timer A** (`$04D8`, `$0535`): for each of the nine YM3526 channels, first voice then second, write pending
  register changes, then count the note duration down; when it reaches zero read the next pattern bytes; then the
  per-tick effects — software envelope, LFO, sweep, pitch modulation — and the key-on/key-off writes. A command
  from the pattern can change timer A's period, which is how a tempo command takes effect at the next tick.
* **Timer B** (`$125E`, `$225B`): the same for the three YM2203 FM channels (each with an alternate record that
  plays when the primary is silent) and the two SSG channels, whose records shadow the SSG registers and write
  only the ones that changed.

A tick is roughly a sixty-fourth note at the theme's tempo; the durations in the patterns are in ticks, so `$18`
= 24 ticks is a dotted quarter at that scale. Nothing in the sound program refers to frames: it is paced entirely
by the chip timers, and the main CPU only ever says "play number 7".

## The commands

The fifty-three sound numbers, with the header kinds they use and where the game issues them (from the traced
play sessions; a few effects are only reached in situations the tracing did not visit):

| Command | Channels | Used for |
| --- | --- | --- |
| `$00` | list of 26 headers | Silence everything: a "stop" sound that claims every record with a short pattern; sent at boot and when a round ends |
| `$01`-`$04` | 9 / 9 / 3 / 3 | Silence lists for the YM3526 first voices, its second voices (the theme), the YM2203 primary and alternate voices: the same stop pattern as `$00`, aimed at one group |
| `$05`, `$06` | SSG A / B | Silence one SSG channel |
| `$07` | 9 YM3526 second voices | The main theme; started by the story intro and left running through the rounds |
| `$08` | 9 | The game-over jingle (task 0 sends it when the last player is gone) |
| `$09` | 3 | An effect |
| `$0A`, `$0B` | 9 / 9 | Music: `$0B` accompanies the GAME OVER text |
| `$0C`-`$0E` | YM2203 channel 1 | Effects: `$0D` the player is hit, `$0E` a rock bursts |
| `$0F`, `$10` | 9 / 9 | Music (the ending, the results) |
| `$11` | YM2203 channel 1 | An item is collected |
| `$13`, `$14`, `$19` | 9 each | Music: the secret room, EXTEND, the ending |
| `$15`-`$17`, `$1A`, `$1D`-`$22` | YM2203 channels 1 and 2 | Effects: `$22` is the fire breather's shot |
| `$25` | 1 | An enemy dies in the floor fire |
| `$29`-`$2B`, `$30`, `$32` | 9 each | More music (rounds with the message panels, the true ending) |
| `$2C` | YM2203 channel 0 | The jump |
| `$2D` | 3 | Sent at the end of boot |
| `$2E` | SSG A | An effect |
| `$2F`, `$31`, `$33` | YM2203 channel 0 | `$31` is the bubble blow, the most frequent sound in the game |
| `$34` | YM2203 channel 0, priority 1 | A coin |

The chain-pop scores of chapter 16 pick their fanfare from a six-byte table at `$46B7` in the main program by the
number of enemies popped: `$26` for two to four, `$27` for five to seven.

## The two chips in one word

The arrangement the tables describe is unusual for 1986: the nine-channel OPL chip, meant for music, plays the
music; the OPN chip, with its richer four-operator voices, is spent on the jump, the bubble and the coin — the
sounds a player hears hundreds of times an hour and that must never be delayed by a busy channel. The priority
byte in every header and step is the only mixing rule, and the two-voice channel record is what lets an effect
interrupt a melody line without silencing it.
