/*
 * Wacko (Siemens A55 SW09 LG7, game id 8): cleaned-up pseudo-C of the game logic.
 * Reconstructed from the Ghidra decompilation of the functions named below; names are mine.
 * State struct S (0x40 bytes, FUN_d30f62) is kept at page 0x54 offsets 0x385E/0x3860.
 */

struct State {
    s16 _0, _2;
    s16 hits;          /* +0x04  wackos hit */
    s16 over;          /* +0x06  game over */
    s16 shown;         /* +0x08  wackos spawned (rate denominator) */
    s16 rabbits;       /* +0x0A  rabbits hit */
    u32 time_left;     /* +0x0C  45000 / 65000 / 110000, -200 per tick */
    s16 score;         /* +0x10 */
    u8  rate;          /* +0x12  percent, set at game over */
    u16 tick_units;    /* +0x14  52 / 26 / 13 by level (FUN_d520da) */
    s16 hold[9];       /* +0x18  per-hole timers */
    s8  hole[9];       /* +0x2A  per-hole state, index = row*3 + col */
    s16 sound;         /* +0x34 */
    /* +0x38.. sprite layers: one per column (x = 24*c, y = c==1 ? 2 : 0, 3 cells of 24x18),
       +0x3E: level-icon layer at (85,25) 10x10 */
};
extern u8  g_level;        /* 1..3, persisted (FUN_d1a832 / FUN_d1a826) */
extern u16 g_best_score;   /* persisted (FUN_d1a7f6 / FUN_d1a80e) */
extern u8  g_best_rate;    /* persisted (FUN_d1a802 / FUN_d1a81a), <= 100 */

/* random(n): FUN_beb128 -> 0..n inclusive (random(2) selects one of 3 rows) — likely */

/* Hole states:
 *  1  wacko hit (3 ticks) -> 2        10 rabbit hit (3 ticks) -> 11
 *  2  empty                           11 empty (after a rabbit)
 *  3,4,5 rising, 6 up (holds hold[i] ticks), 7,8 sinking, 9 -> 2
 *  12,13,14 rising, 15 up (holds), 16,17 sinking, 18 -> 11
 */

void game_start(struct State *S) {                     /* FUN_d528cc */
    for (int i = 0; i < 9; i++) { S->hole[i] = 2; S->hold[i] = 1; }
    static const s16 hold0[3] = {6, 4, 5};
    for (int c = 0; c < 3; c++) {                      /* one wacko fully up per column */
        int r = random(2);
        S->hole[r * 3 + c] = 6; S->hold[r * 3 + c] = hold0[c];
    }
    S->over = S->shown = S->hits = S->score = S->rate = S->rabbits = 0;   /* the 3 above are not "shown" */
    S->time_left = (g_level == 1) ? 45000 : (g_level == 2) ? 65000 : 110000;
    S->tick_units = (g_level == 1) ? 52 : (g_level == 2) ? 26 : 13;
    draw_level_icon(g_level);
    redraw_all(S);
    arm_tick_timer(S->tick_units);                     /* one-shot; re-armed every tick */
}

void on_tick(struct State *S) {                        /* FUN_d53488 */
    if (message_timer_running()) return;               /* '*' sound message pauses the game (1.5 s) */
    S->time_left -= 200;
    if ((s32)S->time_left > 0) { step(S); redraw_all(S); arm_tick_timer(S->tick_units); return; }
    S->over = 1;
    S->rate = min(100, S->hits * 100 / S->shown);      /* no check for shown == 0 */
    if (S->score > g_best_score) g_best_score = S->score;
    if (S->rate  > g_best_rate)  g_best_rate  = S->rate;
    save_best_rate(g_best_rate); save_best_score(g_best_score);
    show_result(S);                                    /* FUN_d52e70: text 0x3D7, zero-padded 4/3/4/4 digits */
}

void step(struct State *S) {                           /* FUN_d5217e(0, ...) */
    int busy = 0;
    for (int i = 0; i < 9; i++) {
        s8 *s = &S->hole[i];
        if (*s == 1)  { if (S->hold[i] < 1) *s = 2;  else S->hold[i]--; }
        if (*s == 10) { if (S->hold[i] < 1) *s = 11; else S->hold[i]--; }
        if (*s > 2 && *s < 10) {
            busy++;
            if (*s == 6) { if (S->hold[i] < 1) (*s)++; else S->hold[i]--; }
            else if (*s < 9) (*s)++;
            if (*s == 9) *s = 2;
        }
        if (*s > 11 && *s < 19) {
            busy++;
            if (*s == 15) { if (S->hold[i] < 1) (*s)++; else S->hold[i]--; }
            else if (*s < 18) (*s)++;
            if (*s == 18) *s = 11;
        }
    }
    while (busy < random(3) + 1) {                     /* re-rolled every iteration */
        int i = random(2) * 3 + random(2);
        int roll = random(100);
        if (S->hole[i] == 2 || S->hole[i] == 11) {
            if (roll < 21) S->hole[i] = 12;            /* rabbit, ~21/101 */
            else { S->hole[i] = 3; S->shown++; }
            S->hold[i] = random(5) + 4;                /* 4..9 ticks up */
            busy++;
        }
    }
}

/* keys '1'..'9' -> (row, col) = ((k-1)/3, (k-1)%3) */
void on_key(struct State *S, int event, int key) {     /* FUN_d530ee */
    if (S->over) { if (key == 0x04 || key == 0x0C) close_game(); return; }
    if (key >= '1' && key <= '9') {
        int r = (key - '1') / 3, c = (key - '1') % 3;
        if (try_hit(S, r, c)) { hit_anim(S, r, c); redraw_cell(S, r, c); }
    } else if (key == 0x0C) close_game();
    else if (key == '*' && event == 2 /* long press */) toggle_sound_with_message();
}

int try_hit(struct State *S, int r, int c) {          /* FUN_d52734 + FUN_d527da */
    s8 s = S->hole[r * 3 + c];
    if (s < 12) {
        if (s < 3 || s > 9) return 0;                  /* empty or already hit: nothing */
        static const u8 k[7] = {14, 12, 10, 8, 6, 4, 2};   /* earlier = more points */
        S->score += k[s - 3] * g_level;
        S->hits++;
    } else {                                           /* any rabbit state */
        S->score = max(0, S->score - 10);
        S->rabbits++;
    }
    return 1;
}

void hit_anim(struct State *S, int r, int c) {         /* FUN_d5217e(1, r, c) */
    int i = r * 3 + c;
    if (S->hole[i] < 10) { S->hole[i] = 1;  if (S->sound) play_sound(0x25); }
    else                 { S->hole[i] = 10; if (S->sound) play_sound(0x01); }
    S->hold[i] = 3;
}
