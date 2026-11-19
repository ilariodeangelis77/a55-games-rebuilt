/*
 * Balloon Shooter (Siemens A55 SW09 LG7, game id 1): cleaned-up pseudo-C of the game logic.
 * Reconstructed from the Ghidra decompilation of the functions named below; names are mine.
 * State: 0x88 bytes (FUN_d30f62), pointer at page 0x54 0x0FD4. Tick = 50 ms (FUN_cac340
 * converts ms with *1300/6/1000 into 4.615 ms timer units).
 */

struct Obj {                    /* 12 bytes, copied from a template (FUN_cab4b4) */
    s8 x, y;                    /* centre */
    s8 dx, dy;
    u8 nframes, frame;
    u8 kind;                    /* low nibble: 0/1/2 balloon size, 3/4/5 popping, 6 crosshair,
                                   7 banner, 9 dynamite, 0xA greeting card, 0xB string;
                                   high nibble 1..4 = balloon design */
    u8 speed;                   /* moves when (counter*50) % speed == 0 */
    Frame **frames;             /* {u8 w, u8 h, u16 off, u16 page} -> bitmap then mask */
};
struct State {
    Obj *slot[5][6];            /* rows 0..2 balloons + attachments, row 3 crosshair, row 4 banner */
    u16 counter;                /* +0x78, +1 per tick, mod 1024 */
    s16 score;                  /* +0x7A */
    s8  lives;                  /* +0x7C, starts at 5, max 5 */
    s8  level;                  /* +0x7D = start_level + 1 */
    s8  cx, cy, vx, vy, mul;    /* +0x7E.. crosshair position/velocity, mul 1 or 2 (long press) */
    u8  paused;                 /* +0x83 */
    u16 pending_sound;          /* +0x84 */
    u8  over;                   /* +0x86 */
};
/* LEVEL[i] at 0xCA926E: {variety, threshold, balloons, min_speed}; i = level-1; entry 14 is
   past the table's end in effect ({0, 2, 2, 7}) and is read too (see level_check). */

int rnd(int n) { return (rand16() * n) >> 16; }        /* FUN_ca3d32: 0..n-1 */

void game_start(State *S) {                            /* FUN_cac3c0 */
    S->start = saved_start_level;                      /* 0..13 (stored inverted in the settings) */
    S->level = S->start + 1; S->score = 0; S->lives = 5;
    S->cx = 50; S->cy = 32; S->vx = S->vy = 0; S->mul = 1;
    add(4, BANNER_TEMPLATE /*0xCA93B4*/, 0, -11);      /* status bar, hidden above the screen */
    add(3, CROSSHAIR_TEMPLATE /*0xCA931C*/, 50, 40);
    spawn(S, LEVEL[S->level - 1].balloons);
    level_check(S);
    arm_timer(50 /* ms */);
}

void spawn(State *S, int n) {                          /* FUN_cab6ac */
    while (n--) {
        int row = 0;
        while (row < 3 && count(row) > 4) row++;       /* each row: up to 3 balloons + attachments */
        if (count(row) > 4) return;
        int yoff = rnd(10), x = rnd(0x5C) + 4;
        int V = LEVEL[S->level - 1].variety;           /* 1..3 */
        int t = (rnd(4 * V) * 3) / V + 3 - V;          /* template 0..11 (4 designs x 3 sizes) */
        Obj *b = add(row, BALLOON[t] /*0xCAB336*/, x, yoff + 71);
        while (b->speed < LEVEL[S->level - 1].min_speed) b->speed += 10;
        int k = (rnd(8) == 1) ? rnd(2) * 3 : 6;        /* 1/8: 0 dynamite or 3 card; else 6 string */
        int size = b->kind & 0xF;
        Obj *a = add(row, ATTACH[size][k / 3] /*0xCAB366/6A/6E*/, x, yoff + 71 + (8, 12, 16)[size]);
        a->speed = b->speed;
    }
}

void on_tick(State *S) {                               /* FUN_cac9ba */
    if (!S->paused) {
        if (banner->y > -11) banner->y--;              /* status bar slides away */
        cleanup(S);                                    /* FUN_cabc0e */
        move_and_animate(S);                           /* FUN_caba8c */
        redraw();
        if (!S->over) level_check(S); else draw_score_box(S);   /* "%d points", blinks on record */
        play(S->pending_sound); S->pending_sound = 0;
    } else {
        if (banner->y < 0) banner->y++;                /* status bar: lives + "Score:" + 4 digits */
        redraw(); level_check(S);
        draw_hourglass(44, 27, (S->counter & 7) >> 2); /* 21x13 icon + 2 blinking sand dots */
    }
    S->counter = (S->counter + 1) & 0x3FF;
    arm_timer(50);
}

void cleanup(State *S) {                               /* FUN_cabc0e */
    int respawn = 0;
    for (each obj o in rows 0..2) {
        int k = o->kind & 0xF;
        if (k < 3 || k > 5) {
            if ((o->y < -10 && !S->over) || (o->y < -15 && S->over)) {
                remove(o);
                if (k != 9 && k != 10 && k != 11) {    /* a balloon escaped */
                    if (S->lives != 0 || S->over) { S->lives--; respawn++; }
                    else { game_over(S); return; }
                }
            }
        } else if (o->nframes == o->frame + 1) {        /* pop animation finished */
            remove(o); respawn++;
        }
    }
    spawn(S, respawn);
}

