# 10. The microcontroller

The fourth processor is a Motorola 6801U4: an 8-bit microcontroller with 4 KB of program in its own mask ROM,
192 bytes of RAM, four 8-bit ports and a 1 MHz clock. Its program is 1,407 lines of disassembly, and its
job, as chapter 1 put it, is to be indispensable. It is the only chip wired to the coin switches, the
joysticks, the buttons and the DIP switches, it raises the main CPU's frame interrupt, and it computes the
one thing the enemy AI cannot do without: where each player is relative to each enemy. This chapter reads the
program service by service, shows which of those services the game actually uses, and ends with the traps
it sets for anyone who tries to replace it.

## The port protocol

The MCU is not on the main CPU's bus. It reaches the 1 KB of shared RAM at `$FC00-$FFFF` — MCU addresses
`$0C00-$0FFF` — and the input ports through its own four ports, bit-banging an address and a data byte:

```asm
shared_read:                   ; B = shared[X]
F1BF  LDAA PORT1
F1C1  ORAA #$80                ; bit 7 high: read
F1C3  STAA PORT1
F1C5  CLR $0004                ; port 3 as input
F1C8  STX $004A
F1CB  LDD $004A                ; A = address high, B = address low
F1CE  ANDA #$0F
F1D0  STAB PORT4               ; address low byte
F1D2  STAA PORT2               ; address high nibble ...
F1D4  ORAA #$10
F1D6  STAA PORT2               ; ... then the strobe bit
F1D8  LDAB PORT3               ; the data comes back on port 3
F1DA  RTS

shared_write:                  ; shared[X] = B
F1DB  LDAA PORT1
F1DD  ANDA #$7F                ; bit 7 low: write
F1DF  STAA PORT1
F1E1  LDAA #$FF
F1E3  STAA P3DDR               ; port 3 as output
F1E5  STAB PORT3               ; the data
F1E7  STX $004A
F1EA  LDD $004A
F1ED  ANDA #$0F
F1EF  STAB PORT4
F1F1  STAA PORT2
F1F3  ORAA #$10
F1F5  STAA PORT2               ; strobe
F1F7  RTS
```

Addresses below `$0800` select the input latches instead of RAM: `$0000` is DIP switch A, `$0001` DIP
switch B, `$0002` the player 1 stick and buttons, `$0003` player 2 and the start buttons. Port 1 carries the
coin and service switches on its low bits and, on its high bits, the outputs: bit 4 the coin lockout coil,
bit 5 the coin counter, bit 6 the main CPU's interrupt line, bit 7 the read/write direction. Every byte the
MCU moves costs it about thirty cycles of port writes; the whole per-frame service list is written around
that cost.

## Boot and the frame

At reset the program first checks whether the factory's port tester is attached (fixed patterns on all four
ports, `selftest_check` at `$FEBB`); if not it falls into `init`: port directions, a clear of its RAM, one
read of the inputs, the coin-lockout coil off, a 500-loop delay after which a coin switch held at power-on is
recorded in `$FC7D`, a 16-bit checksum of its own ROM into `$FC82` (the ROM is padded to make it zero), and
finally the handshake byte:

```asm
F03A  LDAB #$37
F03C  LDX #$0C85
F03F  JSR shared_write         ; $FC85 = $37: the MCU is up
F042  CLI
loc_F043:
F043  BRA loc_F043             ; and it waits for the picture
```

Chapter 3 showed the main CPU waiting for that `$37` at `$FC85`, 394 milliseconds after power-on. From then on
the MCU, like the main CPU, lives in its interrupt handler. The VBLANK signal is wired to its IRQ1 pin, and the
handler is a list of nineteen services:

```asm
irq1_handler:
F046  JSR svc_main_irq         ; pulse the main CPU
F049  JSR svc_inputs           ; DIP switches, sticks, buttons, coins -> $FC1F-$FC23
F04C  JSR svc_coins            ; the MCU's own credit counting
F04F  JSR svc_lockout_cmd      ; $FF94: lockout coil on or off
F052  JSR svc_counter_0C24     ; lives counter, player 1
F055  JSR svc_counter_0C25     ; lives counter, player 2
F058  JSR svc_value_0C26       ; a round-like value
F05B  JSR svc_enemy_p1         ; geometry: 7 enemies against player 1
F05E  JSR svc_enemy_p2         ; ... and player 2
F061  JSR svc_sequence_0C73    ; four "random" sequences
F064  JSR svc_sequence_0C77
F067  JSR svc_sequence_0C81
F06A  JSR svc_countdown        ; a 16-bit frame countdown
F06D  JSR svc_cheat_credits    ; 42 credits for the right key
F070  JSR svc_extend_letter    ; a counter 0..5
F073  JSR svc_table_0C88       ; three table-copy services
F076  JSR svc_table_0D88
F079  JSR svc_table_0E88
F07C  JSR svc_reset_cmd        ; $FF97 = $4A restarts the MCU
F07F  LDX #$0F96
F082  JSR shared_read
F085  CMPB #$47
F087  BEQ loc_F091
F089  LDD #$0170               ; 368 turns of a delay loop
loc_F08C:
F08C  SUBD #$0001
F08F  BNE loc_F08C
loc_F091:
F091  RTI
```

The first service is the one the rest of the machine waits for. It reads `$FF98`, and only if the main CPU
has written `$47` there does it drop port 1 bit 6, raise it and drop it again — the pulse that becomes the
main CPU's interrupt (chapter 9). On the traced board the pulse comes 94 cycles into the handler, about 100
microseconds after VBLANK. The main CPU writes the key exactly once, at the end of boot, after its own tests
have passed: until then there are no interrupts and the game cannot start.

Measured on the emulator during round 1 with one enemy active, the handler takes 7,300 cycles — 7.3 of the
16.9 milliseconds in a frame. The inputs cost 500 cycles, the coin logic 400, the geometry 1,600, and 2,640
go to the delay loop at the end: the main program never writes `$47` to `$FF96`, so the MCU spends a sixth of
every frame counting to 368 for nothing. With all seven enemies active the geometry grows to about 7,000
cycles and the handler to 13 milliseconds — still inside the frame, which is presumably what the delay was
tuned against.

## The inputs

`svc_inputs` copies port 1 and the four input latches into `$FC1F-$FC23` every frame. That is the whole input
path of the game: the main program's `read_inputs` (chapter 13) reads `$FC22` and `$FC23`, `coin_handling`
reads the port copy at `$FC1F`, `irq_vblank` reads DIP switch A at `$FC20` to decide whether it is in test
mode, and nothing on the main board can see a switch any other way. The inputs a task acts on were sampled
during the previous VBLANK, one frame before.

The coin switches are handled twice. The MCU's own `svc_coins` edge-detects the three switches, looks up the
coinage table at `$F187` — four pairs of coins and credits per slot, selected by DIP A — adds to its credit
byte at `$FC1E`, sets `$FF99` to flag the event, and drives the lockout coil: credits at nine or more lock the
mechanism. The main program, meanwhile, does the same job itself in `coin_handling` from the port copy, with
the coinage table it took from bank 3 at boot (chapter 7), keeps the credits it believes in at `$E366`, and
sends the lockout state back as a command in `$FF94`. It never reads `$FC1E`. The two counts agree because
they see the same edges, but only the main CPU's is used; the MCU's coin logic is a service this program
does not call on, left running. Its one visible effect is the lockout coil, which the MCU alone can drive and
which obeys the main CPU's command byte.

## The enemy geometry

Task 4 keeps seven records of four bytes at `$FC01` — `[flags, x, y, -]` per enemy, with bit 0 of the flags
set while the enemy is on the field — and task 3 writes each player's position to `$FC60-$FC61` and
`$FC68-$FC69` after moving it (`player_pos_to_mcu`). During the next VBLANK the MCU computes, for every
active record and each active player, the sign and magnitude of the difference on both axes:

```asm
loc_F4CF:                      ; record X = $0058 -> [flags, x, y]; player x in $55, y in $56
F4CF  LDX $0058
F4D2  INX
F4D3  JSR shared_read          ; B = enemy x
F4D6  LDAA $0055               ; A = player x
F4D9  SBA                      ; A = player - enemy
F4DA  BEQ loc_F4E7             ; equal: code $80
F4DC  BCC loc_F4E3             ; no borrow: player is higher, code 0
F4DE  LDAB #$01                ; borrow: player is lower, code 1
F4E0  NEGA                     ; ... and make the distance positive
F4E1  BRA loc_F4E9
loc_F4E3:
F4E3  LDAB #$00
F4E5  BRA loc_F4E9
loc_F4E7:
F4E7  LDAB #$80
loc_F4E9:
F4E9  LDX $005A                ; result record
F4EC  PSHA
F4ED  JSR shared_write         ; [0] = direction code
F4F0  LDX $005A
F4F3  INX
F4F4  INX
F4F5  INX
F4F6  INX
F4F7  PULA
F4F8  PSHA
F4F9  TAB
F4FA  JSR shared_write         ; [4] = |dx|
F4FD  PULA
F4FE  CMPA #$08
F500  BCC loc_F505
F502  INC $005C                ; within 8: remember it for the touch test
loc_F505:
      ...                      ; the same for y into [2] and [6]
```

The results go to eight-byte records at `$FC27`, player 1 in the even bytes and player 2 in the odd ones.
When an enemy is within eight pixels of the player on both axes the service also writes a touch report —
`$FC62 = 1` and the enemy's index in `$FC63` — and stops scanning.

![The geometry service on the values of one frame.](../img/ch10-geometry.svg)

The main program reads the results in two places, both in the enemy code of bank 0 (chapter 17).
`mcu_player_relation` (`0:$9179`) fetches the direction byte for the enemy's target player and answers "is the
player that way?"; it is the test behind every turn an enemy makes towards a player. `enemy_chase`
(`0:$94FF`) reads the vertical distance and, when it is less than 20 lines, decides between turning and
jumping. Those two reads are the whole of the MCU's contribution to the AI, and they are why a board without
the MCU has monsters that walk back and forth but never come after you: without the codes, the tests fail,
and the enemies fall through to their patrol behaviour.

The touch reports are never read. The main program does not need them because the sub CPU tests every enemy
against every player with the objects' real bounding boxes (chapter 11); the MCU's eight-pixel test is
coarser and a frame older. The service is complete on the MCU's side and unconnected on the other — a
pattern that repeats through the rest of the list.

## The countdown

`svc_countdown` decrements a 16-bit number at `$FC78` while `$FC7A` is set and, at zero, clears the run flag
and sets a done flag at `$FC7B`. The enemy code uses it as a timer for the missile launchers of the rounds
whose record has bit 0 of `[$C]` set (chapter 6): at the start of a round task 4 loads 600 frames, and the
launcher code polls the done flag to release its missiles, then reloads. Ten seconds of the round's timing
therefore run on the MCU's clock, in step with the frame because the MCU is interrupted by the same VBLANK.

## Services that run for nobody

The rest of the list is machinery this game does not switch on. Each service acts on a command byte in the
shared RAM, and the RAM trace of the port — every read and write of the main CPU over hours of play, attract
mode, the test screens and the boot — shows the main program never writing those bytes and never reading the
results:

* **Lives counters** (`$FC24`, `$FC25`): commands in `$FC6F` and `$FC70` initialise a counter from the DIP
  lives table (`[1, 0, 4, 2]`, the same numbers as the main CPU's own table), increment it to a maximum of 10,
  decrement it or set it to 10. The game keeps lives in its work RAM and never sends a command.
* **A value** (`$FC26`): commands in `$FC7E` clear it, increment it, or set it to 49, 98, 99, 100 or 101 — the
  numbers of the rounds after the secret-room warps and the boss. It is the round number, kept in parallel,
  for a program that would consult the MCU about which round it is in. This one does not.
* **Four sequences** (`$FC72-$FC77`, `$FC80-$FC81`): the main CPU names a list, the MCU serves its next value
  every frame and wraps at the `$FF` terminator. The forty lists at `$F769-$F88E` are strings of small
  numbers — list 1 is one 1 in ten zeros, list 20 is mostly 2s, list 39 mostly 4s — the shape of a
  graded random choice, a probability that rises with the list number. The game reads none of the values.
  It does write one of the list-number bytes: the bubble task keeps the round's bubble-speed list number in
  `$FC76` and reads it back as an ordinary variable (chapter 16), and the MCU obligingly serves a sequence
  from that list into `$FC77` every frame that nobody looks at.
* **The EXTEND counter** (`$FC7C`) steps from 0 to 5 and back every frame: a free-running picker for the six
  letters of EXTEND. This one the game does use, rarely: when the round's bubble source decides to release
  an EXTEND bubble (chapter 16), the letter it carries is whatever the counter holds at that moment — a
  random letter, chosen by the only chip on the board that was counting.
* **Table copies**: a request in `$FF88` (`$FF8C`, `$FF90`) with an index, a list number and a destination
  makes the MCU copy one byte from a table in its ROM to `$FC88` (`$FD88`, `$FE88`). The tables at
  `$F9BB-$FEBA` are not tables: they are 1,280 bytes of Z80 code — fragments of some Taito program, used as
  filler to make the ROM's checksum come out — and nothing ever requests a byte of them.
* **The restart** (`$FF97 = $4A`) and **the credit cheat**: if `$FC71` holds `$0D` while the value byte's
  mirror is 12, the MCU writes 42 credits into `$FC1E` — which, as we saw, the main program never reads.

The picture that emerges is of a service MCU written once for a family of Taito boards, with a menu of
facilities a game could call on, and of a Bubble Bobble program that uses five of them: the inputs, the
interrupt, the geometry, the countdown and, once in a while, the EXTEND counter. Everything else is ballast, but ballast that costs nothing to
carry and makes the chip harder to replace, because a copyist reading the shared RAM cannot tell from the
outside which bytes matter.

## The traps

Three of the idle services are armed by a byte the main program never writes. If `$FF95` holds `$42`, the
lives counters and the value byte compare their shared copy with a private mirror in the MCU's own RAM each
frame, and if they differ:

```asm
F2C7  LDX #$0C24
F2CA  JSR shared_read
F2CD  CMPB $0052               ; the shared byte against the private copy
F2D0  BEQ loc_F2D3
F2D2  PSHA                     ; not equal: push one byte and ...
loc_F2D3:
F2D3  RTS                      ; ... return through it
```

The extra byte on the stack turns the `RTS` into a jump to a garbage address, the MCU stops pulsing, and the
game freezes with no message. A player who altered the lives byte in shared RAM with a cheat device, or a
bootleg board that did not keep it, would have met this — had the main program ever armed it. The same
pattern, one `PSHA` too many, sits in an unreachable watcher routine at `$F217` that would have punished a
change to the byte at `$FC7F`.

The trap that is armed is the handshake itself. Chapter 3 showed the boot refusing to continue without the
`$37` at `$FC85`; five more places in the game check it again during play — in the enemy walking code, in the
round-start animation, in the bubble-blowing routine, in the map-drawing pass and in a small routine that is
called from the bubble task — and each responds to a wrong value in its own quiet way. Chapter 20 lists them
with the other protection checks, including the main CPU's own habit of confirming that the interrupt vector
at `$0B2E` still points at the handler the MCU was designed to trigger.

![The shared RAM, and which of it the game uses.](../img/ch10-shared-ram.svg)

## What the MCU is, then

Take the chip away and three things happen at once. The main CPU boots, prints nothing, and waits at
`$0158` for a `$37` that never comes. If that wait is patched out, no interrupt ever arrives and the CPU sits
in `JR $01ED` for ever. If a VBLANK line is wired to the interrupt pin instead, the vector byte at `$FC00` is
not `$2E`, and a bootlegger who fixes that too finds that the joysticks are dead, because the input latches
hang off the MCU's ports. Fix that with a different board and the monsters no longer chase. The MCU is the
copy protection, and every layer of it is also a job the game needs done. That is the design.
