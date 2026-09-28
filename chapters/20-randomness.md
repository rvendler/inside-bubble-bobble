# 20. Randomness, secrets and protection

Three subjects that the previous chapters kept pointing forward to, and that belong together because they
are all about what the program hides: where its chance comes from, what it does when nobody is meant to be
looking, and what it does to anyone who copies it.

## Where the randomness comes from

Bubble Bobble has two random sources, and neither is very random.

The first is a sixteen-bit register at `$E37F`, stepped every frame by the interrupt handler:

```asm
rng_pre:                       ; irq_frame_start: the low byte counts up
0E79  LD HL,rng_seed
0E7C  INC (HL)
0E7D  RET

rng_step:                      ; irq_essentials: the high byte counts down ...
0E7E  LD HL,rng_hi
0E81  DEC (HL)
0E82  JP rng_lfsr              ; ... and the pair is shifted

rng_lfsr:
0E5E  LD HL,(rng_seed)
0E61  ADD HL,HL                ; shift left; the old bit 15 into the carry
0E62  CCF
0E63  RLA
0E64  AND $01
0E66  LD C,A                   ; C = NOT old bit 15
0E67  LD A,L
0E68  RRCA
0E69  RRCA
0E6A  RRCA
0E6B  RRCA
0E6C  AND $01                  ; bit 4 of the shifted low byte
0E6E  XOR C
0E6F  LD C,A
0E70  LD A,L
0E71  AND $FE
0E73  OR C                     ; into bit 0
0E74  LD L,A
0E75  LD (rng_seed),HL
0E78  RET
```

It is a feedback shift register with the counters folded in, and the game reads it from `rng_hi` in a
handful of places: the side a source bubble enters from, the enemy-type list entry that decides its kind,
and the `random_chance` helper (`$0E22`) that compares the pair against a threshold from a table at `$0E30`
to answer "does this happen?" — the 37-in-256 test for an EXTEND bubble is one of its entries. Because the
register is stepped once per frame and only per frame, two decisions made in the same frame see the same
value, and a decision made a frame later sees a value that anyone with the ROM can predict.

The second source is the Z80's refresh register, read with `LD A,R` at twelve places:

| Where | What it decides |
| --- | --- |
| `bubble_random_lifetime` (twice) | How many seconds a bubble lives: the base plus `R AND 7` |
| `bubble_free_slot` (twice) | Where along the wall a source bubble appears |
| `special_item_choose` (three times) | The round's food when no rule applies |
| `bonus_item_pickup` | The I register, when the vector check fails (below) |
| `flying_objects_update`, `seq_f595_update` | The heights of the flying objects and the flyer |
| `ending_zapped` | Which of eight rounds the solo player is zapped to |

The refresh register counts instruction fetches, so its value at any moment depends on exactly how many
instructions the CPU has executed since power-on — which is the same on every board for the same inputs,
frame for frame, cycle for cycle. This is why the emulator of chapter 1 had to be exact to the cycle, and
why the port had to be verified to the cycle: a bubble that lives a second longer in one implementation
than in another is not a bug in the bubble code but a slip in the instruction count somewhere before it.
Bubble Bobble is deterministic in a way that few games are; the randomness is entirely a function of the
player's inputs and their timing.

What is *not* random is worth listing too, because players assumed it was. The enemies never roll a die:
every turn, jump and chase is a function of the MCU's geometry bytes and the map. The bonus item is chosen
from the statistics table (chapter 18). The EXTEND letter is the MCU's counter at the moment the bubble is
spawned — random in effect, deterministic in fact. And the special items of the listed rounds are fixed.

## Secrets

The secrets are scattered through the earlier chapters; here they are in one place.

* **The title-screen codes** (chapter 12): eight joystick and button moves while the logo cycles. Original
  game, POWER UP!, and the super game.
* **The name entry** (chapter 7): ten three-letter names. Six are the team's initials and set one flag; four
  set flags of their own; `SEX` is refused and counted. The flags are thresholds in the bonus-item table
  (chapter 18), so entering `KTT` at a game over changes which item the next game offers — the door to a
  secret room, or the warp to round 70.
* **The demo recorder** (chapter 7): the routine that recorded the attract-mode demos is still in the ROM,
  behind an `LD A,0 / JR NZ` that can never jump.
* **The MCU's spare services** (chapter 10): lives counters, a round-number mirror, forty sequence lists, a
  credits cheat that a genuine board never triggers, and a table-copy service that would copy fragments of
  another program's Z80 code.
* **The unreached code**: a fifth checksum walker that nothing calls (`rom_check_walker5_unused`); a
  watcher routine in the MCU that nothing reaches; the sound CPU's echo mode and its second command table;
  the main CPU's own copy of the enemy touch test (`find_enemy_near_8`), never called because the sub CPU
  does it. Each is a piece of a design that was larger than the game that shipped.

