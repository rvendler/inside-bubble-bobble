# 13. Bub and Bob

The two dragons are two records of fifty bytes at `$E691` and `$E6C3`, a pair of object slots, and one
routine, `player_life_cycle`, that task 3 calls every frame for both of them. Everything the player does —
walking, jumping, blowing, dying — is a function of that record and the input byte the MCU delivered during
the last blanking. This chapter is the record and the parts of the routine that concern walking, blowing and
living; the next two chapters take the jump and the collisions.

## The record

![The fifty bytes of a player.](../img/ch13-record.svg)

The record is cleared at the start of every round and every life (`player_round_init`, `$3EB4`), and its
constants are put back by `player1_params_init`:

```asm
player_round_init_p1:
3EB4  LD HL,player1_record
3EB7  LD BC,$002A
3EBA  CALL mem_clear
      ...
3EEC  LD HL,$E2C5              ; the object slot
3EEF  LD (IX+$03),L
3EF2  LD (IX+$04),H
3EF5  LD (HL),$18              ; x = 24: standing on the floor
3EF7  INC HL
3EF8  LD (HL),$18              ; attribute: Bub's green
3EFA  INC HL
3EFB  LD (HL),$18              ; y = 24: the left corner
3EFD  INC HL
3EFE  LD (HL),$12              ; tile
3F00  LD HL,mcu_p1_active
3F03  LD (HL),$01              ; tell the MCU there is a player 1
3F05  LD (IX+$09),$00          ; player index
3F09  LD (IX+$08),$01          ; facing right
3F0D  LD (IX+$07),$18
3F11  LD (IX+$1A),$1E
      ...
3F2D  LD HL,(e345_timer_word)  ; is the round clock already running?
3F30  LD A,L
3F31  OR H
3F32  RET Z
3F33  LD (IX+$25),$B4          ; then 180 frames of invincibility
3F37  RET

player1_params_init:
3FC0  LD (IX+$30),$0C          ; speed list 12
3FC4  LD (IX+$2C),$00          ; tick-rate index 0
3FC8  LD (IX+$31),$40          ; bubble speed
3FCC  LD (IX+$2E),$14          ; 20 frames between bubbles
3FD0  LD (IX+$2F),$03          ; bubble range
3FD4  LD (IX+$2D),$00          ; no scoring modes
```

Player 2 is the mirror: the slot at `$E2B5`, `y = $D8` (the right corner), facing left, Bob's blue. The
fast player of the POWER UP! code and of round 100 (`player_params_special`) changes three of the constants:
speed list 20, four frames between bubbles, and range 6.

## The life cycle

![The state byte and its transitions.](../img/ch13-states.svg)

`player_life_cycle` dispatches on the bits of the state byte:

```asm
player_life_cycle:
4011  LD IX,player1_record
4015  LD B,$02
loc_4017:
4017  PUSH BC
4018  LD A,(IX+$00)
401B  BIT 7,A
401D  JP NZ,loc_406F           ; $80: dead, the bank-2 handler
4020  BIT 2,A
4022  JP NZ,loc_4061           ; 4: the bank-2 special state
4025  BIT 0,A
4027  JP NZ,player_alive_update; 1: alive
402A  BIT 1,A
402C  JP NZ,loc_40DF           ; 2: dying
402F  BIT 4,A
4031  JP NZ,loc_407D           ; $10: just caught
4034  LD A,(round_start)       ; 0: waiting for the round to start
4037  AND A
4038  JP P,loc_41D6
      ...
405A  LD (IX+$00),$01          ; alive
405E  JP player_alive_update
```

The transition that matters most is the one the main CPU does not make. State `$10` is written by the sub
CPU (chapter 11) when an enemy, a rock, a missile or the boss is close enough; task 3 finds it on the next
frame and runs the hit:

```asm
loc_407D:
407D  LD C,$01
407F  CALL difficulty_drop     ; the rank drops by 1 for a death
      ...
409D  BIT 0,(IX+$19)           ; burnt?
40A1  JR NZ,loc_40BC
40A3  LD A,(IX+$01)
40A6  ADD A,$07                ; the death sprite starts 7 pixels up ...
40A8  LD (HL),A
      ...
40B1  LD A,(IX+$02)
40B4  SUB $08                  ; ... and 8 to the left
40B6  LD (HL),A
      ...
40D6  LD (IX+$00),$02          ; dying
40DA  LD C,$0D
40DC  CALL sound_queue_push    ; the death sound
```

