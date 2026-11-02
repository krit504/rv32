/* port.c: Dhrystone runtime hooks. setStats(1)/setStats(0) bracket the timed loop in the original
 * source; here they open and close the MMIO measurement window, so the cycle and instruction counts
 * come from sys_monitor (this core has no readable cycle counter). printf maps to rt_vprintf;
 * debug_printf is defined (as a no-op) by the benchmark source itself. */
#include <stdarg.h>
#include "../mmio.h"
#include "../rt.h"

void setStats(int enable) {
    if (enable) perf_start(); else perf_stop();
}

int printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int r = rt_vprintf(fmt, ap);
    va_end(ap);
    return r;
}
