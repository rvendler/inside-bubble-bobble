# 9. The frame: interrupts and the scheduler

After boot, the main CPU executes exactly one instruction of its own: `JR $01ED`, a jump to itself. Everything
that makes the game a game — the players, the bubbles, the monsters, the scoring, the attract mode — runs inside
the interrupt handler that the MCU triggers once per frame. The handler calls a small cooperative scheduler,
the scheduler runs each of six tasks until it yields, and when the last one has yielded the handler returns to
the two-byte loop to wait for the next frame. This chapter is about that kernel: it is 150 bytes of code, and
every later chapter runs on top of it.

## The interrupt

The main CPU has no line to the video circuit. Its interrupt comes from the MCU, which is itself interrupted at
the start of vertical blanking (line 240 of the 264-line frame), reads the joysticks and coin switches, and then
drops bit 6 of its port 1 for a moment. On the traced machine the pulse arrives about 100 microseconds after
VBLANK begins. The CPU runs in interrupt mode 2 with `I = $0B`, the MCU has put `$2E` into the shared byte
`$FC00` that the hardware presents as the vector, and the word at `$0B2E` is `$044D`: `irq_vblank`.

```asm
irq_vblank:
044D  PUSH AF
044E  LD (IO_watchdog),A       ; kick the hardware watchdog
0451  LD A,(mcu_dswa)          ; DIP switch A ...
0454  AND $05
0456  JP Z,irq_test_mode       ; ... selects the test modes (chapter 3)
0459  LD A,(frame_done)        ; $E194
045C  AND A
045D  JR Z,irq_nested          ; the previous frame's tasks are still running
045F  CALL irq_frame_start
0462  LD HL,frame_done
0465  LD (HL),$00
0467  EI
0468  CALL scheduler_run
046B  LD A,$01
046D  LD (frame_done),A
0470  POP AF
0471  DI
0472  POP HL                   ; the interrupted PC
0473  PUSH AF
0474  LD A,H
0475  CP $C0
0477  JR C,loc_048B            ; it must be in ROM
0479  ...                      ; otherwise: TIME ERROR
048B  POP AF
048C  PUSH HL
048D  EI
048E  RETI
```

Three paths leave this routine. If the DIP switches ask for a test mode, `irq_test_mode` handles the frame and
the game never runs. If `frame_done` is zero, the tasks of the previous frame have not finished: the handler
takes the `irq_nested` path described below. Otherwise this is a normal frame:

```asm
irq_frame_start:
04AD  LD HL,objram_shadow      ; $E1CD
04B0  LD DE,$DD00
04B3  LD BC,$0168
04B6  LDIR                     ; 360 bytes: the object list, to the hardware
04B8  CALL sound_queue_pump    ; one queued sound byte to the sound CPU (chapter 8)
04BB  CALL rng_pre             ; the random number generator's per-frame step (chapter 20)
                               ; ... falls into irq_essentials

irq_essentials:
04BE  PUSH BC
04BF  PUSH DE
04C0  PUSH HL
04C1  CALL coin_handling       ; credits from the MCU's coin counters
04C4  CALL tilt_check
04C7  CALL rng_step
04CA  CALL timer_chain         ; frames, seconds, minutes
04CD  CALL sub_cpu_watchdog
04D0  LD HL,frame_counter      ; $E338
04D3  INC (HL)
04D4  POP HL
04D5  POP DE
04D6  POP BC
04D7  RET
```

The order matters. The object list is copied first because the video hardware reads object RAM while it draws
the picture, and a half-copied list would show objects at last frame's positions with this frame's tiles. The
`LDIR` of 360 bytes takes 7,560 cycles — 1.26 milliseconds — and VBLANK lasts 2.56 milliseconds, so the copy
is done with a millisecond to spare, before the first visible line. The game code never touches `$DD00`
directly; it builds the next frame's list in the shadow at `$E1CD` (chapter 5) at its leisure, and the handler
commits it atomically.

The per-frame essentials come after: `coin_handling` turns the MCU's coin counts into credits, `timer_chain`
counts frames into seconds and minutes (three bytes at `$E335`, each rolling over at 60), and
`sub_cpu_watchdog` reads the heartbeat byte the sub CPU increments at `$F66E` — if it has not changed for 180
frames, `RST $00` reboots the whole machine, on the theory that a stalled sub CPU means a broken board. Then
`frame_done` is cleared, interrupts are re-enabled, and the scheduler is called from inside the handler.

