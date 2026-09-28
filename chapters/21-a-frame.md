# 21. A frame, exactly

Everything in this article happens inside a sixtieth of a second, and this chapter is that sixtieth of a
second laid end to end. The frame is number 1,500 of the traced one-player game — round 1, twenty-five
seconds in, one dragon on the floor, three Zen-chans, a cluster of bubbles under the ceiling — and the
listing is the order in which the routines of chapters 9 to 18 actually ran, taken from the emulator with
every named routine's entry logged. Nine hundred and four routine entries; the helpers (the wall tests,
the table lookups, the sprite writers, the scheduler's own code and the checksum walkers) are omitted here,
which leaves the ones that decide something.

## Before the interrupt: the tail of the previous frame

The picture that the hardware shows during frame 1,500 was composed during frame 1,499. At the start of
frame 1,500's VBLANK the main CPU is idle, the sub CPU is beginning its collision pass, and the MCU is
reading the joystick. The sub CPU's pass, for this frame, takes about seven milliseconds (chapter 11).

## 0 us: VBLANK

| Time (us) | Processor | What happens |
| --- | --- | --- |
| 0 | video | Line 240: blanking begins. The last picture is complete on the screen |
| 0 | sub Z80 | Interrupt: `frame_handler`. The collision map request is idle; the doors idle; the round is running, so the sixteen tests begin, `players_caught` first |
| 0 | MCU | IRQ1: `svc_main_irq` reads the key at `$FF98` |
| ~100 | MCU | The pulse on port 1 bit 6 |
| 115 | main Z80 | `irq_vblank`: watchdog kicked, DIP switch A read (not a test mode), `frame_done` was 1: a normal frame |
| 115-1395 | main Z80 | `irq_frame_start`: 360 bytes of object list to `$DD00`; `sound_queue_pump` (the queue is empty this frame); `rng_pre` (`$E37F` + 1); `irq_essentials`: `coin_handling` with `coin_sound` and three `edge_detect` calls on the coin switches, `tilt_check`, `rng_step` and `rng_lfsr`, `timer_chain` (the frames byte reaches 60 and the seconds byte steps), `sub_cpu_watchdog` (the heartbeat moved), the frame counter |
| 1395 | main Z80 | `frame_done = 0`, `EI`, `scheduler_run` |
| ~400-1400 | MCU | `svc_inputs`, `svc_coins`, the idle services; the geometry for one active enemy record; the 2.6 ms delay loop |

## 1632 us: task 2, the round loop

The first runnable slot is task 2. Its one frame, in order:

```
join_update                 the INSERT COIN / TO CONTINUE blink in player 2's corner
join_update_p2              player 2's start button: not pressed
round_ready_display         the READY banner is long gone: nothing
read_inputs                 $FC22, $FC23 -> $E33F, $E340
game_over_check             no request
play_time_tick              the round clock: 25 seconds and a fraction
hurry_up_logic              25 is not 27 and not 30: nothing
last_enemy_angry_timer      three enemies left: nothing
last_enemy_check            nothing
                            RST $20
```

Five hundred and thirty-five microseconds, most of them in the prompts.

## 2302 us: task 3, the players and the round objects

```
round_start_anim            the round has started: returns at once
special_item_update         the round's food: timer not yet expired
bonus_item_update           the bonus item: on the field, waiting
seq_f59e_update             the bomb sequence: idle
seq_f595_update             the flyer: idle
round_end_update            the round-clear wipe: idle
seq_f521_update             the treasure fill: idle
seq_f531_update             the growing fill: idle
seq_f52b_update             the second growing fill: idle
hurry_seq_update            the bonus-item spawner's timer, counting
flying_objects_update       idle
falling_items_update        idle
seq_f5ac_update             the bouncing object: idle
bonus_sequence_check
water_flows_update          idle
floor_fires_update          idle
seq_f519_update             the palette flash: idle
big_item_update             idle
boss_lightning_update       not round 100: returns
player_death_check          $E720 is 0
f448_object                 idle
player_life_cycle           player 1: state 1
  player_alive_update
    player_pos_to_mcu       x, y -> $FC60, $FC61
    walk_anim_frame         the speed list's next byte -> [+$20]
    invincible_tick         not invincible
    jump_control            the button is up; not jumping
    bubble_blow             the button is up; the cooldown counts
    walk_move               no push from the sub CPU
    ground_control          the stick is held right: set_anim 8, and the pixels of the step, each with wall_test and wall_test_left3
    bubble_anim_timer       not burnt
    sprite_anim_draw        the walk frame into the object slot
    special_item_pickup     proximity_test: not within 14
    bonus_item_pickup       proximity_test: not within 14
    power_item_pickup       no power item
    big_item_pickup         no big item
    power_effect_update     no effect
    bubble_chain_score      no chain finished
  player 2: state $80 (not in the game): player_death_anim, which returns
                            RST $20
```

