# Inside Bubble Bobble

# 1. Introduction

Bubble Bobble arrived in arcades in 1986. Taito's Fukio Mitsuji designed it, and it became one of the most
copied games of its decade: two small dragons, Bub and Bob, blow bubbles at monsters, trap them, and burst the
bubbles to turn the monsters into fruit. A hundred single-screen rounds, a secret code that changes the rules, a
song that everybody who played it can still hum, and an ending that most players never saw because it needs two
players to reach it.

![The title screen. The logo cycles through six colours, two frames per step.](../img/ch01-title.png)

This article is about the machine underneath. Not the history, not the sequels, but the program: what is in the ROM
chips, how the data is laid out, what the processors do every sixtieth of a second, and how the things a player
feels — the arc of a jump, the way a bubble drifts along the ceiling, the moment an enemy decides to jump at
you — come out of a few thousand lines of Z80 code.

## Why this game

Most arcade games of 1986 are one processor and a video chip. Bubble Bobble has four processors, and each of them
matters to how the game plays:

* A **main Z80** runs the game. It has 96 KB of program, more than three times its address space, and pages it
  in 16 KB banks.
* A **second Z80** shares 6 KB of memory with the first and does nothing but collision work: it checks every
  bubble against both players, every enemy against both players, every bubble against every other bubble, once
  per frame.
* A **third Z80** drives two sound chips with a sequencer that has its own little byte-code language for music
  and sound effects.
* A **Motorola 6801 microcontroller** is the only chip wired to the joysticks, the coin slots and the option
  switches. It also computes, for every enemy, where each player is relative to it. The main program reads those
  results and the enemies use them to chase. Take the microcontroller away and the game has no inputs, no coins,
  and monsters that never jump — which is exactly the point: the MCU is the copy protection, and Taito made it
  indispensable by giving it real work.

![Round 1, a few seconds in. Three Zen-chans, four bubbles, one dragon and 10 points.](../img/ch01-round1.png)

The design is also small. The whole thing — kernel, game flow, a hundred rounds, six enemy types with their
scripts, the bubble engine, the bonus items, a boss fight, the endings, an attract mode with demos, a test mode
and a copy-protection scheme with twenty-three checksum routines hidden in ordinary code — fits into 96 KB for the
main program, 32 KB each for the two helpers, and 4 KB for the microcontroller. Every trick used to make it fit is
visible in the ROM, and this article tries to show them all.

## How the article was made

The source of everything here is the ROM set itself, read through three layers of tooling built for this
project:

1. An **emulator** of the board — the four processors, the video generator, the two sound chips, the shared
   memories and the timing between them — accurate enough that the real program runs on it exactly as on the
   hardware.
2. An **annotated disassembly** of all four programs, with the names of routines and variables recovered by
   reading the code and by recording which routines read and write which bytes of RAM during play
   (`docs/disasm/`, `docs/symbols/`, `docs/analysis/ram-map.md` in the project).
3. A **re-implementation in TypeScript** of every routine of all four programs, verified against the emulator
   in lockstep: the re-implemented routine runs in place of the original, and after each one the machine's
   registers, memory and cycle count must be identical to what the original produces. Every routine described in
   this article has passed that test over hours of simulated play. When the text says "the enemy jumps when the MCU
   reports the player is beyond it", it is because the code that does so has been rewritten, run, and compared —
   not because it looks that way in a listing.

The figures are rendered from the running machine: screenshots at chosen frames, tile sheets decoded straight
from the graphics ROMs with the game's own palette, maps decoded from the level data, and diagrams drawn from the
record layouts.

## How to read it

Part I describes the machine and what happens when it is switched on. Part II is about data: how graphics,
screens, rounds, text and music are stored. Part III is the engine: the frame, the scheduler, and the three
helper processors. Part IV is the gameplay proper: the players, the collision system, bubbles, enemies, items and
the boss. Part V collects the odd corners — randomness, secrets, protection — and walks through one frame of round
1 instruction by instruction.

Some conventions:

* Hexadecimal numbers are written with a dollar sign: `$044D`. Byte offsets inside a record are written in
  brackets: `[$0B]`.
* The main program's banked region is written with the bank number in front: `1:$A73A` is address `$A73A` with
  bank 1 selected. The fixed 32 KB and the other processors' programs need no prefix.
* A **frame** is one vertical blanking period, 1/59.19 of a second. Timers in the game count frames, so "180
  frames" is about three seconds.
* The program names its coordinates the other way round from the video hardware: what the code calls `x` is the
  **vertical** position, measured upwards from the bottom of the 256-line plane, and `y` is the **horizontal** one.
  Chapter 5 explains this once; after that the text says "up", "down", "left" and "right" in the player's sense and
  uses the program's `x` and `y` only when quoting code.
* Routine names in fixed-width type (`bubble_catch`) are the names given during the disassembly. They are not
  Taito's names — no source code survives — but they are used consistently in the listings and in the code that
  accompanies this article.

![The instruction screen of the attract mode: a demo of round 1 with the "how to play" text.](../img/ch01-instructions.png)
