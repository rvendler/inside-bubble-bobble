# 5. Building the screen

The video generator of Bubble Bobble does one thing: sixty times a second it walks a list of objects in the object
RAM at `$DD00` and, for each, draws a column of tiles from the video RAM at `$C000` onto the 256 x 256 pixel plane.
Walls, text, dragons and bubbles are all objects in that list. This chapter explains the list, the columns, the
PROM that shapes them, and then how the program organises its use of them: two playfields, a pool of sprite
slots, and a text printer that writes straight into the columns.

## The object entry

An object entry is four bytes:

| Byte | Meaning |
| --- | --- |
| 0 | `256 - y`: the vertical position, stored negated (so that 0 means the top and a larger value moves the object up) |
| 1 | Bits 7-5: the **shape**, one of eight lines of the video PROM. Bits 4-0: the **column**, which 128-byte block of video RAM holds the tiles |
| 2 | `x`: the horizontal position |
| 3 | Bits 3-0: the **tile bank**, added to every tile number of the column in units of 1024. Bit 6: x is negative (the object starts to the left of the screen) |

An entry of four zero bytes is skipped. The generator processes the entries in order, and later entries are
drawn over earlier ones; the program uses that ordering deliberately, keeping the playfield columns first and the
sprites after them so that dragons walk in front of walls.

![An object column, the object entry, and the eight shapes.](../img/ch04-sprite-cells.svg)

## The columns

The video RAM is 7,424 bytes, `$C000-$DCFF`: 58 columns of 128 bytes. A column is two tiles wide and 32 tiles
high, but it is not stored row by row. Each 128-byte column is two halves of 64 bytes, the left tile column at
offset 0 and the right one at `$40`; each half is four **blocks** of 16 bytes, one per 8 rows; and each block
holds eight 2-byte cells, one per row. The cell's first byte is the low eight bits of the tile number and the
second byte packs the rest:

| Attribute bit | Meaning |
| --- | --- |
| 1-0 | Tile number bits 9-8 |
| 5-2 | Colour group (0-15) |
| 6 | Flip horizontally |
| 7 | Flip vertically |

The entry's column field selects one of the first 32 columns (`$C000-$CFFF`); when bits 7 and 5 of the shape
byte are both set the address gains `$1000`, which reaches the remaining 26 columns at `$D000-$DCFF`. So the 58
columns are really "32 low columns and 26 high columns", and the high ones can only be used by objects whose
shape is `$A0`, `$B0`, `$E0` or `$F0`.

## The shapes

The video PROM (a71-25) has eight lines of sixteen entries in its upper half, one line per shape. An entry covers
two of the object's 32 tile rows and says whether to draw them (bit 3 clear), whether to reload the x position
from the entry before drawing (bit 2 clear) and which of the four blocks of the column supplies the cells (bits
1-0). The eight lines, read straight from the PROM:

```
$80  0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 00
$90  0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 01
$A0  0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 02
$B0  0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 03
$C0  00 00 00 00 01 01 01 01 02 02 02 02 03 03 03 03
$D0  00 00 00 00 01 01 01 01 02 02 02 02 03 03 03 03
$E0  04 04 04 04 05 05 05 05 06 06 06 06 07 07 07 07
$F0  04 04 04 04 05 05 05 05 06 06 06 06 07 07 07 07
```

Shapes `$80` to `$B0` skip 30 rows and draw the last two from block 0, 1, 2 or 3: a 16 x 16 sprite whose top is
16 lines above the line named by byte 0 (the rows are drawn at `256 - byte0 + 240`, modulo 256), which is why
`draw_sprite_2x2` writes rows 6 and 7 of a block (chapter 4) and why the program stores its objects' positions
with an offset of 8. Because the four blocks of one column are addressed by four different
shapes, one 128-byte column holds four independent sprites; 32 columns give 128 **sprite slots**, and a slot is
named by a single byte — the same byte that goes into the entry's shape/column field. The program calls it the
**position code** or slot code (`IX+7` in every object record) and `code_to_map_addr` turns it into the cell
address.

Shapes `$C0` and `$D0` draw all 32 rows, block by block, reloading x from the entry: a full 16 x 256 strip.
Shapes `$E0` and `$F0` are the same strip but with bit 2 set: x is not reloaded, and the generator continues 16
pixels to the right of the previous object. This is how the playfield is drawn as sixteen consecutive strips whose
entries all carry `x = 0`: the first has shape `$C0` and sets x, the fifteen that follow have shape `$E0` and
chain. The listing of the object RAM during round 1 shows it:

