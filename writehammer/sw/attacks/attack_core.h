/* Write Hammer attack kernels. Taxonomy: author's TENDRA and Write Hammer work.
 * See docs/logs/T4.2.md for the paper definitions and their D$ translation.
 */
#ifndef WH_ATTACK_CORE_H
#define WH_ATTACK_CORE_H
#include <stdint.h>
#include "../mmio.h"
#include "lfsr.h"

#ifndef ATTACK_KIND
#error ATTACK_KIND is required (1 RLA, 2 RTA, 3 RnLA, 4 RnTA)
#endif
#if ATTACK_LOCATIONS < 1 || ATTACK_LINE_BYTES < 4
#error invalid attack geometry
#endif
#if (ATTACK_DCACHE_BYTES % ATTACK_LINE_BYTES) != 0
#error cache geometry is not line aligned
#endif
#if ATTACK_KIND == 2 && ATTACK_LOCATIONS < 2
#error RTA needs two targets
#endif
#if ATTACK_KIND == 4 && ATTACK_LOCATIONS < 3
#error RnTA needs at least three possible targets
#endif

#if ATTACK_FORM_DIRECT
#define ATTACK_WORDS_PER_TARGET (ATTACK_LINE_BYTES / 4)
#else
/* Each target array exceeds the D$ by one line, forcing dirty evictions. */
#define ATTACK_WORDS_PER_TARGET ((ATTACK_DCACHE_BYTES + ATTACK_LINE_BYTES) / 4)
#endif

/* The loop count uses measured cycles per store in the frozen RTL. It does not
 * read time or feed timing into the computed result. A later RTL change needs
 * recalibration, along with the T3.4 wear baseline. */
#if ATTACK_KIND == 1
#define ATTACK_CYCLES_PER_STORE (ATTACK_FORM_DIRECT ? 7u : 9u)
#elif ATTACK_KIND == 2
#define ATTACK_CYCLES_PER_STORE (ATTACK_FORM_DIRECT ? 26u : 21u)
#else
#define ATTACK_CYCLES_PER_STORE (ATTACK_FORM_DIRECT ? 12u : 17u)
#endif
#if ATTACK_FORM_DIRECT
#define ATTACK_MAX_STORES (ATTACK_RUN_CYCLES / ATTACK_CYCLES_PER_STORE)
#else
#define ATTACK_MAX_STORES (ATTACK_RUN_CYCLES / (ATTACK_CYCLES_PER_STORE * ATTACK_WORDS_PER_TARGET))
#endif
static volatile uint32_t target[ATTACK_LOCATIONS][ATTACK_WORDS_PER_TARGET]
    __attribute__((aligned(ATTACK_LINE_BYTES)));
/* Keep a live .data item so the linker places .bss on a separate data page. */
static volatile uint32_t data_page_anchor = 1u;

static uint32_t next_dwell(uint32_t *rng) {
    uint32_t span = ATTACK_DWELL_MAX - ATTACK_DWELL_MIN + 1u;
    *rng = attack_lfsr_step(*rng);
    return ATTACK_DWELL_MIN + (*rng % span);
}

static uint32_t next_target(uint32_t *rng, uint32_t old) {
    uint32_t n;
    do {
        *rng = attack_lfsr_step(*rng);
        n = *rng % ATTACK_LOCATIONS;
    } while (n == old);
    return n;
}

static void write_target(uint32_t loc, uint32_t round) {
#if ATTACK_FORM_DIRECT
    (void)round;
    target[loc][0] += 1u;
#else
    /* A whole array sweep reproduces the paper's fill/write-back mechanism. */
    for (uint32_t i = 0; i < ATTACK_WORDS_PER_TARGET; ++i)
        target[loc][i] += 1u;
#endif
}

static int check_targets(uint32_t rounds) {
    uint32_t total = 0u;
    for (uint32_t loc = 0; loc < ATTACK_LOCATIONS; ++loc) {
        uint32_t value = target[loc][0];
        total += value;
#if !ATTACK_FORM_DIRECT
        for (uint32_t i = 0; i < ATTACK_WORDS_PER_TARGET; ++i)
            if (target[loc][i] != value) return (int)loc + 1;
#endif
    }
    return total == rounds ? 0 : 127;
}

int main(void) {
    if (data_page_anchor != 1u) return 126;
    uint32_t rng = attack_lfsr_seed(ATTACK_SEED);
    uint32_t first = 0u, second = 1u;
    uint32_t active = first;
    uint32_t dwell = next_dwell(&rng);
    uint32_t rounds = 0u;
    phase(1u);
    perf_start();
    while (rounds < ATTACK_MAX_STORES) {
        write_target(active, rounds);
        ++rounds;
        if (--dwell != 0u) continue;
#if ATTACK_KIND == 1
        /* RLA repeats its fixed array. Multiple locations are a fixed set. */
        active = (active + 1u) % ATTACK_LOCATIONS;
#elif ATTACK_KIND == 2
        /* RTA toggles between its two fixed locations. */
        active = active == first ? second : first;
#elif ATTACK_KIND == 3
        /* RnLA chooses a new single target and a new dwell time. */
        active = next_target(&rng, active);
#else
        /* RnTA toggles within a pair, then chooses a new random pair. */
        if (active == first) active = second;
        else {
            first = next_target(&rng, second);
            second = next_target(&rng, first);
            active = first;
        }
#endif
        dwell = next_dwell(&rng);
    }
    perf_stop();
    phase(2u);
    return check_targets(rounds);
}
#endif