The dying state runs `death_anim` for 41 frames from a table of `[ticks, tile, tile]` — the dragon spins and
drifts — then takes the consequences: the EXTEND bonus if the letters were complete, the score variables
cleared, a life removed, and either a respawn through `player_round_init` (with the 180 frames of blinking
invincibility if the round clock is running, so that a player who dies mid-round is not caught again on the
spot) or, with no lives left, the player's bit cleared from `players_alive`, the round recorded for the
results screen, and the rank dropped by three more. The invincibility is `[+$25]`, counted down by
`invincible_tick`, and its low bit blanks the sprite every other frame — that is the blink.

## A frame of an alive player

```asm
player_alive_update:
419E  CALL obj_position_from_slot   ; x, y from the object slot into the record
41A1  CALL player_pos_to_mcu        ; ... and to the MCU (chapter 10)
41A4  CALL walk_anim_frame          ; this frame's step from the speed list
41A7  CALL invincible_tick
41AA  CALL jump_control             ; chapter 14
41AD  CALL bubble_blow
41B0  CALL walk_move                ; pushed by a bubble (chapter 11)
41B3  CALL ground_control           ; walking, or falling (chapter 14)
41B6  CALL bubble_anim_timer
41B9  CALL sprite_anim_draw         ; the animation, into the object slot
41BC  LD A,$02
41BE  CALL bank_select
41C1  CALL $854E                    ; special item pickup
41C4  CALL $873E                    ; bonus item pickup
41C7  CALL $91A3                    ; power item pickup
41CA  CALL $8CC7                    ; big item pickup
41CD  CALL $9233                    ; the power effect timer
41D0  CALL bubble_chain_score       ; chain scores from the sub CPU (chapter 16)
41D3  CALL bank_restore
loc_41D6:
41D6  XOR A
41D7  LD (IX+$21),A                 ; the sub CPU's push fields, consumed
41DA  LD (IX+$22),A
41DD  LD (IX+$24),A                 ; and the bounce request
```

The order is the order of authority: the position is taken from the object slot, because the slot is what
was drawn and what the sub CPU tested; the jump is decided before the walk, because a jump in progress
overrides the joystick's sideways control; the animation is drawn last, from whatever the movement decided
the pose is.

## Inputs

`read_inputs`, called by task 2, copies the two MCU bytes `$FC22` and `$FC23` to `$E33F` and `$E340` once
per frame, and `read_input` (`$43B4`) returns the right one for the player in IX. The bits are active low:
bit 0 left, bit 1 right, bit 4 jump, bit 5 bubble, bit 6 start. The joystick's up and down are not read at
all; Bubble Bobble has no ladders and no ducking, and the two bits are ignored everywhere except in the
name entry.

## Walking

Walking is `ground_control` when the player is neither falling nor jumping:

```asm
ground_control:
4246  BIT 0,(IX+$1B)
424A  RET NZ                   ; burnt: no control
424B  BIT 0,(IX+$0B)
424F  JP NZ,fall_control       ; falling: chapter 14
4252  BIT 0,(IX+$0C)
4256  RET NZ                   ; jumping: chapter 14
4257  CALL read_input
425A  BIT 0,A
425C  JR Z,loc_42AD            ; left
425E  BIT 1,A
4260  JR Z,loc_4270            ; right
4262  LD (IX+$23),$00          ; neither: standing
4266  LD A,(IX+$22)
4269  AND A
426A  RET NZ
426B  LD A,$00
426D  JP set_anim              ; animation 0
loc_4270:
4270  CALL set_facing
4273  LD (IX+$23),$02          ; pose 2: walking right
4277  LD A,$08
4279  CALL set_anim            ; animation 8: the walk
427C  LD A,(IX+$20)            ; this frame's step: 0, 1 or 2 pixels
427F  OR A
4280  RET Z
4281  LD B,A
loc_4282:
4282  PUSH BC
4283  CALL obj_position_from_slot
4286  LD A,(IX+$02)
4289  ADD A,$08                ; the cell 8 pixels ahead ...
428B  LD H,A
428C  LD A,(IX+$01)
428F  CALL wall_test           ; ... at the sprite's row
4292  JR Z,loc_42AB            ; solid: stop
4294  CALL wall_test_left3     ; the three cells below
4297  JR NZ,loc_42A5           ; no floor under the next pixel: fall
4299  CALL obj_slot_ptr
429C  INC HL
429D  INC HL
429E  INC (HL)                 ; y + 1 in the object slot
429F  POP BC
42A0  DJNZ loc_4282            ; the next pixel of this frame's step
42A2  JP walk_score
loc_42A5:
42A5  POP BC
42A6  SET 0,(IX+$0B)           ; falling
42AA  RET
```

