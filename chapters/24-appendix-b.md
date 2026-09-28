# Appendix B. Record layouts

The program keeps every moving thing in a fixed-size record, and the records share a convention: byte 0 is a
state or flag byte, bytes 1 and 2 are the position (x vertical, counted upwards; y horizontal), bytes 3 and 4
point at the object entry that draws it. What follows byte 4 differs per kind. These tables gather the layouts
that the chapters use; offsets are hexadecimal and relative to the record's first byte, as the code writes them
(`IX+$nn`).

## The object entry (4 bytes, 90 at `$E1CD`; hardware copy at `$DD00`)

| Byte | Meaning |
| --- | --- |
| 0 | `256 - y`: the vertical position, negated |
| 1 | Bits 7-5 the shape (a line of the video PROM); bits 4-0 the column of video RAM that holds the tiles |
| 2 | x: the horizontal position |
| 3 | Bits 3-0 the tile bank (× 1024); bit 6: x is negative |

Four zero bytes are skipped. Entries 0-15 are the playfield columns, 16-65 the sprites (24 bubbles first), 66-89 the
panels and text objects.

## The video cell (2 bytes, in the 128-byte columns of `$C000-$DCFF`)

| Byte | Meaning |
| --- | --- |
| 0 | Tile number, low eight bits |
| 1 | Bits 1-0 tile number bits 9-8; bits 5-2 colour group; bit 6 flip x; bit 7 flip y |

Sprites for bubbles, players and enemies are object bank 2, so the full tile number is `low + 256 × (attr & 3) +
2048`; items, fruit and captured enemies are bank 3 (`+ 3072`).

## The player record (50 bytes: `$E691` player 1, `$E6C3` player 2)

| Offset | Field | Values |
| --- | --- | --- |
| `+$00` | State | 0 waiting, 1 alive, `$10` caught (set by the sub CPU), 2 dying, 4 and `$80` dead |
| `+$01`, `+$02` | x, y | Copied from the object slot each frame |
| `+$03`, `+$04` | Object slot pointer | `$E2C5` (player 1), `$E2B5` (player 2) |
| `+$05`, `+$06` | Animation frame, tick | Against the table at `$4583` |
| `+$07` | Colour attribute | `$18` Bub, `$19` Bob |
| `+$08` | Facing | 1 right, 0 left; read by the sub CPU |
| `+$09` | Player index | 0 or 1 |
| `+$0A` | Bubble button flags | Bit 0 blowing, bit 1 held, bit 2 blow animation running |
| `+$0B` | Falling | Bit 0: airborne without a jump |
| `+$0C` | Jump flags | Bit 0 jumping, 1 held, 3 right, 4 left, 5 straight up, 6 sideways blocked |
| `+$0D`-`+$11` | Jump arc | Pointer into the table at `$4AEC`, dy, steps left, step index |
| `+$12` | Animation | 0 stand, 8 walk, `$18` fall, `$20` jump, `$30` pushed, `$38` burnt, `$40`-`$58` blowing, `$FF` none |
| `+$13`-`+$16` | Item invincibility | Flag and 900-frame timer |
| `+$18` | Air-control counter | 1 px every third frame while airborne |
| `+$19`, `+$1A` | Death variant, score colour | Bit 0 of `+$19`: burnt |
| `+$1B`, `+$1C` | Burnt, burn timer | 30 frames without control |
| `+$1F`, `+$20` | Speed pattern index, step | Next entry of the speed list: pixels this frame |
| `+$21`, `+$22` | Pushed by a bubble | Written by the sub CPU; `+$22` signed pixels |
| `+$23` | Pose | 0 standing, 1 rising, 2 walking right, 3 falling, 4 walking left |
| `+$24` | Bounce request | Bit 0 set by the sub CPU on landing on a bubble |
| `+$25` | Invincibility frames | 180 after a respawn |
| `+$26`, `+$27`, `+$28` | Blow cooldown, chain timer, bubbles left | `+$26` reloaded from `+$2E`; `+$27` counts 90 |
| `+$2A` | Extra lives pending | One per respawn |
| `+$2C` | Tick-rate index | One of four animation rates |
| `+$2D` | Mode bits | Bit 0 walking scores, 1 jumping scores, 2 blowing scores, 6 extra-life bubbles |
| `+$2E`, `+$2F` | Blow reload, bubble range | 20 and 3; 5 and 6 for the fast player |
| `+$30` | Speed list | 12 normally, 20 fast, 22 invincible |
| `+$31` | Bubble speed parameter | `$40`, copied into the blow request |

