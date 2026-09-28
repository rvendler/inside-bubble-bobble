# 17. Enemies

Bubble Bobble's monsters are six programs in bank 0, one per enemy type, and they are more alike than the
sprites suggest. Each keeps a record per enemy, walks it through the same handful of states — enter, walk,
fall, jump, turn — with the same wall tests, the same speed lists and the same two questions to the MCU,
and differs from the others in one habit: the rock throwers stop to throw, the fire breathers to breathe,
the flyers follow scripts instead of platforms, and the whales bounce. This chapter takes the type-0 driver,
Zen-chan's, as the type specimen, and then the variations.

## The six types

| Type | Driver | Record | Round 1 name | Also known as | Habit |
| --- | --- | --- | --- | --- | --- |
| 0 | `enemy0_update`, `0:$8A17` | 25 bytes at `$ED49` | Zen-chan | Bubble Buster | The walker: platforms, jumps, chases |
| 1 | `enemy1_update`, `0:$8F4D` | 25 bytes at `$EDF8` | Banebou | Coiley | A walker with its own fall: it bounces on landing |
| 2 | `enemy2_update`, `0:$92F0` | 35 bytes at `$EEAC` | Mighta | Stoner | Stops to throw a rock when a player is level with it |
| 3 | `enemy3_update`, `0:$9694` | 27 bytes at `$EFA1` | Hidegons | Incendo | Stops to breathe fire, two shots per life |
| 4 | `enemy4_update`, `0:$98E4` | at `$F05F` | Pulpul | Hullaballoon | Flies: no floors, bounce scripts off the walls |
| 5 | `enemy5_update`, `0:$9E32` | at `$F113` | Monsta | Beluga | Flies diagonally, bouncing off everything |

Two more monsters are variants selected by the round record's flag byte `[$C]` (chapter 6). Bit 0 replaces
the type-0 walkers with **Invader** (Super Socket), who hops and fires missiles from a separate driver
(`enemy0_alt_update`, `0:$B149`, with `missiles_update` behind it); bit 4 replaces the type-2 rock throwers
with **Drunk** (Willy Whistle), who throws bottles from the same driver with a different sprite set. And the
ninth, Skel-Monsta (Baron von Blubba), is not an enemy record at all but a *chaser*, kept in two records of its
own and driven by `chasers_update`; he arrives when a round has gone on too long.

![The six types, each in a round of its own: Zen-chan (round 1), Mighta (7), Monsta (12), Pulpul (22), Banebou (36) and Hidegons (42).](../img/ch17-type-r1.png)

![Round 7: Mighta, the rock thrower.](../img/ch17-type-r7.png)

![Round 12: Monsta, the diagonal bouncer.](../img/ch17-type-r12.png)

![Round 22: Pulpul, the flyer.](../img/ch17-type-r22.png)

![Round 36: Banebou, the spring.](../img/ch17-type-r36.png)

![Round 42: Hidegons, the fire breather.](../img/ch17-type-r42.png)

![Round 60: the type-0 slots filled by Invaders, with their missiles.](../img/ch17-invader.png)

![Round 50: the type-2 slots filled by Drunks, with their bottles.](../img/ch17-drunk.png)

## The record

![The enemy record.](../img/ch17-record.svg)

Two other structures belong to every enemy. The shared record at `$ED21 + 4n` — `[flags, x, y, result]` — is
what task 4 shows to the other processors: the MCU reads it for the geometry, the sub CPU tests it for
touches and writes the result byte, and the bubble task writes its flags when a bubble catches, pops or
releases the enemy (chapters 10, 11, 16). And the MCU's eight bytes at `$FC27 + 8n` are the enemy's eyes: for
each player, which way it is on each axis and how far.

## A frame in the life of a Zen-chan

