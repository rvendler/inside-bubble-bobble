# 16. Bubbles

Everything in Bubble Bobble that is not a wall, a player or a monster is a bubble record. Twenty-four of them,
forty bytes each, from `$E76C`: the bubbles the players blow, the bubbles the round itself releases, the
water, fire and lightning bubbles, the EXTEND letters, the burst that a popped bubble leaves behind, and
the fruit that a popped monster falls as. Task 5 walks the twenty-four every frame and dispatches on a state
byte; the sub CPU walks them again during the blanking and writes back what touched what. This chapter is
the life of a bubble from the button press to the points.

## The record

| Offset | Field |
| --- | --- |
| `+$00` | State: 1 floating, 2 in flight, 4 holding an enemy, 8 an EXTEND letter, `$10` special (water, fire, lightning), `$20` a lightning bolt, `$40` a falling fire, `$80` popping; 0 free |
| `+$01`, `+$02` | x, y, copied from the object slot |
| `+$03`, `+$04` | The object slot: `$E20D + 4n` |
| `+$07` | The slot code for the sprite routines |
| `+$0A` | The last current nibble read from the map |
| `+$0B` | Bit 0: counted out of `bubbles_active` already |
| `+$0C`, `+$0D` | Lifetime: a 60-frame tick and the number of periods left |
| `+$0E` | Phase: 0 and 1 the owner's colour (Bub green, Bob blue), 2 and 3 the ageing colours, `$FF` = pop now |
| `+$0F` | Direction: 1 right, 3 left, 0 up, 2 down; also the sub CPU's push mode |
| `+$10`-`+$12` | The flight: range left in `+$12` |
| `+$13`, `+$14` | Pending vertical and horizontal displacement, written by the sub CPU (crowding, pushing) |
| `+$15` | The caught enemy's record index |
| `+$16` | The owner: player 0 or 1, also written by the sub CPU when a player claims the bubble |
| `+$17` | The EXTEND letter, 0-5 |
| `+$18` | The special kind: 1 fire, 2 water, 3 lightning |
| `+$19` | The caught enemy's tile set (type x 4) |
| `+$1A` | The sub CPU's claim: the bubble's state bit while a player touches it, bit 2 = popped by a player |
| `+$1B` | Bob offset: 4 or 8 while a player stands on it |
| `+$1D` | Group: the record index, used by the chain pop |
| `+$1F` | Flight speed, pixels per frame |
| `+$20`, `+$21` | Animation flags; `+$21` bit 7 a killer bubble, bit 5 and 6 the two kinds of item |
| `+$22` | Place in the chain, from the sub CPU |
| `+$23`, `+$24` | The drift: this frame's step count and the index into the speed list |
| `+$25`, `+$26` | Animation counters; `+$26` bit 5 and 6 the sub CPU's "collected" flags for items |

## Blowing

The player's six-byte request (chapter 13) is picked up by the first free record that `bubble_update` reaches:

```asm
bubble_spawn_from_request:
6349  LD HL,bubble_request_p1  ; $E75E
634C  LD A,(HL)
634D  AND A
634E  JR Z,loc_6357            ; player 1 has not asked: try player 2
6350  LD (IX+$16),$00          ; owner
6354  JP loc_6364
      ...
loc_6364:
6364  PUSH HL
6365  INC HL
6366  LD A,(HL)
6367  AND $F8                  ; x, rounded to the cell
6369  LD E,A
636A  LD (IX+$01),E
636D  INC HL
636E  LD A,(HL)
636F  AND $FE                  ; y, rounded to even
6371  LD D,A
6372  LD (IX+$02),D
6375  INC HL
6376  LD A,(HL)
6377  LD (IX+$0F),A            ; the facing: the flight direction
637A  INC HL
637B  LD A,(HL)
637C  LD (IX+$12),A            ; range: 64 pixels
637F  INC HL
6380  LD A,(HL)
6381  LD (IX+$1F),A            ; speed: 3 pixels per frame
      ...
6394  CALL bubble_phase_from_owner
6397  CALL bubble_random_lifetime
639A  LD HL,bubbles_active
639D  INC (HL)
      ...
63B0  LD (IX+$11),$01
63B4  LD (IX+$00),$02          ; in flight
63B8  LD C,$31
63BA  CALL sound_queue_push    ; the blow sound
```

