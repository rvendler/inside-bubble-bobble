# 11. The sub CPU

The second Z80 is the least visible processor on the board and the one that decides most of what a player
feels. It has no inputs, no outputs, no ROM banking and no RAM of its own: 32 KB of program ROM, of which
28.8 KB are the level maps of chapter 6 and 3.3 KB are code, and the 6 KB of RAM at `$E000-$F7FF` that it
shares with the main CPU. Once per frame it is interrupted by the VBLANK signal, walks every bubble, enemy,
player, rock, missile and item on the field, decides who is touching whom, writes its verdicts into the
records the main CPU owns, and goes back to sleep. Every catch, every pop, every bounce off a bubble and every
death in the game is a byte this processor wrote.

## Boot and the frame

```asm
reset:
0000  DI
0001  IM 1
0003  LD SP,$F7CE              ; a stack in the shared RAM, below the main CPU's
0006  CALL rom_checksum        ; the 32 KB must sum to zero, or spin at $018D
0009  EI
loc_000A:
000A  JP loc_000A              ; and wait

irq_vector:                    ; $0038, interrupt mode 1
0038  JP frame_handler

frame_handler:
0068  LD HL,sub_frame_counter  ; $F66E: the heartbeat the main CPU watches
006B  INC (HL)
006C  CALL build_collision_map ; when $E397 = 1
006F  CALL sequence_objects_hit; the secret-room doors
0072  LD A,(round_running)     ; $F66B
0075  CP $49
0077  JP NZ,loc_00A7           ; nothing else unless a round is being played
007A  CALL players_caught
007D  CALL enemies_touch_players
0080  CALL bubbles_update
0083  CALL chain_pop
0086  CALL flying_objects_catch
0089  CALL falling_items_catch
008C  CALL missiles_hit_players
008F  CALL rocks_hit_players
0092  CALL flyer_catches
0095  CALL bouncing_object_catches
0098  CALL f3ce_objects_hit_players
009B  CALL f367_objects_hit_players
009E  CALL boss_vs_players
00A1  CALL fire_shots_hit_players
00A4  CALL main_watchdog
loc_00A7:
00A7  EI
00A8  RET
```

The handler runs with interrupts disabled and re-enables them only on the way out, so a VBLANK that arrives
while it is still working waits until the next `EI`. The gate at `$0072` is the byte `$F66B`, which the main
CPU sets to `$49` when the round-start animation finishes and clears when the round ends; outside a round the
handler costs 185 cycles and the sub CPU does nothing else. Inside a round it is the sixteen calls below,
and their cost depends on how much is on the field:

| Frame of the traced game | Handler | Of which the bubble pass |
| --- | --- | --- |
| 600 (attract mode, no round) | 185 cycles, 0.03 ms | - |
| 908 (round 1 set-up: the map build) | 130,769 cycles, 21.8 ms | - |
| 1200 (round 1, a few bubbles) | 25,728 cycles, 4.3 ms | 20,975 |
| 1500 | 42,098 cycles, 7.0 ms | 36,003 |
| 2500 (many bubbles) | 58,478 cycles, 9.7 ms | 52,525 |

The rest of the list is cheap — a few hundred cycles each, mostly the cost of looking at a record and finding
it inactive — and the bubble pass, which compares every bubble with every player and every other bubble,
is the whole budget. On the busiest frames the sub CPU is working for more than half of the frame, and it
started at VBLANK: the main CPU's tasks, which begin 1.6 milliseconds later, overlap it for most of that time.
The map build at round start takes longer than a frame; the main CPU's `load_round_map` yields until the
acknowledgement comes back, and the VBLANK that arrives meanwhile is simply taken late.

The opposite case is the idle one. The VBLANK signal stays asserted for the whole blanking period (chapter 2),
about 1.5 milliseconds, so a handler that finishes before the blanking does is entered again at its own `EI`.
Outside a round, where one pass costs 185 cycles, the handler therefore runs several times in each blanking;
inside a round a single pass outlasts the blanking.

## The shared RAM

