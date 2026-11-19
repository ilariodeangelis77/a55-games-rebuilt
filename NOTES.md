# Move the Box: reverse-engineering notes

Running log. Every claim has a **confidence** label and its **evidence**.
Confidence levels: **confirmed** (checked against the dump or a script), **likely** (strong
indirect evidence), **guess** (hypothesis that hasn't been tested yet).

## Status

| Step | State |
|---|---|
| 0. Toolchain | Ghidra 12.2 + C166 module, see below |
| 1. Load firmware | **done**: A55 V9 fullflash, base 0x800000 (confirmed) |
| 2. Locate game | **done**: text decoder, Games menu, entry 0xCB5074, module 0xCB1600–0xCB5A00 |
| 3. Extract assets | **done**: 14 levels (XSB/JSON) + 11 tiles (PNG/JSON), `scripts/extract/extract_mtb.py` |
| 4. Decompile logic | **done**: `docs/move_the_box_logic.c` (pseudo-C), section "Game logic" below |
| 5. Reimplementation | **done**: `port/index.html` (engine; loads the extracted data at runtime) |

Reproduce everything from the dump:
```
python -I scripts/extract/extract_mtb.py firmware/upstream_ff/A55_LG7_V9_00800000.FLS out/mtb
python -I scripts/extract/render_levels.py out/mtb          # contact sheet of all levels
python -m http.server 8765   # then open http://localhost:8765/port/index.html
```

## Target

- Model / SW version: **A55, language group LG1, SW 11** (likely). Evidence: the filename of
  the EEPROM dump below, plus a UTF-16LE string `Siemens A55` inside it.
- Fullflash: _still missing_. Expected at `firmware/<MODEL>_SW<ver>.bin` (gitignored, never committed).

### `firmware/SIEMENS A55 LG1 V11 - 00FA0000.FLS`: EEPROM blocks only, no code
- SHA-256 `5f0a4aa5c55fd87bfc9ec96aeab3a750634915891d5d177a84e4d75a68f629f0`, 175,388 bytes (0x2AD1C)
- **confirmed:** this is not a fullflash. It holds only the emulated-EEPROM area:
  - file offset 0x00000: block header `FE FE "EELITE" 01 00 00 00 A0 FF FE FE`
  - file offset 0x20000: block header `FE FE "EEFULL" 01 00 00 00 A0 FF FE FE`
  - The content is mostly 0xFF (90%), with what look like RF calibration curves near the start
    (**guess**). There's no C166 code and none of the game's strings.
- **likely:** EELITE starts at CPU address **0xFA0000** and EEFULL at **0xFC0000**. The filename
  carries the read address (`00FA0000`) and the EEFULL header sits exactly 0x20000 after EELITE.
  This gives a fixed address to check the flash base against once the fullflash arrives.
- Possibly useful later: the game's highscore/unlock data may live in an EEFULL block (**guess**).

### `firmware/upstream_v11/`: official SW 11 updaters (firmware.center, 2026-11-19)
Never executed. Only read statically.

| File | SHA-256 |
|---|---|
| `A55_110701_UpdateTool.exe` | `0f73173f119ee260825a4c0adb4a5395c955362363257269027612525151d54e` |
| `110301_rus.EXE` | `528b3c3dafda3d229ea83297b315988f7da9a00c7e877b32e0c789daf89982e5` |
| `A55_1_Standard_11_0001.map` | `2f88e272baaa11ffb37b5984df11788303fdf21075e55dae4bba839f47b5f04c` |

**`.map` file** (**confirmed**): not a memory map. It's the default-contents table for EEPROM blocks
(INI-like sections `[blockID]`, `Memory = 2` EELITE / `8` EEFULL, German comments).
- **Block 5062 "GamesData"**: EEFULL, 90 bytes, default all 0xFF. Most likely where game
  scores/progress are saved (**likely**: the name, and it's the only game-related block).

**`A55_110701_UpdateTool.exe` container** (**confirmed**: decrypted plaintext is well-formed and
the PKCS#7 padding checks out). Reverse-engineered from FUN_004086f1 in the x86 code:
1. Trailer at EOF-0x1D: payload offset bytes scattered (b0 | b3<<24 | b1<<8 | b2<<16 at relative
   offsets 0, +3, +7, +12), then magic `SAG_UDT`. Payload offset = 0xBB000.
2. Payload: `00 01` version, 4-byte BE timestamp `3FC6BAAD` (2003-11-28), 4-byte BE sig length
   (0x80), 128-byte signature, then ciphertext.
3. Cipher = **AES-128-CBC** (S-box at 0x450200 and Rcon at 0x452400 in the exe confirm it).
   Key = 16 bytes at VA 0x44FE84. IV = file timestamp (4 bytes) + bytes 4..15 at VA 0x45CDCC.
4. Plaintext = "Siemens Mobile Phones Signature File" block, then the XBI ("Siemens Mobile Phones
   Software" 0x1A, then header records `FF FF FE len tag data chk`, chk = XOR of FE,len,tag,data).
   Tag 0x30 = flash ranges to program: **0x020000–0x67FFFF, 0x6E0000–0x73FFFF,
   0x780000–0x79FFFF** (flash-relative). Then `EXT_SIGNATURE_HASH_AREA`, a second record type
   `FF FF FF len tag …`, and a **5.25 MB compressed stream** (entropy 7.8–7.9).
5. The exe does **not** decompress. It sends "Compression-Info" (mode 3) and the compressed
   stream to the phone, so the decompressor runs on the phone side. Dead end without the
   phone's code, hence the switch to the ready-made fullflashes below.

### Fullflashes found on firmware.center (not downloaded yet)
- `A55 (Piranha)/Flash Files/v.09/ff/SIEMENS A55 LG7 V9 - 00800000.FLS`: 8,388,608 bytes
- `C55 (Tuna)/Flash Files/v.24/ff/C55lg1Sw24_80-80_FF.bin`: 8,388,608 bytes
- `A52 (Fox)/Flash Files/v.09/ff/A52lg1Sw09_80-40_FF.bin`: 4,194,304 bytes

### Fullflashes downloaded (2026-11-19) into `firmware/upstream_ff/`
| File | Size | SHA-256 |
|---|---|---|
| `A55_LG7_V9_00800000.FLS` (A55, SW 09, language group 7) | 8 MB | `7e7b1eb018dc2eb26dd41fda3565fab0f12d368a833825c0b189bb42394afe61` |
| `C55lg1Sw24_80-80_FF.bin` (C55, SW 24, language group 1) | 8 MB | `e4d2ce52008ba703ad9c03163f0806e3f3d72d5fd44f4ad08abd51884750948f` |

**Primary target from here on: the A55 V9 dump** (your model). The C55 dump is for cross-checks
and possibly English text.

## Flash base: CONFIRMED 0x800000 (8 MB, 0x800000–0xFFFFFF)
- **Reset vector:** both dumps start with `FA 80 xx xx` = `JMPS 0x80, xxxx`. A55: reset entry
  **0x803142**, C55: 0x802FC4. Slot 0x20 (trap vector 8) = `JMPS 0x80, 0x0130` in both. The
  jump into segment 0x80 only makes sense if flash offset 0 = CPU 0x800000. **confirmed**
- The EEPROM headers land exactly where the 0xFA0000 dump said: EELITE at CPU 0xFA0010, EEFULL
  at 0xFC0010 and 0xFE0010. **confirmed**
- The updater's programmed ranges (flash 0x020000–0x67FFFF etc.) line up with the code/data
  regions below. **confirmed**
- **Implication (likely):** at reset the flash must also be visible at segment 0 (the CPU
  fetches its vectors from 0x000000). The firmware then jumps to segment 0x80, and segment 0 is
  presumably remapped to RAM. To check in the startup code at 0x803142.

### A55 V9 layout (`scripts/extract/flash_layout.py`, 64 KB granularity)
| CPU range | Content | Interpretation |
|---|---|---|
| 0x800000–0x80FFFF | code | vector table + bootcore/startup (**likely**) |
| 0x810000–0x81FFFF | erased | |
| 0x820000–0x87FFFF | code | |
| 0x880000–0x9FFFFF | high entropy (7.5–7.7) | compressed resources: images/melodies/T9? (**guess**) |
| 0xA00000–0xD9FFFF | code/data | main firmware |
| 0xDA0000–0xDEFFFF | high entropy | **language/text pack**, header `BB BB … "lg7"` at 0xDA0000 (**confirmed** as text: contains "Stack Attack") |
| 0xDF0000–0xDFFFFF | low entropy | |
| 0xE00000–0xE2FFFF | erased | |
| 0xE30000–0xF1FFFF | mixed | FFS / data (**guess**) |
| 0xF20000–0xF3FFFF | erased | |
| 0xF40000–0xF7FFFF | low entropy | FFS (**guess**) |
| 0xF80000–0xF9FFFF | erased | |
| 0xFA0000 / 0xFC0000 / 0xFE0000 | EELITE / EEFULL / EEFULL | emulated EEPROM |

### Startup code at 0x803142 (A55), from the Ghidra listing (`scripts/ghidra/Stats.java`)
- `DISWDT`, then **DPP0 = 0x200** (`mov 0xFE00,#0x200`, page 0x200 × 16 KB = 0x800000 = flash
  base), **DPP1 = DPP2 = DPP3 = 3** (system page 0xC000–0xFFFF). **confirmed** (listing)
- CP (0xFE10) = 0xFC00, STKOV (0xFE14) = 0xFBC0, STKUN (0xFE16) = 0xFBFE, SP (0xFE12) = 0xFBFE.
- Then SYSCON/BUSCON setup and a clock/PLL wait loop. The main firmware later sets its own DPPs,
  to be found per code region.
- Only 2 of the vector slots in flash hold `JMPS` (reset, and trap 8 → 0x800130). The rest
  are presumably installed in RAM at runtime.
- Ghidra auto-analysis from the vectors alone reaches only 39 functions / 3155 instructions
  (bootcore + startup). The main firmware is entered indirectly. **Next:** seed analysis from
  all `CALLS seg,addr` (`DA ss llhh`) targets with seg 0x80–0xDF found by a raw byte scan.

## Text encoding (partially understood)
- None of the game names exist as ASCII or UTF-16 in either dump.
- `scripts/extract/pattern_search.py` matches only which letters repeat in a word, so it works
  whatever the encoding. It finds "Stack Attack" in the text pack:
  - A55: flash 0x5BCF20… (CPU 0xDBCF20), 5 times in a row (probably once per language in LG7)
  - C55: flash 0x614317… (CPU 0xE14317)
- Record format (**likely**): `[len][first byte][codes…]`, len counting itself. Codes are per
  language: an index into that language's character set (uppercase ≈ ASCII−0x10/−0x25 depending
  on the set, lowercase in ASCII order with gaps). Codes ≥ 0x80 look like **dictionary tokens**
  (e.g. one code = "ta", another = "k "). The first byte after len is not decoded yet.
- Next step: find the decoder routine in code instead of guessing. Candidates are the routines
  that read the pack header at 0xDA0000.
- "Move the box": encoding-agnostic matches exist but haven't been checked yet. The menu name
  may differ ("Move The Box", or translated in LG7).

## Flash base: early evidence (kept for the record)
**likely 0x800000, 8 MB (0x800000–0xFFFFFF)**. Three independent hints agree:
1. The A55 V9 fullflash filename carries read address `00800000`, and its size is exactly 8 MB.
2. The EEPROM file is named `00FA0000` (= flash offset 0x7A0000). The updater's last programmed
   range ends at flash offset 0x79FFFF, immediately below it.
3. The updater skips flash 0x000000–0x01FFFF (first 128 KB, so bootcore, **guess**). That's
   consistent with code starting at 0x820000.
Still to confirm against the C166 code itself (far pointers / EXTS segments into 0x80–0xFF).

## Toolchain

| Tool | Version | Location | Notes |
|---|---|---|---|
| Ghidra | 12.2 (`ghidra_12.2_PUBLIC_20261016`) | `tools/ghidra_12.2_PUBLIC/` | needs JDK 21+ |
| C166 module | keyhana/c166-ghidra-module v1.2.4 | installed into Ghidra `Extensions/` | successor of esaulenka/Ghidra_C166 (whose README says it's outdated). Has DPP translation, EXTP/EXTS handling, Tasking (`__stdcall`, R12–R15 args) and Keil (R8–R12) calling conventions. Only C167CR/C167CS processor specs, so E-GOLD+ SFRs will need adding. |
| JDK | Temurin 21.0.11 | system | |
| Python | 3.14, Pillow 12.2, numpy 2.4 | system | for extractors |

Not installed: IDA Pro (not available here), radare2. Add r2 later only if a cross-check is needed.

### Module caveats (from its README; still to confirm on the real dump)
- DPP values are **not** inferred. Set DPP0–DPP3 with *Set Register Values* over the ranges
  where they hold, or data references resolve wrongly.
- Reset DPP defaults (0/1/2/3) are not applied automatically.

## Memory map

_tbd. Hypotheses to test once the dump arrives:_
- **guess:** flash is mapped at a fixed high base in the 16 MB C166 space. Check the reset
  vector (`JMPS seg, addr` at offset 0) and far-pointer (segment, offset) pairs that point into
  the image.
- Cross-check against `.vkp` patches in `patches/`. Some use flash-relative offsets and some use
  absolute addresses, so check each one.

## Compiler conventions

_tbd: Tasking vs Keil, user stack in R0, DPP usage._

## Game location

_tbd_

## Address / symbol table

| Address | Name | Confidence | Evidence |
|---|---|---|---|

## Open questions

- Are UI strings stored inline or referenced by ID through a language pack?

## Text pack decoder (confirmed: decodes all strings)
`scripts/extract/textpack.py` reimplements `FUN_d4850e` (hand-written asm):
- Text API: `FUN_d4a316(id)` → buffer at page 0x54:0x3640. `FUN_d4a242` dispatches by ID:
  0–0xBE2 language pack, 0xBE3–0xE8A plain ASCII via table at page 0x353, ≥0x1388 other.
- String number n = `id × header[0x0E] (=9) + slot`; slot = byte `header[0x08] + lang`.
- 16 KB block page = 0x368 + k, chosen by threshold table at 0xDA003C. Index table
  `header[0x12]` (0xDA0140) points to every 8th string; skip `n & 7` length-prefixed records.
- Record `[len][codes…]`. Language descriptor (14 bytes at `header[0x0A] + lang×14`):
  `{t1, n1, t2, n2, t3, n3, t4}`: code < n1 → 1 char from t1, < n2 → 2 chars from t2,
  < n3 → 3 chars, else 4 chars. Output is 8-bit; 0x95 = format prefix, 0x8A = newline.
- LG7 language 0 = English.

Game text IDs: 0x347/0x348 "Move the box", 0x3E4 help, 0xA98–0xA9A help pages, 0x9F9
"Rotate map", 0x3D8 "You have won!\nYour score:", 0x3E2 "You have lost!…", 0x33E Highscore.

## Game location (all confirmed)
- Games menu items: table at 0xD1A168, 18-byte records `[0,0,title,title2,0,0,0,3,X]`. Handler
  far pointers at 0xD1A1BE → `JMPS` trampolines at 0xD1A0CA…:
  Stack Attack 0xCAF8F8, Balloon Shooter 0xCA8E38, **Move the box 0xCB5074**, Wacko 0xD53C96.
- The module is reached only through pointers and jump tables, so Ghidra needed help:
  `SeedFromList.java` (entries), `SweepRegion.java` (linear sweep 0xCA0000–0xCC0000).

| Address | Name (mine) | Role |
|---|---|---|
| 0xCB5074 | mtb_menu_entry | clamps saved level / highscore, opens start screen |
| 0xCB503A | mtb_open_start_screen | creates UI from descriptor 0xCAFFC6 (callbacks 0xCB4FA4/0xCB4FD0) |
| 0xCB2B2A | mtb_game_create | allocates state (0x114 bytes), reads saved level/highscore/option |
| 0xCB2A78 | mtb_game_start | resets session, loads level, draws |
| 0xCB1FAE | mtb_load_level | level loader (35-case pair switch, jump table 0xCB4F48) |
| 0xCB1FAA | mtb_level_count | returns 14 |
| 0xCB265C | mtb_transpose | diagonal transpose of the 8×8 grid |
| 0xCB26DA | mtb_place_player | finds player tile, positions sprite |
| 0xCB3262 | mtb_on_key | key handler (moves, undo, reset, exit, sound) |
| 0xCB3130 | mtb_save_undo | copies grid + on_goal to backup |
| 0xCB3194 | mtb_undo | restores backup, steps-- |
| 0xCB2C7C | mtb_reset | reload current level |
| 0xCB3210 | mtb_after_move | step count, rotate option, win/lose, scoring, progression |
| 0xCB2750 | mtb_update_highscore | |
| 0xCB2E18 | mtb_show_result | won/lost text + score |
| 0xCB28B4 | mtb_draw_cell | tile → picture via jump table 0xCB4F8E (default: level number) |
| 0xCB276C | mtb_draw_level_number | |
| 0xCB4B40 / 0xCB49EA | redraw all / redraw changed cells | |
| 0xD1A77E/0xD1A796 | get/set highscore (persistent) | |
| 0xD1A78A/0xD1A7A2 | get/set level (persistent) | |

## Assets (confirmed)
- **Levels:** 0xCB4C0C, 14 × 0x26 bytes: `u16 flag, u8 nboxes, u8 prow, u8 pcol, 32 map
  bytes`. Each map byte (0x41–0x63) = 2 cells via the loader switch. The table was traced
  mechanically (`trace_loader_cases.py`). flag≠0 → transposed on load (levels 9–14).
  All 14 levels: boxes = goals = nboxes, exactly one player. Solvability check skipped on
  request (solver is in `scripts/extract/solve_xsb.py`; it solved level 1 in 31 moves).
- **Tiles:** 11 picture descriptors at 0xCB4ED0 `{u8 w=10, u8 h=8, u16 1, u16 off, u16 page}`.
  Bitmaps are rows of big-endian u16, top 10 bits, 1 = black.
  Tile code → picture: 100→2 box, 101→4 goal, 102→5 floor, 103→1 wall, 104→3 box on goal,
  105→6 player, 106–109 → 7–10 player up/down/left/right, 110→0 blank.
- **Screen:** 8×8 cells of 10×8 px = 80×64 at the left. The UI code reserves 101−17 px of
  width for the board and splits it into 8 columns.

## Game logic: see `docs/move_the_box_logic.c`
Quirks vs. standard Sokoban:
- **200-move limit per level**: reaching it = "You have lost!".
- **Score per level = 200 − moves**. The session score accumulates across levels and is what
  becomes the highscore.
- **One-step undo** (left soft), which refunds the move. Reset (right soft) keeps the session
  score. After a win, the level counter is already advanced, so "reset" starts the next level.
- Levels 9–14 are stored transposed. The optional **"Rotate map"** transposes the board every
  50 moves.
- Cell (0,0) holds the level index and is drawn as the level number.
- After level 14 it wraps to level 1. A beep (sound 0x25) plays when a box lands on a goal.
- Key codes 0x01/0x04/0x0C for left soft/right soft/red are **likely** (standard x55 codes).
  The help text confirms the left/right soft roles.
- **Saved data:** the phone stores level and highscore persistently. The EEPROM block 5062
  "GamesData" is the **likely** backing store (not traced through FUN_d1a77e…).

## Reimplementation: `port/index.html`
Single HTML/JS file that implements the logic above, at 101×64 scaled. It loads
`out/mtb/levels.json` + `tiles.json` (your extraction) or files picked by hand. Without
data it runs one placeholder level with placeholder tiles. The original levels/art are never
embedded in the repo, consistent with the no-redistribution rule.
Tested in the browser:
- level 1 solved in 31 moves → score 169, highscore saved, level advanced
- undo once only
- moves blocked after win
- right soft starts the next level
- 200 moves → lost, +0
- rotate map transposes at move 50

### Port-only additions (not in the original firmware)
- **Level selection:** menu item `Level: ◀ n / 14 ▶` (keys 4/6 or the bound Left/Right)
  starts any level. The original only resumes from the saved level.
- **Control remapping:** a `Controls` screen rebinds each action (up, down, left, right,
  undo, reset, OK, sound, exit) to any keyboard key, saved in localStorage
  (`boxport.bindings`).
  - A key drives one action only: binding it elsewhere removes it from its old action.
  - `Esc` cancels a pending rebind.
  - `Restore defaults` resets all bindings.
  - The on-screen phone keys are unaffected.

## Original start menu (confirmed unless marked)
Reached from Games → Move the box (`FUN_cb5074` → `FUN_cb503a`).
- **Start screen:** UI descriptor 0xCAFFC6, key callback `FUN_cb4fa4`, create/close
  callback `FUN_cb4fd0`.
  - Soft-key table at 0xCAFFAE: `{5, 5, "Start" 0x1B2}`, `{0x2D, 0x2D, "Options" 0x215}`.
  - Event 5 → `FUN_cb4ba0` (start the game); event 0x2D → `FUN_cb1888` (Options).
  - Left = Start, right = Options is **likely** (table order).
  - What the screen body shows is **unknown**. The port shows the title.
- **Options list:** descriptor around 0xCB1E7E, five 18-byte item records:
  1. **Start**: text 0x1B1, starts the game.
  2. **Level**: text 0x3DA. A 2-digit number field.
     - `FUN_cb19e8` validates input as it's typed: `*`, `#` or `0` first → rejected; a digit
       above the max or a 2-digit value > 14 → clamped to "14".
     - `FUN_cb18c8` on OK: converts the text to an index (clamped to 13) and saves it as the
       current level (`FUN_d1a7a2`).
     - **So the original did have level selection.**
  3. **Highscore**: text 0x33E. `FUN_cb16ee` shows text 0x3E3 "Best score: %d" with
     `FUN_d1a77e()`.
  4. **Instructions**: text 0x480. `FUN_cb16ce` shows the text list at 0xCAFF9E:
     0x3E4, 0xE74 (" "), 0xA98, 0xE74, 0xA99, 0xE74, 0xA9A, 0x7FFF (end).
  5. **Rotate map**: text 0x9F9, a checkbox item. `FUN_cb1808` toggles the setting
     (`FUN_d1a7ae(!FUN_d1a7ba())`); `FUN_cb184e` draws the checkbox state.
- **Settings storage:** `FUN_ca8b9a(gameId, …)` loads a shared 2-byte field at offset 0x42
  plus a per-game 10-byte slot at `(gameId−1)×10` of a 90-byte record; Move the box = game 9
  → bytes 80–89. This matches EEPROM block **5062 "GamesData"** (90 bytes) → **likely** where
  level, highscore and options are saved.
- `extract_mtb.py` now also writes `out/mtb/texts.json` with these strings, decoded from the
  text pack (`0xA4 + width bytes` = number placeholder → `%d`).

**Port:** "Original menu" in the port's menu opens this start screen, the Options list,
number-entry Level (same input rules), Highscore, Instructions (2/8 scroll) and the Rotate
map checkbox. Exiting a game started from it returns to the start screen. Text comes from
`texts.json`; without it the port uses its own wording.
