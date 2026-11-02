/* storeloop.c: a store-heavy loop: ROUNDS sequential sweeps writing one word per element of a 16 KiB
 * array (every store is to a different word than the previous one, spread over the whole array, so
 * it concentrates nothing on one line). Benign by design: it is what the detectors must NOT flag
 * as an attack. Self-check: after the last sweep, element i holds (ROUNDS-1)*WORDS + i (closed form,
 * independent of the loop). Returns the number of wrong words (0 = correct). */
#include "../mmio.h"

#define WORDS (4 * 1024)
#define ROUNDS 32
static volatile unsigned a[WORDS];

int main(void) {
    perf_start();
    for (unsigned r = 0; r < ROUNDS; r++)
        for (unsigned i = 0; i < WORDS; i++)
            a[i] = r * WORDS + i;
    perf_stop();
    int bad = 0;
    for (unsigned i = 0; i < WORDS; i++) bad += a[i] != (ROUNDS - 1) * WORDS + i;
    return bad;
}
