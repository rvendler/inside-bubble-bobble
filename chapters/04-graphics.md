# 4. Graphics: tiles, sprites and colours

Everything Bubble Bobble shows — walls, dragons, monsters, bubbles, fruit, text, the title logo, the boss — is made of
8 x 8 pixel tiles in sixteen colours. There are no hardware sprites in the usual sense and no scrolling: the video
generator draws tiles from a list of objects, and a "sprite" is just a small group of tiles that the program
moves by rewriting the list. This chapter is about the tiles themselves: how they are stored, how many there are,
what they look like, and how the program groups them into the things a player recognises. The next chapter is about
the list.

> [!NOTE]
> **Tiles, sprites and bit-planes**
> Most arcade boards of the mid-1980s build their picture from two kinds of thing. A **tile map** is a grid of 8 x
> 8 tiles in video RAM: the program writes a tile number into a cell and the hardware draws it there, which makes
> walls and text cheap, and the whole grid can be scrolled. **Sprites** are a separate set of small pictures,
> typically 16 x 16, that the hardware draws on top of the grid at any pixel position given in a list, which is how
> characters move smoothly over the background. Bubble Bobble's board has only the second kind, in an unusual form:
> everything on the screen, walls and text included, is an entry in the object list (chapter 5).
>
> A tile's pixels are stored in **bit-planes**. A pixel with sixteen possible colours needs four bits. Instead of
> keeping the four bits of each pixel together, the ROMs keep the first bit of every pixel of a row together, then
> the second bits, and so on: four one-bit pictures, the planes, which are stacked to give each pixel its colour
> index. On this board planes 0 and 1 are in one half of the graphics ROMs and planes 2 and 3 in the other, so
> every chip supplies two of the four bits of every pixel it holds.

## The tile format

The graphics ROMs hold 512 KB, of which 384 KB are populated: twelve 32 KB chips at positions 0 to 5 and 8 to 13
of the sixteen available. They are read as two halves. The first half (chips a78-09 to a78-14, addresses
`$00000-$2FFFF`) holds bit-planes 0 and 1 of every tile, the second half (a78-15 to a78-20, `$40000-$6FFFF`) holds
planes 2 and 3 of the same tiles at the same offsets. A tile is 8 rows of 8 pixels at 4 bits per pixel, 32 bytes in
all, 16 in each half. Within a half, each row is two bytes:

| Byte | High nibble | Low nibble |
| --- | --- | --- |
| row byte 0 | plane 0, pixels 3 2 1 0 (pixel 3 in the most significant bit) | plane 1, pixels 3 2 1 0 |
| row byte 1 | plane 0, pixels 7 6 5 4 | plane 1, pixels 7 6 5 4 |

and the second half holds planes 2 and 3 in the same arrangement. The pixel's colour index is
`plane0 x 8 + plane1 x 4 + plane2 x 2 + plane3`: plane 0 is the most significant bit. Index 15 is transparent
— the video generator does not draw it, whatever the palette says — so a tile has fifteen usable colours plus
holes. The figure decodes one tile of Bub's walking animation.

![Tile $0A04 taken apart: the 16 ROM bytes of each half, the four bit planes, and the result in colour group 7.](../img/ch04-tile-decode.png)

The emulator's decoder is a direct transcription of this layout and is short enough to show; the game itself
never needs it, because the video generator reads the ROMs directly:

```ts
// Decode 8x8 4bpp tiles into one byte per pixel (src/machine/bublbobl.ts)
const total = rom.length / 2 / 16;                 // 16 bytes per tile in each half
const half = rom.length / 2 * 8;                   // bit offset of the second half
const planes = [0, 4, half, half + 4];
const xoffs = [3, 2, 1, 0, 8 + 3, 8 + 2, 8 + 1, 8 + 0];
for (let t = 0; t < total; t++)
  for (let y = 0; y < 8; y++)
    for (let x = 0; x < 8; x++) {
      let v = 0;
      for (let p = 0; p < 4; p++) {
        const bit = t * 128 + planes[p] + y * 16 + xoffs[x];
        if (rom[bit >> 3] & (0x80 >> (bit & 7))) v |= 1 << (3 - p);   // plane 0 is the MSB
      }
      out[t * 64 + y * 8 + x] = v;
    }
```

