# 22. Afterword: how this article was made

The article you have read is the by-product of a stranger project. Its aim was not to describe Bubble Bobble
but to *rewrite* it: to take the four programs on the board — the main Z80's 96 KB, the sub Z80's 8 KB, the
sound Z80's 16 KB and the 6801's 4 KB — and turn every routine into TypeScript, in a form that behaves
identically to the original down to the clock cycle. The description came afterwards, because once a
routine has been rewritten so exactly that an emulator cannot tell the difference, there is nothing left
about it that is not understood. This chapter is about how that was done, what made it hard, and what is
still not known.

## The emulator

The first tool was an emulator of the board, written from the schematic and the MAME driver's memory maps:
two Z80 cores, a third for the sound board, a 6801 core, the YM2203 and YM3526 register models, the video
circuit as described in chapter 4, and the shared-RAM arbitration. It runs the four programs in lockstep,
cycle for cycle, and it is the machine that rendered every screenshot in this article — `tools/book/shot.ts`
loads a scenario (a scripted sequence of inputs: coin at frame 60, start at 100, right from 910 ...), runs to
a frame number, and writes the frame buffer as a PNG. The scenarios are also what made the game
*reproducible*: the same inputs give the same game, every time, because the program has no other source
of randomness (chapter 20). "Frame 1,500 of the play scenario" is a precise address.

## Hook and lockstep

A program cannot be ported all at once. The method was to replace it one routine at a time, in place:

1. Pick a routine from the disassembly — the annotated listings in `docs/disasm/`, generated from the
   symbol tables in `docs/symbols/`, which grew from a few hundred names to several thousand.
2. Write its TypeScript equivalent as a **hook** keyed by the routine's physical ROM address. When the
   emulated CPU reaches that address, the hook runs instead of the machine code: it reads and writes the
   same RAM, produces the same register and flag results, and *charges the same number of cycles* —
   because the sub CPU and the MCU are running alongside, and a hook that finished a cycle early would
   read a shared byte before the other processor had written it.
3. Run the **lockstep**: two machines side by side, one running the original ROM natively, one with the
   hooks installed, compared at every frame boundary (all of RAM, every register) and at every routine
   end. The first divergence names the routine and the frame.
4. Run the **census**: a coverage tool that lists which addresses still execute natively. When it lists
   nothing but the reset vector and the idle loop, the port of that CPU is complete.

The census mattered more than expected. A passing lockstep proves that the hooked routines behave; it does
not prove that everything is hooked. The sound program's music modulation code, the enemy drivers for types
that appear only after round 40, the ending, the test mode: each was found by the census, not by the
lockstep, and each needed its own scenario (a warp to round 42; a game with the round counter poked to 99;
DIP switch A set to the test position) to reach it at all. The `POKE` mechanism — write a byte into both
machines' RAM at a given frame — is how the rare states in this article were produced: the secret rooms, the
forced item pickups of chapter 18, the boss's death by fiat in chapter 19.

## What was hard

**Timing of shared memory.** The main CPU writes a bubble's position; the sub CPU reads it during blanking;
the main CPU reads back the sub CPU's verdict a frame later. A hook that wrote the position fifty cycles
early — a whole routine done in one step instead of instruction by instruction — changed which frame the sub
CPU saw it in, and the game diverged a thousand frames later. The rule that emerged is stated in chapter 9:
every write to shared RAM has to land in the same scheduler slice as the original instruction. The hooks
became generators that pause before each shared access, charged to the cycle, and the framework grew a set of
checkers for the ways a hook could be wrong: a block boundary off by an instruction, a CALL's cost omitted, a
generator called without being awaited, a branch's fall-through paused where its target should have been.

**The refresh register.** `LD A,R` returns a count of instruction fetches. To reproduce it the emulator must
count fetches exactly, through every interrupt and every wait state, and the hooks must charge exactly the
fetches the replaced code would have made. Twelve instructions in the ROM made the whole project exact by
necessity.

**Names.** The disassembly was made before the program was understood, and its names encode early guesses.
The most consequential was the axis: the record's first coordinate is vertical, the second horizontal, and a
family of wall tests, enemy states and bubble routines had been named for the other convention. `wall_test_left3`
is the floor test; `enemy_walk_down` walks right; `bubble_push_down` pushes right. Every such name was checked
against what the routine does before it appears in this article, and where a name survives from the listings
it is because it happens to be right or because it is a neutral label.

**Which axis is which** turned out to matter for the maps too. The current arrows of chapter 6 were drawn
wrongly in the first version of this article, with rightward and leftward exchanged, and the error was found
by watching a bubble on round 20 drift the way the arrows said it should not. The corrected figures are the
ones printed.

**Four programs, one frame.** Nothing in the main program's listing says when the MCU's geometry byte is
valid or how long the sub CPU's pass takes. Chapters 9 to 11 exist because those numbers had to be measured:
the MCU's handler was timed at 7.3 milliseconds only after an emulated 6801 replaced the ported one for
the measurement, and the sub CPU's cost per bubble was found by counting.

## What is still not known

* **The intent behind the unused MCU services.** Lives counters, a round mirror, forty sequence lists, a
  credit-adding service: the MCU has the outline of a program that would have owned more of the game. Whether
  this was a plan abandoned, a protection scheme half built, or code shared with another Taito board of the
  year, the ROMs do not say.
* **The seventh chain score.** The table at `$460A` has an entry for seven enemies popped at once that the
  count can never reach in a normal round. Either a feature was cut, or it was a guard.
* **Several bank-2 sequences** are described in this article by what they do on screen — the growing fill, the
  bouncing object, the palette flash — and not by what the designers called them. Their names in the
  listings (`seq_f521_update` and its neighbours) are addresses, and they stay addresses here.
* **The Japanese and export differences.** The text language is a DIP switch and the ROM set is the
  export one; the earlier Japanese sets differ in the round data and in details of the enemies' speed that
  this article does not cover.
* **The sound driver's echo mode and second command table**, present and never triggered.

## The tools of this article

The figures were rendered by a handful of scripts in `tools/book/`: `shot.ts` for screenshots, `sheet.ts`
for the contact sheets of frames and the cropped strips, `gfx.ts`, `sprites.ts`, `itemsheet.ts` and `wallsets.ts` for the
graphics sheets, `maps.ts` for the hundred rounds with their current arrows, `busychart.ts` and `jumparc.ts` for the
measured plots, and `build.ts`, which joins the chapters into one Markdown file. The measurements came from throwaway scripts on the same emulator: a per-frame trace of
which routine the main CPU was in, the sub CPU's cycles per handler run, the MCU's per-service costs. The
text was written chapter by chapter against the listings and the running machine, and every claim about
what a routine does that could be tested was tested, usually by forcing the state and watching.

## Why it was worth doing

Bubble Bobble is forty years old and has been played by more people than most books have readers. What is
inside it is neither large nor mysterious once it has been laid out — six tasks, a hundred maps, a few
tables of numbers — and yet the thing those parts produce is still unmistakable the moment the theme starts.
Understanding the program does not diminish that. It shows where it came from: from a bubble that lives a
random number of seconds because someone read the refresh register, from a monster that turns towards you
because a chip meant to guard against copying also does the arithmetic, from a frame that runs the same
order of routines sixty times a second and never slips. The people who made it are named in the credits at
the end of round 100. This article is for the machine they built.
