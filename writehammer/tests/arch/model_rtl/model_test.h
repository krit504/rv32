/* tests/arch/model_rtl/model_test.h: riscv-arch-test model header for the RTL. Halts through the MMIO HALT register
 * (0xF0000000). Same instruction count as tests/arch/model_spike/model_test.h so both ELFs have the same
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

/* 5 instructions, same as tests/arch/model_spike/model_test.h: lui, sw (exit code 0 in x0), nop, nop, j.
 * The MMIO HALT register is at 0xF0000000 (tb/sys_monitor.sv). */
#define RVMODEL_HALT                                                    \
    lui  t0, 0xF0000;                                                   \
    sw   x0, 0(t0);                                                     \
    nop;                                                                \
    nop;                                                                \
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
