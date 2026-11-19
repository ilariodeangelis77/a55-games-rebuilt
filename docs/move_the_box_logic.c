/*
 * Move the Box (Siemens A55 SW09 LG7): cleaned-up pseudo-C of the game logic.
 *
 * Reconstructed by hand from the Ghidra decompilation of the functions named below (CPU
 * addresses in the A55 fullflash, base 0x800000). Names are mine. Confidence: "confirmed"
 * means read directly from the decompiled/disassembled code; "likely" means it was inferred
 * from context (key codes, text IDs). See NOTES.md for evidence.
 *
 * State struct S: allocated by FUN_d30f62(0x114) in FUN_cb2b2a; far pointer kept at page 0x54
 * offsets 0x0FFA/0x0FFC. Globals live in page 0x54 (CPU 0x150000 + offset).
 */

enum Tile {                     /* confirmed: loader switch, key handler, draw table 0xCB4F8E */
    BOX = 100, GOAL = 101, FLOOR = 102, WALL = 103, BOX_ON_GOAL = 104,
    PLAYER = 105,               /* neutral pose; also used while standing on a goal */
    PLAYER_UP = 106, PLAYER_DOWN = 107, PLAYER_LEFT = 108, PLAYER_RIGHT = 109,
    OUTSIDE = 110
};

struct State {                  /* offsets confirmed from accesses */
    s16 steps;                  /* +0x000  moves made in this level */
    s16 last_key;               /* +0x002  key of the last move (used for partial redraw) */
    s16 won;                    /* +0x004 */
    s16 active;                 /* +0x006  0 after win/lose: only RED and right soft accepted */
    s16 started;                /* +0x008 */
    s16 undo_ok;                /* +0x00A  one-step undo available */
    s16 sound;                  /* +0x00C  (also used as "sound on" for the push-on-goal beep) */
    s16 grid[8][8];             /* +0x00E  row stride 16 bytes; grid[0][0] = level index (quirk) */
    s16 backup[8][8];           /* +0x08E  undo copy */
    s16 nboxes;                 /* +0x10E  from level record +2 */
    s16 on_goal;                /* +0x110  player currently stands on a goal */
    s16 backup_on_goal;         /* +0x112 */
};

/* page 0x54 globals */
u8  g_level;                    /* 0x1000, persisted via FUN_d1a7a2 / read FUN_d1a78a */
s16 g_score;                    /* 0x1002, session total (sum of 200 - steps per level) */
s16 g_highscore;                /* 0x1004, persisted via FUN_d1a796 / read FUN_d1a77e */
s16 g_rotate_map;               /* 0x1006, "Rotate map" option (text 0x9F9) */

#define NLEVELS    14           /* FUN_cb1faa returns 0x0E */
#define MAX_STEPS  200
#define LEVELS     ((const u8 *)0xCB4C0C)   /* 14 records x 0x26 bytes */

/* Byte -> (cell, cell) pairs: 35-case switch in FUN_cb1fae, jump table 0xCB4F48.
 * Table extracted by scripts/extract/trace_loader_cases.py (PAIRS in extract_mtb.py). */
extern const u8 PAIRS[35][2];

/* FUN_cb1fae: load g_level into S */
void load_level(struct State *S) {
    const u8 *rec = LEVELS + g_level * 0x26;
    for (int row = 0; row < 8; row++)
        for (int i = 0; i < 4; i++) {
            u8 v = rec[5 + row * 4 + i] - 0x41;
            if (v <= 0x22) {                       /* invalid bytes leave cells untouched */
                S->grid[row][2 * i]     = PAIRS[v][0];
                S->grid[row][2 * i + 1] = PAIRS[v][1];
            }
        }
    S->grid[0][0] = g_level;                       /* quirk: drawn as the level number (FUN_cb276c) */
    S->nboxes = rec[2];                            /* rec[3], rec[4] = player row/col: unused by code */
    if (*(u16 *)rec != 0)                          /* levels 9..14 */
        transpose(S->grid);                        /* FUN_cb265c */
    place_player_sprite(S);                        /* FUN_cb26da */
}

/* FUN_cb2b2a + FUN_cb2a78: game screen created */
void game_start(struct State *S) {
    g_highscore  = read_highscore();               /* FUN_d1a77e */
    g_level      = read_level();                   /* FUN_d1a78a */
    g_rotate_map = (read_rotate_setting() == 0);   /* FUN_d1a7ba */
    S->steps = 0; S->on_goal = 0; g_score = 0; S->won = 0;
    S->active = 1; load_level(S); S->started = 1; S->undo_ok = 0;
    redraw_all(S);
}

/* Key codes (likely, Siemens x55): 0x01 left soft, 0x04 right soft, 0x0C red, 0x2A '*',
 * '2','4','6','8' = ASCII. Help text 0xA99 confirms: right-top = reset, left-top = undo. */