```
obj 00: line=0 x=0 shape/column=$9A  cells: 60/2 60/2 60/0 60/0 204/14 205/14 206/14 207/14 ...
obj 01: line=0 x=0 shape/column=$DB  cells: 60/2 60/2 60/0 60/0 208/14 208/14 F0/14 F2/14 F4/14 ...
obj 02: line=0 x=0 shape/column=$DC  cells: 7C/2 75/2 60/0 60/0 208/14 208/14 F2/14 F2/14 F1/14 ...
...
obj 0F: line=0 x=0 shape/column=$E9  cells: 60/5 60/0 65/5 60/0 204/14 205/14 206/14 207/14 ...
obj 10: line=163 x=92  shape/column=$00 bank=2 cells: 864/7 865/7 866/7 867/7     (a bubble, slot 0 block 0)
obj 11: line=174 x=126 shape/column=$20 bank=2 cells: 864/7 865/7 866/7 867/7     (a bubble, slot 0 block 1)
obj 28: line=117 x=40  shape/column=$0C bank=2 cells: 970/7 971/7 972/7 973/7     (Zen-chan)
obj 3A: line=216 x=200 shape/column=$19 bank=4 cells: 1104/8 1105/8 1106/8 1107/8 (the TO JOIN panel)
```

Entry 0 is shape `$80 | $1A`: column `$1A` of the low half, drawn with shape `$C0` after the `$80`-bit trick
(`$9A & $E0 = $80`, PROM line `$C0`); entries 1 to 15 are `$DB` to `$E9`: shape `$E0`, columns `$1B` to `$29`. The
sprites use columns 0 to 25 of the low half, and each of the four shapes `$00`, `$20`, `$40`, `$60` picks a block.

![Round 1 with every object entry outlined: the sixteen playfield strips (grey, numbered 0-F at the top) and the sprite entries (cyan) with their entry numbers.](../img/ch05-objects-round1.png)

## The program's coordinates

Nothing is rotated: the picture is 256 pixels wide and the object columns are vertical strips, 16 pixels wide and
256 tall, of which lines 16 to 239 are visible. The sixteen playfield strips stand side by side and cover the
whole width; the status row ("1UP", the scores, "HIGH SCORE") is tile rows 2 and 3 of every strip, just below the
invisible top, and the lives icons are drawn near the bottom.

What is unusual is the program's naming. In every record of the game — players, enemies, bubbles, items — the
byte the code calls `x` (`IX+1`) is the **vertical** position, and it grows **upwards**: it is 256 minus the
hardware line of the object's centre. The byte called `y` (`IX+2`) is the horizontal position of the centre.
Bub standing on the floor of round 1 has `x = 32, y = 32`; his object entry holds `256 - 24 = 232` in byte 0 and
`24` in byte 2, which puts the 16 x 16 sprite at lines 216-231 and pixels 24-39: the centre is at line 224 = 256
- 32 and pixel 32. Jumping increases `x`; walking right increases `y`. Whether Taito's engine grew out of a
vertically mounted game or the names were simply chosen this way is not recorded; the article uses "up", "down",
"left" and "right" in the player's sense and quotes `x` and `y` only where the code does.

## Two playfields

The program keeps its object list in work RAM at `$E1CD`, 90 entries (360 bytes), and the frame handler copies it
into `$DD00` at every VBLANK with one `LDIR` (chapter 9). All drawing goes into that shadow and into the video RAM
columns; the generator never sees a half-updated list because the copy happens during the blanking.

The 90 entries are allocated by convention:

| Entries | Address | Use |
| --- | --- | --- |
| 0-15 | `$E1CD` | Playfield A: the sixteen strips in low columns `$1A-$29` (`$CD00-$D4FF`) |
| 16-65 | `$E20D` | Sprites: 24 bubbles first, then enemies, items, panels and the players, in slots of the low columns 0-25 |
| 66-89 | `$E2D5` | Playfield B: sixteen strips in high columns `$0A-$19` (`$D500-$DCFF`), which the round scroll moves about within this range; the part not in use holds Skel-Monsta's sprites |

There are two playfields because the round intro scrolls, but not in the way the word suggests. The sixteen
strips of playfield A are 256 lines tall on a 256-line plane, so each is a ring: raise its line byte and the rows
that leave at the top come back in at the bottom. The scroll rotates the sixteen rings by two pixels a frame for
128 frames, and while a row is out of sight `round_scroll_step` clears it and draws the next round's map row into
it, one row every four frames. The old round rides up and off, the new round rides in from below, and both live in
the same columns the whole time. Playfield B exists for the status row: at the start of the scroll the two text
rows of the score line are copied from A's columns into B's (`swap_playfield_in`, `$CD04` to `$D504`, four bytes per
tile column), B's sixteen entries are at fixed positions so the scores stay still while the walls move, and at the
end the text is copied back and B is cleared (`swap_playfield_out`). `$E352` records which half holds the status
row so that the score printers write into the right columns. Once the round starts, B's entries are cleared
altogether (`clear_init_object_list2`), and the range is free for Skel-Monsta's records. The two sets of columns
are the reason the video RAM is 58 columns rather than 32: sixteen strips twice, plus 26 columns for sprites and
panels. Chapter 6 shows the scroll frame by frame.