## The scheduler

Six tasks live in six bytes at `$E000-$E005`, the **task states**, and six saved stack pointers at
`$E006-$E011`. Each task has a 64-byte stack at `$E020 + 64 x n`. The scheduler makes one pass over the six
slots:

```asm
scheduler_run:
005E  LD HL,task_state         ; $E000
sched_check_slot:
0061  LD A,(HL)
0062  AND A
0063  JR Z,sched_next_slot     ; 0: asleep
0065  DEC (HL)
0066  JR NZ,sched_next_slot    ; 2 or more: counting down, not yet
task_switch_in:
0068  LD (cur_task_ptr),HL     ; $E192
006B  SLA L
006D  LD A,$06
006F  ADD A,L
0070  LD L,A                   ; HL = $E006 + 2n
0071  LD (sched_sp),SP         ; $E1C5: where to come back to
0075  LD E,(HL)
0076  INC HL
0077  LD D,(HL)
0078  EX DE,HL
0079  LD SP,HL                 ; the task's stack
007A  POP IY
007C  POP IX
007E  POP HL
007F  POP DE
0080  POP BC
0081  EXX
0082  POP HL
0083  POP DE
0084  POP BC
0085  RET                      ; ... into the task, where it last yielded
sched_next_slot:
0086  INC L
0087  LD A,L
0088  CP $06
008A  JR NZ,sched_check_slot
008C  RET
```

A state of 0 means the task is asleep and is skipped. A state of 1 means it runs now: the scheduler saves its
own stack pointer, loads the task's, pops the eight register pairs the task saved when it last yielded, and
`RET`s to the instruction after the yield. A state of 2 or more is a countdown: it is decremented once per
frame and the task runs when it reaches 1, which is how a task sleeps for a fixed number of frames without
polling.

Yielding is the reverse, reached through two of the `RST` vectors at the bottom of the ROM:

```asm
rst18_yield:                   ; RST $18: sleep; A = new state
0018  PUSH BC
0019  PUSH DE
001A  PUSH HL
001B  JP task_switch_out
rst20_yield_runnable:          ; RST $20: run again next frame
0020  PUSH BC
0021  PUSH DE
0022  PUSH HL
0023  LD A,$01
0025  JP task_switch_out

task_switch_out:
0093  EXX
0094  PUSH BC
0095  PUSH DE
0096  PUSH HL
0097  PUSH IX
0099  PUSH IY
009B  LD HL,(cur_task_ptr)
009E  LD (HL),A                ; the task's new state
009F  SLA L
00A1  LD A,$06
00A3  ADD A,L
00A4  LD L,A
00A5  LD (tmp_sp),SP
00A9  LD DE,(tmp_sp)
00AD  LD (HL),E                ; save the task's SP
00AE  INC HL
00AF  LD (HL),D
00B0  LD SP,(sched_sp)         ; back on the scheduler's stack
00B4  LD HL,(cur_task_ptr)
00B7  JR sched_next_slot
```

`RST $20` is the ordinary end of a task's frame: "I am done, run me again next frame". `RST $18` with `A = n`
yields and runs again n frames later, so `RST $20` is the case n = 1; with `A = 0` the task is suspended until
another task wakes it. Note that the `DEC` in the scheduler leaves a running task's state at 0: a task is asleep
while it runs and chooses its next state only when it yields. A yield costs about 270 cycles to switch out and
230 to switch in, so with four tasks the scheduler's whole overhead is about 2% of a frame.

The remaining vectors manage tasks from outside:

| Vector | Name | Effect |
| --- | --- | --- |
| `RST $08` | `task_clear` | `state[A] = 0`: put task A to sleep |
| `RST $10` | `task_wake` | `state[A] = 1`: task A runs on the next pass |
| `RST $18` | `yield` | Save the current task with state A |
| `RST $20` | `yield_runnable` | Save the current task with state 1 |
| `RST $28` | `tasks_clear_all` | All six states to 0 |
| `RST $30` | `task_start` | Create task A from scratch |

`RST $30` builds the stack frame that `task_switch_in` expects. It sets the state to 1, points the slot's SP at
the base of the task's stack, and stores the entry address sixteen bytes above it — where the `RET` will find
it after the eight pops — with the sixteen bytes in between as whatever the RAM held:

```asm
rst30_task_start:
0030  LD L,A
0031  LD H,$E0
0033  LD (HL),$01              ; runnable
0035  PUSH HL
0036  CALL times64             ; DE = 64 x A
0039  LD HL,$E020
003C  ADD HL,DE                ; the stack base for this slot
003D  EX DE,HL
003E  POP HL
003F  SLA L
0041  LD C,L
0042  LD A,$06
0044  ADD A,L
0045  LD L,A
0046  LD (HL),E                ; slot SP = base
0047  INC HL
0048  LD (HL),D
0049  LD A,$10
004B  ADD A,E
004C  LD E,A                   ; DE = base + 16
004D  JR NC,loc_0050
004F  INC D
loc_0050:
0050  LD HL,$0B22              ; the entry table
0053  LD B,$00
0055  ADD HL,BC                ; + 2 x task number
0056  LD C,(HL)
0057  INC HL
0058  LD B,(HL)
0059  EX DE,HL
005A  LD (HL),C                ; entry address at base + 16
005B  INC HL
005C  LD (HL),B
005D  RET
```

The entry table at `$0B22` is twelve bytes of addresses followed by two more — the interrupt vector, which the
MCU's `$2E` selects because `$0B22 + 12 = $0B2E`. The two tables are one:

```
0B22  17 1D    task 0  $1D17  task0_game_flow
0B24  F7 2A    task 1  $2AF7  task1_attract
0B26  38 05    task 2  $0538  task2_round_loop
0B28  EF 3D    task 3  $3DEF  task3_enemies
0B2A  A8 85    task 4  0:$85A8 task4_enemies
0B2C  3B 5B    task 5  $5B3B  task5_bubbles
0B2E  4D 04    interrupt vector: irq_vblank
```

A task starts with its stack pointer at `base + 18` and pushes downward from there, towards the previous task's
slot. Task 0's stack therefore runs below `$E020`, into the fourteen free bytes `$E012-$E01F` that separate it
from the table of saved stack pointers. The RAM trace recorded during the port shows writes as low as `$E012`
and no lower: two bytes of margin. Nothing in the code checks it; the programmers knew how deep their calls
went.

## The six tasks

| Task | Entry | Started by | Does |
| --- | --- | --- | --- |
| 0 | `task0_game_flow`, `$1D17` | boot | Waits for a coin, starts a game, advances rounds, handles game over and the results (chapter 12) |
| 1 | `task1_attract`, `$2AF7` | task 0 | The attract sequence: title, instructions, demos, high scores (chapter 12) |
| 2 | `task2_round_loop`, `$0538` | task 0, or task 1 for a demo | Sets up a round, then every frame: inputs, the join prompts, HURRY UP, the round clock, game over |
| 3 | `task3_players`, `$3DEF` | task 2 | Round-start initialisation, then every frame: both players (chapters 13-15), the special and bonus items, the falling and flying objects, the message-panel and HURRY UP sequences (chapter 18) |
| 4 | `task4_enemies`, `0:$85A8` | task 3 | The enemies: their entrance, the six type drivers, the chasers, rocks and missiles, the records the MCU reads, and the boss (chapters 10, 17, 19) |
| 5 | `task5_bubbles`, `$5B3B` | `round_start_anim` | Bubbles, items, the EXTEND letters, the boss (chapters 16, 18, 19) |

Task 3 starts task 4 (the enemies) from its own set-up, and `round_start_anim`, which task 3 calls every frame
until the players have walked in, starts task 5 (and task 4 again on the rounds where task 3 did not). Task 2
is the shape of all of them. Its opening is a straight sequence of set-up calls; its middle is a loop
that starts with a yield:

