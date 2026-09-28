# 6. Rounds: maps, walls and the round table

A round of Bubble Bobble is a single screen: a border, some platforms, a set of monsters, a time limit, a colour
scheme. All of it comes from two pieces of data — a 43-byte **round record** in bank 1 of the main program and a
288-byte **collision map** in the sub CPU's ROM — plus a few tables that describe the top and bottom borders. This
chapter decodes both and shows all one hundred maps at once.

## The round record

`round_setup` (`$1775`) copies the record of the current round from bank 1 into work RAM at `$E598`:

```asm
round_setup:
1775  LD A,$01
1777  CALL bank_select
177A  LD A,(round_number)      ; $E64B: 0 for round 1
177D  LD B,$2B
177F  CALL mul8x8              ; HL = round x 43
1782  LD DE,$A73A
1785  ADD HL,DE
1786  LD DE,round_record       ; $E598
1789  LD BC,$002B
178C  LDIR
178E  CALL bank_restore
```

and then, unless this is round 100, adjusts three of the fields by the difficulty rank (chapter 12). The record of
round 1 reads:

```
05 90 53 AA 30 00 00 1E 0A 04 90 A0 00 1E 05 0A 01 01 78 90 15 78 90 29 78 90 00 ... 00 78
```

| Offset | Round 1 | Meaning |
| --- | --- | --- |
| `[0]` | `$05` | Palette selector: `load_round_palette` copies the 32-byte scheme number `[0]` from the table at `1:$8200` into colour group 14 or 15, by round parity |
| `[1]`, `[2]` | `$90`, `$53` | Position of the round's special item (the one that appears after a while and is picked up by walking into it) |
| `[3]` | `$AA` | Layout byte: high nibble selects the top-border rows of the map, low nibble the bottom rows; bits 5 and 7 mark rounds whose corner cells are open |
| `[4]`, `[5]`, `[6]` | `$30 $00 $00` | Enemy counts, two per byte: type 0, 1 / type 2, 3 / type 4, 5. Round 1 has three enemies of type 0 (Zen-chan) |
| `[7]` | `$1E` | How long a bubble holds an enemy before it escapes (30 units) |
| `[8]` | `$0A` | The enemies' base speed, from which the difficulty rank adds or subtracts |
| `[9]`-`[$B]` | `$04 $90 $A0` | Bubble-source parameters used when the round spawns its own bubbles (chapter 16) |
| `[$C]` | `$00` | Round flags: bit 0 replaces the type-0 enemies by the missile launchers, bit 4 enables the rounds-49-57 variant (chapter 17) |
| `[$D]` | `$1E` | Time limit in seconds: HURRY UP appears three seconds before it, Skel-Monsta at it |
| `[$E]` | `$05` | Not read by any code path the verification reached |
| `[$F]` | `$0A` | Seconds with a single enemy left before it turns angry |
| `[$10]` | `$01` | Entrance script selector: how the enemies walk in |
| `[$11]`-`[$25]` | `01 78 90 / 15 78 90 / 29 78 90 ...` | Up to seven spawn entries of three bytes: delay in frames, `x`, `y`. Round 1's three Zen-chans appear at the same spot 1, 21 and 41 frames after the start |
| `[$26]`-`[$29]` | `00 00 00 00` | Read by the bubble task's set-up, which builds the round's list of enemy types from the record (chapter 16) |
| `[$2A]` | `$78` | Read by the enemy helper at bank 0 `$87BD`; part of the enemies' entrance behaviour |

The counts in `[4]`-`[6]` are all a round says about its monsters; their behaviour is in the six drivers of
bank 0 (chapter 17). The whole table for all hundred rounds is in appendix D; the first dozen give the flavour:

| Round | Palette | Layout | Type 0 | Type 1 | Type 2 | Type 3 | Type 4 | Type 5 | Time | Angry |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5 | `$AA` | 3 | | | | | | 30 | 10 |
| 2 | 4 | `$AA` | 4 | | | | | | 30 | 10 |
| 3 | 4 | `$00` | 4 | | | | | | 30 | 10 |
| 4 | 1 | `$50` | 6 | | | | | | 30 | 10 |
| 5 | 6 | `$55` | 4 | | | | | | 30 | 10 |
| 6 | 0 | `$55` | 2 | | 2 | | | | 30 | 10 |
| 7 | 2 | `$55` | | | 4 | | | | 30 | 10 |
| 8 | 3 | `$5A` | 2 | | 2 | | | | 30 | 10 |
| 9 | 0 | `$5A` | | | 5 | | | | 30 | 10 |
| 10 | 1 | `$55` | 4 | | | | | 3 | 30 | 10 |
| 11 | 3 | `$55` | 3 | | | | | 4 | 30 | 10 |
| 12 | 1 | `$00` | | | | | | 6 | 30 | 10 |

The time limit stays at 30 seconds for the first 41 rounds, then drops towards 20 in the fifties and rises again
for the long late rounds (40 seconds for rounds 63, 72, 79, 81, 83, 84, 88, 94, 95, 99, 100; 50 for round 92; 112
for round 97). Round 56 gives eight seconds and one enemy of every type but the last. Round 100 sets the angry
time to 164 seconds, which is never reached: the boss does not use it.

## The collision map

Everything that moves in Bubble Bobble consults one map: 32 rows of 32 cells, one 8 x 8 pixel cell each, covering
the whole 256 x 256 plane, stored as nibbles in 512 bytes at `$E398-$E597` (16 bytes per row). A cell's value
means:

| Value | Meaning |
| --- | --- |
| 0 | Solid: wall or floor |
| 1 | Air |
| 2 | Air with a current pushing bubbles right |
| 3 | Air with a current pushing bubbles left |
| 4 | Air with a current pushing bubbles down |

The map is assembled from three sources. Rows 5 to 28 — the playfield proper, 24 rows of 16 byte-pairs — are
built by the **sub CPU** from its own ROM: at `$0CFC` it holds 288 bytes per round, a bit stream of six bits per
pair of cells (three bits for the left cell, three for the right), and its `build_collision_map` routine unpacks
one round's 384 pairs into `$E3E8-$E567` whenever the main CPU asks by writing 1 to `$E397`. The stream costs
28,800 bytes for the hundred rounds, most of the sub CPU's 32 KB. Rows 0-4 and 29-31 — the top and bottom borders,
where the status row and the floor live — come from bank 1 of the main program: `load_round_map` picks an
80-byte block for the top and a 48-byte block for the bottom from the table at `1:$95AA` using the two nibbles of
the layout byte, so that the top row of currents and the shape of the floor can differ between rounds without
storing them a hundred times. The sub CPU's contribution is also why the round cannot start until the sub CPU has
acknowledged: `load_round_map` sets `$E397`, yields to the scheduler until bit 7 comes back, and only then copies
the borders.

The map decoded from the ROMs, with the currents as arrows, matches the screen:

![Round 1's collision map decoded from the sub CPU's ROM and bank 1, with the currents drawn as arrows. Compare the screenshot in chapter 1.](../img/ch06-map1.png)

A cell is looked up by `wall_test` (`$174C`) for a position given in the program's coordinates — `x` vertical,
growing upwards, and `y` horizontal — which explains the arithmetic:

```asm
wall_test:                    ; A = x, H = y; returns the cell's nibble in A
174C  LD D,H
174D  NEG                     ; 256 - x
174F  AND $F8                 ; ... rounded to a row of 8 pixels
1751  ADD A,A                 ; x 2: 16 bytes per row (with the carry into H)
1752  LD L,A
1753  LD H,$00
1755  RL H
1757  LD A,D
1758  RRCA
1759  RRCA
175A  RRCA
175B  RRCA
175C  AND $0F                 ; y / 16: the byte within the row
175E  ADD A,L
175F  LD L,A
1760  JP NC,loc_1764
1763  INC H
loc_1764:
1764  LD BC,collision_map     ; $E398
1767  ADD HL,BC
1768  LD A,(HL)
1769  BIT 3,D                 ; y bit 3: which nibble
176B  JP NZ,loc_1772
176E  RRCA
176F  RRCA
1770  RRCA
1771  RRCA
loc_1772:
1772  AND $0F
1774  RET
```