`init_object_list` shows the fixed part of the scheme: it clears the spare entries and writes playfield B's
sixteen entries from a table of shape/column and x bytes:

```asm
init_object_list:
0372  LD HL,object_list_b       ; $E2F5
0375  LD BC,$0040
0378  CALL mem_clear
037B  LD HL,object_list_a       ; $E2D5: playfield B's entries
037E  LD DE,$0394
0381  LD B,$10
loc_0383:
0383  LD (HL),$00               ; y = 0
0385  INC HL
0386  LD A,(DE)                 ; shape/column: $AA, $AB ... $B9
0387  LD (HL),A
0388  INC HL
0389  INC DE
038A  LD A,(DE)                 ; x: $00, $10, $20 ... $F0
038B  LD (HL),A
038C  INC HL
038D  INC DE
038E  LD (HL),$00               ; bank 0
0390  INC HL
0391  DJNZ loc_0383
0393  RET
object_list_init:
0394  db AA 00 AB 10 AC 20 AD 30 AE 40 AF 50 B0 60 B1 70
03A4  db B2 80 B3 90 B4 A0 B5 B0 B6 C0 B7 D0 B8 E0 B9 F0
```

These entries carry explicit x positions and the reloading shape `$D0` (`$AA & $E0 = $A0`), unlike playfield A's
chained `$E0` strips — the two halves are built by different code, and both work.

## Sprite slots and object records

A moving thing in the game — a dragon, an enemy, a bubble, an item — is described by a record in work RAM whose
first bytes are the same for all of them:

| Offset | Meaning |
| --- | --- |
| +0 | State flags (the meaning of the bits differs by kind) |
| +1 | x |
| +2 | y |
| +3, +4 | Pointer to the object's entry in the shadow list |
| +5 | Animation frame |
| +6 | Animation tick |
| +7 | Slot code: the column and block whose cells the object draws into |
| +8 | Player number (whose object this is) |
| +9, +A | Kind-specific flags |
| +B | Tick counter |

To move an object, the program updates x and y in the record and copies them into the entry through the
pointer; to animate it, it calls `draw_sprite_2x2` with the slot code and the frame's first tile, which overwrites
the four cells the entry displays. Nothing else is needed: the entry's shape/column byte was set to the slot code
when the record was created, and stays. Creating the bubbles, for instance, links 24 records at `$E76C` to the 24
entries from `$E20D` and hands each a slot (chapter 16); the players' arrival objects at `$E700` take two more.
`anim_step` (`$15CA`) is the shared animation clock: it counts the tick at +6 up to a limit and then the frame at
+5, and reports when the sequence wraps, so that a caller can index its tile table with the frame.

The 16 x 32 figures of the entrance and death animations, the message panels and the big items use several slots
and several entries at once: `draw_sprite_column` stacks cells downwards from a slot code, block after block, and
the panel routines allocate their entries from the spare part of the list.

## Text

Text is written directly into the columns by `print_text`:

```asm
print_text:                     ; HL -> [count, characters...], DE = cell address, C = attribute
0E9A  LD B,(HL)
0E9B  INC HL
loc_0E9C:
0E9C  LD A,(HL)
0E9D  LD (DE),A                 ; the character is the tile number
0E9E  INC HL
0E9F  INC DE
0EA0  LD A,C
0EA1  LD (DE),A                 ; the attribute: colour group
0EA2  LD A,$3F
0EA4  CALL de_add_a             ; DE += $40: the next tile to the right
0EA7  DJNZ loc_0E9C
0EA9  RET
```

Because the font tiles `$20-$5F` have the ASCII codes, a text record is a length byte followed by the string as
it reads. The step of `$40` between characters is the distance between the left and right tile of a column, and
then between the right tile of one column and the left tile of the next, so a string runs horizontally across the
strips without the routine knowing where a column ends. `print_text_list` prints a table of `[address, text,
attribute]` records — the instruction screen, the test screens and the results screen are such tables — and
`copy_tile_block` copies a rectangle of tile numbers from ROM with one attribute, which is how the title logo and
the EXTEND screen are drawn. The status row is printed the same way, into rows 0 and 1 of the current playfield's
strips: "1UP" in group 1 (green), "HIGH SCORE" in group 3 (red), "2UP" in group 2 (blue), the scores in group 0
(white) by `print_score6`, which blanks leading zeros and appends the implied final 0 of the BCD score.

## Effects without redrawing

Three tricks avoid rewriting cells. Flipping a sprite is an attribute bit, so a dragon turning round costs the
same four writes as any frame. The round-clear wipe blinks the walls by toggling attribute bit 6 of a few cells.
And the palette is separate memory, so colour cycling — the title logo's six-entry rotation every two frames, the
flashes of the secret door and the power item — touches no tile at all. The generator reads the palette during
the frame, which is why palette writes are done from the VBLANK handler or accepted as a one-frame glitch.
