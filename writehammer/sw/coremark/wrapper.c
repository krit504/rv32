/* wrapper.c: the program's real main for the CoreMark build, plus printf for CoreMark's output.
 *
 * CoreMark's own main is renamed coremark_main by the port header (core_main.c only). It returns a
 * constant, and its internal error count always includes one error for "Must execute for at least 10
 * secs": this core has no clock, so the run is bounded by a fixed ITERATIONS and the rate is computed
 * outside from the MMIO measurement window's cycle count. So the exit code is built from CoreMark's
 * own CRC checks instead: CoreMark compares the list, matrix and state CRCs with its known values for
 * this seed and size and prints "[%u]ERROR! ... crc ... - should be ..." on a mismatch. printf below
 * counts those messages; main returns the count (0 = all CRCs matched).
 * tests/bench_test.py additionally requires every CRC line to be present and equal to a native run.
 */
#include <stdarg.h>
#include "../rt.h"

int coremark_main(void);

static int crc_errors;

int printf(const char *fmt, ...) {
    if (fmt[0] == '[' && fmt[1] == '%')                       /* "[%u]ERROR! list crc 0x%04x - ..." */
        for (const char *p = fmt; *p; p++)
            if (p[0] == 'E' && p[1] == 'R' && p[2] == 'R' && p[3] == 'O' && p[4] == 'R') { crc_errors++; break; }
    va_list ap;
    va_start(ap, fmt);
    int r = rt_vprintf(fmt, ap);
    va_end(ap);
    return r;
}

int main(void) {
    coremark_main();
    return crc_errors;
}