Row 0 of the map is line 0 of the picture, so `256 - x` turns the program's height into a line number. The
routines built on `wall_test` — the cell below an object, above it, to its left and right, and the three cells
along its moving side — are the subject of chapter 15.

## Drawing the walls

The walls are not a separate drawing; they are the map made visible. When a round is set up, the strips of the
off-screen playfield are cleared and `round_scroll_step` (`$18EE`) draws them one tile row per call, or all 32 at
once when `$E5C3` is zero. Each call runs three
passes over the map row:

1. `scroll_draw_walls` (`$1958`) puts the round's wall tile into every cell whose nibble is zero. The tile comes
   from `wall_tile_base`: `round x 5 + $0204`, so each round has its own set of five consecutive tiles in bank 0
   (four patterned blocks and a plain one, chapter 4), and the attribute byte is `$38` on even rounds and `$3C` on
   odd ones — colour group 14 or 15. Alternating the group is what lets two rounds be on screen at the same time
   during the scroll with different colours: `load_round_palette` fills the other group while the old one is still
   visible.
2. `scroll_shade_walls` (`$199C`) looks at the empty cells next to solid ones and writes the edge tiles `$F0-$F5`
   into them, which gives the platforms their lit top edge and shaded underside.
3. `scroll_cap_columns` fixes the cells at the top of each strip, where the border meets the status row.

The pass runs at 32 rows per round; with the scroll enabled, that is a 32-frame reveal of the new round while the
old one is pushed off. The two playfields of chapter 5 exist for this half-second.

![Round 20 as played: the layout is a mirrored pair of figures, with the wall tiles and colour scheme of that round.](../img/ch06-round20.png)

## All hundred maps

![The collision maps of all 100 rounds decoded from the ROMs. Red is solid, black is air, blue-green-brown mark cells with a rightward, leftward or downward current.](../img/ch06-all-maps.png)

Seen together, the maps show what the level designers did with 32 x 32 cells. The early rounds are ladders of
platforms with gaps; from round 10 the layouts become pictures — a heart (13), a face (14), a butterfly (49),
an eye (56), the letters of "BUBBLE" (24), "POPCORN" (25), "JUMP!" (35), "SOS!!" (44), "BONUS" (45), "OUCH!!!"
(46), "BR10" (59), "RUN AWAY!!" (69), "HI-TECH!" (72), "DRUNK!" (75), "KIMI" (85), "DEADHEAT" (86), "SUPER GAMER!!"
(91), "MTJ." (92, the designer's initials) and "WELCOME" (98). The currents are drawn wherever a bubble should
travel: along the ceiling in almost every round (blue and green rows at the top), down the shafts of the rounds
built around vertical wells, and in loops around the closed figures, so that a bubble blown anywhere circulates
back to the player. Round 100, the boss's room, is empty air with a few solid specks: the boss fight is fought on
the bubble ring alone (chapter 19).

![Round 45, "BONUS": a word spelled in wall cells.](../img/ch06-round45.png)

![Round 60: a stack of ledges with a ceiling current.](../img/ch06-round60.png)

![Round 99, the last ordinary round.](../img/ch06-round99.png)

The border tables of bank 1 give the tops and bottoms: layout `$AA` (rounds 1, 2, 16, 24 ...) has a five-row solid
top and a three-row solid bottom; `$55` and `$5A` open the corners so that bubbles and enemies wrap round; `$00`
(round 3, the letter rounds) uses the plain border with a full-width ceiling current. Where the low nibble differs
from the high one (`$50`, `$19`, `$22`, `$88`), the bottom is not the mirror of the top: a floor with holes, or a
raised floor.

## Round 100

The last round has no walls at all in its stream: the map is air with the boss's arena rules coming from code.
Its record sets seven enemies (`2 of type 2, 2 of type 4, 2 of type 5` — the counts are read but the boss task
ignores them), a 40-second limit and the impossible 164-second angry time. The round loop treats it specially at
every step: `round_setup` skips the difficulty adjustment, the enemy task only animates the boss, and the bubble
task links 18 records instead of 24.
