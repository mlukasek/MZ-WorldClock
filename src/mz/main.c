/* MZ-WorldClock for the Sharp MZ-700 (EU, JP), MZ-800 and MZ-1500: main loop.
 *
 * Start: detect the machine, start the time base, get the time (the test hook, the Unicard RTC or the
 * dialog), then the historic screen with the keys under it for a few seconds, one pass per frame. The keys
 * (the letters of the first version still work):
 *   SPACE (M)    swap the continents (Americas on the left), the historic look and the map
 *   <- -> (G)    the MZ-800's looks round: historic, map, digital clock, analog clock (each through black)
 *   CR (T)       set the date, the time and the home zone
 *   BREAK        back to the monitor with its clock set */
#include "machine.h"
#include "timebase.h"
#include "kbd.h"
#include "histview.h"
#include "setup.h"
#include "zones.h"
#include "wctime.h"
#include "rtcsync.h"
#include "rtc_unicard.h"
#include "cgram.h"
#include "pcg1500.h"
#include "modview.h"
#include "clockview.h"
#include "gfx800.h"

#define LOOK_HISTORIC 0
#define LOOK_MAP 1
#define LOOK_DIGITAL 2
#define LOOK_ANALOG 3

static uint8_t home;
static uint8_t look;                 /* LOOK_...; only the MZ-800 leaves the historic one */

/* Back to the text screen of MZ-700 mode (from the MZ-800 mode: a black screen, its CG-RAM rebuilt) */
static void look_text(void)
{
    if (look != LOOK_HISTORIC) {
        gfx_end();
        cgram_restore();
        cgram_load();
    }
}

/* Draw the current look and view from scratch */
static void look_draw(wc_time_t utc)
{
    if (look == LOOK_MAP)
        mod_enter(home, hist_view, utc);
    else if (look != LOOK_HISTORIC)
        clk_enter(look == LOOK_ANALOG, home, utc);
    else
        hist_draw();
}

int main(void)
{
    wc_time_t now;
    uint16_t hint;
    uint16_t frac;
    uint8_t key;
    uint32_t local_secs = 0;
    struct wc_tm tm;

    machine_init();
    tb_init(mach.line_hz);
    if (mach.model == MODEL_MZ800) {
        cgram_load();                /* the hiragana title and the half cell of the bar */
        hist_hiragana = 1;
        hist_half = hist_half_cgram;
    } else if (mach.model == MODEL_MZ1500) {
        pcg_init();                  /* the half cell of the bar */
        hist_half = pcg_half;
    }
    home = mach.jp ? ZONE_TOKYO : ZONE_PRAGUE;

    rtc_present = rtc_detect();
    if (test_hook.flags & TEST_TIME_VALID) {
        clock_set(test_hook.utc);
    } else {
        if (rtc_present)
            hist_draw();             /* the screen while the card's second is awaited */
        if (!rtc_start(home) && !setup_run(&home, 0))
            goto out;
    }

    hist_draw();
    hist_hint(1);
    hint = HINT_FRAMES;
    if (mach.model == MODEL_MZ800)
        mod_prepare(home);           /* the modern look (G) comes up faster */
    for (;;) {
        tb_wait_frame();
        now = clock_now(&frac);
        if (look == LOOK_MAP)
            mod_update(now);
        else if (look != LOOK_HISTORIC)
            clk_update(now);
        else
            hist_update(now, frac < tb_line_hz / 2);
        rtc_poll(now, home);
        if (hint && !--hint && look == LOOK_HISTORIC)
            hist_hint(0);
        key = kbd_get();
        if (key == K_BREAK)
            break;
        if (key == 'T' || key == K_CR) {
            look_text();
            setup_run(&home, 1);
            look_draw(clock_now(&frac));
        } else if ((key == 'M' || key == ' ') && look <= LOOK_MAP) {
            hist_view ^= 1;
            look_draw(now);
        } else if ((key == 'G' || key == K_RIGHT || key == K_LEFT) && mach.model == MODEL_MZ800) {
            key = (key == K_LEFT ? look - 1 : look + 1) & 3;
            if (key == LOOK_HISTORIC)
                look_text();         /* the other changes go from black to black in gfx_begin */
            look = key;
            look_draw(now);
        }
    }
    look_text();
    now = clock_now(&frac);
    wc_split(wc_to_local(now, wc_zones[home].std_minutes, wc_zones[home].dst), &tm);
    local_secs = (uint32_t)tm.hour * 3600 + (uint16_t)(tm.min * 60 + tm.sec);
out:
    kbd_wait_release();          /* the monitor must not see the BREAK */
    machine_exit(local_secs);
    return 0;
}
