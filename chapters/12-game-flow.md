# 12. Game flow

Three of the six tasks are about the shape of a session rather than the play itself. Task 0 is the state
machine: it waits for a coin, runs the mode select and the story, hands each round to task 2, judges the
outcome and runs the game over. Task 1 is the attract mode, started whenever there are no credits. Task 2
is a round from set-up to clear, and it serves the demos as well as the game. This chapter follows the three
through a session, from the first coin to GAME OVER, and stops at the doors of the play chapters.

![The states of a session.](../img/ch12-flow.svg)

## Task 0: waiting for a coin

Task 0 is the first task the boot creates (chapter 3). It prints the licence notice and the score header,
and enters a loop that it will return to after every game:

```asm
loc_1D1E:
1D1E  RST $20
1D1F  LD B,$03                 ; the first three ROM bytes must sum to $3E ...
1D21  XOR A
1D22  LD HL,$0000
loc_1D25:
1D25  ADD A,(HL)
1D26  INC HL
1D27  DJNZ loc_1D25
1D29  SUB $3E
1D2B  JR Z,loc_1D2E
1D2D  POP AF                   ; ... or the stack is unbalanced (chapter 20)
loc_1D2E:
1D2E  LD A,$01
1D30  LD (attract_active),A    ; $E5D4
1D33  LD (demo_flag),A         ; $E5D3
      ...                      ; clear the playfields and object lists, the palette, the credit text
1D4B  LD A,$01
1D4D  RST $30                  ; start task 1, the attract mode
loc_1D4E:
1D4E  RST $20
1D4F  LD A,(credits)           ; $E366
1D52  OR A
1D53  JR NZ,loc_1D70           ; a coin: go on
1D55  LD A,(attract_active)
1D58  AND A
1D59  JR NZ,loc_1D4E           ; the attract task is still busy: wait
1D5B  RST $28                  ; it has finished its phase: stop everything ...
      ...
1D6E  JR loc_1D1E              ; ... and start it again
```

With a credit, task 0 stops all tasks, draws the title logo, and waits for a start button while it prints the
credit count, the bonus thresholds and "PUSH ONLY 1 PLAYER BUTTON" or "PUSH 1 OR 2 PLAYERS BUTTON":

![With one credit: the title with the bonus thresholds from DIP switch B and the start prompt.](../img/ch12-flow-200.png)

`start_buttons` (`$1FF7`) accepts player 1's button whenever there is a credit; player 2's button needs two
credits, takes both, and starts a two-player game. Every pass through the wait also compares the interrupt
vector with `$044D` and pushes IX if it differs, the second of the tamper checks that chapter 20 lists.

## Mode select and the story

The start button leads to a screen this version of the game has and the Japanese original does not:

![SELECT GAME MODE: the joystick chooses, a button confirms, and after 1,200 frames the normal game is chosen by default.](../img/ch12-flow-360.png)

`mode_select` (`$2931`) draws two logos from tile blocks and a joystick picture, highlights NORMAL GAME or
SUPER GAME as the stick is pushed left or right, and returns on either button. The choice is one byte,
`$E5DB`, which the round set-up reads (chapter 6): in the super game the enemy parameters of every round
record are rewritten before the round starts, and the true ending needs it (chapter 19). The routine also opens with a check that `$FC85` still holds the
MCU's `$37`; if not, it swaps the return address for garbage.

Then the story. `story_intro` (`$2578`) clears the screen, prints the four lines of the introduction, starts the
theme — sound command 7, from which point it plays without a break until the game ends — and for 480
frames drifts the two dragons across a field of bubbles:

![The story intro: 480 frames of bubbles, the two dragons, and the theme's first bars.](../img/ch12-flow-600.png)

After it, task 0 sets up a new game. Round number 0, the EXTEND letters, the round counters and the flags are
cleared; the difficulty rank comes from DIP switch B (`13`, `10`, `4` or `7` for the four settings, so the
factory setting starts at rank 7) and is raised by 3 for a two-player game; the clocks are reset, the players'
scores and parameters initialised, the playfields cleared, and the board of the new game drawn. Then:

```asm
loc_1E2F:
1E2F  LD A,$02
1E31  RST $30                  ; start task 2: the round
1E32  XOR A
1E33  RST $18                  ; and sleep until it wakes us
1E34  RST $28                  ; back: stop everything
1E35  RST $20
1E36  LD A,(players_alive)     ; $E5D7
1E39  AND A
1E3A  JP Z,loc_1F90            ; nobody left: game over
1E3D  RST $20
1E3E  CALL difficulty_by_rounds
1E41  CALL difficulty_by_minutes
1E44  CALL round_counters
1E47  LD HL,round_number       ; $E64B
1E4A  INC (HL)
1E4B  LD A,(HL)
1E4C  CP $64
1E4E  JR Z,ending              ; after round 100
1E50  CALL round_flags
      ...                      ; clear the screen and the object lists
1E62  JR loc_1E2F
```

That is the whole of a game as task 0 sees it: start a round, sleep, be woken, count, start the next. The
round loop never returns; it wakes task 0 with `RST $10` and suspends itself (chapter 9), and task 0's
`RST $28` clears every task slot including the round's, so each round starts on fresh stacks.

## The difficulty rank

Two routines run between rounds. `difficulty_by_rounds` counts the rounds played (`$E5DE`) and adds 1 to the
rank on the second and third round of every four (`BIT 1` of the count); at 5, 10, 15, 20 and 30 rounds it
raises a floor — `$E5DD` — to 8, 15, 20, 25 and 30 and lifts the rank to it. `difficulty_by_minutes` does the
same with the clock: after 10, 15, 20 and 25 minutes of play the floor becomes 15, 20, 25 and 30. The rank
is capped at 30 by `difficulty_bump`, and everything that depends on it goes through the tables that
`round_setup` applies to the round record (chapter 6):

| Rank | Bubble hold time `[7]` | Time limit `[$D]` | Angry time `[$F]` | Enemy speed `[8]` |
| --- | --- | --- | --- | --- |
| 0-7 | +7 down to 0 | - | - | - |
| 8-15 | -1 down to -8 (never below 1) | - | - | - |
| 16-30 | -8 | -3 down to -7 s (never below 5) | -2 down to -7 s (never below 2) | +1 up to +5 (never above 30) |

A game that starts at rank 7 spends its first five rounds with the bubbles holding enemies a little longer
than the record says; by round 30 the floor has pushed the rank to 30 and every round is seven seconds
shorter, the enemies five units faster, and a caught enemy escapes eight units sooner. Nothing else
in the game reads the rank; the record's five numbers are where difficulty lives.

## The round, from task 2's side

Chapter 9 printed the round loop. Its life, in order:

1. **Set-up.** `clear_round_vars`, the round record and the map request (chapter 6), the animation
   counter, the object lists, the round's palette. Task 3 is started; it starts task 4, and later
   `round_start_anim` starts task 5.
2. **The banner.** `round_intro` prints ROUND n and READY while the players walk in from the corners — the
   entry animation is 90 frames — and the enemies drop in from the top on the record's schedule:

![ROUND 1 READY: the banner stays while the enemies arrive and the player is already free to move.](../img/ch12-ready.png)

3. **The wait.** The loop at `$057B` yields each frame until `round_start` (`$E6FF`) has bit 7 set, which
   `round_start_anim` does when the arrival is complete; then two frames' pause, and a branch to the demo
   variant if this is the attract mode.
4. **The frame loop** at `$05A3`: the join prompts, the READY banner's removal, the inputs, the game-over check,
   the round clock, HURRY UP, the angry timer, the last-enemy flag. It ends when `players_alive` is zero or
   the enemy count reaches zero.
5. **The clear.** With the last enemy gone `bubble_pause` is set, the round's special item is chosen, and the
   loop continues for 420 frames — seven seconds in which the fruit can still be collected and the players
   still move — unless the bonus flag or the game-over flag ends it sooner.
6. **The hand-off.** Task 0 is woken; task 2 sleeps with state 0.

The join prompts are the small texts in the second player's corner of the status row, INSERT COIN alternating
with TO CONTINUE every sixty frames (`join_update`, `2:$B18F`), and the TO JOIN!! panel that slides in at the
bottom right; when the 2P button is pressed with a credit in hand, the second player enters the running
round. In a two-player game, or in a game the second player has joined, both players are in the round for
the rest of the game; there is no separate continue.

## HURRY UP

The round clock is three bytes, `$E344-$E346`: frames, seconds, minutes, stepped by `play_time_tick` unless
`time_paused` is set. `hurry_up_logic` compares the seconds with the record's time limit:

```asm
0765  LD A,(play_minutes)
0768  AND A
0769  RET NZ                   ; past a minute: nothing more happens
076A  LD A,(e345_timer_word)   ; the seconds
076D  LD HL,round_time_limit   ; $E5A5
0770  CP (HL)
0771  JR Z,loc_0781            ; at the limit: the sequence
0773  LD A,(HL)
0774  SUB $03
0776  LD HL,e345_timer_word
0779  CP (HL)
077A  RET NZ
077B  LD HL,hurry_up_flag      ; $E34A: three seconds to go
077E  LD (HL),$01
0780  RET
loc_0781:
0781  LD A,$03
0783  RST $08                  ; sleep task 3 (players, items) ...
0784  LD A,$05
0786  RST $08                  ; ... task 5 (bubbles) ...
0787  LD A,$04
0789  RST $08                  ; ... and task 4 (enemies)
078A  LD HL,$F66B
078D  LD (HL),$00              ; collisions off (chapter 11)
078F  CALL rom_check_walker3
0792  LD A,$00
0794  LD (IO_sound_latch),A    ; all sound off
0797  LD HL,$0847
079A  LD DE,object_list_a
079D  LD BC,$0010
07A0  LDIR                     ; four objects: the HURRY UP text
07A2  LD HL,hurry_state
07A5  LD (HL),$FF
```

The flag three seconds early does not show anything; it tells the item code to stop producing bonus items for
the last stretch of the round. What the player sees happens at the limit itself: the whole game freezes —
players, enemies and bubbles asleep, the sub CPU's collisions switched off, the music silenced — and the
HURRY UP text, four sprites, rises from the bottom four pixels a frame until it reaches the middle of the
screen; the jingle plays (sound `$18`), the text waits sixty frames, and then everything is woken and the
text carries on upward, eight pixels a frame, until it has left the screen. When it has, `last_enemy_flag` is
set to 1 — the value that the enemy drivers read as "everyone is angry" — and a flag at `$F453` is raised for
the enemy code, which brings Skel-Monsta, the invincible ghost that hunts the players until the round ends:

![At the limit: the freeze and the rising HURRY UP.](../img/ch12-hurry-1425.png)

![Three seconds later: the survivors have turned angry, recoloured and faster, and the player has already paid for it.](../img/ch12-hurry-1600.png)

The sequence has a cousin for the *last* enemy. `last_enemy_check` raises `last_enemy_flag` to `$FF` when
the enemy count is 1, and `last_enemy_angry_timer` counts seconds from then: when they exceed the record's
angry time (`[$F]`, 10 seconds in round 1), the flag becomes 1 — the same "angry" value — and the last monster
speeds up. A player who dawdles over the final enemy meets the same monster as one who lets the clock run
out, only sooner.

## Game over

When task 0 wakes to find no players alive it takes the path at `$1F90`. It first confirms that the `RST $00`
vector at `$0004` still points at the boot — the third of the checks in this task — and then clears the
screen, redraws the board, plays the game-over jingle, and calls three routines that chapter 7 described:
`high_score_check` runs the name entry if the score ranks, `results_screen` shows the table and the round bar,
and `game_over_sequence` prints GAME OVER, waits 200 frames, and resets the sound CPU:

![The name entry: 300 frames per letter with the joystick and the button.](../img/ch12-end-1450.png)

![The results: TODAY'S RECORD, the table, and the bar along which each player's round is counted up.](../img/ch12-end-1700.png)

![GAME OVER, 200 frames, and the sound CPU is reset.](../img/ch12-end-1950.png)

Then `JP loc_1D1E`: the loop at the top of the task, which will start the attract mode if the credits are
gone and the next game if they are not. There is no continue in this game. What looks like one — TO
CONTINUE in the corner during play — is the invitation to a second player.

## Task 1: the attract mode

Task 1 runs whenever task 0 is waiting for a credit, and alternates two phases each time it is started (a bit
in `$E635` remembers which):

* **Title and instructions.** `title_screen` (`$1AED`) draws the logo and cycles its colour every two frames
  for 390 frames — the six palette words at `$1BAE` — while `title_code_input` listens to the joystick (below).
  Then INSERT COIN, in the singular only when both coin slots are set to one coin per credit, and the
  instructions: a one-player demo of the single-platform layout that the ROM keeps as round index 100, with
  the seven lines of "how to play" printed over it in English or Japanese (chapter 7), the last two blinking
  for 360 frames.
* **A demo round.** `attract_demo_round` (`$2EC9`): two players from the recordings of chapter 7 on one of
  the seven demo rounds, 1,320 frames, then a faked game over and the high-score table.

Both phases end by clearing `attract_active` and sleeping, which task 0 reads as the signal to clear all
tasks and start the attract mode again from the other phase. A demo is a real round: task 2 runs it with
`demo_flag` set, which only changes where the inputs come from and skips the parts of the loop — HURRY UP,
the game-over test — that would end it early.

## The codes on the title screen

While the logo cycles, `title_code_input` records every change of the player 1 inputs, up to eight, and when
the eighth arrives compares the buffer with three tables. The bytes are the input latch with the coin bit
masked, so each entry is one control:

| Sequence | On a genuine board | Sets |
| --- | --- | --- |
| BUBBLE JUMP BUBBLE JUMP BUBBLE JUMP RIGHT START | Prints ORIGINAL GAME ... | `$E5D1`, read by `round_flags` |
| LEFT JUMP LEFT START LEFT BUBBLE LEFT START | Prints POWER UP! | `$E5D2`: the fast player of `player_params_special` (chapter 13) |
| START JUMP BUBBLE LEFT RIGHT JUMP START RIGHT | Draws a small logo | `$E5DB`: the super game, without the mode select |

The second table has the sharpest teeth in the program. After the eight bytes match, the code runs five
checks: the MCU's `$37`, a ROM byte, the interrupt vector's target, the sum of the first three ROM bytes, and
the vector itself. If they all pass, it prints ORIGINAL GAME and sets its flag. If any fails, it prints
DEAD COPY GAME !!! and gives the player 100 credits. A pirate testing a bootleg with the cheat everybody knew
would see the credits arrive and the words, and conclude the board was fine; the message was for the
operator who looked over the player's shoulder, and the 100 credits for anyone who preferred not to read.
The strings are held as tile numbers in the bank-1 alphabet, which is why they do not show up in a text
search of the ROM.

## The secret rooms

One more branch of the flow belongs here because task 0 does not know about it. On certain rounds a door
may appear; a player who reaches it is taken to a secret room — the same round
loop, a different map, a treasure of diamonds, a message written in the game's own alphabet, and no enemies:

![A secret room: WELCOME TO SECRET ROUND, the statue, the diamonds, and the coded message.](../img/ch12-secret.png)

The secret rooms and the warp they give are chapter 18's; from task 0's point of view they are rounds like
any other, and the round counter is simply moved.