![The shared 6 KB: what the sub CPU reads and writes.](../img/ch11-shared-ram.svg)

The two processors have no way to lock a byte against each other and, apart from the map request, no
handshake. The convention that keeps them consistent is one of roles: for every record, one side moves things
and the other side judges. The main CPU writes positions; the sub CPU reads them and writes flags — a player's
state becomes `$10`, an enemy's touch byte names a player, a bubble's push and pop fields are filled in — and
the main CPU's tasks act on the flags in the frame that follows. Nothing is ever written by both sides in the
same frame except by accident of timing, and the timing is exact enough that the accidents are the same on
every board: the sub CPU's pass starts within sixteen microseconds of VBLANK and the main CPU's tasks at a
fixed offset after it, so which frame's positions a test sees is decided by how long the pass is. The emulator
interleaves the two CPUs four times per scan line for this reason; a coarser interleave changes which bubble
catches which enemy.

Two bytes exist only to watch the other side. The main CPU's `sub_cpu_watchdog` (chapter 9) reboots the board
if the heartbeat at `$F66E` stops for 180 frames. The sub CPU's `main_watchdog` does the reverse with the main
CPU's frame counter at `$E338`:

```asm
main_watchdog:
0190  LD A,($E338)
0193  LD HL,watchdog_copy      ; $F66C
0196  CP (HL)
0197  LD (HL),A
0198  INC HL
0199  JR NZ,loc_01B6           ; changed: reset the count
019B  INC (HL)                 ; $F66D
019C  LD A,(HL)
019D  CP $3C
019F  RET C                    ; under 60 frames: fine
01A0  LD HL,$E800              ; otherwise: copy the upper half of the shared RAM
01A3  LD DE,$E000              ; over the lower half, inverted ...
01A6  LD BC,$0800
loc_01A9:
01A9  LD A,(HL)
01AA  CPL
01AB  LD (DE),A
01AC  INC HL
01AD  INC DE
01AE  DEC BC
01AF  LD A,C
01B0  OR B
01B1  JR NZ,loc_01A9
loc_01B3:
01B3  JP loc_01B3              ; ... and stop
loc_01B6:
01B6  LD (HL),$00
01B8  RET
```

If the main CPU's frame counter stops moving for a second during a round, the sub CPU destroys the kernel's
RAM and hangs. The main CPU, if it is still running at all, can no longer kick the hardware watchdog from a
scheduler whose task table has been overwritten, and the board resets. It is a deliberate second line behind
the hardware watchdog, for a main CPU that is alive enough to kick it but no longer playing.

## The windows

Every test in the program has the same shape. It takes a record's `(x, y)` — `x` vertical, `y` horizontal, as
in the rest of the code — subtracts the other object's, takes the absolute value of each difference and
compares it with a constant. The result is a square window; no test looks at a sprite's real outline. The
helper that does it for the enemies is typical:

```asm
enemy_near:                    ; an active enemy within C pixels of (E, D)? carry, HL -> its record
02B4  LD B,$00
02B6  LD HL,$ED21
loc_02B9:
02B9  BIT 0,(HL)               ; flags: bit 0 = on the field
02BB  JR Z,loc_02D4
02BD  PUSH HL
02BE  INC HL
02BF  LD A,(HL)                ; enemy x
02C0  SUB E
02C1  JP P,loc_02C6
02C4  NEG
loc_02C6:
02C6  CP C
02C7  JR NC,loc_02D2           ; too far vertically
02C9  INC HL
02CA  LD A,(HL)                ; enemy y
02CB  SUB D
02CC  JP P,loc_02D1
02CF  NEG
loc_02D1:
02D1  CP C
loc_02D2:
02D2  POP HL
02D3  RET C                    ; within C on both axes
loc_02D4:
02D4  INC HL
02D5  INC HL
02D6  INC HL
02D7  INC HL
02D8  INC B
02D9  LD A,B
02DA  CP $07
02DC  JR NZ,loc_02B9
02DE  XOR A
02DF  RET
```