void on_key(struct State *S, int event, int key) {            /* FUN_cb3262 */
    if (event != 0 && event != 2) return;
    S->last_key = key;
    if (!S->active && key != 0x0C && key != 0x04) return;

    switch (key) {
    case '2': try_move(S, -1,  0, PLAYER_UP);    break;
    case '8': try_move(S, +1,  0, PLAYER_DOWN);  break;
    case '4': try_move(S,  0, -1, PLAYER_LEFT);  break;
    case '6': try_move(S,  0, +1, PLAYER_RIGHT); break;
    case 0x01:                                     /* left soft: one-step undo */
        if (S->started && S->undo_ok) undo(S);     /* FUN_cb3194 */
        redraw_all(S); break;
    case 0x04:                                     /* right soft: reset (or next level after a win) */
        if (S->started) { S->on_goal = 0; reset_level(S); }   /* FUN_cb2c7c */
        redraw_all(S); break;
    case 0x0C:                                     /* red: leave */
        S->on_goal = 0; S->active = 0; close_screen(); break;
    case '*':                                      /* toggle sound, only while active */
        toggle_sound_and_show_icon(); break;
    }
}

/* Movement: the four direction branches of FUN_cb3262 are identical apart from the offsets. */
void try_move(struct State *S, int dr, int dc, s16 face) {
    int r, c; get_player_pos(&r, &c);              /* FUN_d43538 (sprite position) */
    s16 t1 = S->grid[r + dr][c + dc];
    s16 t2 = S->grid[r + 2 * dr][c + 2 * dc];      /* no bounds check: levels are walled */
    s16 new_player, beyond = 0; int now_on_goal, box_on_goal = 0;

    if (t1 == BOX || t1 == BOX_ON_GOAL) {
        if (t2 != FLOOR && t2 != GOAL) return;     /* wall / box / outside blocks */
        beyond      = (t2 == GOAL) ? BOX_ON_GOAL : BOX;
        box_on_goal = (t2 == GOAL);
        new_player  = (t1 == BOX_ON_GOAL) ? PLAYER : face;
        now_on_goal = (t1 == BOX_ON_GOAL);
    } else if (t1 == FLOOR) { new_player = face;   now_on_goal = 0; }
    else if (t1 == GOAL)    { new_player = PLAYER; now_on_goal = 1; }
    else return;

    save_undo(S);                                  /* FUN_cb3130: copy grid + on_goal, undo_ok = 1 */
    move_player_sprite(r + dr, c + dc);            /* FUN_cb25d6 (wraps with FUN_cb2632/2646) */
    S->grid[r + dr][c + dc] = new_player;
    if (beyond) S->grid[r + 2 * dr][c + 2 * dc] = beyond;
    S->grid[r][c] = S->on_goal ? GOAL : FLOOR;
    S->on_goal = now_on_goal;
    after_move(S);                                 /* FUN_cb3210 */
    if (box_on_goal && S->sound) play_sound(0x25); /* FUN_a82494 */
}

/* FUN_cb3210 */
void after_move(struct State *S) {
    S->steps++;
    if (g_rotate_map && S->steps % 50 == 0) {      /* "Rotate map": transpose every 50 steps */
        transpose(S->grid); place_player_sprite(S); redraw_all(S);
    } else redraw_changed_cells(S);                /* FUN_cb49ea */

    int done = 0;
    for (int r = 0; r < 8; r++) for (int c = 0; c < 8; c++)
        if (S->grid[r][c] == BOX_ON_GOAL) done++;
    if (done == S->nboxes) S->won = 1;

    if (S->won || S->steps == MAX_STEPS) {
        g_score += MAX_STEPS - S->steps;           /* losing at 200 adds 0 */
        if (g_score > g_highscore) { g_highscore = g_score; save_highscore(g_highscore); }
        if (S->won) {
            g_level = (g_level < NLEVELS - 1) ? g_level + 1 : 0;   /* wraps to level 1 */
            save_level(g_level);
        }
        show_result(S);                            /* FUN_cb2e18: text 0x3D8 "You have won!\nYour score: %d"
                                                      or 0x3E2 "You have lost!\nYour score: %d"; S->active = 0 */
    }
}

/* FUN_cb3194 */
void undo(struct State *S) {
    memcpy(S->grid, S->backup, sizeof S->grid);
    S->steps--;                                    /* the undone step is refunded */
    S->on_goal = S->backup_on_goal;
    place_player_sprite(S);
    S->undo_ok = 0;                                /* only one level of undo */
}

/* FUN_cb2c7c */
void reset_level(struct State *S) {
    S->active = 1; load_level(S);                  /* g_level was already advanced after a win */
    S->steps = 0; S->won = 0; S->undo_ok = 0;      /* g_score is kept for the session */
}

/* Quirks vs. standard Sokoban
 *  - 200-move limit per level; score per level = 200 - moves; session score accumulates
 *    over consecutive levels and is the value compared with the highscore.
 *  - Only one undo step (undo refunds the move). Reset keeps the session score.
 *  - Levels 9..14 are stored transposed and flipped back by the loader.
 *  - Optional "Rotate map": the board is transposed every 50 moves (player sprite follows).
 *  - grid[0][0] is overwritten with the level index and drawn as the level number.
 *  - After the last level the game wraps to level 1.
 */
