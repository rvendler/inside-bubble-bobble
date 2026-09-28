# 18. Items, bonuses and secrets

Bubble Bobble's items are the part of the game that players traded rumours about: the candy that comes
from blowing thirty-five bubbles, the shoes for walking far enough, the umbrella that skips rounds, the
doors to the secret rooms. Almost all of it is one table. This chapter decodes it, follows an item from
its counter to its effect, and then takes the bigger set pieces — the message panels, the secret rooms,
EXTEND — that the round objects of bank 2 run.

## Three kinds of item

The program distinguishes three things a player can pick up:

* **Fruit** — what a popped monster falls as. It is the enemy record itself, in its dead state, drawn from the
  fruit table by the monster's place in the chain (chapter 17). Five hundred to ten thousand points.
* **The round's food** — one item per round, spawned where the last bubble of a cleared round bursts
  (chapter 16) from the table at `$E744`. `special_item_select` chooses it at the round's end: a fixed item for
  sixteen listed rounds (`$0710`: rounds 1, 5, 10, 15 ... 50, and 85, 86, 92, 93, 94), an item by the shared
  digit when both players' scores end in the same digit (`$0706`), the big item's item if the big item is on,
  and otherwise a choice by the players' situation. It is collected by walking into it, fourteen pixels.
* **The bonus item** — the one that matters. One per round, chosen at the round's start by
  `bonus_item_select` from a table of fifty-four statistics, placed on the playfield after a delay
  (`bonus_item_update`), collected within fourteen pixels (`bonus_item_pickup`), scored from the table at
  `2:$B66C`, and then acted on through a table of fifty-four effect handlers at `2:$8AFF`.

![The fifty-four bonus items in table order, drawn from the tile and attribute bytes of 2:$B66C.](../img/ch18-bonus-items.png)

## The statistics table

```asm
bonus_item_select:             ; at round start
      ...
8611  LD B,$36                 ; 54 entries
8613  LD HL,$B4F2
loc_2_8616:
8616  LD E,(HL)                ; the counter's address
8617  INC HL
8618  LD D,(HL)
8619  INC HL
861A  PUSH HL
861B  PUSH HL
861C  LD A,(difficulty_rank)
861F  LD HL,$8667              ; rank -> which of the four thresholds
8622  CALL hl_add_a
8625  LD A,(HL)
8626  POP HL
8627  CALL hl_add_a
862A  LD A,(DE)                ; the counter
862B  CP (HL)                  ; against the threshold
862C  POP HL
      ...
8631  JR NC,loc_2_863D         ; reached: this is the item
      ...
8635  JR NZ,loc_2_8616         ; else the next entry
      ...
loc_2_863D:
863D  LD A,(HL)
863E  LD (bonus_item_value),A
8641  LD A,B
8642  DEC A
8643  LD (bonus_item_number),A ; item number = 54 - entry
8646  XOR A
8647  LD (DE),A                ; and the counter starts again
```

Each of the fifty-four entries is seven bytes: the address of a counter in work RAM, four thresholds, and
a value. The rank table at `$8667` picks the threshold column: ranks 0-4 use the third, 5-7 the fourth,
8-11 the second, 12 and above the first — so the same statistic asks for more in an easy game than in a
hard one, on the theory that a good player does not need the help. The first entry whose counter has
reached its threshold wins, its counter is reset, and the search stops; the entries are scanned from the
top, and the item number is the entry's distance from the bottom, so the rarest conditions are checked
first. With the counters named from the code that increments them:

| Item | Counter | Threshold (rank 12+ / 8-11 / 0-4 / 5-7) | Picture | Effect |
| --- | --- | --- | --- | --- |
| 0 | `$E5DF` bubbles blown | 35 | pink candy | bubble parameter (`2:$87B1`) |
| 1 | `$E5E0` bubbles popped | 35 | blue candy | faster bubbles: range parameter 6 |
| 2 | `$E5E4` jumps | 35 | yellow candy | rapid fire: cooldown 5 |
| 3 | `$E5E6` distance walked | 12 x 256 pixels | shoes | faster walking: speed list 13 |
| 4 | `$E5E1` lightning bubbles burst | 12 | clock | the enemies freeze (`$E341`) |
| 5 | `$E5E2` fire bubbles burst | 19 / 16 / 10 / 13 | bomb | the `$F59E` sequence: every enemy dies |
| 6, 7, 8 | `$E5E3` water bubbles burst | 15, 20, 25 | umbrellas | skip 3, 5 or 7 rounds |
| 9-13 | `$E5E7` fell through the bottom | 15, 16, 17, 18, 19 | potions | the showers of items |
| 14 | `$E5E8` items collected | 65 / 60 / 50 / 55 | (points sprite) | `2:$88D2` |
| 15, 16, 17 | `$E5E9`, `$E5EA`, `$E5EB` candies eaten | 3 | rings | points for walking, jumping, blowing |
| 18, 19 | `$E5EF`, `$E5F0` | 5 | crosses | the `$F590` and `$F595` sequences |
| 20 | `$E5EE` enemies killed | 7 / 6 / 4 / 5 | cross | sixteen bubbles of count 2 |
| 21 | `$E5F6` | 13 / 12 / 10 / 11 | cup | `2:$8938` |
| 22 | `$E5F7` round foods eaten | 16 / 14 / 10 / 12 | cup | `2:$8941` |
| 23 | `$E5EC` rounds skipped | 2 / 2 / 1 / 1 | cup | the `$F5B6` sequence |
| 24 | `$E5ED` clocks used | 4 / 3 / 1 / 2 | cup | `2:$898E` |
| 25 | `$E5F3` enemies burnt by fire | 16 / 14 / 10 / 12 | book | every enemy on the field dies (`$E720`) |
| 26 | `$E5F4` enemies caught by special bubbles | 16 / 14 / 10 / 12 | necklace | the flying objects |
| 27, 28 | `$E5D9`, `$E5DA` games and rounds played | 30 / 25 / 15 / 20 | pearls | `2:$89BC`, `2:$89C2` |
| 29 | `$F457` | 1 | fork | falling items |
| 30 | `$F458` | 1 | chest | the big item, level 10 |
| 31-34 | `$E601`, `$E602`, `$E600`, `$E5FF` uses of items 25, 23, 18, 19 | 3 | chests | the big item, levels 9-6 |
| 35-40 | `$E5FD`-`$E5F8` letters of EXTEND collected | 3 each | canes | the big item, levels 5-0 |
| 41 | `$E5FE` HURRY UPs survived | 14 / 12 / 8 / 10 | bell | `2:$8A6A` |
| 42, 43, 44 | `$E606`, `$E605`, `$E604` name-entry flags | set | octopus, flamingo, mug | `$F464`: the round food forced |
| 45 | `$E607` name-entry flag | set | knife | falling items |
| 46, 47 | `$E609`, `$E60A` name-entry flags | set | lamp, dynamite | `2:$8AA3`, `2:$8AA9` |
| 48 | `$E611` last-enemy timers run out | 20 / 25 / 30 / 27 | skull | `2:$8AB1` |
| 49, 50, 51 | `$E60D`, `$E60E`, `$E60F` name-entry flags | set | doors | the secret rooms, kinds 0-2 |
| 52 | `$E610` name-entry flag | set | door | warp to round 70 |
| 53 | `$E608` a default name entered | set | can | falling items |

Most of the folklore is in the table, and so is the mechanism behind it. Thirty-five bubbles blown, popped
or jumped give the candies and the shoes; the special bubbles' counters give the clock, the bomb and the
umbrellas; falling off the bottom of the screen fifteen to nineteen times gives the potions; eating three
candies of a kind gives a ring. The four counters that the name entry sets (chapter 7) are the developers'
own: the initials `TAK`, `STR`, `KTT` and the rest do nothing but set a flag, and the flag is a threshold
of 1 for the doors to the secret rooms and the warp. The items at 42-44 and 46-48 are the same trick with
other names. And the table explains the rule that puzzled players most: the bonus item is chosen at the
*start* of the round from what was counted before it, so what you do in a round earns the item of the next.

## From pickup to effect

```asm
bonus_item_pickup:
873E  LD A,(bonus_item_state)
8741  BIT 0,A
8743  RET Z                    ; not on the field
      ...
8753  CALL proximity_test      ; a player within 14 pixels?
8756  RET NC
8757  LD A,(bonus_item_number)
875A  LD B,$05
875C  CALL mul8x8
875F  LD DE,$B66E              ; the record's points sprite and points
      ...
877F  CALL score_add_player
      ...
878F  LD C,$16
8791  CALL sound_queue_push
8794  LD HL,bonus_items_collected
8797  INC (HL)
8798  LD HL,($0B2E)            ; the interrupt vector ...
879B  LD BC,$044D
879E  LD A,H
879F  SUB B
87A0  JR Z,loc_2_87A6
87A2  LD A,R                   ; ... or the I register is scrambled (chapter 20)
87A4  LD I,A
loc_2_87A6:
87A6  LD A,(bonus_item_number)
87A9  LD HL,$8AFF
87AC  CALL table_lookup_de     ; the effect handler
      ...
```

The effects are fifty-four small routines. Some set a byte in the player record — the candies and the
shoes change the parameters chapter 13 listed, the rings set the scoring-mode bits so that every step, jump
or bubble is worth points — and some start a sequence in bank 2 that runs for many frames: the potions'
showers (`item_shower`: a kind byte in `$F523`, a rain of items over the whole field), the bomb's explosion,
the book's kill-all (verified by forcing the pickup: the enemy count drops to zero forty frames later), the
big item (`item_big`, eleven levels of the four-slot object that scrolls in when the round is cleared),
the falling items (`item_falling`: forks, knives and cans drop from the top and can be caught), the flying
objects (`item_flying_objects`: eight small shapes cross the screen for 25 points each). The umbrellas
(`item_skip3`) put tasks 2, 4 and 5 to sleep, flash the screen and add 3, 5 or 7 to the round counter
before waking the round loop: the shortest of the effects and the most valuable. The warp door
(`item_warp70`) sets the counter to 69 and the rank to 30.

