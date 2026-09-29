# 7. Text, fonts and tables

Between the graphics and the code sit the small tables that give the game its words and its numbers: the messages,
the two languages of the instruction screen, the score thresholds, the default high-score table, the demo
recordings. None of them is large, and each shows a habit of the programmers worth knowing before reading the
engine.

## Text records

Chapter 5 showed `print_text`: a record is one length byte followed by the characters, and each character is a
tile number — the font tiles `$20-$5F` carry the ASCII codes, so the strings read directly in a hex dump. The
boot's error messages at `$0234` are typical:

```
0234  0E "WORK RAM ERROR"
0244  10 "COMMON RAM ERROR"
0254  0D "PS4 SUM ERROR"
0262  09 "I/O ERROR"
```

Every message is printed with `print_text` at an explicit cell address and colour, or through `print_text_list`,
which walks a table of `[cell address, text pointer, colour]` triples. The routine steps `$40` bytes per
character, so a string can only run horizontally; there is no word wrap and no centring — every line of the game
was positioned by hand.

Some strings carry tile numbers below `$20`. The instruction texts begin each line with `$12` or `$1A`, tiles
from the row `$10-$1F` of the font: small marker glyphs used as bullets. Other tables use the heavier alphabet at
`$60-$7F`: the status row ("1UP", "HIGH SCORE", "2UP") is printed with those tiles, which is why it looks bolder
than the play-time messages.

## The instruction screen

The attract mode's "how to play" screen is a table of seven text records printed over a running demo of
round 1 (chapter 12). The English strings live at `$2D7E-$2EDB`:

```
BASIC SKILL ...
TRAP ENEMIES INSIDE BUBBLES.
BURST BUBBLES WITH YOUR HORNS OR FINS.
ADVANCED SKILL ...
HIGHER POINTS ARE SCORED WHEN BURSTING SEVERAL BUBBLES AT THE SAME TIME.
YOU CAN JUMP OVER BUBBLES.
ONE STAGE CLEARED WHEN ALL ENEMIES ARE DESTROYED.
```

DIP switch A bit 0 selects the Japanese version instead. It is printed by a different routine
(`instructions_japanese`, `$2B69`) because its characters are not font tiles: the kana are 16 x 16 pictures in
bank 1 of the tile ROM, placed with the sprite routines rather than the text printer, and the text records are
lists of tile numbers.

![The Japanese instruction screen: kana from tile bank 1, drawn as 2 x 2 cells.](../img/ch07-instructions-jp.png)

## Scores and thresholds

Scores are three bytes of binary-coded decimal, least significant byte first, and a final zero is implied: the
bytes `00 50 00` are the number 005000 and print as 50000. `print_score6` prints six digits with leading zeros
blanked and appends the 0, so every score on screen ends in 0 and the largest representable score is 9,999,990.
There are three of them in work RAM — player 1 at `$E641`, player 2 at `$E646`, the high score at `$E64C` — and
`add_score` (chapter 16) is the only routine that changes the first two.

> [!NOTE]
> **Binary-coded decimal**
> Binary-coded decimal (BCD) stores a number the way it is written rather than the way the CPU counts. Each half of
> a byte — a nibble, four bits — holds one decimal digit from 0 to 9, so a byte holds two digits and the byte `$50`
> means fifty, not eighty. The nibble values `$A-$F` are never used.
>
> It wastes space — a byte holds 0 to 99 instead of 0 to 255 — but printing becomes trivial: each nibble is already
> a digit, and the printing routine needs no division by ten, which the Z80, having no divide instruction, would do
> slowly. Adding is nearly as easy, because the Z80 has an instruction, `DAA`, that corrects the result of an
> ordinary binary addition back into two decimal digits. Three bytes give six digits; with the implied final zero,
> that is the 9,999,990 ceiling.

The extra-life thresholds come from a 96-byte table at `$3180`: four entries of eight BCD numbers, selected by
DIP switch B bits 2-3:

| Entry | 1st life | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 50,000 | 250,000 | 500,000 | 1,000,000 | 2,000,000 | 3,000,000 | 4,000,000 | 5,000,000 |
| 1 | 40,000 | 200,000 | 500,000 | 1,000,000 | 2,000,000 | 3,000,000 | 4,000,000 | 5,000,000 |
| 2 | 20,000 | 80,000 | 300,000 | 1,000,000 | 2,000,000 | 3,000,000 | 4,000,000 | 5,000,000 |
| 3 | 30,000 | 100,000 | 400,000 | 1,000,000 | 2,000,000 | 3,000,000 | 4,000,000 | 5,000,000 |

The game keeps a pointer to the next threshold per player (`$E63B`, `$E63E`) and awards at most eight extra
lives; after the eighth entry the pointer stops. The first threshold of the selected entry is also the default
high score: `init_high_score` copies it into `$E64C` at boot, which is why a freshly switched-on machine shows
30000 (entry 3, the factory setting of the DIP switches).