void move_and_animate(State *S) {                      /* FUN_caba8c */
    for (each obj o in rows 0..2) {
        int k = o->kind & 0xF;
        if (k < 3 || k > 5) {
            if ((u16)(S->counter * 50) % o->speed != 0) continue;   /* no move, no animation */
            o->x += o->dx; o->y += o->dy;
        }
        o->frame = (o->frame + 1) % o->nframes;
    }
    S->cx += S->vx; S->cy += S->vy;                    /* wraps: x 0..100, y 0..63 */
    if (S->cx < 0) S->cx = 100; if (S->cx > 100) S->cx = 0;
    if (S->cy < 0) S->cy = 63;  if (S->cy > 63)  S->cy = 0;
}

void level_check(State *S) {                           /* FUN_cabd42 */
    if (S->score < 0 || S->score > 9999) return;
    if (S->score >= LEVEL[S->level - S->start].threshold) {        /* relative to the start level */
        int diff = LEVEL[S->level].balloons - LEVEL[S->level - 1].balloons;
        if (diff < 0) { remove_all_balloons(); spawn(S, LEVEL[S->level].balloons); }
        else spawn(S, diff);
        want_sound(0x59); S->level++;
    }
    if (S->level > 14 || S->lives == 0) game_over(S);
    else draw_hud(lives at x=4, score 4 digits at x=76, y = banner->y + 1);
}
/* Quirk: starting at level 1, reaching level 14 reads the threshold of entry 14 (= 2),
   so the next tick goes to level 15 and the game ends ("won"). */

void shoot(State *S) {                                 /* FUN_cac016, key '5' (press only) */
    want_sound(0x5E);
    int hit = 0, removed = 0;
    for (each obj o in rows 0..2 whose box contains (cx, cy)) {   /* box centred, FUN_cabf0c */
        switch (o->kind & 0xF) {
        case 0: S->score += 30; hit = 1; break;
        case 1: S->score += 20; hit = 1; break;
        case 2: S->score += 10; hit = 1; break;
        case 3: case 4: case 5: continue;              /* already popping */
        case 9:                                        /* dynamite */
            S->score += 40;
            for (each obj p in rows 0..2) if (!start_pop(p)) remove(p);
            want_sound(0x55); vibrate(4);
            return;                                    /* no miss penalty, no respawn here */
        case 10:                                       /* greeting card */
            S->score += 40; if (S->lives < 5) S->lives++; want_sound(0x54); break;
        default: S->score += 10; break;                /* string and anything else */
        }
        remove_attachments_below(o);                   /* same x, y == o->y + frame height */
        if ((o->kind & 0xF0) >= 0x10 && (o->kind & 0xF0) <= 0x40) { start_pop(o); want_sound(0x61); }
        else { remove(o); if (hit) removed++; }
    }
    if (!hit) S->score -= 10;
    if (S->score < 0) S->score = 0;
    spawn(S, removed);
}

int start_pop(Obj *o) {                                /* FUN_cabf90 */
    int k = o->kind & 0xF;
    if (k > 2) return 0;
    o->frames = POP[k] /*0xCAB38A*/; o->dy = 0; o->frame = 0; o->kind += 3; o->speed = 10;
    return 1;
}

void game_over(State *S) {                             /* FUN_cacbc6 */
    if (S->over) { close_game(); return; }
    S->over = 1; want_sound(0x56);
    if (S->score > highscore) { highscore = S->score; new_record = 1; }
    remove_crosshair();
    int n = objects_in_rows_0_to_2();
    if (6 - n / 2 > 1) spawn(S, 5 - n / 2);            /* a few balloons float up behind the score */
}

void on_key(State *S, int event /*0 press, 1 release, 2 long*/, int key) {   /* FUN_cac508 */
    if (S->over) { if (key == 0x0C && event == 0) game_over(S) /* -> close */; return; }
    if (event == 1) { S->vx = S->vy = 0; S->mul = 1; return; }
    if (event == 2) S->mul = 2;
    if (S->paused && key != '0') S->paused = 0;        /* any key resumes */
    switch (key) {
    case '1': vx = -mul; vy = -mul; break;   case '2': vx = 0;    vy = -mul; break;
    case '3': vx = +mul; vy = -mul; break;   case '4': vx = -mul; vy = 0;    break;
    case '6': vx = +mul; vy = 0;    break;   case '7': vx = -mul; vy = +mul; break;
    case '8': vx = 0;    vy = +mul; break;   case '9': vx = +mul; vy = +mul; break;
    case '5': if (event == 0) shoot(S); break;
    case '0': S->paused = !S->paused; break;           /* shows the status bar */
    case '*': if (event == 2) toggle_sound_with_message(); break;
    case 0x0C: close_game(); break;
    }
}
/* Sounds: one pending slot, priority 0x56 game over > 0x59 level > 0x54 card > 0x55 dynamite
   > 0x61 pop > 0x5E shot (FUN_cab3b6). */
