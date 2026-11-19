/*
 * Stack Attack (Siemens A55 SW09 LG7, game id 2): cleaned-up pseudo-C of the game logic.
 * Names are mine; addresses are the original functions. port/stack.html is a line-by-line
 * translation of the same functions onto the same flat grid, so it doubles as executable notes.
 *
 * Tick: 125 ms (FUN_cae6f2(0x7D)). Grid: 12 columns x 6 rows, row 0 = bottom, 4 bytes per cell
 * at grid[col*24 + row*4]: {s8 type, s8 xoff, s8 yoff, -}. Type 1 = player (bottom half of a
 * 2-cell figure), 2..9 = crates, 10..13 = breaking animation (10 -> 11 -> 12 -> 13 -> empty).
 * x/y offsets are pixel offsets that shrink by 2 per tick (sliding / falling animations).
 * Neighbour reads use the flat array (e.g. "row-1" of row 0 is the previous column's row 5),
 * exactly as the firmware does.
 */

struct State {                 /* 0xFE bytes (FUN_d30f62) */
    u16 counter;               /* +0x00, +1 per tick mod 65000 */
    s8  grid_ptr...;           /* +0x02 -> grid (0x120 bytes, FUN_cae052) */
    s8  col, row;              /* +0x06/+0x07 player cell */
    Bitmap *cell_bitmap[18];   /* +0x14 + 8*i: resource ids 0x1E+i (types 2..13, scenery) */
    s8  facing;                /* +0xA0: <=0 normal, >0 mirrored (moves set -1/+1, idle toggles 0/1) */
    s8  anim_prev, anim;       /* +0xA1/+0xA2: 0 walk, 1 stand, 2 crushed, 3 push, 4 jump/fall */
    s8  cooldown;              /* +0xA3: ticks until the next action */
    s8  cranes_wanted;         /* +0xA4: "level" = cranes on screen; +1 per cleared row */
    u16 score;                 /* +0xA6, capped at 65000 */
    u16 input;                 /* +0xA8: 0 right, 1 jump right, 2 left, 3 jump left, 4 jump up, 5 none */
    Crane crane[12];           /* +0xAA, 6 bytes: dir (+1 from left, -1 from right), crate type,
                                  carrying, x pos (0..112, +2/tick), target column, wait */
    u16 paused, over;          /* +0xF2/+0xF4 */
    u8  frame;                 /* +0xF6 animation frame */
};

void new_board(void) {                                 /* FUN_cae052 */
    /* 8 random columns get a crate (type 2..9) on row 0, then 4 of those get a second crate.
       Both choices shuffle a bit mask by random bit swaps (100 / 50 swaps). */
}
void game_start(State *S) {                            /* FUN_cae73a */
    new_board();
    S->col = first column whose row 1 is occupied; S->row = 2;   /* player starts on a 2-high stack */
    grid(S->col, 2).type = 1;
    S->input = 5; S->anim = S->anim_prev = 1; S->score = 0;
    S->cranes_wanted = saved_level (1..3);
    arm_timer(125);
}

void on_key(int event, int key) {                      /* FUN_cae9b2 */
    if (S->over) { if (key == RED) close(); return; }
    if (event == RELEASE) { S->input = 5; return; }
    if (S->paused && !held) { S->paused = 0; return; } /* any key resumes */
    switch (key) {
    case '6': S->input = 0; break;  case '3': S->input = 1; break;
    case '4': S->input = 2; break;  case '1': S->input = 3; break;
    case '2': S->input = 4; break;
    case '0': S->paused = 1; step(S); break;         /* hourglass + "%d points" box */
    case '*': if (event == LONG) toggle_sound(); break;
    case RED: close(); break;
    }
}

