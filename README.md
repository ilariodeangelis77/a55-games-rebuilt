# A55 Games, rebuilt

The four built-in games of the Siemens A55 phone, reverse-engineered from its firmware
(C166 / E-GOLD+) and rebuilt as small browser pages:

- **Move the box**: push every box onto a marked spot (14 levels).
- **Wacko**: hit the critters popping out of nine holes, and spare the bunnies.
- **Balloon Shooter**: aim the crosshair and shoot the balloons.
- **Stack Attack**: cranes drop crates. Fill rows and don't get crushed.

A **Games menu** works like the phone's own: one page per game with its original start picture,
plus a Setup page.

> Personal preservation project. **No firmware and no original assets are in this repository.**
> The pages contain only the rebuilt game logic. Levels, graphics and texts are extracted from
> your own firmware dump by the scripts in `scripts/extract/` into `out/` (gitignored). Without
> that data, Move the box and Wacko fall back to placeholder art; the other two need the data.

## Run it

You need Python 3 and a fullflash dump of an A55 (the notes use SW 09, language group LG7).

```sh
FF=firmware/upstream_ff/A55_LG7_V9_00800000.FLS     # your dump; firmware/ is gitignored
python -I scripts/extract/extract_mtb.py        $FF out/mtb
python -I scripts/extract/extract_wacko.py      $FF out/wacko
python -I scripts/extract/extract_balloon.py    $FF out/balloon
python -I scripts/extract/extract_stack.py      $FF out/stack
python -I scripts/extract/extract_games_menu.py $FF out/games
python -m http.server 8765 --bind 127.0.0.1
```

Then open <http://localhost:8765/>. It redirects to the Games menu.

### Controls

Every page lists its keys next to the phone. The common ones:

| Key | Phone key |
|---|---|
| `F1` / `F2` | left / right soft key |
| `Enter` | OK |
| `Esc` | End: leave the game; on a start screen, back to the Games menu |
| `0`–`9`, arrows | keypad |
| `*` | sound on/off (in game) |

You can also click the on-screen keys. **LCD depth** (a soft shadow behind every pixel, like a
real passive LCD) can be switched in the Settings card or under Games → Setup.

## What's where

| Path | What |
|---|---|
| `port/` | The pages: `games.html` (menu), `index.html` (Move the box), `wacko.html`, `balloon.html`, `stack.html`, plus the shared `shell.css`, `shell.js`, `lcd-depth.js` |
| `scripts/extract/` | Extractors: text pack decoder, picture decoder, one script per game, and level tools (render, solve) |
| `scripts/ghidra/` | Ghidra headless scripts used for the analysis (C166 module) |
| `docs/*_logic.c` | Cleaned-up pseudo-C of each game's logic, with the original function addresses |
| `NOTES.md` | The full reverse-engineering log. Every claim is marked confirmed, likely or guess |

## What is original and what isn't

- **From the firmware** (and confirmed in `NOTES.md`): game rules, timings and scoring; level
  layouts; sprites and splash pictures; texts; and the Games menu's order and titles.
- **Port additions:**
  - in Move the box: the port menu (level select, key remapping)
  - in the Games menu: the custom Setup picture and the page dots
  - everywhere: the LCD depth effect and the page layout around the phone

  Details that couldn't be fully traced (some sound timbres, the real Setup contents) are marked
  as approximations in the notes.
