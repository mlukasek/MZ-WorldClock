/* MZ-WorldClock for the Sharp MZ-700 (EU, JP) and MZ-800: main loop.
 *
 * Start: detect the machine, start the time base, get the time (test hook or the dialog), then the historic
 * screen, one pass per frame. T sets the time again, BREAK returns to the monitor with its clock set. */
#include "machine.h"
#include "timebase.h"
#include "kbd.h"
#include "histview.h"
#include "setup.h"
#include "zones.h"
#include "wctime.h"

static uint8_t home;

int main(void)
{
    wc_time_t now;
    uint16_t frac;
    uint8_t key;
    uint32_t local_secs = 0;
    struct wc_tm tm;

    machine_init();
    tb_init(mach.line_hz);
    home = mach.jp ? ZONE_TOKYO : ZONE_PRAGUE;

    if (test_hook.flags & TEST_TIME_VALID)
        clock_set(test_hook.utc);
    else if (!setup_run(&home, 0))
        goto out;

    hist_draw();
    for (;;) {
        tb_wait_frame();
        now = clock_now(&frac);
        hist_update(now, frac < tb_line_hz / 2);
        key = kbd_get();
        if (key == K_BREAK)
            break;
        if (key == 'T') {
            setup_run(&home, 1);
            hist_draw();
        }
    }
    now = clock_now(&frac);
    wc_split(wc_to_local(now, wc_zones[home].std_minutes, wc_zones[home].dst), &tm);
    local_secs = (uint32_t)tm.hour * 3600 + (uint16_t)(tm.min * 60 + tm.sec);
out:
    kbd_wait_release();          /* the monitor must not see the BREAK */
    machine_exit(local_secs);
    return 0;
}