```asm
enemy0_update:
8A17  LD A,(enemy_type_nibbles)  ; how many of this type
8A1A  AND A
8A1B  RET Z
8A1C  LD A,(round_flags)
8A1F  BIT 0,A
8A21  RET NZ                   ; an Invader round: the other driver
8A22  LD IX,enemy0_records
      ...
loc_0_8A27:
8A28  BIT 3,(IX+$00)
8A2C  JP NZ,loc_0_8E30         ; gone: skip
8A2F  LD A,(IX+$00)
8A32  BIT 2,A
8A34  JP NZ,loc_0_8A67         ; in a bubble: watch for release or escape
8A37  BIT 1,A
8A39  JP NZ,loc_0_8A73         ; dying: the death code
8A3C  CALL enemy_bubble_events ; the bubble task's verdicts in the shared record
8A3F  JP C,loc_0_8E30
8A42  CALL enemy_hurry_check   ; angry? hurried?
8A45  BIT 0,(IX+$00)
8A49  JR NZ,loc_0_8A79         ; on the field
      ...                      ; not yet: draw the drop-in sprite, set up the entrance
8A59  CALL enemy_round_init
      ...
loc_0_8A79:
8A79  CALL obj_position_from_slot
      ...
8A81  CALL enemy_caught_check  ; caught by an item?
8A84  JP C,loc_0_8E30
8A87  CALL enemy_speed_select  ; this frame's speed list
8A8A  JP NC,enemy0_draw        ; hurry-up: it fell instead
8A8D  CALL enemy_drift         ; this frame's step count from the list
8A90  LD A,(mcu_countdown_run)
8A93  AND A
8A94  JP NZ,loc_0_8E30         ; the launchers' countdown freezes them
8A97  BIT 5,(IX+$00)
8A9B  JR NZ,loc_0_8AA3
8A9D  CALL enemy_entrance      ; still walking in
8AA0  JP enemy0_draw
loc_0_8AA3:
8AA3  BIT 0,(IX+$18)
8AA7  JR Z,loc_0_8AC5          ; not in a jump script
      ...                      ; in one: the spin frames
loc_0_8AC5:
8AC5  LD A,(IX+$07)            ; the state
8AC8  LD HL,$8E5E
8ACB  CALL table_lookup_de
8ACE  EX DE,HL
8ACF  JP (HL)                  ; 0 idle, 1 walk right, 2 fall, 3 walk left, 4 jump, 5 jump
```

The order says what the enemy is. Before it moves, it learns what happened to it since last frame: the
bubble task may have caught it (flag bit 2), a player may have popped the bubble (dying), HURRY UP may have
made it angry. Only then does it take its step, and the step is a state machine that the entrance, the
walk, the fall and the jump share.

![The states.](../img/ch17-states.svg)

### The entrance

An enemy arrives on the round record's schedule (chapter 6): task 4's spawner activates the record at the
delay the record gives, `enemy_round_init` reads the entrance script for its index from `$E5A9`, and
`enemy_entrance` drops the sprite one line per timer tick down to its target line, then waits out a
180-frame timer before setting flag bit 5, "loose". During the entrance the monster cannot be caught and
does not chase; it is the grace period at the start of every round.

### Walking

```asm
enemy_walk_down:               ; state 1: walking right (y + 8 ahead)
8B7D  LD A,(IX+$0D)            ; this frame's pixels
8B80  OR A
8B81  RET Z
8B82  LD B,A
loc_0_8B83:
8B83  PUSH BC
8B84  CALL obj_position_from_slot
8B87  LD A,(IX+$02)
8B8A  ADD A,$08
8B8C  LD H,A
8B8D  LD A,(IX+$01)
8B90  CALL wall_test           ; the cell ahead
8B93  JR NZ,loc_0_8B9B
8B95  INC (IX+$14)             ; blocked: count it ...
8B98  JP loc_0_8BF9            ; ... and turn round
loc_0_8B9B:
8B9B  LD A,(IX+$17)
8B9E  CP $03
8BA0  JR Z,loc_0_8BB0          ; a variant that never chases
8BA2  CALL target_player_alive
8BA5  JR Z,loc_0_8BB0          ; nobody to chase
8BA7  CALL mcu_player_relation ; is the player ahead of us?
8BAA  JR Z,loc_0_8BB8
8BAC  BIT 7,(HL)
8BAE  JR NZ,loc_0_8BB8         ; level with us: also "ahead"
loc_0_8BB0:
8BB0  CALL wall_test_left3     ; the floor under the next pixel
8BB3  JP NZ,enemy_fall_start   ; none: walk off the edge
8BB6  JR loc_0_8BBD
loc_0_8BB8:
8BB8  CALL enemy_wall_down_left; the cell below and ahead
8BBB  JR NZ,loc_0_8BCE         ; a gap ahead with the player beyond it: jump or turn
loc_0_8BBD:
8BBD  SET 1,(IX+$0E)
8BC1  CALL obj_slot_ptr
8BC4  INC HL
8BC5  INC HL
8BC6  INC (HL)                 ; y + 1
8BC7  POP BC
8BC8  DJNZ loc_0_8B83
8BCA  CALL enemy_decide        ; and after the step: chase or jump?
8BCD  RET
```

