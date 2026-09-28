# 19. Round 100 and the endings

Round 100 is the only round that is not a round. Its map is empty air with a few solid specks (chapter 6),
its record's enemy counts are ignored, and the round loop, the enemy task and the bubble task each take a
special path for it. What lives there is Super Drunk, a boss the size of sixteen ordinary sprites, and the
only way to hurt him is with the one weapon the rest of the game never needs: lightning. This chapter is
the fight, and the three things that can happen after it.

## Setting the stage

`round_setup` skips the difficulty adjustment for round 100; `init_object_list2` lays out a different object
list; `bubble_init` links eighteen bubble records instead of twenty-four, because the boss needs the object
slots. Task 4's spawner runs `boss_init_a846` and `boss_init_b938` — the boss record at `$F296` with its
sixteen slots from `$E275`, and the eight-record *ring* at `$F367` — instead of the enemy drivers, and its
frame loop is the short one at the end of the type drivers: `boss_update`, `boss_ring_update`. Task 5 adds
`boss_round_update` for the two figures at `$EB36` and `$EB46`, the captives in their bubbles at the top
corners, and the bank-2 subsystem `boss_lightning_update` places two potions (`$F611`) that give the
player who touches them the *lightning charge* — `lightning_bubbles_p1` at `$F60F` — that turns every
bubble they blow into a lightning bubble (chapter 16).

![Round 100: Super Drunk, the two captives in the corners, the ring of bubbles he has thrown, and Bub with a lightning bolt in flight.](../img/ch19-boss-2020.png)

## The boss

![The boss record's states.](../img/ch19-boss-states.svg)

`boss_update` (`0:$A8C6`) dispatches on the flag byte of the record: appearing, active, hit, dying. The
appearance is three cycles of a palette flash written straight into the palette RAM (`$F9DE`, `$F9FE`); the
active state waits 120 frames with sound `$15`, then moves. The movement is a diagonal bounce like Monsta's:
a direction byte selects one of four step routines from the table at `$AAA7`, and the edge tests turn it at
the walls. Every step also moves the sixteen object slots that make up the sprite, four columns of four
tiles drawn with `draw_sprite_column`, so that the boss is one record with sixteen shadows.

The ring is the boss's attack. `boss_ring_update` keeps eight bubble records of its own at `$F367`; while
the boss is active it launches idle ones from the boss's position towards the player — the direction is
chosen from which side of `x = $80` the player is on — and flies them along four scripts at `$BBAE`, one per
quadrant, until they leave the screen. When all eight are gone the ring resets. They are the records the sub
CPU tests against the players with an eight-pixel window (chapter 11, the `$F367` objects): a touch is a
death.

## Hurting him

The lightning bolts are ordinary bubble records in the bolt state (chapter 16), flying at three pixels a
frame. On round 100 the sub CPU's special-bubble test does something it does nowhere else:

```
; the sub CPU, special_bubble on round 100
057D  LD HL,$F296              ; the boss record
      BIT 0,(HL)
      JP Z,next                ; no boss: nothing
      ...                      ; |dx| < 44 and |dy| < 44 from the boss
      SET 7,(HL)               ; flash
      LD HL,$F2A1
      INC (HL)                 ; one more hit
      LD (IX+$1A),$20          ; and the bolt is spent
```

Every bolt that comes within forty-four pixels of the boss counts once in `$F2A1` and sets the flash bit,
which `boss_flash` clears again after six frames: the sparkle the player sees on a hit. From the seventieth
hit the boss flashes on its own, the visible sign that it is nearly done, and the fatal hit sets bit 2, which
`boss_hit` turns into sound `$27` and the dying state. The dying state is a shrink animation in
`boss_dying`; when the sprite is small enough the sixteen slots are cleared, the record's state becomes
`$20`, and — this is the line that ends the round — the enemy count at `$ED3D` is set to zero. The round
loop sees no enemies left and treats round 100 like any other cleared round.

![The boss with the bubble ring in flight.](../img/ch19-boss-2140.png)

## Three endings

Task 0 wakes with the round counter at 100 and, instead of a new round, runs `ending` (`$1E64`). What
happens next depends on how many players there are and which game mode was chosen at the start.

**One player.** The walls dissolve row by row (the wipe at `0:$BEA8`), the captive comes down from her
corner and joins the dragon, and the message from bank 2 (`not_true_ending_screen`, `2:$B77A`) is printed
line by line:

> CONGRATULATIONS! BUT THIS IS NOT A TRUE ENDING! COME HERE WITH YOUR FRIENDS! YOU WILL BE IMPRESSED BY THE
> TRUTH OF THIS STORY!! NEVER FORGET YOUR FRIEND! TRY AGAIN!!

Then `ending_zapped`: YOU ZAPPED TO ..., and the game continues in a round chosen by the refresh register
from a table of eight — rounds 50, 55, 60, 65, 70, 75, 80 or 85 — with the difficulty rank forced to 30.
A solo player cannot finish the game; the program says so, and sends them back to play more.

![The walls dissolve.](../img/ch19-zapped-2325.png)

![The one-player message.](../img/ch19-zapped-2925.png)

**Two players.** With both players alive at the boss's death (`players_alive = 3`), `ending_true` runs the
scene the game was made for. The boss's death sequence has already awarded a hundred bonuses of ten
thousand — the 1,000,000 PTS!! of the screen — and the couples meet under a heart that alternates between
the two players' colours over HAPPY END!!. Then the message: NOW, YOU FOUND THE MOST IMPORTANT MAGIC IN THE
WORLD. IT'S "LOVE" & "FRIENDSHIP"! and the credits roll (`$563E`, text lists in bank 1): MTJ/MITSUJI for game
design and character, ICH/FUJISUE and NSO/NISHIYORI for the software, KIM/KIMIJIMA for the sound,
YSH/YOSHIDA, KTU/FUJIMOTO, SAK/SAKAMOTO, the special thanks, and the cast — BUBBLUN, BOBBLUN, ZEN-CHAN,
MONSTA, SKEL-MONSTA, MIGHTA, PULPUL, BANEBOU, INVADER, HIDEGONS, DRUNK, SUPER DRUNK — the same names the
name-entry table's initials belong to (chapter 7). In the normal game the bank-2 message BUT IT WAS NOT A
TRUE ENDING follows for 2,400 frames, and the results screen.

![HAPPY END!!: the true ending's first scene.](../img/ch19-ending-3150.png)

![The message.](../img/ch19-ending-4350.png)

![The credits.](../img/ch19-ending-5100.png)

**The super game.** With two players in the super game — `$E5DB`, chosen on the mode-select screen or by the
title code (chapter 12) — `boss_dying` takes the branch at `0:$AC21`, the *mode-3 finale*: the players'
sprites are placed at the sides, a different animation plays through the four-slot figures, and task 5's
`boss_round_update` draws the finale's tile blocks and cycles the palette. The message about the true ending
is skipped. It is the ending the two-player super game earns, and the one almost nobody saw in an arcade: it
needs two players, the harder game, and a hundred rounds.

## What the boss is made of

Nothing in round 100 is new code so much as old code used differently. The boss is an enemy record with
sixteen slots; its ring is eight bubble-like records flown by the movement scripts of chapter 17; its
weakness is the bubble task's lightning state and one extra case in the sub CPU's special-bubble test; its
death is a decrement of the enemy count; the endings are the round loop's normal exit with a new screen.
Even the captives are task 5's business, two records in the space where the bubble table would have been.
The last round of the game is the whole engine, pointed at one monster.
