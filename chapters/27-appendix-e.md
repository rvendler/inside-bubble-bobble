# Appendix E. Glossary

**Angry.** The state of an enemy that has waited too long: after the HURRY UP freeze, or after escaping a
bubble that was not popped in time. An angry enemy uses a faster speed list and is drawn in a different
palette. Chapter 17.

**Attribute byte.** The fourth byte of an object entry: bits 1-0 select the upper part of the tile number,
bits 5-2 the colour group, bit 6 flips horizontally, bit 7 vertically. Chapter 4.

**Bank.** One of four 16 KB pages of the main program's ROM switched into `$8000-$BFFF` by the byte at
`$FA80`. Bank 0 holds the enemy drivers, bank 1 the data (maps, round records, tables), bank 2 the round
objects and messages, bank 3 the story and graphics for the intro. Chapter 3.

**Bolt, lightning.** A bubble record in the flight state that carries lightning: it kills what it touches and
is the only thing that hurts the boss. Chapters 16 and 19.

**Bubble record.** One of twenty-four forty-byte records at `$E76C`, each a bubble that is rising, holding an
enemy, flying, popping or free. Appendix B.

**Cell.** One 8 × 8 picture element of the map, addressed by column and row; the collision map is one
nibble per cell. Chapters 5 and 15.

**Chain.** Several enemies popped by one burst of bubbles within ninety frames; scored 2,000, 4,000, 8,000,
16,000, 32,000, 64,000. Chapter 16.

**Collision map.** The sub CPU's 32 × 32 nibble map of the round, built from the map data when a round
starts and consulted by the wall tests. Chapter 15.

**Current.** The air current in a cell: nibble 2 pushes a bubble right, 3 left, 4 down, 5 and 6 hold it,
anything else lets it rise. Chapter 6.

**Difficulty rank.** A number from 0 to 30 that adjusts the round's time limits and the item thresholds;
raised by clearing rounds quickly, lowered by dying. Chapter 12.

**Drift table.** The sideways movement per step of a jump, at `$4B0F`. Chapter 14.

**EXTEND.** The six letters that award an extra life when all are collected from EXTEND bubbles; the
letter is chosen by the MCU's counter. Chapters 10 and 16.

**Frame.** One sixtieth of a second, marked by the VBLANK interrupt; the unit of all timing in the program.
Chapter 9.

**Geometry.** The MCU's per-enemy computation of where the players are relative to it: direction flags and
distances in the result bytes at `$FC27`. Chapter 10.

**Handshake.** The MCU writes `$37` to `$FC85` when it has started; the main program checks it fourteen
times. Chapters 10 and 20.

**Hook.** In the port, a TypeScript routine installed at a ROM address that runs instead of the machine code
there, charging the same cycles. Chapter 22.

**HURRY UP.** The message and the freeze when a round's time limit runs out; the enemies then turn angry.
Chapter 12.

**Invader.** The Space Invaders enemy that replaces Zen-chan from round 60; a flag in the type-0 driver, not
a type. Chapter 17.

**Lockstep.** Running the original and the ported program side by side and comparing them every frame.
Chapter 22.

**MCU.** The Motorola 6801U4 microcontroller: inputs, the frame interrupt pulse, the geometry, a countdown,
and the protection. Chapter 10.

**Object entry.** Four bytes in the object list: line, shape or column, x, attribute. Ninety entries at
`$E1CD` are copied to the hardware every VBLANK. Chapter 5.

**Object list.** The hardware's whole picture: there is no tile map, only objects. Chapter 5.

**Pose.** The player record's byte that names the animation family: standing, rising, walking, falling.
Read by the sub CPU for the landing test. Chapter 13.

**Refresh register.** The Z80's `R` register, a count of instruction fetches, read as a random number at
twelve places. Chapter 20.

**Round record.** Forty-three bytes per round in bank 1 at `$A73A`: enemy list, time limits, item rules,
palette, layout. Appendix D.

**RST.** The Z80's one-byte call to a low address; the kernel uses `RST $08` to `RST $30` as its system
calls: yield, sleep, start a task, and so on. Chapter 9.

**Scheduler.** The kernel's loop that runs each of the six tasks whose state has counted down to zero,
once per frame. Chapter 9.

**Shared RAM.** The 2 KB at `$E000-$E7FF` and the records beyond it that the main and sub CPUs both address,
and the 1 KB at `$FC00-$FFFF` that the main CPU and the MCU share. Chapters 10 and 11.

**Slot.** A position code that names a sprite's place in the object list and the cells it draws into; each
record carries one. Chapter 5.

**Source bubble.** A bubble that enters from the side of the screen on its own, every 128 frames, carrying
water, fire, lightning or an EXTEND letter. Chapter 16.

**Speed list.** A short repeating list of pixels-per-frame at `$11CE` shared by players, enemies and
bubbles; list 12 is 1, 1, 1, 1, 2. Chapter 13.

**Sub CPU.** The second Z80: builds the collision map, tests every bubble, enemy and item against the
players during blanking, and writes verdicts into the records. Chapter 11.

**Task.** One of six cooperative threads of the kernel, each with a state byte, a stack pointer and a
64-byte stack. Chapter 9.

**Walker.** A checksum routine that sums a range of ROM a few bytes at a time across many frames and
sabotages the game when the sum is wrong. Chapter 20.

**Window.** The distance within which the sub CPU counts a touch: ten pixels to catch an enemy, sixteen to
touch a player, eight for the boss's ring, forty-four for a bolt near the boss. Chapter 11.

**Zapped.** The one-player ending's return to play: YOU ZAPPED TO one of eight rounds between 50 and 85 at
difficulty rank 30. Chapter 19.