void step(State *S) {                                  /* FUN_caebae */
    if (!S->over) {
        if (S->cooldown < 1) {
            if (S->anim == 2) { save_highscore(S->score); S->over = 1; return; }   /* crushed */
            switch (S->input) {                        /* jump table 0xCA7FF4 */
            case 0: walk(-1); S->cooldown = 4; break;
            case 2: walk(+1); S->cooldown = 4; break;
            case 1: if (head_blocked_and_standing()) walk(-1); else jump(-1); S->cooldown = 8; break;
            case 3: if (head_blocked_and_standing()) walk(+1); else jump(+1); S->cooldown = 8; break;
            case 4: jump(0); S->cooldown = 2; break;
            }
        }
        if (S->anim_prev != S->anim) { S->frame = 0; set_animation(S->anim); ... }
    }
    clear_screen();
    cranes(S);                                         /* FUN_cacdbe */
    draw_scenery_and_cranes();                         /* FUN_cae268: sky band, rail, ground, wall */
    advance_animation();                               /* idle animation flips 'facing' each loop */
    draw_player(col*8 + 4 + xoff, 44 - row*8 - yoff, mirrored = facing > 0);
    for (col = 0..11) for (row = 0..5) {
        draw_cell(col, row);                           /* FUN_cae1ce, at (col*8+4+xoff, 52-row*8-yoff) */
        switch (type) {
        case 0: break;
        case 1: player_physics(col, row); break;       /* FUN_cad68c: fall 1 row when unsupported,
                                                          offsets -> 0 by 2 px/tick, lands -> stand */
        case 10: case 11: case 12: type++; break;
        case 13: type = 0; break;
        default: crate_physics(col, row); break;       /* FUN_cad8b6, below */
        }
        line_check();                                  /* FUN_caccf0 (runs after every cell) */
    }
    if (!S->over && S->cooldown > 0) S->cooldown--;
}

void walk(int p) {                                     /* FUN_cada5e; new column = col - p */
    /* - blocked by the screen edges and while still sliding;
       - if the next cell is empty: move there if standing on something (own column or the
         next one, or row 0), the cell above it is free and no crate is about to land on the
         head; the player slides in from 8 px (xoff = 8p);
       - if the next cell holds a crate: push it one column further if that cell is empty, the
         crate has nothing on top and it is not falling; both slide 8 px (push animation). */
}
void jump(int p) {                                     /* FUN_cad29e */
    /* only from rows 0..2 and when not sliding/falling:
       - p = 0: straight up one row (yoff = -8). If a crate sits right above the head it must be
         falling (yoff >= 2) and is broken (type 10) -- "jump against a falling crate";
         otherwise a crate above the head prevents the jump (FUN_cad1fc).
       - p = +-1: two columns over and one row up in one go (xoff = 16p, yoff = -8), only if
         the four cells on the way are free. */
}
void crate_physics(int c, int r) {                     /* FUN_cad8b6 */
    if (yoff == 0) {
        if (r > 1 && player is right below (rows r-1/r-2) or sliding into that spot) {
            S->anim = 2; S->cooldown = 10; type = 10;  /* crate breaks, player is crushed */
        }
        if (r > 0 && cell below empty && xoff == 0) move down one row with yoff = 8;
    } else yoff -= 2;                                  /* 4 ticks per row */
    xoff -> 0 by 2;
}
void line_check(void) {                                /* FUN_caccf0 */
    if (all 12 cells of row 0 are settled crates (2..9)) {
        S->score += active_cranes * 10;
        S->cranes_wanted++;                            /* gets harder with every row */
        row 0 -> type 10 (breaking animation), everything above falls afterwards;
    }
}
void cranes(State *S) {                                /* FUN_cacdbe */
    /* while fewer cranes than cranes_wanted are active, and every active crane has moved at
       least 21 px, a new crane starts: from the left with probability 7/12 (else right),
       crate type 2..8, random target column. Cranes move 2 px per tick; at the target
       (x == target*8 + 12 from the left, 100 - x == target*8 from the right) they drop the
       crate into row 5 if row 4 is free there (+2 points). A crate dropped straight onto the
       player's head (FUN_cae618) crushes him. Cranes leave the screen at x = 112. */
}
/* Game over only happens by being crushed; there is no "stack too high" loss. */
