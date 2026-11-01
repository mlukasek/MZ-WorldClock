/* Own glyphs in the CG-RAM of the MZ-800 in MZ-700 mode (data/glyphs.txt): the hiragana of the title and
 * the half cell of the seconds bar. */
#ifndef WC_CGRAM_H
#define WC_CGRAM_H

void cgram_load(void);       /* write the glyphs over their codes */
void cgram_restore(void);    /* the CG-RAM again a copy of the CG-ROM (as the IPL makes it) */

#endif