## The blow request (6 bytes: `$E75E` player 1, `$E764` player 2)

| Byte | Meaning |
| --- | --- |
| 0 | Pending flag |
| 1, 2 | x, y of the mouth |
| 3 | Facing |
| 4 | Range (`+$2F` of the player) |
| 5 | Speed parameter (`+$31`) |

## The bubble record (40 bytes, 24 at `$E76C`)

| Offset | Field | Values |
| --- | --- | --- |
| `+$00` | State | 0 free, 1 floating, 2 in flight, 4 holding an enemy, 8 EXTEND letter, `$10` special, `$20` lightning bolt, `$40` falling fire, `$80` popping |
| `+$01`, `+$02` | x, y | From the object slot |
| `+$03`, `+$04` | Object slot | `$E20D + 4n` |
| `+$07` | Slot code | For the sprite routines |
| `+$0A` | Current nibble | The last one read from the map |
| `+$0B` | Counted | Bit 0: already counted out of `bubbles_active` |
| `+$0C`, `+$0D` | Lifetime | 60-frame tick, periods left |
| `+$0E` | Phase | 0, 1 owner's colour; 2, 3 ageing; `$FF` pop now |
| `+$0F` | Direction | 1 right, 3 left, 0 up, 2 down; also the sub CPU's push mode |
| `+$10`-`+$12` | Flight | Range left in `+$12` |
| `+$13`, `+$14` | Pending displacement | Vertical, horizontal; written by the sub CPU (crowding, pushing) |
| `+$15` | Caught enemy | Record index |
| `+$16` | Owner | Player 0 or 1; the sub CPU writes it when a player claims the bubble |
| `+$17` | EXTEND letter | 0-5 |
| `+$18` | Special kind | 1 fire, 2 water, 3 lightning |
| `+$19` | Caught enemy's tile set | Type × 4 |
| `+$1A` | The sub CPU's claim | Touch state; bit 2 popped by a player |
| `+$1B` | Bob offset | 4 or 8 while a player stands on it |
| `+$1D` | Group | Record index for the chain pop |
| `+$1F` | Flight speed | Pixels per frame |
| `+$20`, `+$21` | Animation flags | `+$21` bit 7 killer bubble, bits 5 and 6 the two kinds of item |
| `+$22` | Chain place | From the sub CPU; chooses the fruit |
| `+$23`, `+$24` | Drift | This frame's step count, speed-list index |
| `+$25`, `+$26` | Animation counters | `+$26` bits 5 and 6: the sub CPU's "collected" flags for items |

## The enemy record (type 0: 25 bytes at `$ED49 + 25n`; type 2: 35; type 3: 27)

| Offset | Field | Values |
| --- | --- | --- |
| `+$00` | Flags | Bit 0 on the field, 1 dying, 2 in a bubble, 3 gone, 4 killed by a pop, 5 entrance done, 6 released, 7 angry |
| `+$01`, `+$02` | x, y | Also copied to the shared record at `$ED21` |
| `+$03`, `+$04` | Object slot pointer | From the slot allocator |
| `+$05`, `+$06` | Animation frame, tick | Walk cycle or tumble |
| `+$07` | State | 0 idle, 1 walking right, 2 falling, 3 walking left, 4 and 5 jumping |
| `+$08` | Direction | 1 right, 3 left |
| `+$09` | Enemy index | 0-6: selects the shared record and the MCU result at `$FC27 + 8n` |
| `+$0A` | Slot code | |
| `+$0B`-`+$0D` | Speed list index, list, step | Lists at `$11CE`; +6 when angry, capped at 40 |
| `+$0E` | Movement flags | Bit 1 moved, 5 fell, 6 angry speed applied, 7 hurry-up speed; while dying: the death state |
| `+$0F` | Chase flag | Player within 32 lines; while dead: which player collected the fruit |
| `+$10`, `+$11` | Script pointer | Jump or turn script; during the entrance: step timer and target line |
| `+$12`, `+$13` | Script step, repeats | During the entrance: the 180-frame timer |
| `+$14` | Blocked counter | At 60 the enemy jumps out |
| `+$15` | Decision timer | While dead: the fruit index |
| `+$16` | Timer | 120 at start; while dead: the 60-frame fruit pauses |
| `+$17` | Tile set | 3 marks the variant that never chases |
| `+$18` | Decision bits | Bit 0 jump script running, 1 next decision is a jump, 2 landed, 7 jump script armed |
| `+$19`-`+$22` | Type 2 only | The second slot and sprite for the rock in hand, the throw timer |
| `+$19`, `+$1A` | Type 3 only | The shot budget (two per life) and its timer |

