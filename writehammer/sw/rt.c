/* rt.c: minimal printf for bare metal (no libc stdio): %d %i %u %x %X %c %s %ld %lu %lx %%, with
 * optional zero pad and width. Output goes to the MMIO PUTCHAR register (sys_monitor prints it). */
#include <stdarg.h>
#include "mmio.h"
#include "rt.h"

static void put_num(unsigned long v, unsigned base, int neg, int width, char pad, int upper) {
    char buf[24];
    int n = 0;
    do { unsigned d = (unsigned)(v % base); buf[n++] = (char)(d < 10 ? '0' + d : (upper ? 'A' : 'a') + d - 10); v /= base; } while (v);
    if (neg) buf[n++] = '-';
    for (int i = n; i < width; i++) putch(pad);
    while (n) putch(buf[--n]);
}

int rt_vprintf(const char *fmt, va_list ap) {
    for (; *fmt; fmt++) {
        if (*fmt != '%') { putch(*fmt); continue; }
        fmt++;
        char pad = ' ';
        int width = 0, lng = 0;
        if (*fmt == '0') { pad = '0'; fmt++; }
        while (*fmt >= '0' && *fmt <= '9') width = width * 10 + (*fmt++ - '0');
        while (*fmt == 'l') { lng = 1; fmt++; }
        switch (*fmt) {
        case 'd': case 'i': {
            long v = lng ? va_arg(ap, long) : va_arg(ap, int);
            put_num(v < 0 ? -(unsigned long)v : (unsigned long)v, 10, v < 0, width, pad, 0);
            break; }
        case 'u': put_num(lng ? va_arg(ap, unsigned long) : va_arg(ap, unsigned), 10, 0, width, pad, 0); break;
        case 'x': put_num(lng ? va_arg(ap, unsigned long) : va_arg(ap, unsigned), 16, 0, width, pad, 0); break;
        case 'X': put_num(lng ? va_arg(ap, unsigned long) : va_arg(ap, unsigned), 16, 0, width, pad, 1); break;
        case 'c': putch((char)va_arg(ap, int)); break;
        case 's': { const char *s = va_arg(ap, const char *); while (*s) putch(*s++); break; }
        case '%': putch('%'); break;
        default: putch('?'); break;
        }
    }
    return 0;
}

int rt_printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int r = rt_vprintf(fmt, ap);
    va_end(ap);
    return r;
}
