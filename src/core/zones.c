/* Time zones the user can choose as home (see zones.h). Order: from Greenwich eastwards to Sydney, then from
 * Honolulu eastwards to Rio; ZONE_* in zones.h are indices into this table. */
#include "zones.h"
#include "wctime.h"

const struct wc_zone wc_zones[] = {
    {"UTC", 0, DST_NONE},
    {"LONDON", 0, DST_EU},
    {"PRAGUE", 60, DST_EU},
    {"HELSINKI", 120, DST_EU},
    {"S.AFRICA", 120, DST_NONE},
    {"MOSCOW", 180, DST_NONE},
    {"DUBAI", 240, DST_NONE},
    {"DELHI", 330, DST_NONE},
    {"PEKIN", 480, DST_NONE},
    {"TOKYO", 540, DST_NONE},
    {"SYDNEY", 600, DST_AU},
    {"HONOLULU", -600, DST_NONE},
    {"L.ANGELES", -480, DST_US},
    {"DENVER", -420, DST_US},
    {"CHICAGO", -360, DST_US},
    {"NEW YORK", -300, DST_US},
    {"RIO", -180, DST_NONE},
};

const uint8_t wc_zone_count = sizeof(wc_zones) / sizeof(wc_zones[0]);
