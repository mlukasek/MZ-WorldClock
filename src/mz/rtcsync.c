/* The clock from the Unicard RTC (see rtcsync.h).
 *
 * The card gives whole seconds. At the start the program waits for the card's second to change and sets the
 * clock at that edge (a fraction of a millisecond); if it does not change within 2 s of the machine's own
 * clock (the emulated card follows the host's clock, not the emulated time), the read time is taken as it is.
 * Every 10 minutes it reads the card once per frame until the second changes and sets the clock again (one
 * frame of precision), so the crystal of the machine never drifts away from the card. When the user sets the time by hand, it is written to the card; if the card
 * does not take it (the emulated Unicard does not implement setting), the card is no longer followed. */
#include "rtcsync.h"
#include "rtc_unicard.h"
#include "timebase.h"
#include "zones.h"

#define SYNC_EVERY 600               /* seconds */
#define SYNC_FRAMES 150              /* give up a sync after 3 s without a change of the card's second */

uint8_t rtc_present;
static uint8_t follow;               /* the card is the time source */
static wc_time_t next_sync;
static uint8_t sync_sec, sync_frames, syncing;

static wc_time_t to_utc(struct wc_tm *tm, uint8_t zone)
{
    return wc_to_utc(wc_make(tm), wc_zones[zone].std_minutes, wc_zones[zone].dst);
}

uint8_t rtc_start(uint8_t zone)
{
    struct wc_tm tm;
    uint8_t sec;
    uint16_t frac;
    wc_time_t t0;

    if (!rtc_present || !rtc_read(&tm))
        return 0;
    sec = tm.sec;
    t0 = clock_now(&frac);
    do {                             /* to the edge of the card's second, at most 2 s of our own clock */
        if (!rtc_read(&tm))
            return 0;
    } while (tm.sec == sec && clock_now(&frac) - t0 < 2);
    clock_set(to_utc(&tm, zone));
    follow = 1;
    syncing = 0;
    next_sync = to_utc(&tm, zone) + SYNC_EVERY;
    return 1;
}

void rtc_poll(wc_time_t now, uint8_t zone)
{
    struct wc_tm tm;

    if (!follow || now < next_sync)
        return;
    if (!rtc_read(&tm)) {
        syncing = 0;
        next_sync = now + SYNC_EVERY;
        return;
    }
    if (!syncing) {
        syncing = 1;
        sync_sec = tm.sec;
        sync_frames = 0;
    } else if (tm.sec != sync_sec) {
        syncing = 0;
        clock_set(to_utc(&tm, zone));
        next_sync = to_utc(&tm, zone) + SYNC_EVERY;
    } else if (++sync_frames > SYNC_FRAMES) {
        syncing = 0;
        next_sync = now + SYNC_EVERY;
    }
}

void rtc_manual_set(uint8_t zone)
{
    struct wc_tm tm;
    uint16_t frac;
    wc_time_t now;

    if (!rtc_present)
        return;
    now = clock_now(&frac);
    wc_split(wc_to_local(now, wc_zones[zone].std_minutes, wc_zones[zone].dst), &tm);
    follow = rtc_write(&tm);
    syncing = 0;
    next_sync = now + SYNC_EVERY;
}