A walking monster moves one pixel at a time, as many as its speed list gives this frame, and at every pixel
asks the map two things: is the cell ahead solid (then turn), and is there a floor under the next pixel
(then fall). The second question is asked only when the player is *not* ahead; when the MCU says the player
is in the direction of travel, the enemy asks a different question — is there a gap ahead, with the player
on the other side — and if so it does not walk off the edge but jumps (the script at `$9624`) or, if a wall
is in the way, turns (the script at `$8E73`). This one branch is the difference between a monster that
wanders and one that comes after you, and it hangs entirely on the MCU's byte.

The speed list is `[+$0C]`, the round record's `[8]` for the round — a number from 4 to about 20 that names
one of the lists of chapter 13 — and `enemy_drift` reads the next entry into `[+$0D]` each frame. Round 1's
list 10 is a flat `1`: one pixel every frame, a little slower than the player's 1.2. The record's
speed is what the difficulty rank raises (chapter 12), and the angry bonus of +6 lists is what makes the
last monster of a round, or every monster after HURRY UP, faster than you.

### Falling and landing

`enemy_fall` drops one pixel per frame — not the speed list's rate, a flat one — until the floor test finds
solid cells under the sprite at an aligned line, and then chooses the walk state from the direction byte
`[+$08]`, or forces one at the plane's edges. A walker that has fallen off the bottom reappears at the top
like a player. The type-1 driver, Banebou's, replaces this state with a bounce: it lands and takes off
again, which is the whole of Banebou's character.

### Deciding

```asm
enemy_decide:
8E3F  DEC (IX+$15)             ; the decision timer
8E42  JR NZ,loc_0_8E4F
8E44  CALL enemy_timer_reset
8E47  LD A,(IX+$18)
8E4A  XOR $02                  ; alternate: chase, jump, chase, jump ...
8E4C  LD (IX+$18),A
loc_0_8E4F:
8E4F  BIT 1,(IX+$18)
8E53  JP NZ,loc_0_8E5A
8E56  CALL enemy_chase
8E59  RET
loc_0_8E5A:
8E5A  CALL enemy_jump_decision
8E5D  RET

enemy_chase:
94FF  LD A,(IX+$01)
9502  CP $20
9504  RET Z                    ; on the bottom row: nothing to do
9505  CALL target_player_alive
9508  RET Z
      ...                      ; the interrupt-vector check (chapter 20)
951A  LD HL,mcu_player_distance; $FC2B + 8n: |dx| to the player
      ...
9529  LD A,(HL)
952A  CP $20
952C  RET NC                   ; more than 32 lines away: ignore
952D  LD (IX+$0F),$01
9531  CALL mcu_player_relation ; which way, vertically?
9534  JR Z,loc_0_953C
9536  XOR A
9537  BIT 7,(HL)
9539  RET Z
953A  SCF                      ; level: jump
953B  RET
loc_0_953C:
953C  CALL mcu_player_relation2; which way, horizontally?
953F  JR Z,loc_0_9547
      ...
loc_0_9547:
9547  INC HL
9548  INC HL
9549  INC HL
954A  INC HL
954B  LD A,(HL)                ; |dy| to the player
954C  CP $10
954E  JR NC,loc_0_9556
9550  SET 1,(IX+$18)           ; within 16 across: next decision is a jump
9554  XOR A
9555  RET
loc_0_9556:
9556  LD (IX+$07),$01          ; further: turn towards the player
955A  LD (IX+$08),$01
955E  XOR A
955F  RET
```

The decision timer runs every step; when it expires the enemy alternates between two questions. *Chase*: if
the player is within thirty-two lines vertically, face towards it horizontally, and if it is within sixteen
pixels across, arm a jump. *Jump*: if the player is above and a wall is not in the way, run the jump script
towards it. Both questions are answered from the MCU's bytes, and both fail safely when the MCU is absent:
`mcu_player_relation` returns "not that way" for a zero byte, `enemy_chase` finds a distance of zero and
returns before deciding. A board without the MCU has monsters that patrol their platforms for ever.

### Jumping

The jump states run a **movement script**: a list of `[direction byte, repeats]` steps from a table at
`$10A2`, where each step's byte says which way to move the slot one pixel — bit 0 vertical, bit 3 its sign,
bit 4 horizontal, bit 7 its sign — so that a jump arc, a hop or a turn is a short string of bytes. `$9624`
is the standard jump up, `$9627` its mirror, `$8E73` the turn-round, and `enemy_script_step` executes one
byte per pixel of the frame's speed, with `$88` ending a script and `$99` pausing it. During a jump the
side cells are tested exactly as for the player (chapter 14), a solid cell above ends the rise, and landing
goes through the same floor test. The same script machine, with different tables, moves Pulpul and Monsta,
who never touch a floor: their "walk" states are bounce scripts chosen by which wall they met.

### Angry, hurried, stuck