Two other small DIP tables live nearby. The number of lives is `1 + table[$32DB]` indexed by DIP B bits 4-5:
the bytes `01 00 04 02` give 2, 1, 5 or 3 lives. The starting difficulty rank is `table[$22D6]` indexed by bits
0-1: `0D 0A 04 07`, so the "normal" setting starts at rank 7 and the hardest at 13 (chapter 12 explains what the
rank does).

## The high-score table

The table at `$E654` has five entries of seven bytes: a three-byte score, the best round reached, and three
letters. `sub_3448` fills it at boot from the extend table's first four thresholds and from a list of names:

```
347B  db 00 20 00  1F  "I.F"
      db 00 20 00  1B  "MTJ"
      db 00 20 00  17  "NSO"
      db 00 20 00  13  "KIM"
      db 00 20 00  0F  "YSH"
```

The scores in the ROM are placeholders; the loop that follows overwrites the first five with the values from the
DIP-selected extend entry, so the default table reads 50000, 250000 ... or 30000, 100000 ... as the switches
dictate, and the rounds are 31, 27, 23, 19 and 15. The names are the initials of the team; `MTJ` is Fukio
Mitsuji, the game's designer.

After a game over that reaches the table, `name_entry` (`$36D0`) lets the player enter three letters with the
joystick and the button, 300 frames per letter. Ten three-letter codes are recognised. `SEX` is refused: the name
becomes `H.!`, the screen flashes and a counter is incremented. `TAK`, `STR`, `KTT` and three more set flags at
`$E604-$E607`, and the six names of the default table — `.I.`, `.F.`, `MTJ`, `NSO`, `KIM`, `YSH` — set `$E608`.
What the flags do is left to chapter 20; they are the developers' own back door into the game.

## The results screen

When a game ends, `high_score_rank` compares the score with the five entries and, if it ranks, runs the name
entry; then `results_screen` draws the table with headings from `print_text_list`, the five scores, the rounds
("ALL" for a completed game) and the names, and finally a bar along which each player's round is counted up
with the big digit sprites from tile bank 6, one frame per step.

## Demo recordings

The attract mode plays the game itself. Its inputs are recordings in bank 1, one stream per player, encoded as
run-length pairs: a count and an input byte. `demo_playback` (`$08C0`) keeps a countdown per player (`$E33D`,
`$E33E`) and a pointer (`$E353`, `$E355`); when the countdown reaches zero it takes the next pair:

```asm
demo_playback:
08C0  LD A,$00
08C2  AND A
08C3  JR NZ,loc_0909       ; never: the recorder
08C5  LD A,$01
08C7  CALL bank_select
08CA  LD IY,(demo_ptr_p1)
08CE  LD HL,$E33D
08D1  LD A,(HL)
08D2  AND A
08D3  JR NZ,loc_08E1
08D5  LD A,(IY+$00)        ; count
08D8  LD (HL),A
08D9  INC IY
08DB  INC IY
08DD  LD (demo_ptr_p1),IY
loc_08E1:
08E1  DEC (HL)
08E2  LD A,(IY-$01)        ; the input byte of the current pair
08E5  LD (input_p1),A
      ...                  ; the same for player 2
0906  JP bank_restore
```

The first three instructions are the remains of a development switch: `LD A,0 / AND A / JR NZ` can never jump,
but the code it would jump to is still in the ROM. `$0909` is the **recorder** — it reads the real joysticks and
appends run-length pairs to the stream in RAM — and Taito's staff used it to produce the demos, then left it in
with its switch turned off. The recordings themselves are the streams at bank 1 `$A5BC` and `$A6BC` for the
instruction screen's demo of round 1, and the seven demo rounds are chosen from the table at `$2FAB`:

```
2FAB  db 00 04 15 23 18 1B 31        ; rounds 1, 5, 22, 36, 25, 28, 50
```

with their streams from a table at bank 1 `$9A6A`. Every demo is a two-player recording that runs for 1,320
frames, after which `demo_game_over` fakes the end and the next round in the table is chosen (`$E634` counts
modulo 7).

## The coinage table

One more boot-time copy deserves a mention because its name in the listings is misleading. `round_table_copy`
takes sixteen bytes from the end of bank 3 — the entry at `$BFDF + 16 x (byte at $BFFF)` — into `$E36A`. The
bytes are not rounds: they are the coinage table, eight pairs of `[coins, credits]` for the two slots (`$E36A`
and `$E372`), selected by a version byte at the very end of the bank so that regional editions could ship
different pricing without touching the fixed ROM. The rounds themselves need no list; the game walks them in
numerical order through the record table of chapter 6.

## Message panels

The words a player sees during play — "INSERT COIN", "PUSH 1P START", "TO JOIN!!", "GAME OVER", "THANK YOU",
the two message panels of rounds 16 and 32 — are not text records but sprites: 2 x 2 cells and columns from tile
bank 4, moved into place by the panel routines of bank 2 (chapter 18). Only the status row, the ROUND/READY
banner, the instruction screen, the results and the test mode use the text printer. The choice is deliberate:
the panels have to slide in and out over the playfield, and only objects can move.