A new bubble starts where the dragon's mouth is and flies in the facing direction at three pixels a frame
for sixty-four pixels — twenty-one frames — while `bubble_in_flight` looks for an enemy within fourteen
pixels every frame with `find_enemy_near`. The fast player's range of 6 doubles the distance. During the
flight the bubble is drawn from the growing frames at the start of the bubble tile set; when the range is
used up it becomes a floating bubble (state 1), or, if its owner has a lightning charge from the lightning
item, a lightning bubble.

![The bubble tiles of object bank 2: Bub's blowing and floating frames (green), Bob's (blue), the four ageing phases with their squashed "ridden" variants, the two burst frames and the star.](../img/ch16-bubble-tiles.png)

## Floating

A floating bubble does two things every frame: it bobs, and it drifts. The bob is `bubble_rise_draw`: a
six-frame counter that selects the tile from the phase's set, with the sub CPU's `[+$1B]` — 4 or 8 while a
player stands on the bubble — added to pick the squashed frames. The drift is the air:

```asm
bubble_drift:
6143  LD A,(mcu_bubble_speed)  ; $FC76: the round's speed list
6146  LD HL,$11CE
6149  CALL table_lookup_de
614C  LD A,(IX+$24)
614F  CALL de_add_a
6152  LD A,(DE)                ; this frame's number of steps
6153  OR A
6154  JP P,loc_615D
6157  LD (IX+$24),$00          ; $FF: wrap the list
615B  JR bubble_drift
loc_615D:
615D  LD (IX+$23),A
6160  INC (IX+$24)
6163  LD A,(IX+$23)
6166  OR A
6167  RET Z
6168  LD B,A
loc_6169:
6169  PUSH BC
616A  CALL obj_position_from_slot
616D  CALL bubble_current_step ; one pixel along the current
6170  POP BC
6171  DJNZ loc_6169
6173  RET

bubble_current_step:
6174  LD A,(IX+$0A)            ; the current nibble under the bubble
6177  LD HL,$61F3
617A  CALL table_lookup_de
617D  EX DE,HL
617E  JP (HL)                  ; 0, 1, 7-15: up; 2: right; 3: left; 4: down; 5, 6: hold
```

The speed list is the same table the players and enemies use (chapter 13); the round record's byte `[9]`
names it, and the bubble task keeps the number in `$FC76`, one of the MCU's shared bytes, where the MCU
mistakes it for a sequence-list selector (chapter 10). Each step is one pixel in the direction of the current
nibble the bubble last read from the collision map. The map is re-read only when the bubble is aligned to a
cell on the axis it is moving along — `AND $07` on `x` or `y` — so a bubble commits to a cell's direction until
it has crossed the cell. Nibble 0 and 1, plain air, mean *up*, which is why bubbles rise; 2 and 3 are the
horizontal currents, 4 pushes down, and 5 and 6 hold the bubble in place. Chapter 6's maps are, read this way,
diagrams of where bubbles will go: up through the open air, along the ceiling currents, down the shafts and
round the loops that bring them back to the players.

