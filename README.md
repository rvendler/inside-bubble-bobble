# Inside Bubble Bobble

A walkthrough of the arcade game's code, data and design: how the 1986 Taito board builds its picture, keeps time,
moves the dragons, drifts the bubbles, hunts with its monsters and hides its secrets. Written from the ROMs and
verified against a cycle-exact emulator and a routine-by-routine port of all four processors' programs.

## Read it

* **[inside-bubble-bobble.html](inside-bubble-bobble.html)** — the whole article as one standalone page, every image embedded (1.2 MB). Download it and open it, or read the published copy on GitHub Pages if this repository has it enabled.
* **[inside-bubble-bobble.md](inside-bubble-bobble.md)** — the same text as one Markdown file.
* **[chapters/](chapters/)** — one file per chapter, readable directly on GitHub.

## Contents

* [Inside Bubble Bobble](chapters/01-introduction.md)
* [2. The hardware](chapters/02-hardware.md)
* [3. Power-on](chapters/03-power-on.md)
* [4. Graphics: tiles, sprites and colours](chapters/04-graphics.md)
* [5. Building the screen](chapters/05-screen.md)
* [6. Rounds: maps, walls and the round table](chapters/06-rounds.md)
* [7. Text, fonts and tables](chapters/07-text-and-tables.md)
* [8. Sound and music data](chapters/08-sound.md)
* [9. The frame: interrupts and the scheduler](chapters/09-frame.md)
* [10. The microcontroller](chapters/10-mcu.md)
* [11. The sub CPU](chapters/11-sub-cpu.md)
* [12. Game flow](chapters/12-game-flow.md)
* [13. Bub and Bob](chapters/13-players.md)
* [14. Jumping, falling and riding](chapters/14-jumping.md)
* [15. Collision](chapters/15-collision.md)
* [16. Bubbles](chapters/16-bubbles.md)
* [17. Enemies](chapters/17-enemies.md)
* [18. Items, bonuses and secrets](chapters/18-items.md)
* [19. Round 100 and the endings](chapters/19-boss.md)
* [20. Randomness, secrets and protection](chapters/20-randomness.md)
* [21. A frame, exactly](chapters/21-a-frame.md)
* [22. Afterword: how this article was made](chapters/22-afterword.md)
* [Appendix A. Work RAM map](chapters/23-appendix-a.md)
* [Appendix B. Record layouts](chapters/24-appendix-b.md)
* [Appendix C. Sound commands](chapters/25-appendix-c.md)
* [Appendix D. The round table](chapters/26-appendix-d.md)
* [Appendix E. Glossary](chapters/27-appendix-e.md)

## What is in the images

Every screenshot was rendered from the ROMs by an emulator written for this project, at a stated frame of a
scripted game, so that every picture is reproducible. The figures (SVG) were drawn from the measurements
described in the text. The `img/` directory holds all of them.

## Copyright

Bubble Bobble is © 1986 Taito Corporation. The screenshots, the graphics excerpts and the short listings quoted
from the disassembly are reproduced for the purpose of description and study. The text and figures of this
article are by the author of this repository.