The seven enemy records at `$ED21` are the same four bytes per enemy that task 4 hands to the MCU (chapter
10), kept in the shared RAM for the sub CPU: `[flags, x, y, touch]`. The windows, collected:

![The proximity windows.](../img/ch11-windows.svg)

| Test | Window | Effect |
| --- | --- | --- |
| Enemy against a live player | 10 | The player is caught: its state byte becomes `$10`. If the player is in the invulnerable state, the enemy is marked caught instead and the enemy count drops |
| Enemy against a live player | 16 | The enemy's touch byte is set to 1 or `$FF` for the player it touches; the enemy AI reads it to turn on the player |
| Player walking, a bubble behind | 18 across, 12 up or down | The bubble pops: a pop event (the fins) |
| Player walking, a bubble in front | 10 across, 12 up or down | The bubble is pushed: the player's walking speed is added to its push field, the player is noted as the pusher, and the bubble gets a push mode; a standing player is shoved back by the bubble's own drift |
| Player falling, above a bubble | 12 across, under 12 above | The bubble pops |
| Player falling, above a bubble | 12 across, 12 to 21 above | The player lands on it: a flag in the player record makes the jump code bounce |
| Bubble against bubble | 13, on the side of its push mode | The neighbour's push field moves by 1 (2 if it is being pushed itself) |
| Chain pop | 20 | Every bubble of another group within 20 pixels of the last pop pops next frame |
| Special bubble (water, fire, lightning) against a player | 10 | The player is hit for 60 frames |
| Special bubble against an enemy | 15 | The enemy is caught |
| Flying object, falling item, bouncing object against an enemy | 15 | The enemy is caught; the object is marked used |
| The flyer against an enemy | 24 | The enemy is caught |
| Any of those against a bubble | 16 | The bubble is treated as popped by it |
| Fire shot, rock against a player | 8 | The player is burnt: it stumbles and is caught |
| Missile, message-panel object against a player | 8 | The player is caught |
| Special bubble against the boss (round 100) | 44 | A hit on the boss |
| Skel-Monsta record against a player | 10 | In a secret room, where the records are the exits, the round-end flag is raised; otherwise the player is caught |
| The boss against a player | 36 | The player is caught |

Two of the numbers are the game's feel. A monster catches you at ten pixels, on both axes, from centre to
centre: with sixteen-pixel sprites that means the pictures overlap by about a third before the sub CPU calls
it a touch, which is why Bubble Bobble feels forgiving. And the bubble rules are exactly the ones the
instruction screen states: a bubble in front of you, within ten pixels, is pushed along by your walking; a
bubble behind you, within eighteen, bursts on your fins; a bubble you fall onto from less than twelve pixels
bursts on your horns, and from twelve to twenty-one you land on it and bounce.

## The bubble pass

`bubbles_update` walks the twenty-four records of forty bytes at `$E76C` and dispatches on each bubble's
state byte: an ordinary drifting bubble, a bubble with an enemy inside, the two states between, or a special
bubble. For the first four it does the same three things:

1. **Push the neighbours.** If the bubble has a push mode in `[$0F]`, it looks at every other bubble on the
   side the mode names and, for each within thirteen pixels, moves the neighbour's push counter by one
   (`[$14]` horizontally, `[$13]` vertically). The main CPU's bubble code turns the counters into motion
   next frame (chapter 16). This is what makes a crowd of bubbles spread and a pushed bubble shove the ones
   in front of it.
2. **Player 1, then player 2.** `player_vs_bubble` applies the walking or falling windows above, using the
   player's facing byte to tell front from behind. On a pop it calls `pop_event`; on a push it fills in the
   push and pusher fields and returns. The first player to touch a
   bubble claims it for the frame — `[$1A]` is set to the bubble's state, and a claimed bubble is skipped
   until the main CPU has processed it.
3. **A bubble with an enemy inside** is first offered to the flying objects, the falling items, the flyer and
   the bouncing object: any of them within sixteen pixels pops it, so that a thrown item bursts the bubbles it
   passes.

`pop_event` is the sub CPU's one message to the main CPU:

```asm
pop_event:                     ; bubble IX popped by player IY
09C7  LD HL,pop_event          ; $F66F
09CA  BIT 0,(HL)
09CC  JP NZ,loc_0A2E           ; one pop per frame: the rest wait
09CF  LD (HL),$01
09D1  INC HL
09D2  LD A,(IX+$1D)
09D5  LD (HL),A                ; $F670: the bubble's group
09D6  INC HL
09D7  LD A,(IX+$01)
09DA  LD (HL),A                ; $F671: x
09DB  INC HL
09DC  LD A,(IX+$02)
09DF  LD (HL),A                ; $F672: y
09E0  INC HL
09E1  BIT 2,(IX+$00)           ; an enemy inside?
09E5  JR Z,loc_0A02
09E7  INC (HL)                 ; $F673: the chain count
09E8  LD A,(HL)
09E9  DEC A
09EA  LD (IX+$22),A            ; this bubble's place in the chain
      ...
0A02  INC HL
0A03  INC HL
0A04  LD A,(IY+$09)
0A07  LD (IX+$16),A            ; the player who popped it ...
0A0A  LD (HL),A                ; ... also in $F675
      ...
0A26  LD A,(IX+$00)
0A29  LD (IX+$1A),A            ; claim the bubble
0A2C  SCF
0A2D  RET
```

Only one pop is reported per frame. The next routine in the handler, `chain_pop`, is what turns one into many:
if a pop was reported, it clears the flag, finds the first bubble of a different group within twenty pixels of
the popped position and reports *that* one, with the chain count advanced. So a cluster of bubbles pops one
per frame, outward from the first, each link twenty pixels from the last — the ripple a player sees when a
row of trapped monsters goes up together — and the chain count in `$F673` climbs with it. When no bubble is
left within reach the count is reset and two done flags are raised for the tallies at `$F677` and `$F679`,
which the main CPU's bubble task reads to award the chain scores of chapter 16: the sub CPU counts the chain,
the main CPU prices it.

## Everything else on the field

The remaining routines are the same window applied to the other things that can touch a player or an enemy,
each reading a table the main CPU owns and writing a result byte into it:

* `players_caught` and `enemies_touch_players`: the ten- and sixteen-pixel windows over the seven enemy
  records. A player is "catchable" only if it is alive, not already caught, not in its invulnerable spell, and
  between eight and 247 pixels from the bottom of the plane — the last test keeps a player who is walking off
  the top or bottom edge from dying to an enemy on the other side of the wrap.
* `flying_objects_catch`, `falling_items_catch`, `flyer_catches`, `bouncing_object_catches`: the items of the
  special rounds and the thrown objects of chapter 18 catch enemies at fifteen pixels (the flyer at
  twenty-four); the enemy's flags become `$10` and its result byte says what caught it, so that the enemy code
  can turn it into the right kind of fruit.
* `fire_shots_hit_players` and `rocks_hit_players`: the fire breathers' shots and the rock throwers' rocks burn
  a player at eight pixels; `missiles_hit_players` and the two message-panel object tables catch at eight.
* `special_bubble`: water, fire and lightning bubbles hit a player at ten pixels (sixty frames of the effect) and
  otherwise catch an enemy at fifteen. On round 100 there are no enemies to catch: a special bubble within
  forty-four pixels of the boss sets bit 7 of the boss record and counts a hit at `$F2A1`, which is how the boss
  is beaten (chapter 19).
* `boss_vs_players`: the boss catches at thirty-six pixels while it is active, and while it is dying it notes
  which player was within thirty-six pixels, for the ending.
* `sequence_objects_hit`, called even outside a round: the two records at `$F1C2` and `$F1D4` — Skel-Monsta's
  in a normal round, the exits in a secret room — catch a player within ten pixels; in the secret room the touch
  raises the round-end flag instead of a death.

None of these routines moves anything. The sub CPU never changes a position; it only says, in a byte of the
record, what the position means. The main CPU's tasks read the bytes in the frame that follows, and chapters
13 to 19 are about what they do with them.