`enemy_hurry_check` runs every frame before the movement. If HURRY UP has been declared (`$F44E`) the
monster is *hurried*: `enemy_speed_select` drops it through the floors instead of walking, so that the whole
round collapses to the bottom where the players are. If the last-enemy flag is up, or the monster's own flag
bit 7 is set because it escaped from a bubble, it is *angry*: six is added to its speed list, capped at 40,
and its sprite changes to the angry frames — the recolouring the player sees. A monster pressed against a
wall for sixty frames (`[+$14]`) jumps out with `enemy_stuck_jump`, which is why a Zen-chan trapped in a
corner eventually leaps free.

## Rocks and fire

Mighta and Hidegons walk like Zen-chan and interrupt the walk with an attack. The decision is the aim check
at `$7B93`, shared by both:

```asm
7B93  BIT 1,(IX+$0E)
7B97  RET Z                    ; only after a step
7B98  CALL target_player_alive
7B9B  RET Z
7B9C  LD HL,mcu_player_distance
      ...
7BAC  LD A,(HL)                ; |dx|: the player must be within 8 lines
7BAD  CP $08
      ...                      ; and at least $40 across; two free cells ahead
```

On the floor, with a live player on the same level and at least sixty-four pixels away in the facing
direction, and nothing solid in the two cells ahead, the throw starts: the wind-up animation plays on the
enemy and on a second sprite in its second slot — the rock in its hands, six frames of five — and the rock
is launched as a record of its own in `rocks_update` (`$EC29`, one per thrower), flying horizontally at the
thrower's speed plus four until it meets a wall and bursts. Hidegons's shots are the same idea with a budget
of two per life, spawned from the fire-shot table at `$EB99`, flying at speed plus ten. Both are objects the
sub CPU tests against the players (chapter 11): a rock or a shot within eight pixels burns the dragon.

Drunk's bottles are Mighta's rocks in a different tile set; Invader's missiles have their own driver,
`missiles_update`, and a launch timer that the MCU counts down for them (chapter 10) — six hundred frames,
which is why a round of Invaders fires in volleys.

## Death

When a player pops a bubble with a monster in it, the bubble task writes `$40` into the shared record with
the bubble's position and the chain place (chapter 16), and the driver's next frame finds flag bit 1 and
calls `enemy_death_update` (`$7BFC`), a routine in the fixed ROM that reads its tables from bank 0:

1. **The tumble.** A script from the table at `$80C8`, chosen by enemy type (with alternatives for a monster
   killed while hurried, released, or during the invincibility item), throws the corpse along a trajectory;
   it bounces off the top and bottom of the plane and, when the script ends, falls with the floor test until
   it lands. The frames come from `$801E` by type.
2. **The fruit.** On landing the record becomes an item (shared record state 8): the tile and attribute from
   the eleven-entry table at `$8008`, chosen by the chain place — a banana for a single monster, and better
   fruit for the second, third and later members of a chain — drawn by `death_draw_item`.
3. **The pickup.** The sub CPU's touch byte says which player walked into it; `death_draw` reads it, scores
   from the table at `$8031`, sound `$11`, and the fruit bounces four times and vanishes, or vanishes unpicked
   after the timer.

| Chain place | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th | 9th | 10th | 11th |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Points | 500 | 1000 | 2000 | 3000 | 4000 | 5000 | 6000 | 7000 | 8000 | 9000 | 10000 |

The eleven fruits are more than a round can produce — seven monsters make a chain of seven — so the last
entries are reachable only through the chain the big item asks for (chapter 16). A monster caught by an
item, a special bubble or the water dies through the same code from state `$10`, and a monster whose bubble
timed out goes back on the field through `enemy_escaped_check` with its flags set to `$A1`: on the field,
loose, and angry.

## Skel-Monsta

The chasers are two records at `$F1C2`, driven by `chasers_update` while the angry-done flag `$E343` is set —
that is, once the last-enemy timer has run out, or the HURRY UP sequence has passed and the round still has
enemies. A chaser appears in a puff near the player it is assigned to (the sprite column at `$A377`, the
cloud frames), then hunts: every frame it moves its slot one pixel towards the player on each axis, ignoring
the map entirely, and the sub CPU catches the player at ten pixels. It cannot be bubbled — it has no shared
enemy record — and it leaves only when the round ends or its player dies, puffing out as it came. In a secret
room the same two records are the exits: the sub CPU's touch test on them raises the round-end flag instead
of a death (chapter 11).

![Object bank 3 in colour group 7: the monsters' captured forms and the fruit and item tiles they fall as.](../img/ch17-sprites-bank3.png)