The speed is not a number but a list. `walk_anim_frame` steps through the list named by `[+$30]` — one
byte per frame, `$FF` wrapping to the start — and puts the byte in `[+$20]`; `ground_control` then moves that
many pixels, one at a time, with the wall tests repeated for each. List 12, the normal player, is `1 1 1 1
2`: six pixels in five frames, 1.2 pixels per frame, 71 pixels a second. The fast player's list 20 is a flat
`2`, and the invincible player's list 22 is `3 2 2 2 2 2 2 2 2 2`. There are forty-two lists in the table at
`$11CE`, most of them for the enemies (chapter 17), and they are why the monsters' speeds can be graded so
finely by the round record: a speed of 12 and a speed of 13 differ by one extra pixel every few frames.

> [!NOTE]
> **Fractional speeds without fractions**
> A sprite can only be drawn at whole pixels, but games want speeds in between. The common solution is
> **fixed-point** arithmetic: the position is kept with an extra byte for the fraction of a pixel, the speed is
> added to it every frame — 1.2 pixels becomes 1 and 51/256 — and only the whole part is used for drawing. The
> fraction carries over, and every fifth frame or so the sprite moves one pixel more.
>
> Bubble Bobble gets the same result with a table instead of arithmetic. The speed list spells out the pixels to
> move, frame by frame: `1 1 1 1 2` is 1.2 pixels per frame, written out in full. The table costs a few bytes per
> speed, but it keeps every position a single whole byte, lets the wall tests run once for every pixel moved, and
> lets the designers choose exactly on which frames the extra pixels come.

The wall tests are the subject of chapter 15; here it is enough that the cell ahead must be air and one of
the three cells under the sprite must be solid, or the pixel is not taken and, in the second case, the player
falls. The map has no rows above `x = $E0`; up there the air-control routine clamps `y` to `$18-$E7` instead
of testing cells.

## The animation system

The player is always in exactly one of twelve animations, named by an offset into the table at `$4583`:

| Offset | Frames | Tick rates | Used for |
| --- | --- | --- | --- |
| 0 | 2 | 20, 10, 10, 5 | Standing (a slow two-frame idle) |
| 8 | 4 | 5, 3, 3, 2 | Walking |
| `$10` | 2 | 10, 6, 6, 4 | (spare) |
| `$18` | 2 | 10, 6, 6, 4 | Falling |
| `$20` | 2 | 10, 6, 6, 4 | Jumping |
| `$28` | 3 | 8, 6, 6, 5 | (spare) |
| `$30` | 3 | 8, 6, 6, 5 | Being pushed by a bubble |
| `$38` | 2 | 10, 8, 8, 7 | Burnt |
| `$40`, `$48`, `$50`, `$58` | 4 | 3, 2, 2, 2 | Blowing, one-shot: standing, walking, falling, jumping variants |

Each entry is eight bytes: the frame count, four tick rates of which `[+$2C]` picks one, a pointer to the
tiles, and flags — bit 0 marks a one-shot animation that ends with `[+$12] = $FF`, bit 1 a list of tile
numbers rather than a base. `sprite_anim_draw` advances the tick and the frame and writes the tile into the
object slot through `draw_sprite_2x2` or its flipped twin, chosen by the facing byte; the tile of a frame is
the base plus four times the frame number, which is how the tile ROM is laid out (chapter 4). The four tick
rates are a design allowance that the shipped game barely uses: `[+$2C]` is set to 0 and stays there.