The round's type-list byte at `[$C]` of the round record adds the variants: bit 0 Invader instead of type 0, bit 4
Drunk instead of type 2.

## The shared enemy record (4 bytes, 7 at `$ED21`; read by the sub CPU and the MCU)

| Byte | Meaning |
| --- | --- |
| 0 | Flags: bit 0 on the field; `$80` caught in a bubble, `$40` dead and falling, `$20` escaped angry, `$10` caught by an item, 8 lying as fruit |
| 1, 2 | x, y |
| 3 | Result: the sub CPU's touch report, the chain place, or which player picked the fruit up (bit 7 = player 2) |

## The MCU geometry record (8 bytes, 7 at `$FC27`; written by the MCU from the `$FC01` records)

Player 1's values are in the even bytes, player 2's in the odd ones.

| Byte | Meaning |
| --- | --- |
| 0, 1 | Horizontal direction code: `$00` the player is one way, `$80` the other, as `mcu_player_relation` tests it |
| 2, 3 | Vertical direction code, the same way |
| 4, 5 | \|dx\| |
| 6, 7 | \|dy\|, the value `enemy_chase` compares with 20 |

When both distances are under eight the MCU also writes a touch report to `$FC62`/`$FC63`, which the main
program never reads.

## Rocks, shots, chasers, the ring

| Record | Where | Layout |
| --- | --- | --- |
| Rock | `$EC29`, 16 bytes, one per type-2 enemy | `+0` flags (bit 0 live, bit 2 bursting), `+1`/`+2` x y, `+3`/`+4` object slot (the thrower's second slot), `+7` slot code, `+$0A` the thrower's direction, `+$0C` speed: the thrower's speed + 4, capped at 30 |
| Fire shot | `$EB99`, two per type-3 enemy | The same shape; speed the breather's + 10 |
| Missile | `$ECAA`, Invader's | The same shape; launched on the MCU's 600-frame countdown |
| Chaser | `$F1C2`, `$F1D4`, 18 bytes each | `+0` flags (bit 0 live, 1 hunting, 2 puffing out, 7 done), `+1`/`+2` x y, `+3`/`+4` slot, `+9` phase bits, `+$0E` movement bits; exist while `$E343` is set — Skel-Monsta in a round, the exits in a secret room |
| Boss ring bubble | `$F367`, eight records | `+0` flags (bit 0 live, bit 1 launched), `+3`/`+4` slot, `+7` quadrant and script bits selecting one of the four scripts at `$BBAE`; `$F3C9` counts the ring |

## The sound channel record (sound CPU RAM `$8000-$89DF`)

The record size depends on the chip: 112 bytes for an SSG channel, 288 for a YM2203 FM channel (the primary
voice and the alternate voice share it), 80 for a YM3526 voice. The bytes the YM3526 interpreter touches:

| Offset | Meaning |
| --- | --- |
| `[0]` | State bits: bit 3 a note has been set, bits 4 and 7 request key-on, bit 2 sustain, bit 5 tested on return from a command |
| `[$0F]` and following | Dirty bits per register group; the tick writer clears them as it writes the chip |
| `[$18]`-`[$4D]` | The instrument: the operator registers as the loader copied them from the header's instrument list |
| `[$1A]`, `[$1B]` | Frequency number, low byte, from the note table at `$0840` (current and pending) |
| `[$1C]`-`[$1E]` | Frequency number high bits with the octave from the pattern byte's bits 6-4, and the key-on form of the same |

The pattern pointer itself lives in `BC` while the interpreter runs and is saved back to the record between
ticks; the step pointer, loop counts and priority are kept in the first sixteen bytes.

## The kernel's task table (`$E000-$E011`, stacks at `$E020 + 64n`)

| Address | Meaning |
| --- | --- |
| `$E000`-`$E005` | State of task n: 0 running or runnable now, k = runs in k frames, `$FF` stopped |
| `$E006`-`$E011` | Saved stack pointer of task n |
| `$E020 + 64n` | Task n's 64-byte stack |
| `$0B22` | Entry table: the start address of each task |
| `$0B2E` | The interrupt vector word, `$044D`, checked twenty-four times |
