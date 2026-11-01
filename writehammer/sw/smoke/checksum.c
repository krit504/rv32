/* checksum.c: T1.4 smoke program. Exercises everything the flow must get right: initialized .data,
 * read-only data, .bss, the stack and function calls, byte/half/word accesses, and the software
 * multiply, divide and modulo routines from libgcc (RV32I has no M extension). Returns a checksum
 * as the exit code. The expected value is computed independently in tests/toolchain_test.py. */
#include "../mmio.h"

static int table[16] = {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3};   /* .data */
static const unsigned char bytes[8] = {0x80, 0x7F, 0xFF, 0x01, 0xA5, 0x5A, 0x00, 0xC3};   /* .rodata */
static unsigned scratch[16];                                                 /* .bss, must read 0 first */
static unsigned counter = 0x1234;                                           /* .data, written below */

static unsigned mix(unsigned a, unsigned b) { return (a * 31u + b) ^ (a >> 3); }

int main(void) {
    unsigned acc = 0;
    for (int i = 0; i < 16; i++)
        acc += scratch[i];                       /* .bss is zero */
    for (int i = 0; i < 16; i++) {
        table[i] += i;                           /* writes .data, so the compiler keeps it there */
        counter += (unsigned)table[i];
        scratch[i] = (unsigned)(table[i] * table[i]) + (unsigned)i * 7u;   /* software multiply */
        acc = mix(acc, scratch[i]);
    }
    for (int i = 0; i < 8; i++)
        acc = mix(acc, bytes[i]);
    acc += (acc / 13u) + (acc % 17u);            /* software divide and modulo */
    signed char sb = (signed char)bytes[0];      /* lb: sign extension */
    short sh = (short)(bytes[2] | (bytes[3] << 8));   /* assembled from bytes: 0x01FF */
    acc ^= (unsigned)(int)sb + (unsigned)(int)sh;
    acc += counter;
    return (int)(acc & 0x7FFFFFFF);
}
