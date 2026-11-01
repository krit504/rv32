/* crt0.S: startup for the bare-metal flow (T1.4). Only RV32I base instructions.
 *   1. set sp to the top of memory
 *   2. zero .bss (the simulation memories start zeroed; this keeps the code correct on dirty memory)
 *   3. call main
 *   4. write main's return value to the HALT MMIO register (0xF0000000), then spin
 */
    .section .text.init, "ax"
    .globl  _start
_start:
    la      sp, __stack_top

    la      t0, __bss_start
    la      t1, __bss_end
1:  bgeu    t0, t1, 2f
    sw      zero, 0(t0)
    addi    t0, t0, 4
    j       1b
2:
    call    main

    lui     t0, 0xF0000          /* MMIO base */
    sw      a0, 0(t0)            /* HALT with main's return value as the exit code */
3:  j       3b
