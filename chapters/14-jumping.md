# 14. Jumping, falling and riding

A jump in Bubble Bobble is a table. The player rises forty-two pixels along a fixed arc, drifts sideways on
the steps a second table marks, passes up through platforms and lands on the first one whose cells are
solid under the sprite's feet on the way down. There is no velocity and no gravity anywhere in the program:
what feels like an arc is a list of sixty-one numbers read one per step, and what feels like weight is the
number of steps taken per frame.

> [!NOTE]
> **How games usually jump**
> Most platform games model a jump with two numbers. The vertical **velocity** says how far the character moves up
> or down each frame; **gravity** is a constant subtracted from the velocity each frame. A jump sets the velocity
> to a large upward value; gravity wears it down to zero at the top of the arc and then makes it more and more
> negative, so the character falls faster and faster, usually up to a maximum, the **terminal velocity**. The
> result is a smooth parabola whose shape follows from the numbers: a stronger launch or weaker gravity gives a
> higher, floatier jump, and many games let the player cut a jump short by releasing the button.
>
> Bubble Bobble does none of this. Its arc is written out as a table of movements per step, the same every time,
> and a fall is a constant one pixel per step. What it gives up is variety; what it gains is a jump whose height
> and reach are the same everywhere — forty-two pixels up, about thirty-three across — for the round designers to
> build around.

## Starting a jump

```asm
jump_control:
4868  BIT 0,(IX+$0B)
486C  JR NZ,loc_4874           ; falling
486E  BIT 0,(IX+$0C)
4872  JR Z,loc_4894            ; not jumping: may we start one?
loc_4874:
4874  BIT 0,(IX+$24)           ; landed on a bubble (the sub CPU)?
4878  JR Z,loc_488D
487A  RES 0,(IX+$24)
487E  CALL read_input
4881  BIT 4,A
4883  JR NZ,loc_488D           ; button not held: no bounce
4885  LD DE,$0001
4888  CALL score_add_player    ; a bounce is worth one point
488B  JR loc_48A5              ; and restarts the jump
loc_488D:
488D  BIT 0,(IX+$0B)
4891  RET NZ                   ; falling: nothing
4892  JR loc_4911              ; jumping: continue below
loc_4894:
4894  CALL read_input
4897  BIT 4,A
4899  JR Z,loc_48A0            ; button down
489B  RES 1,(IX+$0C)           ; button up: arm
489F  RET
loc_48A0:
48A0  BIT 1,(IX+$0C)
48A4  RET NZ                   ; still held: no auto-jump
loc_48A5:
48A5  LD C,$2C
48A7  CALL sound_queue_push    ; the jump sound
48AA  LD (IX+$0C),$00
48AE  SET 1,(IX+$0C)
      ...
48BA  BIT 1,(IX+$2D)
48BE  LD DE,$0050
48C1  CALL NZ,score_add_player ; 50 points in the power-up mode
48C4  SET 0,(IX+$0C)           ; jumping
48C8  LD HL,jumps_count
48CB  INC (HL)
48CC  CALL read_input
48CF  BIT 0,A
48D1  JR Z,loc_48DD            ; left held
48D3  BIT 1,A
48D5  JR Z,loc_48E3            ; right held
48D7  SET 5,(IX+$0C)           ; neither: straight up
48DB  JR loc_48E7
loc_48DD:
48DD  SET 4,(IX+$0C)           ; to the left
48E1  JR loc_48E7
loc_48E3:
48E3  SET 3,(IX+$0C)           ; to the right
loc_48E7:
48E7  LD HL,$4AEC              ; the arc table
48EA  LD (IX+$0D),L
48ED  LD (IX+$0E),H
48F0  LD A,(HL)
48F1  LD (IX+$0F),A            ; dy of the first segment
48F4  INC HL
48F5  LD A,(HL)
48F6  LD (IX+$10),A            ; its length
48F9  INC HL
48FA  LD A,(HL)
48FB  CALL set_anim            ; its animation
48FE  LD (IX+$11),$00          ; step 0
      ...
490D  RES 0,(IX+$0B)
loc_4911:
4911  CALL set_facing
4914  CALL walk_step           ; air control: 1 pixel every third frame
4917  LD A,(IX+$20)            ; this frame's step count from the speed list
491A  OR A
491B  RET Z
491C  LD B,A
loc_491D:
491D  PUSH BC
491E  CALL jump_physics        ; one step of the arc
4921  POP BC
4922  DJNZ loc_491D
4924  RET
```

