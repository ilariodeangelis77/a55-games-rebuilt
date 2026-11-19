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
  - Left = Start, right = Options: **confirmed** by a photo of a real A55 (Russian UI:
    "Старт." / "Опции"), matching the table order.
  - Body: **a full-width splash picture** (confirmed by the same photo): a round, angry
    bomb-like creature on the left, a running man, brick walls and boxes.
    **Found: picture id 0xCB, 101×49** (confirmed, it matches the photo). The chain:
    descriptor +0x18 = `{x 0, y 0, w 101, h 50, → list}`, and the list at 0xCAFFC4 holds the
    id 0xCB (Wacko's start screen, descriptor 0xD53B28, uses 0xCD).
    `extract_mtb.py` writes `splash.json`/`splash.png`; the port draws it on the start screen.
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

## Picture system (confirmed)
- **Draw by id:** `FUN_a95066(x, y, id)` → `FUN_a9514a` → `FUN_a95df8(theme, id)`. The theme
  struct (`FUN_c6f124()`) holds a far pointer to the descriptor table (+0x0E/+0x10) and a count
  (+0x12). The descriptor is at `table + id × 8`. IDs 0x4E20–0x4E9E are special (RAM) pictures.
- **Table** in this dump: CPU **0xE6C5B8**, 525 descriptors
  `{u8 w, u8 h, u16 type, u16 offset, u16 page}`. 523 are type 0x81, 2 are type 0x01.
  (So 0xE30000+ holds picture data, not only file-system data.)
- **Packed 1-bpp (type 0x81),** decoder `FUN_a9f67a`, called from `FUN_a95828`:
  - a row-major pixel stream; tokens can span rows
  - `b & 0x80 == 0` → literal: 7 pixels = bits 6..0, MSB first
  - otherwise → a run of `b & 0x3F` pixels in colour `(b >> 6) & 1` (1 = black)
  - check: picture 0 (4×4) is the single byte 0x90 = white run of 16
- Reusable decoder: `scripts/extract/siemens_pics.py <dump> <id>…`.
- The game's own 10×8 tiles are *not* in this table: they use their own unpacked descriptors at
  0xCB4ED0 (type 1, drawn with `FUN_d434b6`).

# Wacko (game id 8)

## Location (confirmed)
| Address | Role |
|---|---|
| 0xD53C96 → 0xD53BE4 | Games-menu entry: start screen (descriptor 0xD53B28, splash picture 0xCD), loads saved level/best score/best rate |
| 0xD53B4E / 0xD53B7A | start-screen key / create-close callbacks (event 5 → start, 0x2D → Options) |
| 0xD535D6 | start the game screen (descriptor 0xD53AD6 → method table 0xD53ABE) |
| 0xD528CC | create / start game |
| 0xD530EE | key handler |
| 0xD53488 | tick (timer callback): time, step, game over |
| 0xD5217E | step (state machine + spawning) and hit animation |
| 0xD52734 / 0xD527DA | hit test / points (switch table 0xD53B02) |
| 0xD52444 / 0xD52506 | redraw / draw one hole (switch table 0xD53ADE → picture descriptors) |
| 0xD52C2C | layout: 3 column layers at x = 24c (middle column y + 2), cells 24×18; level icon at (85,25) |
| 0xD52E70 | result screen (text 0x3D7) |
| 0xD51DCE → descriptor 0xD51FF8 | Options: Start, Level (shows "Level 1/2/3"), Highscore (0x3D6), Instructions (0x3E5, 0x9F8) |

## Rules
See `docs/wacko_logic.c`.
- **Board and states:** a 3×3 board with per-hole states. A wacko rises in 3 frames, holds
  for 4–9 ticks, then sinks. A rabbit follows the same cycle in its own states. At least
  1–4 holes are kept busy; a new animal is a rabbit with probability 21/101.
- **Points:** hitting a wacko earns 14/12/10/8/6/4/2 × level depending on its frame (the
  earlier the better). Hitting a rabbit costs 10, never going below 0.
- **Rate** = hits × 100 / wackos spawned, capped at 100. The 3 wackos already up at the start
  aren't counted, and there's no division-by-zero check.
- **Timing by level (1/2/3):**
  - tick period 52/26/13 timer units
  - duration 45000/65000/110000 at −200 per tick, i.e. 225/325/550 ticks
  - The unit is the GSM frame, **confirmed**: `FUN_cac340` converts ms to units with
    `ms × 1300 / 6 / 1000`, so 1 unit = 4.615 ms. That gives 240/120/60 ms per tick and
    about 54 / 39 / 33 s per game.
- **Sound toggle:** a long press of `*` (confirmed by instruction text 0x9F8) toggles key
  sound. The tick is paused while its 1.5 s message is shown.
- **Saved values:** best score and best rate, kept separately, plus the level.
- **Quirk:** `random(n)` returns 0..n inclusive (**confirmed**: `FUN_c1bf24` returns
  `(random byte × (n+1)) >> 8`). Balloon Shooter's own random returns 0..n−1.

## Assets and port
- `scripts/extract/extract_wacko.py` writes `out/wacko/sprites.json` (state → sprite mapping
  read from the draw switch's code), `splash.json` (picture 0xCD) and `texts.json`.
- `port/wacko.html` loads them at runtime and has placeholder art without them.
  - Tested: hits and points, the rabbit penalty, step transitions, game over and rate, saved
    bests, level cycling, the board layout and tick rate.
  - Level cycling 1→2→3 on select is **likely** (the item shows "Level N"; the cycle itself
    wasn't traced).

# Balloon Shooter (game id 1)

## Location (confirmed)
| Address | Role |
|---|---|
| 0xCA8E38 | Games-menu entry. Start screen descriptor 0xCA8DC0 (splash picture **0xCA**); callbacks 0xCA8E0A (keys: 0x2C start, 0x2D/0x21 Options) and 0xCA8DEC (create/close) |
| 0xCACCA6 | start the game screen (descriptor 0xCAB3AE → method table 0xCAB396) |
| 0xCAC3C0 / 0xCAC508 / 0xCAC9BA / 0xCACB04 | create / keys / tick / close |
| 0xCAB6AC | spawn |
| 0xCABC0E | cleanup (escapes, finished pops) |
| 0xCABA8C | move and animate |
| 0xCAC016 | shoot; per-kind switch at 0xCA7FDE |
| 0xCABD42 | level-up and status display |
| 0xCACBC6 | game over |
| 0xCAB3B6 | pending-sound priorities |
| 0xCA2xxx–0xCA5xxx | shared game graphics library (sprites with masks, digits, boxes) |
| 0xCA922A → descriptor 0xCA8F1E | Options: Start, Level (start level, number entry; **likely**), Highscore, Instructions (0x6E7) |

## Rules
See `docs/balloon_logic.c`.
- **Tick:** 50 ms.
- **Objects:** 12-byte records copied from templates. Balloons come in 4 designs × 3 sizes.
  Small ones are worth 30, medium 20 and large 10, and the large ones rise fastest.
- **Attachments:** about 1 balloon in 8 carries dynamite or a greeting card instead of a
  plain string.
  - Shooting dynamite gives +40 and pops everything.
  - Shooting a card gives +40 and a life (maximum 5).
  - Shooting a balloon removes what hangs under it.
- **Score changes:** a shot that hits no balloon costs 10. Each escaped balloon costs a life.
- **Levels:** 14 in the table at 0xCA926E: score thresholds 0…9100, 2–7 balloons, and a
  minimum speed divisor of 30/20/10. Thresholds count from the start level chosen in Options.
- **Quirk:** reaching level 14 (when starting from level 1) ends the game on the next tick,
  because the entry after the table has threshold 2.
- **Controls:**
  - 1–9 (except 5) aim, at double speed on a long press.
  - 5 shoots.
  - 0 pauses: the status bar (lives, score) slides down and an hourglass shows. The status
    bar is only visible while paused.

## Assets (confirmed formats)
- **Object frames:** `{u8 w, u8 h, u16 off, u16 page}` → bitmap then mask (mask 1 = transparent).
- **`FUN_ca262a` descriptors** (pause icon, HUD digits) store **height first**. The digits are
  5×7 and stored inverted.
- **Extraction:** `scripts/extract/extract_balloon.py` → `out/balloon/data.json`,
  `splash.json`, `texts.json`.
- **Port:** `port/balloon.html` loads them; with no data it has nothing to play.
  - Tested: start, aim, scoring for each kind, dynamite, card, popping and respawn, escapes,
    level-up, the end at level 15, pause with the status bar.

# Stack Attack (game id 2)

## Location (confirmed)
| Address | Role |
|---|---|
| 0xCAF8F8 | Games-menu entry. Start screen descriptor 0xCAF880 (splash picture **0xCC**); keys 0xCAF8CA (0x2C start, 0x2D/0x21 Options), create/close 0xCAF8AC |
| 0xCAF434 | start the game screen (descriptor 0xCAF496 → method table 0xCAF47E) |
| 0xCAE73A / 0xCAE9B2 / 0xCAF298 / 0xCAF372 | create / keys / tick (125 ms) / close |
| 0xCAEBAE | step. Action switch at 0xCA7FF4: 0 right, 1 jump right, 2 left, 3 jump left, 4 jump up |
| 0xCADA5E / 0xCAD29E / 0xCAD1FC | walk and push / jump / jump-up check (breaks a falling crate overhead) |
| 0xCAD68C / 0xCAD8B6 | player physics / crate physics (falling and crushing) |
| 0xCACCF0 | bottom-row clear |
| 0xCACDBE / 0xCAE618 | cranes / crate-on-head check |
| 0xCAE052 | random starting board |
| 0xCAE268 / 0xCAE1CE | draw scenery and cranes / draw a cell |
| 0xCAF574 → descriptor 0xCAF51C | Options: Start, Level (starting crane count 1–3; **likely** number entry), Highscore, Instructions (0x6E8) |

## Rules
See `docs/stack_logic.c`. `port/stack.html` is a literal translation on the firmware's own
flat grid.
- **Board:** 12×6 cells of 8 px, with row 0 at the bottom.
- **Player:** 2 cells tall. Walks and pushes single crates (4/6). Jumps up, or two columns
  over and one row up (1/2/3).
- **Cranes:** each drops a random crate in a random column, worth +2 per drop. The number of
  cranes on screen equals the "level".
- **Full bottom row:** it breaks away, scores active cranes × 10, and adds one more crane.
- **Game over:** only by being crushed: a crate falls or is dropped onto the head (anything
  else just piles up). Jumping into a crate that's still falling breaks it instead.
- **Pause:** 0 pauses and shows the hourglass and the "%d points" box. The score is shown
  nowhere else during play.

## Assets (confirmed)
- **Sprite resource block** at **0xCAF932**, read by the shared library (`FUN_ca45ac`,
  `FUN_ca493e`, `FUN_ca4536`). It has an offset table at +0x26, and its id 1 is the animation
  set. Each player state has an animation (state → frame-id list); frames are 8×16 plus a mask.
- **Cells:** ids 0x1E–0x29 are 8×8 graphics for types 2–13.
- **Cranes:** 0x2A and 0x2B are 16×16 plus a mask, claw closed and open.
- **Scenery:** 0x2C ground 4×4, 0x2D rail 8×4, 0x2E wall 4×4, 0x2F sky band 24 px wide.
- **Extraction:** `scripts/extract/extract_stack.py` → `out/stack/data.json`, `splash.json`,
  `texts.json`.
- **Port:** `port/stack.html`.
  - Tested: starting board and spawn, walk, push, jump up and land, side jump onto a crate,
    crane drop (+2) and falling (4 ticks per row), being crushed (game over and highscore),
    row clear (+10 per crane and an extra crane), and the live rendering.
  - **Unverified details:** which crane image means "carrying" (closed when carrying is my
    reading), and the sky band's height (24 rows chosen from the data; the descriptor
    holding it wasn't traced).

# All four games: ports
| Game | Port | Extractor |
|---|---|---|
| Move the Box | `port/index.html` | `scripts/extract/extract_mtb.py` |
| Wacko | `port/wacko.html` | `scripts/extract/extract_wacko.py` |
| Balloon Shooter | `port/balloon.html` | `scripts/extract/extract_balloon.py` |
| Stack Attack | `port/stack.html` | `scripts/extract/extract_stack.py` |
| Games menu | `port/games.html` (start here) | `scripts/extract/extract_games_menu.py` |

Run every extractor against the dump, then serve the repo (`python -m http.server 8765`) and
open `http://localhost:8765/port/…`.

# Games menu (launcher)
- **Descriptor 0xD1A1F0** (confirmed by reading it, `scripts/extract/extract_games_menu.py`):
  - +2 far ptr → item table 0xD1A164: five 18-byte records `{0, 0, title, title2, 0, 0, 0, 3, x}`.
  - +6 far ptr → handler table 0xD1A1BE: far pointers to JMPS trampolines that land on the game
    entry points.
  - +10 item count (5), +12 text 0x127 "End of menu". Header text list at 0xD1A20C: 0x19F "Games".
- **Order on the phone:** Stack Attack (0xCAF8F8), Balloon Shooter (0xCA8E38), Move the box
  (0xCB5074), Wacko (0xD53C96), Setup (0xCA8AF0, game id 0).
- **Output:** `out/games/menu.json` (header, titles, entry points, which port each one opens).
- **Port:** `port/games.html`.
  - Every entry is a page laid out like the games' start screens: the 101-wide picture at
    x 0, y 0, then the bottom strip with ◀ ▶ arrows and one dot per entry (the strip is my own
    addition). Soft key: left = "Select". 4/6, 2/8 or arrows browse.
  - Game pages show that game's own splash (`out/<game>/splash.json`). Selecting opens the port
    on its original start screen (`?from=games`; Move the box opens directly on its "orig" screen).
  - End on that start screen goes back to the menu, on the same page.
  - **Setup splash: my own art**, not from the firmware. It is 101×49, 1 bit, drawn by
    `games.html` itself: "SETUP" lettering, a speaker and two gears.
  - **Approximation:** Setup's real contents weren't traced. The port's Setup has a single
    Sound on/off item that switches the sound setting of all four ports at once.
