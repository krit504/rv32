/* rt.h: tiny runtime for the benchmarks: formatted output over the MMIO PUTCHAR register. */
#ifndef RT_H
#define RT_H
#include <stdarg.h>
int rt_printf(const char *fmt, ...);
int rt_vprintf(const char *fmt, va_list ap);
#endif