One thousand four hundred and thirty-eight microseconds. Two-thirds of the bank-2 subsystems return in
their first ten instructions; the player's own frame is about a third of the task.

## 3817 us: task 4, the enemies

```
enemy0_update               three Zen-chan records
  record 0: flag bit 1: enemy_death_update -> death_draw   (a monster popped moments ago, tumbling)
  record 1: enemy_bubble_events, enemy_hurry_check, enemy_caught_check,
            enemy_speed_select, enemy_drift, enemy_walk_down:
              enemy_stuck_jump (not stuck), then per pixel: wall_test ahead,
              target_player_alive, mcu_player_relation (the MCU's byte: the player is that way),
              enemy_wall_down_left (no gap), y + 1;
            enemy_decide -> enemy_chase (|dx| from $FC2B: too far to jump);
            enemy0_draw -> enemy_draw_walk
  record 2: enemy_death_update -> death_script_step -> death_draw   (another one tumbling)
enemy0_alt_update           not an Invader round: returns
enemy1_update .. enemy5_update   no enemies of those types: each returns
chasers_update              no chasers
subsystem_a5fe
rocks_update                no rocks
falling_objects_update
subsystem_bc14
missiles_update             the MCU countdown is not running
                            RST $20
```

Two thousand one hundred and eleven microseconds. Of the three monsters, one is walking and two are dying:
the player has just popped a pair, and the tumbling corpses cost about as much as the walker.

## 6006 us: task 5, the bubbles

```
secret_door_transition      no door
bubble_update
  bubble_spawn_gate
  records 0-6: floating bubbles, each: bubble_just_blown -> bubble_spawn_allowed,
     bubble_drift (one or two steps: bubble_current_step, and bubble_current_read on a cell boundary),
     bubble_rise_draw (bubble_lifetime inside), bubble_apply_move, bubble_edge_test
  record 7: in flight: bubble_in_flight -> find_enemy_near (nothing within 14), bubble_float
  record 8: floating, as above
  records 9-23: free: bubble_free_slot -> bubble_spawn_from_request (no request) x 15
extend_letters_complete     not all six
                            RST $20
```

Four thousand three hundred and ten microseconds: nine live bubbles at about three hundred microseconds
each, fifteen free records at a hundred each just to find out that nobody asked for a bubble. The bubble
task is the most expensive thing on the main CPU in an ordinary frame, and the reason is in this list: every
free record still walks the spawn path.

## 10358 us: done

`scheduler_run` returns to `irq_after_scheduler`: `frame_done = 1`, the interrupted address is checked
against `$C000`, `RETI`, and the main CPU is back in its two-byte loop with 6.5 milliseconds to spare. The
sub CPU finished its pass at about 7 milliseconds and has been idle since; the MCU finished its handler at
about 7.3 milliseconds. The object list built during the tasks is in the shadow at `$E1CD`; it will be
copied to the hardware at the next VBLANK, and drawn during the frame after that.

![The same frame as a timeline (chapter 9).](../img/ch09-frame-timeline.svg)

## What a frame costs

| Where the cycles go, frame 1,500 | Cycles | Share |
| --- | --- | --- |
| Interrupt handler and essentials | 7,680 | 7.6% |
| Scheduler and task switches | ~2,000 | 2% |
| Task 2 | 3,210 | 3.2% |
| Task 3 | 8,628 | 8.5% |
| Task 4 | 12,666 | 12.5% |
| Task 5 | 25,860 | 25.5% |
| Idle | ~41,000 | 40.7% |

Over the whole traced game the picture is the one chapter 9 charted: half the frame in round 1, the
spikes to 100% only at the screen transitions, and never a slowdown in play.

![Main CPU time per frame over the first 3,000 frames (chapter 9).](../img/ch09-busy-play.png)

## What a frame is, then

Read as a whole, the frame has a shape that none of its routines knows about. The interrupt handler
commits last frame's picture and reads the world's inputs. Task 2 keeps time. Task 3 moves the players on
those inputs and runs the things the players touch. Task 4 moves the monsters against where the players
now are, using what the MCU worked out from where they were last frame. Task 5 moves the bubbles against
both, using what the sub CPU worked out during the blanking. Then the CPU rests, and while it rests the two
helpers read what it wrote and prepare the next frame's verdicts. Four processors, six tasks, one frame,
and the same order every time: that regularity is what makes the game feel the way it does, and it is what
made it possible to take the program apart routine by routine and put it back together in another
language, exact to the cycle.