## Protection

The MCU is the protection's foundation (chapter 10): without it there are no inputs and no frame interrupt,
and without its geometry the monsters do not hunt. Everything else is built to make replacing it, or
patching the program around it, fail in ways that are hard to find.

![The checks, and where they hide.](../img/ch20-checks.svg)

### The checksum walkers

Twenty-three routines, in the fixed ROM and in banks 0 and 2, each sum a range of the program a few bytes
at a time. They are *incremental*: a call adds one, two, four or eight bytes to a running sum kept in work
RAM and advances a pointer; when the pointer reaches the end of the range the sum is compared with the
expected value stored next to it, and the walk starts again. Because each step is a dozen instructions, a
walker costs nothing, and because the steps are spread over thousands of frames the checksum of the whole
program is complete only after minutes of play.

| Walker | Range | Step | Stepped by |
| --- | --- | --- | --- |
| `rom_check_walker_0ae3` | `$0004-$0C08` | 4 | the enemies' escape, the lightning objects, the fall state |
| `rom_check_walker1` | `$0030-$314E` | 1 | the invincibility tick, the enemies' round init |
| `rom_check_walker2` | `$0000-$7781` | 2 | the jump start, the title screen |
| `rom_check_walker3` | `$0020-$0600` | 1 | the chain score, the HURRY UP sequence |
| `rom_check_walker_340a` | `$028E-$757B` | 3 | scoring; its bomb rewrites the high-score table |
| `rom_check_walker4` | `$147E-$7ACD` | 1 | the death animation, the enemy draw |
| `rom_check_walker_482b` | `$0001-$0EDD` | 1 | a floor item rising, the title |
| `rom_check_walker_6064` | `$2642-$731C` | 2 | the round scroll, the bubble spawn |
| `rom_check_walker6` | `$0038-$142C` | 1 | the bubble spawn, a bank-2 sequence |
| `rom_check_walker_9240`, `_9d95` | bank 0, `$8000-$C000` | 1 | the type-5 and type-4 enemy drivers |
| `rom_check_walker_b8fc` | bank 0, `$A103-$BFFF` | 1 | the boss |
| `rom_check_walker_85ae`, `_8b6b`, `_8d64`, `_8f17`, `_909a`, `_932d`, `_96a9`, `_a2c0`, `_a7e3`, `_b4b5` | bank 2 ranges | 1-8 | the item effects, the sequences, the floor fires, the message panels |

The walkers are called from the routines they have nothing to do with — a walker steps when an enemy is
initialised, when the player blinks, when a jump starts, when the floor fire spreads — and their state
lives among the ordinary variables of those routines, so that neither the code nor the RAM gives them away.
The one at `$340A` has the most pointed bomb: when the sum is wrong it copies the default high-score table
from ROM over the live one, quietly, every time. A patched board would work, and would never keep a score.

### The vector and the handshake

The other checks are inline and repeated. Twenty-four places compare the interrupt vector's target
`$0B2E` with `$044D`; eight rebuild the vector from the I register and `$FC00` and compare it with `$0B2E`;
thirteen check that the `RST $00` jump at `$0004` still goes to the boot at `$00B9`; seven sum the first three
bytes of the ROM and compare with `$3E`; six check that the byte at `$0002` is `$5E`; fourteen read the MCU's
handshake byte and expect `$37` or some of its bits. They sit at the start of task 4, in the round loop, in
the chase decision of every enemy driver, in the bubble blow, in the bonus item pickup, in the water burst,
in the lightning bolt, in the boss's every frame. A copier who patched the interrupt to come from the
video circuit instead of the MCU — the obvious change on a board without the chip — would have to find all
twenty-four.

What a failed check does is never to stop. The instrument is the Z80 stack: an extra `POP AF`, a `PUSH IX`
left in place, an `EX (SP),HL`, so that a `RET` somewhere later goes to the wrong address; or `RST $38`,
which jumps into the vector page; or, in the bonus item pickup, `LD I,R`, which moves the interrupt vector
page to wherever the refresh register happens to point. The bubble blow's check pushes BC; the mode select's
swaps the return address; task 3's start pushes DE if the ROM's first bytes have changed. The game runs on,
and dies somewhere else, later, in a way that does not point back at the check. Bootleg Bubble Bobble
boards exist — the copiers replaced the MCU with a 68705 that reproduces its services — and the effort that
took is the measure of how well this worked.

### The honeypot

And one check that rewards the copier. The ORIGINAL GAME code of chapter 12 runs five of the tests above
after the eight-move sequence; on a genuine board it prints ORIGINAL GAME and sets a flag, and on a board
that fails any test it prints DEAD COPY GAME !!! and gives 100 credits. A pirate testing a bootleg with the
cheat everyone knew would see the credits arrive. The message was for the operator.