![Bub's walk and blow frames, decoded from the tile ROM.](../img/ch04-bub-frames.png)

`set_anim` refuses to change the animation while a one-shot is playing (`[+$0A]` bit 2), which is what keeps
the blowing pose on screen for its full four frames while the player keeps walking underneath it.

## Blowing bubbles

```asm
bubble_blow:
4B75  BIT 0,(IX+$0A)
4B79  JP NZ,loc_4C02           ; already blowing: count the cooldown
4B7C  CALL read_input
4B7F  BIT 5,A
4B81  JR Z,loc_4B88            ; button down
4B83  RES 1,(IX+$0A)           ; button up: arm it again
4B87  RET
loc_4B88:
4B88  BIT 1,(IX+$0A)
4B8C  RET NZ                   ; still held from last time: nothing
4B8D  LD A,(mcu_ready)
4B90  AND $25
4B92  JR NZ,loc_4B95
4B94  PUSH BC                  ; the MCU byte has the wrong bits: unbalance the stack
loc_4B95:
4B95  LD HL,bubble_request_p1  ; $E75E (player 2: $E764)
      ...
4BA1  LD A,$01                 ; count 1 ...
4BA3  BIT 6,(IX+$2D)
4BA7  JR Z,loc_4BB3
4BA9  DEC (IX+$28)             ; ... or 2 for an extra-life bubble
      ...
4BB3  LD (HL),A
4BB5  LD A,(IX+$01)
4BB8  LD (HL),A                ; x
4BBA  LD A,(IX+$02)
4BBD  LD (HL),A                ; y
4BBF  LD A,(IX+$08)
4BC2  LD (HL),A                ; facing
4BC4  LD A,(IX+$31)
4BC7  LD (HL),A                ; speed
4BC9  LD A,(IX+$2F)
4BCC  LD (HL),A                ; range
4BCD  LD B,$0D
4BCF  LD HL,$4C1A              ; the blowing variant of the current animation
      ...
4BDE  CALL set_anim
4BE1  LD HL,bubbles_blown
4BE4  INC (HL)
4BE5  BIT 2,(IX+$2D)
4BE9  LD DE,$0010
4BEC  CALL NZ,score_add_player ; 10 points in the power-up mode
4BEF  LD A,(IX+$2E)
4BF2  LD (IX+$26),A            ; the cooldown
4BF5  SET 1,(IX+$0A)
4BF9  SET 0,(IX+$0A)
4BFD  SET 2,(IX+$0A)
4C01  RET
```

A bubble is a request: six bytes at `$E75E` for player 1 or `$E764` for player 2 — count, position, facing,
speed, range — that the bubble task (chapter 16) picks up in its own frame and turns into a record. The player
code never touches a bubble after that. The button must be released between bubbles (`[+$0A]` bit 1), and
the cooldown of twenty frames (`[+$2E]`, four for the fast player) is what limits a player to three bubbles a
second; the fast player's twelve a second, with range 6, is the difference the POWER UP! code makes.

## What goes out, what comes back

Every frame the player sends two bytes to the MCU — its position — and nothing else. It reads nothing back:
the MCU's geometry is for the enemies. What the player does read, in the frame after they are written, are
the sub CPU's bytes in its own record: the state `$10`, the push fields `[+$21]`, `[+$22]` that
`walk_move` turns into motion with the same wall tests as walking, the bounce request `[+$24]`, and the
burnt flags. The bank-2 pickup routines that follow the movement are the only object-against-object tests
the main CPU makes on the player's behalf: an item within fourteen pixels (twenty-four for the big items) is
collected, scored and its effect started (chapter 18).

Lives are two bytes at `$E645` and `$E64A`, drawn by `lives_display` as up to five small dragons along the
bottom of the screen; the extra-life thresholds of chapter 7 raise them through `add_score`, and the
respawn takes one. The player's position is never bounds-checked against the enemies by the main CPU, its
sprite is never compared with anything but the map, and its death is a byte it did not write. That division
is the subject of chapter 15.
