# A55 Games, rebuilt

The four built-in games of the Siemens A55 phone, reverse-engineered from its firmware
(C166 / E-GOLD+) and rebuilt as small browser pages:

- **Move the box**: push every box onto a marked spot (14 levels).
- **Wacko**: hit the critters popping out of nine holes, and spare the bunnies.
- **Balloon Shooter**: aim the crosshair and shoot the balloons.
- **Stack Attack**: cranes drop crates. Fill rows and don't get crushed.

A **Games menu** works like the phone's own: one page per game with its original start picture,
plus a Setup page.

**Play it in the browser: <https://ilariodeangelis77.github.io/a55-games-rebuilt/>**

> Personal preservation project. **The firmware itself is not in this repository.** The pages
> contain the rebuilt game logic. The game data they load (levels, sprites, start pictures and
> texts, as JSON in `out/<game>/`) was extracted from a firmware dump by the scripts in
> `scripts/extract/`. It is included so the page is playable, and it can be regenerated from your
> own dump. Without it, Move the box and Wacko fall back to placeholder art; the other two need it.

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

The games only know the phone's keys: 1–9, 0, `*`, the two soft keys, OK and End. **Which keyboard
keys press them is up to you.** Open **Keyboard keys…** (the button under Controls on every page,
or Games → Setup → Keyboard keys). It shows a keypad where each phone key can have any number of
keyboard keys. The same mapping applies to every game and is saved in your browser. The on-screen
keys show their keyboard keys as small hints.

Default mapping:

| Phone key | Keyboard |
|---|---|
| Left soft / Right soft | `F1` / `F2` |
| OK | `Enter` |
| End | `Esc` |
| 1–9, 0 | number row and numpad; also `Q W E` / `A S D` / `Z X C` as a 3×3 block, arrows for 2 4 6 8, `Space` for 5 |
| `*` | numpad `*` (or a typed `*`) |

Each page lists what the phone keys do in that game. You can also click the on-screen keys.
**LCD depth** (a soft shadow behind every pixel, like a real passive LCD) can be switched in the
Settings card or under Games → Setup.

## What's where

| Path | What |
|---|---|
| `port/` | The pages: `games.html` (menu), `index.html` (Move the box), `wacko.html`, `balloon.html`, `stack.html`, plus the shared `shell.css`, `shell.js`, `keys.js` (keyboard mapping), `lcd-depth.js` |
| `scripts/extract/` | Extractors: text pack decoder, picture decoder, one script per game, and level tools (render, solve) |
| `scripts/ghidra/` | Ghidra headless scripts used for the analysis (C166 module) |
| `docs/*_logic.c` | Cleaned-up pseudo-C of each game's logic, with the original function addresses |
| `NOTES.md` | The full reverse-engineering log. Every claim is marked confirmed, likely or guess |

## What is original and what isn't

- **From the firmware** (and confirmed in `NOTES.md`): game rules, timings and scoring; level
  layouts; sprites and splash pictures; texts; and the Games menu's order and titles.
- **Port additions:**
  - in Move the box: the port menu (level select)
  - everywhere: the global keyboard mapping
  - in the Games menu: the custom Setup picture and the page dots
  - everywhere: the LCD depth effect and the page layout around the phone

  Details that couldn't be fully traced (some sound timbres, the real Setup contents) are marked
  as approximations in the notes.