With 32 bytes per tile the populated 384 KB give 12,288 tiles, numbered `$0000-$2FFF`; the numbers `$3000-$3FFF`
address the empty positions and read as blank. A tile's number is 14 bits: the video RAM cell that places it
holds ten of them, and the object entry that owns the cell adds a "tile bank" of four more bits, in units of 1024
tiles. So the tile ROM is best thought of as sixteen banks of 1024 tiles, twelve of them filled, and an object can
only show tiles from one bank at a time. That constraint shaped where the artists put things.

## What is where

| Bank | Tiles | Contents |
| --- | --- | --- |
| 0 | `$0000-$03FF` | The font (`$0000-$007F`: the TAITO logo pieces, arrows, punctuation, digits and capitals), small item pieces, the round-wall tile sets (`$0200-$02FF`) and the wall edge tiles (`$00F0-$00F5`) |
| 1 | `$0400-$07FF` | A second copy of the font (so text can share an object with bank-1 graphics), the title logo, the Japanese kana used by the instruction screen and the ending |
| 2 | `$0800-$0BFF` | The sprites of play: bubbles and their bursts (`$0800-$08BF`), the points markers, Zen-chan and the other walkers (`$0900-$09FF`), Bub (`$0A00-$0AFF`), the remaining enemies (`$0B00-$0BFF`) |
| 3 | `$0C00-$0FFF` | Monsta (`$0C00-$0C7F`), the items (`$0C80-$0DFF`, `$0EC0-$0FFF`), the green score numbers 10 to 9000 and the x2..x9 multipliers (`$0E00-$0EBF`) |
| 4 | `$1000-$13FF` | The message panels (PUSH 1P START, TO JOIN, GAME OVER, THANK YOU, INSERT COIN), the EXTEND letters, the secret-room doors, the boss's small sprites |
| 5-7 | `$1400-$1FFF` | Large figures: the boss, the story-intro and ending pictures, the big digits of the results screen |
| 8-11 | `$2000-$2FFF` | More large pictures (the ending), two more copies of the font for the mode-select and results screens, the EXTEND bonus screen frame, the second-player dragon Bob in his own colours |
| 12-15 | `$3000-$3FFF` | Empty |

The font appears four times because the tile bank is a property of the object, not of the cell: a panel that
mixes large artwork from bank 9 with letters needs letters in bank 9. The copies are byte-identical.

![The font: tiles $0000-$007F in colour group 0. Tiles $0020-$005F follow the ASCII code exactly, so a text byte is a tile number; $0060-$007F hold a second, heavier alphabet used for the status row, and $0000-$001F the pieces of the TAITO logo and the arrows of the instruction screen.](../img/ch04-font.png)

![The round-1 wall tiles ($0204-$0208 in colour group 14) among the wall sets of bank 0. Each round uses five consecutive tiles: four fill patterns and the plain block.](../img/ch04-walls.png)

