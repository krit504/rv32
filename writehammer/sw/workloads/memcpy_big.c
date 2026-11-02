/* memcpy_big.c: libc memcpy over 16 KiB buffers, larger than every D$ size in the study (up to 8 KiB),
 * repeated PASSES times (benign sequential load+store stream). Self-check: the destination must equal
 * the pattern computed on the fly (independent of the source array and of memcpy). Returns the number
 * of wrong bytes (0 = correct). */
#include <string.h>
#include "../mmio.h"

#define N (16 * 1024)
#define PASSES 8
static unsigned char src[N], dst[N];
static void *(*volatile copy_fn)(void *, const void *, size_t) = memcpy;   /* keep the call, no inlining */

static unsigned char pat(unsigned i) { return (unsigned char)(i * 31u + 7u); }

int main(void) {
    for (unsigned i = 0; i < N; i++) src[i] = pat(i);
    perf_start();
    for (int p = 0; p < PASSES; p++) copy_fn(dst, src, N);
    perf_stop();
    int bad = 0;
    for (unsigned i = 0; i < N; i++) bad += dst[i] != pat(i);
    return bad;
}
