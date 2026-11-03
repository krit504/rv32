/* Benign/attack/benign sequence using the author's prior attack taxonomy
 * (TENDRA and the Write Hammer draft). ATTACK_KIND selects the middle phase.
 */
#define ATTACK_NO_MAIN 1
#include "attack_core.h"

#define BENIGN_WORDS 256u
#ifndef BENIGN_ITERATIONS
#define BENIGN_ITERATIONS 100000u
#endif
static volatile uint32_t benign[BENIGN_WORDS];

static void benign_phase(void) {
    for (uint32_t i = 0; i < BENIGN_ITERATIONS; ++i)
        benign[i & (BENIGN_WORDS - 1u)] += 1u;
}

static int check_benign(void) {
    for (uint32_t i = 0; i < BENIGN_WORDS; ++i) {
        uint32_t want = 2u * (BENIGN_ITERATIONS / BENIGN_WORDS +
                              (i < BENIGN_ITERATIONS % BENIGN_WORDS));
        if (benign[i] != want) return (int)i + 1;
    }
    return 0;
}

int main(void) {
    if (data_page_anchor != 1u) return 126;
    perf_start();
    phase(0u);
    benign_phase();
    phase(1u);
    uint32_t rounds = attack_execute();
    phase(2u);
    benign_phase();
    phase(3u);
    perf_stop();
    int err = check_targets(rounds);
    return err ? err : check_benign();
}
