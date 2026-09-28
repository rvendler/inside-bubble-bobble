# Appendix C. Sound commands

The fifty-three commands of the sound program (chapter 8): the table entry at $329C + 2n, the number of channel headers it requests, the first header's record and priority, its follow-up command, and where the game uses it (from the traced sessions; a blank means the tracing did not hear it).

| Command | Headers | First record (kind) | Priority | Follow-up | Used for |
| --- | --- | --- | --- | --- | --- |
| `$00` | 26 | `$8440` (`$98`) | 0 | none | silence everything (sent at boot and when a round ends) |
| `$01` | 9 | `$8440` (`$98`) | 0 | none | silence the nine YM3526 first voices |
| `$02` | 9 | `$8490` (`$9A`) | 0 | none | silence the nine YM3526 second voices (the theme) |
| `$03` | 3 | `$80E0` (`$8C`) | 0 | none | silence the three YM2203 primary voices |
| `$04` | 3 | `$8170` (`$8E`) | 0 | none | silence the three YM2203 alternate voices |
| `$05` | 1 | `$8000` (`$84`) | 0 | none | silence SSG channel A |
| `$06` | 1 | `$8070` (`$86`) | 0 | none | silence SSG channel B |
| `$07` | 9 | `$8490` (`$9A`) | 8 | `$30` | the main theme (started by the story intro) |
| `$08` | 9 | `$8440` (`$98`) | 8 | none | the game-over jingle |
| `$09` | 3 | ? | ? | ? |  |
| `$0A` | 9 | `$8490` (`$9A`) | 8 | none |  |
| `$0B` | 9 | `$8440` (`$98`) | 8 | none | GAME OVER music |
| `$0C` | 1 | `$8200` (`$90`) | 1 | none |  |
| `$0D` | 1 | `$8200` (`$90`) | 7 | none | the player is hit |
| `$0E` | 1 | `$8200` (`$90`) | 7 | none | a rock bursts |
| `$0F` | 9 | ? | ? | ? |  |
| `$10` | 9 | `$8490` (`$9A`) | 8 | `$32` | the results / ending music |
| `$11` | 1 | `$8200` (`$90`) | 8 | none | an item is collected |
| `$12` | 3 | `$80E0` (`$8C`) | 8 | none |  |
| `$13` | 9 | `$8440` (`$98`) | 8 | none | the secret room |
| `$14` | 9 | `$8440` (`$98`) | 8 | none | EXTEND |
| `$15` | 1 | `$8200` (`$90`) | 6 | none | the boss starts moving |
| `$16` | 1 | `$8200` (`$90`) | 8 | none | a bonus item is taken |
| `$17` | 1 | `$8320` (`$94`) | 7 | none | an EXTEND letter |
| `$18` | 3 | ? | ? | ? | HURRY UP |
| `$19` | 9 | `$8440` (`$98`) | 8 | none | the ending |
| `$1A` | 1 | `$8200` (`$90`) | 8 | none |  |
| `$1B` | 2 | `$80E0` (`$8C`) | 7 | none |  |
| `$1C` | 3 | `$8170` (`$8E`) | 8 | none |  |
| `$1D` | 1 | `$8200` (`$90`) | 8 | none |  |
| `$1E` | 1 | `$8200` (`$90`) | 6 | none |  |
| `$1F` | 1 | `$8200` (`$90`) | 6 | none |  |
| `$20` | 1 | `$8200` (`$90`) | 8 | none | the round food is taken |
| `$21` | 1 | `$8200` (`$90`) | 6 | none |  |
| `$22` | 1 | `$8200` (`$90`) | 6 | none | a fire shot |
| `$23` | 2 | `$8200` (`$90`) | 8 | none |  |
| `$24` | 2 | `$8200` (`$90`) | 8 | none |  |
| `$25` | 1 | `$80E0` (`$8C`) | 7 | none | an enemy dies (bubble popped, fire) |
| `$26` | 2 | `$80E0` (`$8C`) | 7 | none | chain of 2-4 |
| `$27` | 3 | `$80E0` (`$8C`) | 7 | none | chain of 5-7 (and the fatal boss hit) |
| `$28` | 2 | `$8200` (`$90`) | 8 | none |  |
| `$29` | 9 | `$8490` (`$9A`) | 8 | none |  |
| `$2A` | 9 | `$8440` (`$98`) | 8 | none |  |
| `$2B` | 9 | `$8440` (`$98`) | 8 | none |  |
| `$2C` | 1 | `$80E0` (`$8C`) | 8 | none | the jump |
| `$2D` | 3 | `$80E0` (`$8C`) | 2 | none |  |
| `$2E` | 1 | ? | ? | ? |  |
| `$2F` | 1 | `$80E0` (`$8C`) | 7 | none |  |
| `$30` | 9 | `$8490` (`$9A`) | 8 | `$30` | round clear with EXTEND collected |
| `$31` | 1 | `$80E0` (`$8C`) | 8 | none | the bubble blow |
| `$32` | 9 | ? | ? | ? |  |
| `$33` | 1 | `$80E0` (`$8C`) | 8 | none | a lightning bolt hits |
| `$34` | 1 | `$80E0` (`$8C`) | 1 | none | a coin |
