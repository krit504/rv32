/* tests/arch/model_spike/model_test.h: riscv-arch-test model header for Spike (the reference). Halts through HTIF
 * (tohost). Instruction count of RVMODEL_HALT equals tests/arch/model_rtl/model_test.h's so both ELFs have the same
 * layout and the same data addresses; tests/arch_test.py checks the symbol addresses match. */
#ifndef _COMPLIANCE_MODEL_H
#define _COMPLIANCE_MODEL_H
#define ALIGNMENT 2

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                            \
        .align 8; .global tohost; tohost: .dword 0;                     \
        .align 8; .global fromhost; fromhost: .dword 0;                 \
        .popsection;                                                    \
        .align 8; .global begin_regstate; begin_regstate:               \
        .word 128;                                                      \
        .align 8; .global end_regstate; end_regstate:                   \
        .word 4;

/* 5 instructions: lui, addi, li, sw, j (la of a far symbol is forced to lui+addi by %hi/%lo) */
#define RVMODEL_HALT                                                    \
    lui  t0, %hi(tohost);                                               \
    addi t0, t0, %lo(tohost);                                           \
    li   t1, 1;                                                         \
    sw   t1, 0(t0);                                                     \
1:  j    1b;

#define RVMODEL_BOOT
#define RVMODEL_DATA_BEGIN RVMODEL_DATA_SECTION .align ALIGNMENT; .global begin_signature; begin_signature:
#define RVMODEL_DATA_END   .global end_signature; end_signature:
#define RVMODEL_IO_INIT
#define RVMODEL_IO_WRITE_STR(_R, _STR)
#define RVMODEL_IO_CHECK()
#define RVMODEL_IO_ASSERT_GPR_EQ(_S, _R, _I)
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)
#define RVMODEL_SET_MSW_INT
#define RVMODEL_CLEAR_MSW_INT
#define RVMODEL_CLEAR_MTIMER_INT
#define RVMODEL_CLEAR_MEXT_INT
#endif
