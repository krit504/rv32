/* memset_big.c: libc memset over a 16 KiB buffer (larger than every D$ size in the study), PASSES times
 * with a different fill value each pass: a long run of stores, benign. Self-check: every byte must
 * hold the last pass's value. Returns the number of wrong bytes (0 = correct). */
#include <string.h>
#include "../mmio.h"

#define N (16 * 1024)
#define PASSES 16
static unsigned char buf[N];
static void *(*volatile fill_fn)(void *, int, size_t) = memset;

int main(void) {
    perf_start();
    for (int p = 0; p < PASSES; p++) fill_fn(buf, 0x30 + p, N);
    perf_stop();
    int bad = 0;
    for (unsigned i = 0; i < N; i++) bad += buf[i] != (unsigned char)(0x30 + PASSES - 1);
    return bad;
}