The direction of a jump is fixed at take-off. Whichever way the stick is held when the button goes down
becomes bit 3 or 4 of `[+$0C]`, or bit 5 for a vertical jump, and the drift follows that bit for the whole
arc; the stick can only add the slow air control of `walk_step`, one pixel every third frame. This is the
Bubble Bobble jump everyone remembers: committed, and steerable only a little.

## The arc

```
jump_arc_table:   ; [dy, steps, animation] until $80
4AEC  02 10 20    ; +2 pixels for 16 steps, animation $20 (jumping)
4AEF  01 09 20    ; +1 for 9
4AF2  00 02 20    ; hover
4AF5  01 01 20
4AF8  00 02 20
4AFB  00 03 18    ; the top, animation $18 (falling)
4AFE  FF 01 18    ; -1
4B01  00 02 18
4B04  FF 09 18    ; -1 for 9
4B07  FE 10 18    ; -2 for 16
4B0A  80          ; end
```

![The arc from the table: 42 pixels up, 33 across when the drift is applied throughout.](../img/ch14-jump-arc.png)

`jump_physics` executes one step: it sets the pose (1 while `dy` is positive, 3 while it is negative), runs
the side tests of chapter 15 on the moving side, then adds `dy` to the slot's `x` and, if the drift table
says so for this step number and nothing has blocked the side, one pixel to `y`:

```asm
loc_4A7D:
4A7D  CALL obj_slot_ptr
4A80  LD A,(IX+$0F)
4A83  ADD A,(HL)               ; x += dy
4A84  LD (HL),A
4A85  BIT 5,(IX+$0C)
4A89  JR NZ,loc_4AAA           ; a vertical jump: no drift
4A8B  BIT 6,(IX+$0C)
4A8F  JR NZ,loc_4AAA           ; blocked at the side: no drift
4A91  INC HL
4A92  INC HL
4A93  LD A,(IX+$11)
4A96  LD DE,$4B0F              ; the drift table
4A99  CALL de_add_a
4A9C  LD A,(DE)
4A9D  OR A
4A9E  JR Z,loc_4AAA            ; 0: not this step
4AA0  BIT 3,(IX+$0C)
4AA4  JR NZ,loc_4AA9
4AA6  DEC (HL)                 ; y - 1
4AA7  JR loc_4AAA
loc_4AA9:
4AA9  INC (HL)                 ; y + 1
loc_4AAA:
4AAA  INC (IX+$11)             ; next step
4AAD  DEC (IX+$10)
4AB0  JR NZ,loc_4AD3           ; more of this segment
      ...                      ; else the next segment, or $80: the jump is over
loc_4ADF:
4ADF  SET 0,(IX+$0B)           ; falling from here
```

The drift table is sixty-one bytes of ones and zeros, with a one on about two steps in three — sparser at
the beginning and the end of the arc, denser in the middle — so a jump covers about thirty-three pixels
across for forty-two up. Because the arc is walked in steps and the player takes as many steps per frame as
the speed list gives (one, or two on every fifth frame), the whole rise takes twenty-seven frames and a
fast player's jump is the same shape at a different speed.

![One jump, from the traced game: frames 1031 to 1069, three frames apart. Launch from the floor, the rise through the platform, the landing, and the next jump.](../img/ch14-jump-strip.png)

The traced jump above began at `x = 32`, reached `x = 74` at its top after 27 frames, and landed on the
first platform at `x = 72` two steps into its descent.

## Through the platforms

Nothing in `jump_physics` stops a rising player: the tests on the way up concern the sides only. The
platforms are one-way because of what the landing test asks for. On the way down, at every step where `x`
is a multiple of eight, the code looks at the three cells of the sprite's own lower row and at the three
below it:

```asm
loc_4A3E:
4A3E  BIT 7,(IX+$0F)
4A42  JP Z,loc_4A7D            ; rising: no landing test
4A45  LD A,(IX+$01)
4A48  AND $07
4A4A  JR NZ,loc_4A7D           ; not on a cell boundary: not yet
4A4C  LD H,(IX+$02)
4A4F  LD A,(IX+$01)
4A52  CALL wall_test           ; the cell at (x, y)
4A55  JR Z,loc_4A7D            ; solid: we are inside a platform, keep going
4A57  LD A,(IX+$02)
4A5A  SUB $07
4A5C  LD H,A
4A5D  LD A,(IX+$01)
4A60  CALL wall_test           ; (x, y - 7)
4A63  JR Z,loc_4A7D
4A65  LD A,(IX+$02)
4A68  ADD A,$07
4A6A  LD H,A
4A6B  LD A,(IX+$01)
4A6E  CALL wall_test           ; (x, y + 7)
4A71  JR Z,loc_4A7D
4A73  CALL wall_test_left3     ; the three cells under the sprite
4A76  JR NZ,loc_4A7D           ; all air: keep falling
4A78  SET 0,(IX+$0B)           ; a floor: land
4A7C  RET
```

A player whose lower half overlaps a platform is inside it and passes through; one whose lower half is
clear with solid cells beneath has landed. The same test, in `fall_control`, governs a plain fall, and it is
why a jump that reaches a platform's height exactly at a cell boundary lands on it and one that is a pixel
short passes up through it and comes down on top: the test only fires on multiples of eight, so the sprite
snaps to the grid on landing.

## Falling

```asm
fall_control:
42E2  CALL rom_check_walker_0ae3
42E5  LD (IX+$23),$03          ; pose 3
42E9  LD A,$18
42EB  CALL set_anim            ; the falling animation
42EE  LD A,(IX+$20)
42F1  OR A
42F2  RET Z
42F3  LD B,A                   ; this frame's pixels
loc_42F4:
42F4  PUSH BC
42F5  CALL obj_position_from_slot
42F8  LD A,(IX+$01)
42FB  CP $20
42FD  JR C,loc_4312            ; below the map: keep falling
42FF  CP $E0
4301  JP NC,loc_4312           ; above it: keep falling
4304  AND $07
4306  JR NZ,loc_4312           ; not on a boundary
4308  CALL wall_test_here3     ; the sprite's own row
430B  JR Z,loc_4312            ; inside a platform
430D  CALL wall_test_left3     ; the row below
4310  JR Z,loc_4325            ; a floor: land
loc_4312:
4312  CALL obj_slot_ptr
4315  DEC (HL)                 ; x - 1
4316  JR NZ,loc_431C
4318  LD HL,fell_through_count ; x reached 0: through the bottom
431B  INC (HL)
loc_431C:
431C  POP BC
431D  DJNZ loc_42F4
431F  CALL walk_step           ; air control
4322  JP set_facing
loc_4325:
4325  POP BC
4326  LD (IX+$0B),$00          ; landed
432A  LD A,(IX+$0C)
432D  AND $02
432F  LD (IX+$0C),A            ; keep only "button held"
4332  RET
```

A fall is one pixel per step at the speed list's rate — the same 1.2 pixels a frame as walking. There is no
terminal velocity because there is no velocity; a long fall takes as long as the distance divided by the
walking speed. When `x` counts down through zero the slot's byte wraps to 255 and the sprite reappears at
the top of the plane, still falling: the bottom of every round is open, and the round's top border rows are
air in the map wherever the designers wanted the wrap to work (chapter 6).

## Bouncing and riding

The sub CPU's landing window (chapter 11) sets `[+$24]` when a falling player is twelve to twenty-one pixels
above a bubble. `jump_control` reads it at the top of the next frame: with the jump button held the arc is
restarted from where the player is — a bounce, worth one point — and with the button up the request is
simply cleared, and the player keeps falling onto the bubble, which the sub CPU has meanwhile pushed down
(`[$1B] = 4` in the bubble's record) so that the player appears to ride it for a moment before the fall
resumes. Bouncing repeatedly across a field of bubbles is the technique the instructions call "YOU CAN JUMP
OVER BUBBLES", and it is one flag, one table restart and one point per bounce.

A player carried by a bubble the other way — pushed sideways by a bubble drifting into it while it stands
still — is `walk_move`: the sub CPU writes the displacement into `[+$22]` and `walk_move` applies it a pixel
at a time with the same wall tests as walking, in the "pushed" animation. Neither routine knows about
bubbles; they know about a byte in their own record, written by another processor.
