/* Deterministic 32-bit Galois LFSR for the attack workloads.
 * State is supplied by the caller; zero is normalized to one because an LFSR
 * stays at zero forever. Taps use the reflected mask 0x80200003. This module
 * makes no claim about maximal period. It has no MMIO or platform dependency.
 * The RLA/RTA/RnLA/RnTA taxonomy is prior work of the author's group
 * (TENDRA and the Write Hammer draft); this utility does not define it.
 */
#ifndef WH_ATTACK_LFSR_H
#define WH_ATTACK_LFSR_H

#include <stdint.h>

static inline uint32_t attack_lfsr_seed(uint32_t seed) {
    return seed ? seed : 1u;
}

static inline uint32_t attack_lfsr_step(uint32_t state) {
    return (state >> 1) ^ ((state & 1u) ? 0x80200003u : 0u);
}

#endif