![The six edge tiles $00F0-$00F5 that shade a wall cell's empty neighbours (chapter 6).](../img/ch04-edges.png)

## The palette

The palette lives in the main CPU's memory at `$F800-$F9FF`: 256 entries of two bytes, big-endian nibbles,
`RRRRGGGG` in the first byte and `BBBBxxxx` in the second. Four bits per component give 4,096 possible colours,
of which a round uses a few dozen. The 256 entries are sixteen **colour groups** of sixteen; a tile's cell
selects the group, the pixel selects the entry within it, and entry 15 of any group is never drawn because 15 is
the transparent index. Entry 255 — group 15, colour 15 — is the one exception: the video generator uses it as the
background colour behind everything.

![The palette while round 1 is being played. Each cell shows its three nibbles. Groups 0-5 are the text colours, 7 the sprites, 8 the panels, 14 the walls.](../img/ch04-palette-round1.png)

The groups are assigned by convention in the program: text is printed in groups 0 to 5 (white, green, blue, red,
yellow ...), the sprites of the round use group 7, the panels group 8, the walls group 14 (which the round loader
fills from the round's palette selector, chapter 6), and the rest are used by the title, the ending and the
special sequences. The program changes palette entries at run time for effects: the title logo cycles six
entries every two frames, the secret door and the "power up" item flash whole groups, and the round-clear wipe
blinks the wall tiles by flipping an attribute bit rather than the palette (chapter 18).

## From tiles to things

A tile is 8 x 8; almost everything in the game is 16 x 16. The program's unit is the **2 x 2 cell**: four
consecutive tile numbers drawn as top-left, top-right, bottom-left, bottom-right. The artists laid the sprites
out that way in the ROM, so a sprite frame is named by its first tile and the drawing routine adds 1, 2 and 3.

![Bank 2 as 16 x 16 sprites, in colour group 7: bubbles, bursts and stars; Zen-chan in his three moods; Bub's walk, jump, fall, blow and death frames; Mighta, Pulpul, Banebou and Hidegons.](../img/ch04-sprites-bank2.png)

Every 16 x 16 thing on screen is drawn by one small family of routines in the fixed ROM. `code_to_map_addr`
turns a **position code** — one byte, bits 0-4 a column and bits 5-6 a block — into the address of the cell in
video RAM, and `draw_sprite_2x2` writes the four tiles:

```asm
code_to_map_addr:                  ; IY = video RAM address of position code A
145D  PUSH AF
145E  AND $1F                      ; column 0-31
1460  LD L,A
1461  LD H,$00
1463  ADD HL,HL  x7                ; x $80: one column is 128 bytes
146A  LD DE,$C000
146D  ADD HL,DE
146E  POP AF
146F  SRL A
1471  AND $30                      ; block 0-3 x $10
1473  ADD A,L
1474  LD L,A
1475  JP NC,loc_1479
1478  INC H
1479  PUSH HL
147A  POP IY
147C  RET

draw_sprite_2x2:                   ; tiles B..B+3, attribute C, at position code A
147D  CALL code_to_map_addr
1480  LD (IY+$0C),B                ; row 6, left cell: code
1483  LD (IY+$0D),C                ;                   attribute
1486  INC B
1487  LD (IY+$4C),B                ; row 6, right cell ($40 on)
148A  LD (IY+$4D),C
148D  INC B
148E  LD (IY+$0E),B                ; row 7, left
1491  LD (IY+$0F),C
1494  INC B
1495  LD (IY+$4E),B                ; row 7, right
1498  LD (IY+$4F),C
149B  RET
```

The four cells are the last two rows (offsets `$0C` and `$0E`) of an 8-row block, because the video PROM's sprite
shapes draw exactly those two rows (chapter 5). The attribute byte `C` carries the colour group in bits 2-5 and
the high two bits of the tile number in bits 0-1; the flipped variant `draw_sprite_2x2_flipped` sets bit 6 (flip
x) and swaps the left and right tiles, which is how the same four tiles serve for a dragon facing either way.
`draw_sprite_column` stacks `B` such cells downwards from an object's position code, taking the tiles from a
table at `HL`; it builds the 16 x 32 player figures of the entrance and death animations and the tall panels,
and its flipped twin handles mirrored figures. Chapter 5 shows how the game hands out position codes to its
objects so that these writes land in the right place on screen.

![Bub's frames at $0A00-$0A7F: standing and walking (four frames), jumping, falling, blowing, the hit and death poses, and the "puff" of a burst bubble. All are drawn facing left; the right-facing versions are the flipped tiles.](../img/ch04-bub-frames.png)

![Zen-chan at $0900-$09BF: the walk, the jump, the fall, the angry (red) and the trapped-in-a-bubble frames, then the same set for the hurry-up state.](../img/ch04-zenchan-frames.png)

## What is not there

Two absences are worth pointing out. There is no 1 x 1 or 8 x 8 sprite format: the points markers, the small
bubbles of the stream a dragon blows, even the single-tile eyes of a caught enemy are all placed as 2 x 2 cells
with three transparent tiles. And there is no compression anywhere in the graphics: 384 KB of ROM in 1986 was
expensive, and Taito spent it on redundancy — four fonts, left- and right-facing copies of a few asymmetric
figures, whole colour variants of the enemies — rather than on a decoder. The program's own data, by contrast,
is packed tightly (chapters 6 and 8).