![Object bank 3: the captured monsters, the fruit, the points sprites, and the items.](../img/ch18-items-sheet.png)

## The message panels

Rounds 16, 32, 48, 64, 80 and 96 open with a scene rather than a round: two of the round's monsters
carrying the dragons' girlfriends across the top of the screen, HELP!! in their speech bubbles. It is a
bank-2 sequence (`seq_f536_update`, `2:$9D35`) driven from `round_start_anim`: fifteen sprites per panel
from two slot groups, a letter animation of five frames, the panels slid in one pixel a frame to `x = $70`,
held 120 frames, and slid out to `$F0`; `$E5F5` counts the messages so that the next scene shows the next
picture, and `$F536` set to `$FF` releases the round. The second panel of a pair waits for a button press,
which it reads from bits 4 and 5 of the MCU's `$FC85` — an input that does not exist, so that the wait
always ends with the un-pressed path, which pushes DE and thereby makes the loop run once more for the
second panel. It is one of the stranger control-flow tricks in the program, and it works.

![Round 16 opens with the message: the captors, the girls, HELP!!.](../img/ch18-panel.png)

## The secret rooms

A secret door (`item_secret_door`, items 49-51) sets `$E723` to `$29` and the room kind in `$E724`; the round
loop finishes normally, and the next round is a secret room (`$504B` in the main ROM): the map of a
treasure vault, a message in the game's own alphabet, and thirty-six item records filled into the bubble
table for the players to collect. The room's entry door opens after twenty-four pickups and its exit after
thirty-six; the room times out after 2,400 frames. On leaving, the round counter jumps — the secret rooms
are the warps of the game — and in a two-player game the second player's exit is what the sub CPU's
"door" test on the chaser records is for (chapter 11). There are three room kinds, three messages, and
one player who reads the alphabet.

![A secret room.](../img/ch12-secret.png)

## The fills

Three of the effects fill the playfield. `seq_f521_update`, `seq_f52b_update` and `seq_f531_update`
(`2:$9373`, `$96EF`, `$99EB`) scan the map in 2 x 2 cell quads — eleven columns by thirteen rows of them — and
put an item tile in every quad that is air: the treasure fill drops diamonds, the two growing fills plant
items that grow through their frames. For 1,800 frames the players collect them (`treasure_pick_check`:
is the player standing on an item tile?), then the quads shrink and the map is cleared. They share the cell
quad routines with the round-clear wipe (`round_end_update`, `2:$A310`), which walks the map column by
column replacing the solid cells' tiles and finally blinks four cells' attribute bit 6 while the theme
restarts: the flash that ends every round.

## EXTEND

The six letters live in bubbles (chapter 16), each spawned by the round's bubble source with a letter from
the MCU's counter. A player who bursts one gets its bit in `$E742` or `$E743` and the letter lights in the
status row. Six bits set is `$3F`, and `extend_letters_complete` in task 5 takes the game over:

```asm
extend_start:                  ; the letters taken back, the tasks put to sleep, sound $10
      ...
extend_flash:                  ; the six status-row letters cycle through three tile sets, 5 frames a step, 7 times
      ...
extend_bonus:                  ; the bonus screen: the frame from bank 1, the flyer, six letters in four slots each, 900 frames
```

Tasks 2, 3 and 4 sleep; task 5 draws the bonus screen — a field of flowers from bank 1 — and the player's
flyer carries the six letters in along a flight script (`$79C5`, mirrored for player 2); each letter panel
glows through three tile sets and flickers when hit; then the big letters fall, the fourth lands and slides
into the lives row, and the extra life is awarded through the same routine as a score threshold. NICE 1P!
holds for the rest of the 900 frames, and `$7912` wakes the round loop, which restarts the round the letters
were collected in as the next one.

![The EXTEND screen: the letters carried in by the flyer.](../img/ch18-extend-1500.png)

![NICE 1P! — the extra life has been awarded; the round resumes after 900 frames.](../img/ch18-extend-2000.png)

## The rest of bank 2

The remaining round objects are smaller: the power item (`power_item_pickup`, `$F514`) gives both players
nine hundred frames of the invincibility that chapter 13's `[+$13]` flags and 3,000 points; the flyer
(`$F595`) and the bouncing object (`$F5AC`) are two more things that cross the field catching enemies
(chapter 11); the water flows (`water_flows_update`) carry the head of a burst water bubble down the platforms
with a trail of ten flowing tiles, taking players, enemies and rocks with it; the floor fires
(`floor_fires_update`) spread sixteen cells of flame from a landed fire. Each has its flag byte in
`$F44C-$F62F`, cleared by `clear_round_vars` at the start of a round, and each is a line in task 3's frame
list (chapter 9). None of them knows about the others; the round is what happens when they all run.