![Round 1, a few seconds in: Bub's green bubbles rising towards the ceiling current; the enemies on the top platform.](../img/ch16-play-1160.png)

Two more things move a bubble. `bubble_apply_move` applies the displacement the sub CPU left in `[+$13]`
and `[+$14]` — a neighbour crowding it, a player pushing it — with a wall test on each axis and undoes the
axis that is blocked. And a bubble that drifts off the top or bottom edge is tested against the layout byte's
corner bits (`bubble_edge_test`): where the round's corners are open it is simply freed, which is how
bubbles leave a round with an open ceiling.

## Lifetime and ageing

```asm
bubble_random_lifetime:
6213  LD A,(mcu_bubble_speed)
6216  LD HL,$6229              ; a base per speed list: 8 periods for the slow lists down to 3
6219  CALL hl_add_a
621C  LD A,R                   ; the refresh register: a random 0-7
621E  AND $07
6220  ADD A,(HL)
6221  LD (IX+$0D),A            ; periods
6224  LD (IX+$0C),$01
6228  RET

bubble_lifetime:
60B5  DEC (IX+$0C)
60B8  JP NZ,loc_60CD
60BB  LD (IX+$0C),$3C          ; a period is 60 frames
60BF  DEC (IX+$0D)
60C2  LD A,(IX+$0D)
60C5  CP $FF
60C7  RET NZ
60C8  LD (IX+$0E),$FF          ; out of periods: pop
60CC  RET
loc_60CD:
60CD  LD A,(IX+$0D)
60D0  CP $04
60D2  RET NC                   ; more than three periods left: the owner's colour
60D3  OR A
60D4  JR Z,loc_60E1
60D6  LD HL,$60EE              ; 3, 2, 1 periods left: phases 3, 3, 2 ...
60D9  CALL hl_add_a
60DC  LD A,(HL)
60DD  LD (IX+$0E),A
60E0  RET
loc_60E1:
60E1  LD A,$02                 ; the last period: phase 2 or 3, blinking on a lifetime bit
```

A bubble lives a random eight to fifteen seconds in round 1 (the base of its speed list plus the Z80's refresh
register masked to three bits), and for its last three seconds it changes colour through the ageing phases —
green or blue to pink to red — and then bursts on its own. The refresh register is the game's second random
source (chapter 20); it makes two bubbles blown in the same frame live different lengths.

![Twenty seconds later: the oldest bubbles have turned pink and are about to burst.](../img/ch16-play-1290.png)

## Catching

```asm
bubble_in_flight:
5D95  LD E,(IX+$01)
5D98  LD D,(IX+$02)
5D9B  LD C,$0E
5D9D  CALL find_enemy_near     ; an enemy within 14 pixels?
5DA0  JP C,bubble_catch
      ...
bubble_catch:
5DE4  LD (IX+$15),B            ; which enemy
5DE7  LD (HL),$80              ; its record: caught
5DE9  INC HL
5DEA  INC HL
5DEB  INC HL
5DEC  LD A,(HL)
5DED  ADD A,A
5DEE  ADD A,A
5DEF  LD (IX+$19),A            ; type x 4: the tile set
5DF2  CALL bubble_phase_from_owner
5DF5  CALL obj_slot_attr_15
5DF8  CALL bubble_current_read
5DFB  LD A,(round_caught_lifetime)  ; the round record's [7], adjusted by the rank
5DFE  LD (IX+$0D),A
6001  LD (IX+$0C),$01
6005  CALL obj_anim_reset
6008  LD (IX+$1A),A
600B  LD (IX+$00),$04          ; holding an enemy
```

Only a bubble in flight catches. The test is the main CPU's own, one of the few object tests it makes: a
fourteen-pixel window over the seven enemy records, run every frame of the flight. On a catch the enemy's
record byte becomes `$80` — the enemy driver (chapter 17) sees it and stops driving — and the bubble's
lifetime is replaced by the round's hold time, thirty periods in round 1 less the rank adjustment of chapter
12. The bubble now floats like any other, drawn from the caught-enemy sets:

![Object bank 2, second quarter: the enemies as they look inside a bubble, three frames each, and the angry and captured forms.](../img/ch16-caught-tiles.png)

`bubble_with_enemy` watches five situations that let the enemy out unharmed — the round ending, a
release flag, a player dying, the bonus round flag, the HURRY UP release — and two that end the hold. If the
lifetime runs out, the enemy escapes: its record becomes `$20` at the bubble's position, and the driver
brings it back angry. If the sub CPU has marked the bubble as popped by a player (`[+$1A]` bit 2), the enemy
dies:

```asm
bubble_popped_with_enemy:
5E65  LD DE,$0100
5E68  CALL bubble_score        ; 1000 points to the owner
loc_5E6B:
5E6B  LD A,(IX+$15)
      ...
5E76  LD (HL),$40              ; the enemy's record: dead, falling as an item
5E78  INC HL
5E79  LD A,(IX+$01)
5E7C  LD (HL),A                ; at the bubble's x
5E7D  INC HL
5E7E  LD A,(IX+$02)
5E81  LD (HL),A                ; and y
5E82  INC HL
5E83  LD A,(IX+$22)
5E86  LD (HL),A                ; and its place in the chain: which fruit
5E87  LD HL,enemy_count
5E8A  DEC (HL)
5E8B  LD C,$25
5E8D  CALL sound_queue_push
5E90  JP bubble_start_pop
```

The enemy count is the round's exit condition (chapter 12), so this `DEC` is what ends a round. What falls is
the enemy driver's business — the tumble, the bounce off the edges, the landing as fruit and the pickup are
in the enemy's death code (chapter 17) — but the fruit is chosen here: `[+$22]` is the bubble's place in the
chain that the sub CPU counted, and the death code turns the count into the item table's entry, which is why
the second and third monsters of a chain fall as better fruit than the first.

## Popping and chains

Any bubble a player touches on the fin side, falls onto from close above or jumps into is a pop event on the
sub CPU (chapter 11); the main CPU sees the claim in `[+$1A]` and calls `bubble_start_pop`:

```asm
bubble_start_pop:
5F7A  LD HL,bubbles_active
5F7D  DEC (HL)
5F7E  SET 0,(IX+$0B)
5F82  CALL obj_anim_reset
5F85  LD (IX+$1A),A
5F88  LD (IX+$21),A
5F8B  LD (IX+$26),A
5F8E  LD (IX+$00),$80          ; popping
5F92  CALL obj_slot_attr_12
bubble_popping:
5F95  LD DE,$0408
5F98  CALL anim_step           ; four frames of the burst
5F9B  JR Z,loc_5FBB
      ...
loc_5FBB:
5FBB  LD A,(IX+$18)            ; a special kind?
5FBE  CP $01
5FC0  JP Z,pop_effect_fire
5FC3  CP $02
5FC5  JP Z,pop_effect_water
5FC8  CP $03
5FCA  JP Z,pop_effect_lightning
5FCD  LD A,(enemy_count)
5FD0  AND A
5FD1  JP NZ,bubble_free        ; enemies left: just free the record
      ...
5FDC  LD A,(special_item)      ; the last bubble of a cleared round drops the round's item
5FDF  AND A
5FE0  JP P,bubble_item_spawn
```

An empty bubble popped by a player is worth one point. The chain is the sub CPU's (chapter 11): after a pop
it bursts every other bubble within twenty pixels, one per frame, counting the ones with enemies inside, and
raises a flag when the ripple has died out. `bubble_chain_score`, which runs in the player's frame, reads
the count:

```asm
bubble_chain_score:
45F0  LD HL,chain_flag_p1      ; $F678 (player 2: $F67A)
      ...
45FC  LD A,(HL)
45FD  CP $01
45FF  JR NZ,loc_4673           ; no chain finished this frame
4601  LD (HL),$00
4603  DEC HL
4604  LD A,(HL)                ; the count of enemies in the chain
4605  LD (HL),$00
4607  CP $02
4609  RET C                    ; one enemy: no bonus
460A  LD (IX+$27),$01
460E  DEC A
460F  DEC A
4610  CP $07
4612  JR C,loc_4616
4614  LD A,$06                 ; eight or more: the top entry
loc_4616:
4616  PUSH AF
4617  PUSH AF
4618  LD HL,$46A9
461B  CALL table_lookup_de     ; 2000, 4000, 8000, 16000, 32000, 64000, 64000
461E  CALL score_add_player
4621  POP AF
4622  LD HL,$46B7
4625  CALL hl_add_a
4628  LD C,(HL)                ; sound $26 or $27
4629  CALL sound_queue_push
      ...                      ; and three "points" sprites that drift up for 90 frames
```

So a monster is a thousand points, two at once are a thousand each plus two thousand, three are three
thousand plus four thousand, and all seven of a round's monsters at once are seven thousand plus sixty-four
thousand — the bonus doubles with each link. The table has a seventh entry for eight or more that no round can
reach, and it is why the game rewards patience: herd the monsters, trap them together, and burst the cluster
with one touch.

## The round's own bubbles

When the player-request queue is empty, `bubble_free_slot` consults the round:

```asm
loc_6D9A:
6D9A  LD A,(bubble_timer)      ; $E75D: counts down from 128 frames
6D9D  AND A
6D9E  JP NZ,bubble_next
6DA1  LD A,(enemy_count)
6DA4  AND A
6DA5  JP Z,bubble_next         ; no enemies: no bubbles
6DA8  LD A,(round_layout)
6DAB  CP $AA
6DAD  JP Z,bubble_next         ; a closed layout: no sources
6DB0  LD A,(bubbles_active)
6DB3  CP $10
6DB5  JP NC,bubble_next        ; sixteen bubbles already
6DB8  LD A,(rng_hi)
6DBB  BIT 0,A                  ; a coin toss for the side
      ...                      ; x = 0 or $F0 by the layout's open corners, y from LD A,R
6E1B  CALL bubble_random_lifetime
      ...
6E2E  LD A,$25
6E30  CALL random_chance       ; 37 in 256: an EXTEND letter instead
6E33  JR NC,loc_6E70
      ...
6E3B  LD A,(rng_hi)
6E3E  AND $0F
6E40  LD DE,enemy_type_list    ; sixteen entries built from the record's [$26]-[$29]
6E43  CALL de_add_a
6E46  LD A,(DE)
6E47  LD HL,$6E4F
6E4A  CALL table_lookup_de
6E4D  EX DE,HL
6E4E  JP (HL)                  ; 0 plain, 1 lightning, 2 water, 3 fire, 4 an item bubble
```

Every 128 frames, in a round whose layout is not the closed `$AA`, one bubble enters from an open corner and
drifts on the currents like any other. Its kind is drawn from a sixteen-entry list that the round record fills
— bytes `[$26]` to `[$29]` are the counts of lightning, water, fire and item bubbles among the sixteen, the
rest plain — and with a chance of 37 in 256 it is an EXTEND letter instead, the letter taken from the MCU's
free-running counter. The special kinds get a lifetime of `$7F` periods, effectively for ever, and drift until
a player bursts them.

![Round 10: water bubbles coming in over the ceiling, a fire bubble at the left wall, and the round's Monstas.](../img/ch16-round10.png)

## Water, fire, lightning

The three special kinds burst into effects that are bubble records too:

* **Fire** (`pop_effect_fire`): the record becomes a falling fire (state `$40`) that drops a pixel a frame until
  it lands on an aligned cell, then files a floor-fire request at `$F624`; the bank-2 fire code spreads a line
  of flame along the platform for a while, and any enemy within eight pixels of a flame cell dies.
* **Water** (`pop_effect_water`): a water-flow request at `$F557` — `[1, x, y, direction]` — that the bank-2
  water code turns into the stream that runs down the platforms, carrying enemies and players with it; it also
  steps one of the checksum walkers and checks the MCU's `$37`.
* **Lightning** (`pop_effect_lightning`): the record becomes a bolt (state `$20`) that flies horizontally at
  three pixels a frame in the direction the player faced when it burst; an enemy it meets dies in a seven-frame
  explosion (`lightning_hit`, sound `$33`), and the RST 0 vector is checked on the way.

A bubble that holds an enemy is not special; the special kinds catch enemies only through the sub CPU's
fifteen-pixel window (chapter 11), which marks the enemy caught without a bubble to hold it. Round 100 has no
enemies, and there the special bubbles' burst is aimed at the boss (chapter 19).

## Items in bubbles

Two flag bits of `[+$21]` make a record an item rather than a bubble. Bit 6 is a floor item: the fruit an
enemy fell as, or the round's special item, dropping two pixels a frame to a floor and, when the sub CPU marks
it collected, rising for sixty frames as its points sprite. Bit 5 is the big item — the record that scores
fifty thousand, gives the collector sixteen bubbles of count 2 (the extra-life bubbles of chapter 13) and
asks the sub CPU for a chain of eight. And the last pop of a cleared round, if the round has a special item
left to give, spawns it from the item table at `$E744` where the bubble burst: the reason the round's item
appears where your last bubble popped. What the items do is chapter 18.
