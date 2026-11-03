/* Known-answer LFSR micro-program. Literal expected states were derived from
 * the tap polynomial by hand; the host and RV32I builds execute the same C.
 * It returns nonzero at the first mismatch, so a broken transition fails.
 * This is a test of the LFSR utility, not an RLA/RTA/RnLA/RnTA attack. Those
 * names come from the author's group (TENDRA and the Write Hammer draft).
 */
#include <stdint.h>
#include "lfsr.h"

static volatile uint32_t test_seed = 1u;  /* prevent a compile-time folded sequence */

int main(void) {
    static const uint32_t expected[] = {
        0x80200003u, 0xc0300002u, 0x60180001u,
        0xb02c0003u, 0xd8360002u, 0x6c1b0001u
    };
    uint32_t state = attack_lfsr_seed(test_seed);
    if (attack_lfsr_seed(0u) != 1u) return 1;
    for (unsigned i = 0; i < sizeof(expected) / sizeof(expected[0]); i++) {
        state = attack_lfsr_step(state);
        if (state != expected[i]) return (int)(i + 2u);
    }
    return 0;
}