```asm
task2_round_loop:
0538  CALL clear_round_vars
053B  CALL round_setup         ; the round record (chapter 6)
053E  CALL anim_counter_reset
      ...
0552  CALL load_round_palette
      ...
0563  LD A,$03
0565  RST $30                  ; start task 3
0566  CALL round_intro         ; ROUND n / READY
      ...
loc_057B:
057B  RST $20                  ; one frame
057C  CALL read_inputs_unless_demo
057F  LD A,(round_start)       ; $E6FF: set by round_start_anim
0582  AND A
0583  JP P,loc_057B            ; wait until the arrival animation is over
      ...
0599  LD A,$03
059B  RST $18                  ; skip two frames
059C  LD A,(demo_flag)
059F  AND A
05A0  JP NZ,task2_demo_loop
loc_05A3:
05A3  RST $20                  ; --- the frame loop ---
05A4  LD A,$02
05A6  CALL bank_select
05A9  CALL $B18F               ; 2:$B18F join_update: PUSH START prompts, a second player joining
05AC  CALL bank_restore
05AF  CALL round_ready_display
05B2  CALL read_inputs
05B5  CALL game_over_check
05B8  CALL play_time_tick
05BB  CALL hurry_up_logic
05BE  CALL last_enemy_angry_timer
05C1  CALL last_enemy_check
05C4  LD A,(players_alive)
05C7  AND A
05C8  JR Z,loc_0614            ; nobody left: end the round
05CA  LD A,(enemy_count)
05CD  AND A
05CE  JP M,loc_05D3
05D1  JR NZ,loc_05A3           ; enemies left: next frame
loc_05D3:
05D3  LD HL,bubble_pause
05D6  LD (HL),$01
      ...
05E5  LD BC,$01A4              ; 420 frames of clean-up after the last enemy
loc_05E8:
05E8  RST $20
      ...                      ; players still move, bubbles still pop
0612  JR NZ,loc_05E8
loc_0614:
      ...
0622  LD A,$00
0624  RST $10                  ; wake task 0: the round is over
0625  XOR A
0626  RST $18                  ; and sleep for good
```

Every frame, then, task 2 captures the inputs, runs the round clock and the end-of-round tests and yields; when the
last enemy is gone it keeps yielding for seven seconds so that the fruit can be collected, then wakes task 0 and
suspends itself with state 0. Task 0, which has been asleep since it started task 2, resumes on the next pass
and decides whether to advance the round, show a message panel, or end the game. Tasks 3, 4 and 5 are ended
from outside, with `RST $08`, when task 0 tears the round down. There is no return value and no message queue:
tasks talk to each other through work RAM and through the six state bytes.

## What a frame looks like

The figure gives the timing of one frame of round 1, with one player and the traced machine's clock:

![One frame of round 1 with one player, measured on the emulated board. Microseconds after the start of VBLANK.](../img/ch09-frame-timeline.svg)

| Time (us) | Event |
| --- | --- |
| 0 | VBLANK begins at line 240. The sub CPU is interrupted and starts its collision pass; the MCU is interrupted |
| ~100 | The MCU pulses the main CPU's interrupt line |
| 115 | `irq_vblank` entered |
| 1395 | Object list copied, sound queue pumped, RNG stepped, essentials done |
| 1632 | Scheduler pass begins |
| 1690-2225 | Task 2: the round loop: inputs, clocks, prompts |
| 2302-3740 | Task 3: both players, items, sequences |
| 3817-5928 | Task 4: the enemies, and their records for the MCU |
| ~4000 | The sub CPU finishes its pass and idles |
| 6006-10316 | Task 5: bubbles and items |
| 10358 | `frame_done = 1`; the handler returns to the idle loop |
| 16896 | The next VBLANK |

Tasks 0 and 1 are asleep during play, so the pass goes 2, 3, 4, 5 in slot order every frame, which is also a
data-flow order: task 2 reads the inputs, task 3 moves the players on them, task 4 moves the enemies against
where the players now are and updates the records the MCU will read during the next VBLANK, and the
bubbles — which need both the players' and the enemies' new positions — go last. All of it fits in the first ten milliseconds; the CPU idles for the remaining
six and a half. Averaged over sixty frames of round 1 with one player:

| Where the main CPU spends a frame | Cycles | Share |
| --- | --- | --- |
| Idle loop | 44,981 | 44% |
| Task 5, bubbles and items | 17,453 | 17% |
| Task 4, enemies | 13,328 | 13% |
| Task 3, players and items | 11,167 | 11% |
| Interrupt handler | 9,103 | 9% |
| Task 2, round loop | 3,227 | 3% |
| Scheduler | 1,975 | 2% |

The sub CPU is busy for about 23% of its frame and the sound CPU is not paced by the frame at all: it runs its
sequencer from the chip timers (chapter 8). The chart below stretches the same measurement over the first
3,000 frames of a one-player game, from power-on through the attract screens, the story intro and round 1 into
round 2:

![Main CPU time per frame over the first 3,000 frames: boot, title, instructions, the story intro (task 0 alone), round 1 and the transition to round 2.](../img/ch09-busy-play.png)

The attract screens cost almost nothing; the story intro, which runs entirely in task 0, climbs to half a frame
as its animation fills the screen; and round 1 settles between 45% and 60%, with the bubble task growing as bubbles
accumulate. The spikes to 100% are the subject of the next section. The same picture for the attract mode's
demos looks like a game with nobody at the controls:

![The attract mode's first 2,500 frames: title, instructions with a demo of round 1 in task 2, and the first demo round.](../img/ch09-busy-attract.png)

## Overruns

A frame is not guaranteed to fit. If the tasks are still running when the MCU's next pulse arrives,
`frame_done` is still zero and the handler takes the short path:

```asm
irq_nested:
0490  LD (irq_saved_sp),SP     ; $E1C7
0494  LD SP,sched_sp           ; a temporary stack just below $E1C5
0497  CALL irq_essentials
049A  LD SP,(irq_saved_sp)
049E  POP AF
049F  EI
04A0  RETI
```

Only the essentials run — coins, timers, the sub CPU watchdog, the frame counter — on a temporary stack in the
gap above task 5's slot, and control returns to the interrupted task. The object list is not copied, the sound
queue is not pumped and the random number generator's per-frame step is skipped; the tasks finish in their own
time, the CPU idles, and the following pulse starts a normal frame. The visible effect is one frame in which
nothing on screen moves, and one frame's delay to any queued sound. The invisible effect is that the frame
counter and the clock keep going, so the game's timers do not drift.

In the traced 3,000 frames this happened 21 times, all at transitions: the screen clears of the boot and title
sequence, the story intro's screen fills, and seven consecutive frames at the start of round 1, where task 2's
set-up draws all thirty-two rows of the map at once — the three passes of `round_scroll_step` (chapter 6) with
the scroll disabled — behind a screen that has just been cleared. In play proper, with the player, the bubbles and the enemies all active, the worst frame stayed under 69%. Bubble Bobble does not slow down; it
was budgeted not to, and the overruns are confined to moments when nothing is moving.

The check after the scheduler is a different guard. `irq_vblank` pops the interrupted program counter and
insists that it lie below `$C000`. A frame that starts with `frame_done = 1` can only have interrupted the idle
loop at `$01ED`, so a return address in RAM means the stack has been corrupted; the code prints `TIME ERROR`
from the string at `$04A2`, clears the MCU's enable key so that no further interrupts come, and hangs. The name
suggests the programmers once used it to catch overruns during development; the shipped check catches crashes.

## The other processors' frames

Each of the helpers has its own relationship to the picture.

* The **sub CPU** is interrupted by the VBLANK signal directly, sixteen microseconds after line 240 in the
  trace. Its handler runs the whole collision pass — every bubble against every player, every enemy against
  every player, bubbles against bubbles — and returns to its idle loop about four milliseconds later. It reads
  the object positions that the main CPU wrote during the previous frame's tasks, so the collisions it reports
  are one frame old when the main CPU acts on them (chapter 11).
* The **MCU** is interrupted at the same instant. It samples the inputs, updates the coin counters, and pulses
  the main CPU; then it spends the rest of the frame on the enemy-to-player geometry it computes from the
  records task 4 maintains (chapter 10). The main CPU therefore sees inputs that are at most a frame old and
  MCU results from the frame before.
* The **sound CPU** never sees VBLANK. It is interrupted by the timers of the YM2203 several hundred times a
  second and drains its command ring in between (chapter 8). The only frame-paced thing about sound is that
  the main CPU sends at most one command per frame.

One detail of task 4's start belongs here because it concerns the interrupt: before it does anything else, the
task compares `$044D` with the word at `$0B2E` — the interrupt vector — and if they differ, pushes IX and
leaves it on the stack. The task's first `RET` then goes somewhere else, and the game dies a little later in a
way that does not point at the check. A bootleg that replaced the MCU with a plain VBLANK line and its own
vector would fail here. Task 3 opens the same way, summing the first three bytes of the ROM (`DI`, `IM 2`) and
pushing DE if the sum is not `$3E`. Chapter 20 collects the rest of these traps.
